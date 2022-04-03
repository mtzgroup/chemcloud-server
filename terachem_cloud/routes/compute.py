from typing import Optional, Type, Union

from celery.result import AsyncResult
from fastapi import APIRouter, BackgroundTasks, HTTPException, Path

from terachem_cloud.config import get_settings
from terachem_cloud.models import (
    AtomicInputOrList,
    OptimizationInputOrList,
    Result,
    ResultGroup,
    SupportedEngines,
    SupportedProcedures,
    TaskState,
)

from .helpers import _bytes_to_b64, compute_inputs_async, delete_result, restore_result

settings = get_settings()

router = APIRouter()


@router.post(
    "",  # NOTE: "/compute" prefix is prepended in top level main.py file
    # Appears correct: https://fastapi.tiangolo.com/tutorial/extra-models/?h=union#union-or-anyof
    response_description="Task ID for the requested computation.",
)
async def compute(
    input_data: AtomicInputOrList,
    engine: SupportedEngines,
    queue: Optional[str] = None,
) -> str:
    """Submit a computation: AtomicInput (or list) and computation engine."""
    return compute_inputs_async(input_data, engine, queue)


@router.post(
    "-procedure",  # NOTE: "/compute" prefix is prepended in top level main.py file
    response_description="Task ID for the requested computation.",
)
async def compute_procedure(
    input_data: OptimizationInputOrList,
    procedure: SupportedProcedures,
    queue: Optional[str] = None,
) -> str:
    """Submit a computation: OptimizationInput (or list) and procedure"""
    return compute_inputs_async(input_data, procedure, queue)


@router.get(
    "/result/{result_id}",  # NOTE: "/compute" prefix is prepended in top level main.py file
    response_model=Union[ResultGroup, Result],  # type: ignore
    response_description="A compute task's status and (if complete) return value.",
)
async def result(
    background_tasks: BackgroundTasks,
    result_id: str = Path(
        ...,
        title="The ID of the result to get",
        regex=r"[0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12}",
    ),
) -> Union[ResultGroup, Result]:
    """Retrieve a result's status and (if complete) output."""
    try:
        result = restore_result(result_id)
    except ValueError:
        raise HTTPException(
            status_code=410, detail="Result has already been deleted from server"
        )

    state = TaskState.PENDING
    data = None

    if result.ready():
        state = TaskState.COMPLETE
        data = result.get()
        # Transform any binary native_files and .extras to b64 encoded string
        _bytes_to_b64(data)
        # Remove result from backend AFTER function returns successfully
        background_tasks.add_task(delete_result, result)

    fr_model: Union[Type[Result], Type[ResultGroup]] = (
        Result if isinstance(result, AsyncResult) else ResultGroup
    )
    return fr_model(state=state, result=data)
