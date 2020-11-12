import re
from enum import Enum
from typing import Optional

from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException
from qcelemental.models.results import AtomicInput, AtomicResult

from .tasks import celery_app
from .tasks import compute as compute_task


class SupportedEngines(Enum):
    """Compute engines currently supported by TeraChem Cloud"""

    PSI4 = "psi4"


app = FastAPI()


@app.get("/")
def hello_world():
    """A test endpoint to make sure the app is working"""
    return {"Hello": "World"}


@app.post("/compute")
def compute(atomic_input: AtomicInput, engine: SupportedEngines) -> str:
    """Endpoint to submit a computation"""
    # TODO: Create custom task_id enabling caching. Will need to update task_id validation in /result.
    # https://docs.celeryproject.org/en/latest/faq.html#can-i-specify-a-custom-task-id
    # http://docs.qcarchive.molssi.org/projects/QCFractal/en/stable/results.html#results
    task = compute_task.delay(atomic_input, engine)
    return task.id


@app.get("/result")
def result(task_id: str) -> tuple[str, Optional[AtomicResult]]:  # type: ignore
    """Get a result back from a computation"""
    # Notify user if task_id doesn't match celery naming convention
    if not re.match(
        "^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$", task_id
    ):
        raise HTTPException(status_code=422, detail="Invalid task_id")

    celery_task = AsyncResult(task_id, app=celery_app)
    status = celery_task.status
    if status == "SUCCESS":
        result = AtomicResult(**celery_task.get())
    else:
        result = None
    return (status, result)
