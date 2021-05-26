import re
from time import sleep

import pytest
from qcelemental.models import AtomicResult, OptimizationResult
from qcelemental.models.procedures import OptimizationInput, QCInputSpecification
from qcelemental.models.results import AtomicInput


def test_compute_requires_auth(settings, client):
    response = client.post(f"{settings.api_v1_str}/compute")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "engine,model,keywords",
    (
        ("psi4", {"method": "HF", "basis": "sto-3g"}, {}),
        ("rdkit", {"method": "UFF"}, {}),
        ("xtb", {"method": "GFN2-xTB"}, {"accuracy": 1.0, "max_iterations": 20}),
    ),
)
@pytest.mark.timeout(45)
def test_compute_and_result(
    settings, client, fake_auth, hydrogen, engine, model, keywords
):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    atomic_input = AtomicInput(
        molecule=hydrogen,
        driver="energy",
        model=model,
        keywords=keywords,
    )
    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute",
        data=atomic_input.json(),
        params={"engine": engine},
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
        sleep(0.2)

    assert status == "SUCCESS"
    assert isinstance(AtomicResult(**result), AtomicResult)

    # Assert result deleted from backend after retrieval
    status, result = _get_result(task_id)
    assert status == "PENDING"
    assert result is None


@pytest.mark.parametrize(
    "optimizer,model,keywords",
    (
        (
            "berny",
            {"method": "HF", "basis": "sto-3g"},
            {"program": "psi4", "maxsteps": 2},
        ),
        (
            "geometric",
            {"method": "HF", "basis": "sto-3g"},
            {"program": "psi4", "maxiter": 2},
        ),
        ("geometric", {"method": "UFF"}, {"program": "rdkit", "maxiter": 2}),
    ),
)
@pytest.mark.timeout(65)
def test_compute_procedure_optimization(
    settings,
    client,
    fake_auth,
    hydrogen,
    optimizer,
    keywords,
    model,
):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    optimization_input = OptimizationInput(
        input_specification=QCInputSpecification(driver="gradient", model=model),
        protocols={"trajectory": "all"},
        initial_molecule=hydrogen,
        keywords=keywords,
    )

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute-procedure",
        data=optimization_input.json(),
        params={"procedure": optimizer},
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
