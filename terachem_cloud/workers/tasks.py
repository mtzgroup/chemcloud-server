import ssl
from itertools import zip_longest
from typing import List, Union

import numpy as np
import qcengine as qcng
from celery import Celery
from geometric.normal_modes import frequency_analysis as geometric_frequency_analysis
from kombu.serialization import register
from qcelemental.models import (
    AtomicInput,
    AtomicResult,
    FailedOperation,
    OptimizationInput,
    OptimizationResult,
)
from qcelemental.util.serialization import json_dumps as qcel_json_dumps
from qcelemental.util.serialization import json_loads as qcel_json_loads

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
    qcel_json_dumps,
    qcel_json_loads,
    content_type="application/x-qceljson",
    content_encoding="utf-8",
)

celery_app.conf.update(
    # task_serializer="qceljson",
    # accept_content=["qceljson"],
    # result_serializer="qceljson",
    # NOTE: Switching to pickle serializer for now so that chords receive python objects
    task_serializer="pickle",
    accept_content=["pickle"],
    result_serializer="pickle",
    task_track_started=True,
    # Cause workers to only receive and work on one task at a time (no prefetching of messages)
    # https://docs.celeryproject.org/en/stable/userguide/optimizing.html#prefetch-limits
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Only one concurrent worker process. One process may use multiple CPU cores anyways.
    worker_concurrency=1,
    broker_connection_retry_on_startup=True,
)

# NOTE: Setting this value means celery will change ports for amqp to 5671 by default
# this means I should probably only set this value if I am not running locally
if "amqps" in settings.celery_broker_connection_string:
    celery_app.conf.update(
        broker_use_ssl={
            # Do not verify broker certificate on client. Since Traefik is dynamically
            # assigning SSL certs, client-side verification is not possible
            "cert_reqs": ssl.CERT_NONE,
        },
    )


@celery_app.task
def compute(
    atomic_input: AtomicInput, engine: str, raise_error: bool = False
) -> Union[AtomicResult, FailedOperation]:
    """Celery task wrapper around qcengine.compute"""
    return qcng.compute(atomic_input, engine, raise_error=raise_error)


@celery_app.task
def compute_procedure(
    input: OptimizationInput, procedure: str, raise_error: bool = False
) -> Union[OptimizationResult, FailedOperation]:
    """Celery task wrapper around qcengine.compute_procedure"""
    return qcng.compute_procedure(input, procedure, raise_error=raise_error)


@celery_app.task
def hessian(
    gradients: List[AtomicResult], dh: float
) -> Union[AtomicResult, FailedOperation]:
    """Compute hessian in parallel from array of gradient computations

    Params:
        gradients: List of gradient AtomicResult objects alternating between a
            "forward" and "backward" computation. NOTE: The last computation on the
            list is a basic energy calculation of the original geometry.
        dh: The displacement used for finite difference displacements of gradient
            geometries

    Note:
        Another way I've tested this algorithm is to compute the hessian using psi4
        and then using this algorithm at the save level of theory and then compare
        their eigenvalues. The results have always matched up to two decimal places.
        The matrices can't be compared directly because it appears psi4 does some sort
        of rotation on their matrix, so the eigenvalues are a better mechanism for
        comparison.
    """
    # Validate input array; return FailedOperation if a gradient or energy failed
    for gradient in gradients:
        if isinstance(gradient, FailedOperation):
            return gradient

    # Pop energy calculation from gradients (last value in gradients list)
    energy = gradients.pop()

    dim = len(gradients[0].molecule.symbols) * 3
    hessian = np.zeros((dim, dim), dtype=float)

    for i, pair in enumerate(zip_longest(*[iter(gradients)] * 2)):
        forward, backward = pair
        val = (forward.return_result - backward.return_result) / (dh * 2)
        hessian[i] = val.flatten()

    result = energy.dict()
    result["driver"] = "hessian"
    result["return_result"] = hessian

    return AtomicResult(**result)


@celery_app.task
def frequency_analysis(
    input_data: AtomicResult, **kwargs
) -> Union[AtomicResult, FailedOperation]:
    """Perform geomeTRIC's frequency analysis using AtomicResult with hessian result

    Params:
        input_data: AtomicResult with return_result=hessian
        kwargs: Keywords passed to geomeTRIC's frequency_analysis function
            energy: float - Electronic energy passed to the harmonic free energy module
                default: 0.0
            temperature: float - Temperature passed to the harmonic free energy module;
                default: 300.0
            pressure: float - Pressure passed to the harmonic free energy module;
                default: 1.0

    Returns:
        AtomicResult | FailedOperation - AtomicResult will be driver=properties with
            dictionary of values returned from frequency_analysis as return_result

    """
    freqs, n_modes, g_tot_au = geometric_frequency_analysis(
        input_data.molecule.geometry.flatten(),
        input_data.return_result,
        list(input_data.molecule.symbols),
        **kwargs,
    )
    result = input_data.dict()
    result["driver"] = "properties"
    result["return_result"] = {
        "freqs_wavenumber": freqs.tolist(),
        "normal_modes_cart": n_modes.tolist(),
        "g_total_au": g_tot_au,
    }
    return AtomicResult(**result)


@celery_app.task
def add(x, y):
    """Add two numbers

    NOTE: Used for design testing
    """
    return x + y


@celery_app.task
def csum(values: List[Union[float, int]], extra: int) -> Union[float, int]:
    """Sum all the values in a list

    NOTE: Used for design testing as a summation at the end of add (a chord)
    """
    values.append(extra)
    return sum(values)
