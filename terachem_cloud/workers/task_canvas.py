"""Top level functions for parallelized TeraChem Cloud algorithms

Use compute_tcc and pass AtomicInput to get back a signature that can be called
asynchronously.
"""
from typing import List

from celery.canvas import Signature, group
from qcelemental.models import AtomicInput, DriverEnum

from terachem_cloud import models
from terachem_cloud.config import get_settings

# from .helpers import gradient_inputs
from .tasks import compute as compute_task
from .tasks import frequency_analysis as frequency_analysis_task
from .tasks import hessian as hessian_task

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


def parallel_hessian(
    input_data: AtomicInput,
    engine: models.SupportedEngines = models.SupportedEngines.TERACHEM_FE,
    dh: float = settings.hessian_default_dh,
) -> Signature:
    """Create parallel hessian signature

    Params:
        input_data: AtomicInput with driver=hessian
        package: compute engine to use for gradient calculations
        dh: displacement for finite difference computation

    Note: Creates a Celery Chord where gradients are computed in parallel, then the
        list of gradients is fed as the first argument to the hessian celery task.
        Once called this signature will execute asynchronously and will return an
        AsyncResult with a .parent attribute referencing the group of gradient
        computations. The last computation on the list is a basic energy calculation of
        the original geometry.
    """
    assert (
        input_data.driver == DriverEnum.hessian
    ), f"input_data.driver should be '{DriverEnum.hessian}', got '{input_data.driver}'"

    gradients = _gradient_inputs(input_data, dh)
    # Perform basic energy computation on unadjusted molecule as final item in group
    energy_calc = input_data.dict()
    energy_calc["driver"] = "energy"
    gradients.append(AtomicInput(**energy_calc))

    # | is chain operator in celery; chaining a group to another task automatically
    # upgrades it to a chord. The returned object below is a chord
    return group(compute_task.s(inp, engine) for inp in gradients) | hessian_task.s(dh)


def parallel_frequency_analysis(
    input_data: AtomicInput,
    engine: models.SupportedEngines = models.SupportedEngines.TERACHEM_FE,
    dh: float = settings.hessian_default_dh,
    **kwargs,
) -> Signature:
    """Create frequency_analysis signature leveraging parallel hessian

    Params:
        input_data: AtomicInput with driver=properities and engine=tcc
        kwargs: Keywords passed to geomeTRIC's frequency_analysis function
            energy: float - Electronic energy passed to the harmonic free energy module
                default: 0.0
            temperature: float - Temperature passed to the harmonic free energy module;
                default: 300.0
            pressure: float - Pressure passed to the harmonic free energy module;
                default: 1.0

    """
    assert input_data.driver == DriverEnum.properties, (
        f"input_data.driver should be '{DriverEnum.properties}', got "
        f"'{input_data.driver}'"
    )
    hessian_inp = input_data.dict()
    hessian_inp["driver"] = DriverEnum.hessian
    hessian_sig = parallel_hessian(AtomicInput(**hessian_inp), engine, dh)
    # | is celery chain operator
    return hessian_sig | frequency_analysis_task.s(**kwargs)


def _gradient_inputs(
    input_data: AtomicInput, dh: float = settings.hessian_default_dh
) -> List[AtomicInput]:
    """Create AtomicInput gradient calculations for a numerical hessian

    Params:
        input_data: AtomicInput with keywords specific to the gradient computations
            that will comprise the hessian
        dh: Offset for numerical hessian calculation

    Returns:
        Flat list of AtomicInput gradient calculations with dh offset for each geometry
            value. The first AtomicInput represents a "forward" step by dh and the next
            AtomicInput represents a "backward" step by dh and so on.
    """
    as_dict = input_data.dict()
    as_dict["driver"] = "gradient"
    as_gradient = AtomicInput(**as_dict)

    gradient_calls = []
    for i, row in enumerate(input_data.molecule.geometry):
        for j, _ in enumerate(row):
            forward, backward = as_gradient.copy(deep=True), as_gradient.copy(deep=True)

            forward.molecule.geometry[i][j] += dh
            backward.molecule.geometry[i][j] -= dh

            gradient_calls.append(forward)
            gradient_calls.append(backward)

    return gradient_calls


def _gradient_inputs_2(
    input_data: AtomicInput, dh: float = settings.hessian_default_dh
) -> List[AtomicInput]:
    """Create AtomicInput gradient calculations for a numerical hessian

    Params:
        input_data: AtomicInput with keywords specific to the gradient computations
            that will comprise the hessian
        dh: Offset for numerical hessian calculation

    Returns:
        Flat list of AtomicInput gradient calculations with dh offset for each geometry
            value. The first AtomicInput represents a "forward" step by dh and the next
            AtomicInput represents a "backward" step by dh and so on.
    """
    as_dict = input_data.dict()
    as_dict["driver"] = "gradient"
    as_gradient = AtomicInput(**as_dict)

    gradient_calls = []
    for i, row in enumerate(input_data.molecule.geometry):
        for j, _ in enumerate(row):
            forward, backward = as_gradient.copy(deep=True), as_gradient.copy(deep=True)

            forward.molecule.geometry[i][j] += dh
            backward.molecule.geometry[i][j] -= dh

            gradient_calls.append(forward)
            gradient_calls.append(backward)

    return gradient_calls
