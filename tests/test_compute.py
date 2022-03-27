import pytest
from fastapi import status as status_codes
from qcelemental.models.procedures import OptimizationInput, QCInputSpecification
from qcelemental.models.results import AtomicInput
from qcelemental.util.serialization import json_dumps
from tcpb.config import settings as tcpb_settings

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


@pytest.mark.skip(
    "Skipping because must run with terachem_fe. Run when terachem_fe is available."
)
@pytest.mark.timeout(15)
def test_compute_with_binary_extras(settings, client, fake_auth, hydrogen):
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
        extras={
            tcpb_settings.tcfe_keywords: {
                "c0_b64": "3zRS3mHX7z/BLb1nMtDKP47ElALlza6+2WtQ2FIyt79oVsETNuW+vq0LIzKrcLY/6ZGZv9fpZT5MUQWkRqqmPj5rq6TUaqG/0SO/FAnf2D6ZUXEbBwu0PyQqDmSVkZe+Dcj7yruCqz8nZAwtWY6cP4wQ8dlJtd2/9+olWNACvz49PXVyQcjJP+BmuyNeCcg+4/uLwkOUw7/QXW2F0de1PqIcA1VuMNa+wZC47AoiyT8/05CAcesGvyypD8CNWt+/JSDMhkyFwr7frrA35JH6v6mXcQf/0Iq/BK2rccjt3L+zXUIMzKTKPgCqWO3X6dc/pb/ABU+y4T4+Yx/vkjTxv/msMOFyLc++412SW2cY5D5abTgHQL3Sv66GoxlIbAs/ZbKB3dt6wD/ANK5hLDHgPnQmeM5I9QVAxyewudFnIz+CSG0UuhTDv1QZcKhUANE/xSD8rqtmwr9tMvB03oTQviMoFmJUaLk/12kmAci3uT8C3OVt6grvv/b7hgqXT+e/WOffYgC4HT8ZIYNhtevkP6UL9T53Sp4/z9uINHru3r/qv6fTQNdoP0Y1mx+TIkC/L40eLoRvwz8IIalcxWS7vz0Ycxr2o9K+bveOtUK+7T+W0DrrvUn0P6FigRVRVeY/N/G2rNRp4z/C8zUYx5AQv8Qg8+WTlMa/RZbhobLm7D9i9NhLGnzjv6tLRZorZyM/ST50occUw79N1xO3VgDRv8Qe8QKhZsK/Fo0DbNOOpr7dJHVGd2i5P8pwNhj9t7m/fP8mqC8L7z+MK55HME/nv/b9JB5Z3BU/NEyZ973r5D/dPbpE202ev2YEKlGB7t6/WhKHjkbXaD8KNr0xhCZAvyC9I4SIb8O/8ptqCJ1ku7/MkGFS3mS4PhjNCfVIvu0/2neKo7ZJ9L8J4/jwklXmv4PonZOtaeM/cAtG/poRGL/ZQcdnxJTGv47d66Sw5uy/SrZAuxV8478I4fqpwLFaP/KIiCH/qry/Wy64Zah4vL8HkG5yuMPZvzSZ+ZmAUdq/BdgkdJ78y7/1/nymZ0i3P78OuExAVqa/yKIFhLoF4j+iSaAfn4Djv0d272VHXNw/6xjWM8EZy79XIrmHUJLBvwUTo0lZw1M/qKIYPw45tb8g2ctKTnHYP3iopC82E9O/vUxKQcwK0D+2abUBG7jEv6dlRu8u/dO/DWYGLloqwz8Lr7vk4bDaP3WRsEmdxdc/Xpz/aKP+1D/fDmPzwETnP2DW+/3zBLq/jPHNmJPtS792IiHtkf2tP2V53QjF/NQ/crc+XIP0yj+ETa+Pu5vbv2ujNtZVR70/2f0PGNsp0b/7YI7w8HTAPzkfC7lo3NK/rWsJX6V05L/BZEgNYKrNv7i+qW7q+uM/qpI3lCBisj8nhEU4DoRgv8/JqiSur6q/72J9Xzgyqr/U/lPDTsDRv9/VaxsIi9S/zwKm6ao91b9MSa0CbbbEP+k9E+xy4rq/1PWR1zX71b9hqrCGUyrlPyOS2IUfjeq/BI763uTx1j/d88hbLsnkP67vnwF7dFi//Uex1qHBo79lpKWseX3GPy/jPnPPSMq/tOfU+Q4LyT/g9/hCXXPPvy8kkZ1oyOG/a6aG7f0V1z+fb+1+T0fQv3Q55s2pzdm/YaY+Iuun479qP+rWEbPzv/I9SlP2xt4/OUJUXVBHUT/pgNAI/uqbP/VHsYOgT8M/75Z5WzmSwj/HtteHzozVv9FRAmyVOMY/Q9gTHNuJ3r8yAnknpNLTP17vH9cwA8c/rG0yBXMz5j/A3gBwUMbbPw94jN9Q6vC/p9SARcm+1b8="
            }
        },
    )

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute",
        data=json_dumps(atomic_input),
        params={"engine": "terachem_fe"},
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


# @pytest.mark.skip("Long test so skipping for brevity")  # Comment out to run test
@pytest.mark.parametrize(
    "driver,model,tcc_keywords,group",
    (
        (
            "hessian",
            {"method": "HF", "basis": "sto-3g"},
            {"gradient_engine": "psi4"},
            False,
        ),
        (
            "hessian",
            {"method": "HF", "basis": "sto-3g"},
            {"gradient_engine": "psi4"},
            True,
        ),
        (
            "properties",
            {"method": "HF", "basis": "sto-3g"},
            {
                "gradient_engine": "psi4",
                "energy": 1.5,
                "temperature": 310,
                "pressure": 1.2,
            },
            False,
        ),
    ),
)
@pytest.mark.timeout(450)
def test_compute_tcc_engine(
    settings, client, fake_auth, water, driver, model, tcc_keywords, group
):
    """Test TeraChem Cloud specific methods"""
    atomic_input = AtomicInput(
        molecule=water,
        driver=driver,
        model=model,
        extras={settings.tcc_keywords: tcc_keywords},
    )
    if group:
        atomic_input = [atomic_input, atomic_input]

    # Submit Job
    job_submission = client.post(
        f"{settings.api_v1_str}/compute",
        data=json_dumps(atomic_input),
        params={"engine": "tcc"},
    )
    as_dict = job_submission.json()

    _make_job_completion_assertions(as_dict, client, settings)
