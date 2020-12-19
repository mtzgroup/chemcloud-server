import qcengine as qcng
from celery import Celery
from kombu.serialization import register
from qcelemental.models import AtomicInput, AtomicResult
from qcelemental.util.serialization import json_dumps, json_loads

from .config import get_settings

settings = get_settings()

celery_app = Celery(
    # Name of current module is first argument
    # https://docs.celeryproject.org/en/stable/getting-started/first-steps-with-celery.html#application
    "tasks",
    broker=settings.celery_broker_connection_string,
    backend=settings.celery_backend_connection_string,
)

# To serialize the more complex AtomicInput and AtomicResult data structure from QCElemental
register(
    "qceljson",
    json_dumps,
    json_loads,
    content_type="application/x-qceljson",
    content_encoding="utf-8",
)

celery_app.conf.update(
    task_serializer="qceljson",
    accept_content=["qceljson"],
    result_serializer="qceljson",
    task_track_started=True,
    # Cause workers to only receive and work on one task at a time (no prefetching of messages)
    # https://docs.celeryproject.org/en/stable/userguide/optimizing.html#prefetch-limits
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Only one concurrent worker process. One process may use multiple CPU cores anyways.
    worker_concurrency=1,
)


@celery_app.task
def compute(atomic_input: AtomicInput, engine: str) -> AtomicResult:
    return qcng.compute(atomic_input, engine)


@celery_app.task
def add(x, y):
    return x + y
