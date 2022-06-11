"""Top level functions for parallelized TeraChem Cloud algorithms

Use compute_tcc and pass AtomicInput to get back a signature that can be called
asynchronously.
"""

# from .helpers import gradient_inputs
from bigqc.algos import parallel_frequency_analysis, parallel_hessian
from celery.canvas import Signature
from qcelemental.models import AtomicInput, DriverEnum

from terachem_cloud import models
from terachem_cloud.config import get_settings

settings = get_settings()


def compute_tcc(
    input_data: AtomicInput,
    engine: models.SupportedEngines = models.SupportedEngines.TERACHEM_FE,
    **kwargs,
) -> Signature:
    """TeraChem Cloud specific algorithms

    Params:
        input_data: Input specification; driver may be hessian or properties
        engine: Compute engine to use for gradient calculations
        kwargs: kwargs for parallel_hessian or parallel_frequency_analysis
    """

    SUPPORTED_DRIVERS = [DriverEnum.hessian, DriverEnum.properties]
    assert input_data.driver in SUPPORTED_DRIVERS, (
        f"Driver '{input_data.driver}' not supported. Supported drivers include: "
        f"{SUPPORTED_DRIVERS}"
    )

    if input_data.driver == DriverEnum.hessian:
        return parallel_hessian(input_data, engine, **kwargs)
    else:
        return parallel_frequency_analysis(input_data, engine, **kwargs)
