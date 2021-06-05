from typing import Union

from celery import states
from fastapi import APIRouter

from terachem_cloud.config import get_settings
from terachem_cloud.models import (
    AtomicInputOrList,
    FutureResult,
    FutureResultGroup,
    GroupTask,
    OptimizationInputOrList,
    SupportedEngines,
    SupportedProcedures,
    Task,
)
from terachem_cloud.workers.tasks import compute as compute_task
from terachem_cloud.workers.tasks import compute_procedure as compute_procedure_task

from .helpers import compute_inputs_async

settings = get_settings()


router = APIRouter()


@router.post(
    "",  # NOTE: "/compute" prefix is prepended in top level main.py file
    # Appears correct: https://fastapi.tiangolo.com/tutorial/extra-models/?h=union#union-or-anyof
    response_model=Union[GroupTask, Task],  # type: ignore
    response_description="Task ID(s) for the requested computation.",
)
async def compute(
    input_data: AtomicInputOrList, engine: SupportedEngines
) -> Union[GroupTask, Task]:
    """Submit a computation: AtomicInput (or list) and computation engine."""
    return compute_inputs_async(input_data, engine, compute_task)


@router.post(
    "-procedure",  # NOTE: "/compute" prefix is prepended in top level main.py file
    # Appears correct: https://fastapi.tiangolo.com/tutorial/extra-models/?h=union#union-or-anyof
    response_model=Union[GroupTask, Task],  # type: ignore
    response_description="Task ID(s) for the requested computation.",
)
async def compute_procedure(
    input_data: OptimizationInputOrList,
    procedure: SupportedProcedures,
) -> Union[GroupTask, Task]:
    """Submit a computation: OptimizationInput (or list) and procedure"""
    return compute_inputs_async(input_data, procedure, compute_procedure_task)


@router.post(
    "/result",  # NOTE: "/compute" prefix is prepended in top level main.py file
    # Appears correct: https://fastapi.tiangolo.com/tutorial/extra-models/?h=union#union-or-anyof
    response_model=Union[FutureResultGroup, FutureResult],  # type: ignore
    response_description="A compute task's status and (if complete) return value.",
)
async def result(
    task: Union[GroupTask, Task]
) -> Union[FutureResultGroup, FutureResult]:
    """Retrieve a compute task's status and result (if ready)."""
    result = task.to_result()
    if result.compute_status in states.READY_STATES:
        # Remove result from backend
        task.forget()
    return result
