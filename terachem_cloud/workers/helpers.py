from typing import List

from qcelemental.models import AtomicInput

from terachem_cloud.config import get_settings

settings = get_settings()


def gradient_inputs(
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
