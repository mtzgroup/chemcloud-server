import re
from enum import Enum

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from fastapi import status as status_codes
from qcelemental.models import AtomicInput

from terachem_cloud.models import CeleryAtomicResult
from terachem_cloud.workers.tasks import celery_app
from terachem_cloud.workers.tasks import compute as compute_task


class SupportedEngines(str, Enum):
    """Compute engines currently supported by TeraChem Cloud"""

    PSI4 = "psi4"


router = APIRouter()


@router.post("", response_model=str)
async def compute(atomic_input: AtomicInput, engine: SupportedEngines) -> str:
    """Submit a computation using an
    [AtomicInput](http://docs.qcarchive.molssi.org/projects/QCEngine/en/stable/single_compute.html)
    object and a desired computation engine"""
    # TODO: Create custom task_id enabling caching. Will need to update task_id validation in /result.
    # https://docs.celeryproject.org/en/latest/faq.html#can-i-specify-a-custom-task-id
    # http://docs.qcarchive.molssi.org/projects/QCFractal/en/stable/results.html#results
    task = compute_task.delay(atomic_input, engine)
    return task.id


@router.get("/result/{task_id}", response_model=CeleryAtomicResult)
async def result(task_id: str):
    """Retrieve a compute task's status and an
    [AtomicResult](http://docs.qcarchive.molssi.org/projects/QCEngine/en/stable/single_compute.html#returned-fields)
    object from a computation.
    """
    # Notify user if task_id doesn't match celery naming convention
    if not re.match(
        "^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$", task_id
    ):
        raise HTTPException(
            status_code=status_codes.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid task_id",
        )

    celery_task = AsyncResult(task_id, app=celery_app)
    status = celery_task.status
    if status == "SUCCESS":
        atomic_result = celery_task.get()
    else:
        atomic_result = None

    return {"status": status, "atomic_result": atomic_result}
