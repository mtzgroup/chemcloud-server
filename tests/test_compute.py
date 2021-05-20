import re
from time import sleep

import pytest
from qcelemental.models import AtomicResult, OptimizationResult


def test_compute_requires_auth(settings, client):
    response = client.post(f"{settings.api_v1_str}/compute")
    assert response.status_code == 401


@pytest.mark.timeout(45)
def test_compute_and_result(settings, client, fake_auth, atomic_input):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute",
        data=atomic_input.json(),
        params={"engine": "psi4"},
    )
    task_id = job_submission.json()

    # Test returned values
    assert isinstance(task_id, str)
    # returned value matches celery task_id
    assert (
        re.match(
            "^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$", task_id
        )
        is not None
    )

    # Check Status upon submission
    def _get_result(task_id):
        result = client.get(
            f"{settings.api_v1_str}/compute/result/{task_id}",
        )
        response = result.json()
        return response["status"], response["result"]

    status, result = _get_result(task_id)

    assert status == "PENDING" or status == "STARTED"
    # No result while computation is happening
    assert result is None

    # Check that work gets done, AtomicResult-compatible data is returned
    while status in {"PENDING", "STARTED"}:
        status, result = _get_result(task_id)
        sleep(1)

    assert status == "SUCCESS"
    assert isinstance(AtomicResult(**result), AtomicResult)

    # Assert result deleted from backend after retrieval
    status, result = _get_result(task_id)
    assert status == "PENDING"
    assert result is None


@pytest.mark.timeout(45)
def test_compute_procedure_berny(settings, client, fake_auth, optimization_input):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute-procedure",
        data=optimization_input.json(),
        params={"procedure": "berny"},
    )
    task_id = job_submission.json()

    # Test returned values
    assert isinstance(task_id, str)
    # returned value matches celery task_id
    assert (
        re.match(
            "^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$", task_id
        )
        is not None
    )

    # Check Status upon submission
    def _get_result(task_id):
        result = client.get(
            f"{settings.api_v1_str}/compute/result/{task_id}",
        )
        response = result.json()
        return response["status"], response["result"]

    status, result = _get_result(task_id)

    assert status == "PENDING" or status == "STARTED"
    # No result while computation is happening
    assert result is None

    # Check that work gets done, AtomicResult-compatible data is returned
    while status in {"PENDING", "STARTED"}:
        status, result = _get_result(task_id)
        sleep(1)

    assert status == "SUCCESS"
    assert isinstance(OptimizationResult(**result), OptimizationResult)

    # Assert result deleted from backend after retrieval
    status, result = _get_result(task_id)
    assert status == "PENDING"
    assert result is None
