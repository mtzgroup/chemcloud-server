from typing import Optional

from bigchem.canvas import group
from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query
from fastapi import status as status_codes
from qcop.exceptions import QCOPBaseError

from chemcloud_server.config import get_settings
from chemcloud_server.exceptions import ResultNotFoundError
from chemcloud_server.models import (
    Output,
    QCIOInputsOrList,
    SupportedPrograms,
    TaskState,
)

from .helpers import delete_result, restore_result, save_dag, signature_from_input

settings = get_settings()

router = APIRouter()


@router.post(
    "",  # NOTE: "/compute" prefix is prepended in top level main.py file
    # Appears correct: https://fastapi.tiangolo.com/tutorial/extra-models/?h=union#union-or-anyof
    response_description="Task ID for the requested computation.",
)
async def compute(
    background_tasks: BackgroundTasks,
    program: SupportedPrograms,
    inp_obj: QCIOInputsOrList,
    collect_stdout: bool = Query(
        True, description="Collect stdout from the computation."
    ),
    collect_files: bool = Query(
        False, description="Collect all files generated by the QC program as output."
    ),
    collect_wfn: bool = Query(
        False, description="Collect the wavefunction file(s) from the scratch_dir."
    ),
    rm_scratch_dir: bool = Query(
        True, description="Remove scratch directory after a computation completes."
    ),
    propagate_wfn: bool = Query(
        False,
        description=(
            "For any adapter performing a sequential task, such as a geometry "
            "optimization, propagate the wavefunction from the previous step to the "
            "next step. This is useful for accelerating convergence by using a "
            "previously computed wavefunction as a starting guess. This will be "
            "ignored if the adapter does not support it."
        ),
    ),
    queue: Optional[str] = None,
) -> str:
    """Submit a computation: ProgramInput, DualProgramInput (or list) and computation
    program."""
    compute_kwargs = dict(  # kwargs for qcio.compute function
        collect_stdout=collect_stdout,
        collect_files=collect_files,
        collect_wfn=collect_wfn,
        rm_scratch_dir=rm_scratch_dir,
        propagate_wfn=propagate_wfn,
    )

    if isinstance(inp_obj, list):  # Probably a more FastAPI way to do this exists
        if len(inp_obj) > settings.max_batch_inputs:  # Check for too many inputs
            raise HTTPException(
                status_code=status_codes.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Cannot submit more than {settings.max_batch_inputs} inputs "
                    "at once"
                ),
            )
        future_res = group(
            signature_from_input(program, inp, compute_kwargs) for inp in inp_obj
        ).apply_async(queue=queue)

    else:
        future_res = signature_from_input(program, inp_obj, compute_kwargs).apply_async(
            queue=queue
        )

    # Save result structure to DB so can be rehydrated using only id
    background_tasks.add_task(save_dag, future_res)
    return future_res.id


@router.get(
    # NOTE: "/compute" prefix is prepended in top level main.py file
    "/output/{task_id}",
    response_model=Output,  # type: ignore
    response_description="A compute task's status and (if complete) return value.",
)
async def result(
    background_tasks: BackgroundTasks,
    task_id: str = Path(
        ...,
        title="The task id to query.",
        pattern=r"[0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12}",
    ),
) -> Output:
    """Retrieve a task's status and output (if complete)."""
    # Check for result in backend
    try:
        future_res = restore_result(task_id)
    except ResultNotFoundError:  # Result already deleted from backend
        raise HTTPException(
            status_code=410, detail="Result has already been deleted from server"
        )
    if future_res.ready():
        task_status = (
            TaskState.SUCCESS if future_res.successful() else TaskState.FAILURE
        )
        prog_output = []
        # Get list of AsyncResult objects or single AsyncResult object in a list
        frs = getattr(future_res, "results", [future_res])
        for fr in frs:
            try:
                prog_output.append(fr.get())
            except QCOPBaseError as e:
                prog_output.append(e.program_output)
        # If only one result, return it directly instead of a list
        prog_output = prog_output[0] if len(prog_output) == 1 else prog_output
        # Remove result from backend AFTER function returns successfully
        background_tasks.add_task(delete_result, future_res)

    else:
        task_status = TaskState.PENDING
        prog_output = None
    return Output(state=task_status, result=prog_output)
