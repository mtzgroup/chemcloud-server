import pytest
from fastapi import status as status_codes
from qcelemental.models.procedures import OptimizationInput, QCInputSpecification
from qcelemental.models.results import AtomicInput
from qcelemental.util.serialization import json_dumps

from tests.utils import _make_job_completion_assertions


def test_compute_requires_auth(settings, client):
    response = client.post(f"{settings.api_v1_str}/compute")
    assert response.status_code == status_codes.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "engine,model,keywords,group",
    (
        ("psi4", {"method": "HF", "basis": "sto-3g"}, {}, False),
        ("rdkit", {"method": "UFF"}, {}, False),
        ("xtb", {"method": "GFN2-xTB"}, {"accuracy": 1.0, "max_iterations": 20}, False),
        ("xtb", {"method": "GFN2-xTB"}, {"accuracy": 1.0, "max_iterations": 20}, True),
    ),
)
@pytest.mark.timeout(65)
def test_compute(settings, client, fake_auth, hydrogen, engine, model, keywords, group):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    atomic_input = AtomicInput(
        molecule=hydrogen, driver="energy", model=model, keywords=keywords
    )
    if group:
        # Make list of inputs
        atomic_input = [atomic_input, atomic_input]

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute",
        data=json_dumps(atomic_input),
        params={"engine": engine},
    )
    as_dict = job_submission.json()

    _make_job_completion_assertions(as_dict, client, settings)


@pytest.mark.timeout(15)
def test_compute_private_queue(settings, client, fake_auth, hydrogen):
    """Test private queue computing"""
    atomic_input = AtomicInput(
        molecule=hydrogen,
        driver="energy",
        model={"method": "GFN2-xTB"},
        keywords={"accuracy": 1.0, "max_iterations": 20},
    )

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute",
        data=json_dumps(atomic_input),
        params={"engine": "xtb", "queue": "private_queue"},
    )
    as_dict = job_submission.json()

    _make_job_completion_assertions(as_dict, client, settings)


@pytest.mark.timeout(20)
def test_compute_procedure_optimization_private_queue(
    settings,
    client,
    fake_auth,
    hydrogen,
):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    optimization_input = OptimizationInput(
        input_specification=QCInputSpecification(
            model={"method": "GFN2-xTB"},
            keywords={"accuracy": 1.0, "max_iterations": 20},
        ),
        initial_molecule=hydrogen,
        keywords={"program": "xtb", "maxsteps": 2},
    )

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute-procedure",
        data=json_dumps(optimization_input),
        params={"procedure": "berny", "queue": "private_queue"},
    )
    as_dict = job_submission.json()
    _make_job_completion_assertions(as_dict, client, settings)


@pytest.mark.parametrize(
    "optimizer,model,keywords,group",
    (
        (
            "berny",
            {"method": "HF", "basis": "sto-3g"},
            {"program": "psi4", "maxsteps": 2},
            False,
        ),
        (
            "geometric",
            {"method": "HF", "basis": "sto-3g"},
            {"program": "psi4", "maxiter": 2},
            False,
        ),
        ("geometric", {"method": "UFF"}, {"program": "rdkit", "maxiter": 2}, False),
        ("geometric", {"method": "UFF"}, {"program": "rdkit", "maxiter": 2}, True),
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
    group,
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
    if group:
        optimization_input = [optimization_input, optimization_input]

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute-procedure",
        data=json_dumps(optimization_input),
        params={"procedure": optimizer},
    )
    as_dict = job_submission.json()
    _make_job_completion_assertions(as_dict, client, settings)


def test_compute_group_limits(
    settings,
    client,
    fake_auth,
    hydrogen,
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
        model={"method": "HF", "basis": "sto-3g"},
    )
    too_big_list = [atomic_input] * (settings.max_batch_inputs + 1)

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute",
        data=json_dumps(too_big_list),
        params={"engine": "psi4"},
    )

    assert job_submission.status_code == status_codes.HTTP_413_REQUEST_ENTITY_TOO_LARGE


def test_compute_procedure_group_limits(
    settings,
    client,
    fake_auth,
    hydrogen,
):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    optimization_input = OptimizationInput(
        input_specification=QCInputSpecification(
            driver="gradient", model={"method": "GFN2-xTB"}
        ),
        protocols={"trajectory": "all"},
        initial_molecule=hydrogen,
    )

    too_big_list = [optimization_input] * (settings.max_batch_inputs + 1)

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute-procedure",
        data=json_dumps(too_big_list),
        params={"procedure": "geometric"},
    )

    assert job_submission.status_code == status_codes.HTTP_413_REQUEST_ENTITY_TOO_LARGE
