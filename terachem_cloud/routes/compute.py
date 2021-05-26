import re
from enum import Enum

from celery import states
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from fastapi import status as status_codes
from qcelemental.models import AtomicInput, OptimizationInput

from terachem_cloud.models import TaskResult
from terachem_cloud.workers.tasks import celery_app
from terachem_cloud.workers.tasks import compute as compute_task
from terachem_cloud.workers.tasks import compute_procedure as compute_procedure_task


class SupportedEngines(str, Enum):
    """Compute engines currently supported by TeraChem Cloud"""

    PSI4 = "psi4"
    TERACHEM_PBS = "terachem_pbs"
    RDKIT = "rdkit"
    XTB = "xtb"


class SupportedProcedures(str, Enum):
    """Procedures currently supported by TeraChem Cloud"""

    BERNY = "berny"
    GEOMETRIC = "geometric"


router = APIRouter()


@router.post(
    "",  # NOTE: "/compute" prefix is prepended in top level main.py file
    response_model=str,
    response_description="Task ID for the requested computation.",
)
async def compute(atomic_input: AtomicInput, engine: SupportedEngines) -> str:
    """Submit a computation using an AtomicInput object and a desired computation engine"""
    # TODO: Create custom task_id enabling caching. Will need to update task_id validation in /result.
    # https://docs.celeryproject.org/en/latest/faq.html#can-i-specify-a-custom-task-id
    # http://docs.qcarchive.molssi.org/projects/QCFractal/en/stable/results.html#results
    task = compute_task.delay(atomic_input, engine)
    return task.id


@router.post(
    "-procedure",
    response_model=str,
    response_description="Task ID for the requested computation.",
)
async def compute_procedure(
    input: OptimizationInput, procedure: SupportedProcedures
) -> str:
    """Submit a procedure computation using an OptimizationInput specification"""
    task = compute_procedure_task.delay(input, procedure)
    return task.id


@router.get(
    "/result/{task_id}",  # NOTE: "/compute" prefix is prepended in top level main.py file
    response_model=TaskResult,
    response_description="A compute task's status and (if complete) return value.",
)
async def result(task_id: str):
    """Retrieve a compute task's status and result. Returns TaskResult."""
    # Notify user if task_id doesn't match celery naming convention
    if not re.match(
        "^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$", task_id
    ):
        raise HTTPException(
            status_code=status_codes.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid task_id",
        )

    celery_task = AsyncResult(task_id, app=celery_app)
    status = celery_task.state
    if status == states.SUCCESS:
        # Should indicate that result is either AtomicResult or FailedOperation

        # Calling .get() due to message re: backend resources. Not totally clear why
        # this call must be made instead of celery_task.result but going on faith for now
        # https://docs.celeryproject.org/en/stable/reference/celery.result.html#celery.result.AsyncResult.get
        result = celery_task.get()
        # Appears .get() does not remove result from Redis, so calling .forget() to
        # specifically remove result. Don't want Redis to hold results in memory after
        # retrieval and become a memory hog.
        celery_task.forget()
        # Since I am currently swallowing exceptions in the qcengine layer using
        # qcengine.compute(..., raise_error=False), Celery will report a "success"
        # since Celery didn't handle any exceptions when indeed the compute task
        # failed. This is because compute() will swallow exceptions and return a
        # FailedOperation object instead. Hence I am relying upon compute()'s status
        # reporting and passing along this value to the end users.
        if result.get("success") is not True:
            status = states.FAILURE
    else:
        result = None

    return {"status": status, "result": result}
