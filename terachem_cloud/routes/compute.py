from typing import Optional, Union

from fastapi import APIRouter

from terachem_cloud.config import get_settings
from terachem_cloud.models import (
    AtomicInputOrList,
    FutureResult,
    FutureResultGroup,
    OptimizationInputOrList,
    SupportedEngines,
    SupportedProcedures,
)
from terachem_cloud.task_models import GroupTask, Task

from .helpers import _bytes_to_b64, compute_inputs_async

settings = get_settings()

router = APIRouter()


@router.post(
    "",  # NOTE: "/compute" prefix is prepended in top level main.py file
    # Appears correct: https://fastapi.tiangolo.com/tutorial/extra-models/?h=union#union-or-anyof
    response_model=Union[GroupTask, Task],  # type: ignore
    response_description="Task ID(s) for the requested computation.",
)
async def compute(
    input_data: AtomicInputOrList,
    engine: SupportedEngines,
    queue: Optional[str] = None,
) -> Union[GroupTask, Task]:
    """Submit a computation: AtomicInput (or list) and computation engine."""
    return compute_inputs_async(input_data, engine, queue)


@router.post(
    "-procedure",  # NOTE: "/compute" prefix is prepended in top level main.py file
    # Appears correct: https://fastapi.tiangolo.com/tutorial/extra-models/?h=union#union-or-anyof
    response_model=Union[GroupTask, Task],  # type: ignore
    response_description="Task ID(s) for the requested computation.",
)
async def compute_procedure(
    input_data: OptimizationInputOrList,
    procedure: SupportedProcedures,
    queue: Optional[str] = None,
) -> Union[GroupTask, Task]:
    """Submit a computation: OptimizationInput (or list) and procedure"""
    return compute_inputs_async(input_data, procedure, queue)


@router.post(
    "/result",  # NOTE: "/compute" prefix is prepended in top level main.py file
    # Appears correct: https://fastapi.tiangolo.com/tutorial/extra-models/?h=union#union-or-anyof
    response_model=Union[FutureResultGroup, FutureResult],  # type: ignore
    response_description="A compute task's status and (if complete) return value.",
)
async def result(
    task: Union[GroupTask, Task],
    # background_tasks: BackgroundTasks,
) -> Union[FutureResultGroup, FutureResult]:
    """Retrieve a compute task's status and result (if ready)."""
    # import pdb; pdb.set_trace()
    result = task.to_result()

    # Transform any binary native_files to b64 encoded string
    if result.result:
        _bytes_to_b64(result.result)

        # if result.compute_status in states.READY_STATES:
        # Remove result from backend
        # NOTE: Need to update to use background_task so only executes if task returned
        # successfully.
        # Will only execute if result returned successfully
        # background_tasks.add_task(delete_task, task)
        # TODO: Use background_tasks; currently having issues with AsyncResult.get()
        # being called twice. the .get() call in GroupTask.to_result() hangs forever
        # for reasons I don't fully understand
        task.forget()
    return result


def delete_task(task: Union[Task, GroupTask]) -> None:
    """Delete Celery result(s) from backend"""
    task.forget()
