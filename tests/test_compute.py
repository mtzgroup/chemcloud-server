import json
from time import sleep

import pytest
from celery.states import READY_STATES
from fastapi import status as status_codes
from httpx import HTTPStatusError
from qcio import DualProgramInput, ProgramInput

from chemcloud_server.models import TaskState
from tests.utils import _get_result, _make_job_completion_assertions

from .utils import json_dumps


def test_compute_requires_auth(settings, client):
    response = client.post(f"{settings.api_v2_str}/compute")
    assert response.status_code == status_codes.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "program,model,keywords,group",
    (
        ("psi4", {"method": "HF", "basis": "sto-3g"}, {}, False),
        ("rdkit", {"method": "UFF"}, {}, False),
        ("xtb", {"method": "GFN2xTB"}, {"accuracy": 1.0, "max_iterations": 20}, False),
        ("xtb", {"method": "GFN2xTB"}, {"accuracy": 1.0, "max_iterations": 20}, True),
    ),
)
@pytest.mark.timeout(65)
def test_compute(
    settings, client, fake_auth, hydrogen, program, model, keywords, group
):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    prog_inp = ProgramInput(
        molecule=hydrogen, calctype="energy", model=model, keywords=keywords
    )
    if group:
        # Make list of inputs
        prog_inp = [prog_inp, prog_inp]

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v2_str}/compute",
        data=json_dumps(prog_inp),
        params={"program": program},
    )
    as_dict = job_submission.json()

    _make_job_completion_assertions(as_dict, client, settings)


@pytest.mark.timeout(15)
def test_compute_with_binary_extras(settings, client, fake_auth, hydrogen):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    invalid_utf8_bytes = b"\xC0\xBF\xC0\xBF\xC0\xBF\xC0\xBF\xC0\xBF"
    prog_inp = ProgramInput(
        molecule=hydrogen,
        calctype="energy",
        model={"method": "HF", "basis": "sto-3g"},
        files={"binary_input": invalid_utf8_bytes},
    )

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v2_str}/compute",
        data=json_dumps(prog_inp),
        params={"program": "psi4"},
    )
    as_dict = job_submission.json()

    _make_job_completion_assertions(as_dict, client, settings)


@pytest.mark.timeout(15)
def test_compute_private_queue(settings, client, fake_auth, hydrogen):
    """Test private queue computing"""
    atomic_input = ProgramInput(
        molecule=hydrogen,
        calctype="energy",
        model={"method": "GFN2xTB"},
        keywords={"accuracy": 1.0, "max_iterations": 20},
    )

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v2_str}/compute",
        data=json_dumps(atomic_input),
        params={"program": "xtb", "queue": "private_queue"},
    )
    as_dict = job_submission.json()

    _make_job_completion_assertions(as_dict, client, settings)


@pytest.mark.timeout(20)
def test_compute_optimization_private_queue(
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
    optimization_input = DualProgramInput(
        calctype="optimization",
        molecule=hydrogen,
        keywords={"maxsteps": 2},
        subprogram="xtb",
        subprogram_args={
            "model": {"method": "GFN2xTB"},
        },
    )

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v2_str}/compute",
        data=json_dumps(optimization_input),
        params={"program": "geometric", "queue": "private_queue"},
    )
    as_dict = job_submission.json()
    _make_job_completion_assertions(as_dict, client, settings)


@pytest.mark.parametrize(
    "program,keywords,subprogram,model,group",
    (
        (
            "geometric",
            {"maxiter": 2},
            "psi4",
            {"method": "HF", "basis": "sto-3g"},
            False,
        ),
        (
            "geometric",
            {"maxiter": 2},
            "psi4",
            {"method": "HF", "basis": "sto-3g"},
            False,
        ),
        ("geometric", {"maxiter": 2}, "rdkit", {"method": "UFF"}, False),
        ("geometric", {"maxiter": 2}, "rdkit", {"method": "UFF"}, True),
    ),
)
@pytest.mark.timeout(65)
def test_compute_optimization(
    settings,
    client,
    fake_auth,
    hydrogen,
    program,
    keywords,
    subprogram,
    model,
    group,
):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    optimization_input = DualProgramInput(
        calctype="optimization",
        molecule=hydrogen,
        keywords=keywords,
        subprogram=subprogram,
        subprogram_args={"model": model},
    )
    if group:
        optimization_input = [optimization_input, optimization_input]

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v2_str}/compute",
        data=json_dumps(optimization_input),
        params={"program": program},
    )
    as_dict = job_submission.json()
    _make_job_completion_assertions(as_dict, client, settings)


def test_compute_group_limits(settings, client, fake_auth, hydrogen, program_input):
    """Testings as one function so we don't submit excess compute jobs.

    Timeout is long because the worker instance may be waiting to connect to
    RabbitMQ if it just started up. Celery's exponential backoff means that
    it's possible a few early misses on worker -> MQ connection results in the
    worker waiting up for 8 seconds (or longer) to retry connecting.
    """
    too_big_list = [program_input] * (settings.max_batch_inputs + 1)

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v2_str}/compute",
        data=json.dumps([inp.model_dump() for inp in too_big_list]),
        params={"program": "psi4"},
    )
    assert job_submission.status_code == status_codes.HTTP_413_REQUEST_ENTITY_TOO_LARGE


@pytest.mark.parametrize(
    "calctype,keywords,subprogram,model,group",
    (
        (
            "hessian",
            {},
            "rdkit",
            {"method": "UFF"},
            False,
        ),
        (
            "hessian",
            {},
            "rdkit",
            {"method": "UFF"},
            True,
        ),
        (
            "hessian",
            {"temperature": 310, "pressure": 1.2},
            "rdkit",
            {"method": "UFF"},
            False,
        ),
    ),
)
@pytest.mark.timeout(450)
def test_compute_bigchem_program(
    settings, client, fake_auth, water, calctype, keywords, subprogram, model, group
):
    """Test BigChem algorithms."""
    prog_input = DualProgramInput(
        molecule=water,
        calctype=calctype,
        keywords=keywords,
        subprogram=subprogram,
        subprogram_args={"model": model},
    )
    if group:
        prog_input = [prog_input, prog_input]

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v2_str}/compute",
        data=json_dumps(prog_input),
        params={"program": "bigchem"},
    )
    as_dict = job_submission.json()

    _make_job_completion_assertions(as_dict, client, settings)


def test_compute_failed_and_successful_results_in_group(
    settings, client, fake_auth, hydrogen
):
    """Test submitting a group of jobs with one failing and one succeeding."""
    prog_input = ProgramInput(
        molecule=hydrogen,
        calctype="energy",
        model={"method": "HF", "basis": "sto-3g"},
    )
    prog_input_fail = ProgramInput(
        molecule=hydrogen,
        calctype="energy",
        model={"method": "HF", "basis": "bad-basis"},
    )

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v2_str}/compute",
        data=json_dumps([prog_input, prog_input_fail]),
        params={"program": "psi4"},
    )
    task_id = job_submission.json()

    future_result = _get_result(client, settings, task_id)

    # Check that work gets done, AtomicResult-compatible data is returned

    while future_result.state not in READY_STATES:
        # No result while computation is happening
        assert future_result.result is None
        sleep(0.5)
        future_result = _get_result(client, settings, task_id)

    # If any result failed the state will be FAILURE
    assert future_result.state == TaskState.FAILURE
    assert future_result.result is not None

    assert future_result.result[0].success is True
    assert future_result.result[1].success is False

    # Assert result deleted from backend after retrieval
    with pytest.raises(HTTPStatusError):
        future_result = _get_result(client, settings, task_id)


def test_propagate_wfn_exception_handling(settings, client, fake_auth, hydrogen):
    prog_input = DualProgramInput(
        molecule=hydrogen,
        calctype="optimization",
        subprogram="psi4",
        subprogram_args={"model": {"method": "hf", "basis": "sto-3g"}},
    )
    # Submit Job
    job_submission = client.post(
        f"{settings.api_v2_str}/compute",
        data=json_dumps(prog_input),
        params={"program": "geometric", "propagate_wfn": True},
    )
    as_dict = job_submission.json()

    _make_job_completion_assertions(as_dict, client, settings, failure=True)
