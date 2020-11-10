from os import environ

import qcengine as qcng
from celery import Celery
from kombu.serialization import register
from qcelemental.models import AtomicInput, AtomicResult
from qcelemental.util.serialization import json_dumps, json_loads

celery_app = Celery(
    # Name of current module is first argument
    # https://docs.celeryproject.org/en/stable/getting-started/first-steps-with-celery.html#application
    "tasks",
    # broker example: "amqps://admin123:supersecret987@mq-connect.dev.mtzlab.com:5671",
    broker=environ.get("CELERY_BROKER_CONNECTION_STRING", "amqp://localhost"),
    # backend example: "rediss://:password123@redis.dev.mtzlab.com:6379/0?ssl_cert_reqs=CERT_NONE"
    backend=environ.get("CELERY_BACKEND_CONNECTION_STRING", "redis://localhost/0"),
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
