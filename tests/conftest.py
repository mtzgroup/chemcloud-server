import pytest
import qcelemental as qcel
from fastapi.testclient import TestClient
from qcelemental.models import AtomicInput
from qcelemental.models.common_models import Model
from qcelemental.models.procedures import OptimizationInput, QCInputSpecification

from terachem_cloud.auth import bearer_auth
from terachem_cloud.config import get_settings
from terachem_cloud.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def fake_auth():
    """Fake authentication for webserver"""

    def fake_bearer_auth():
        return {
            "iss": "https://dev-mtzlab.us.auth0.com/",
            "sub": "auth0|5fb8828f1bda000075e14b0a",
            "aud": "https://terachemcloud.dev.mtzlab.com",
            "iat": 1606866842,
            "exp": 1606953242,
            "azp": "lQvfKdlfxLE0E9mVEIl58Wi9gX2AwWop",  # pragma: allowlist secret
            "scope": "compute:public compute:private",
            "gty": "password",
        }

    app.dependency_overrides[bearer_auth] = fake_bearer_auth
    yield
    app.dependency_overrides = {}


@pytest.fixture(scope="function")
def water():
    return qcel.models.Molecule.from_data(
        """
        O 0 0 0
        H 0.52421003 1.68733646 0.48074633
        H 1.14668581 -0.45032174 -1.35474466
        """
    )


@pytest.fixture(scope="function")
def atomic_input(water):
    model = Model(method="B3LYP", basis="sto-3g")
    return AtomicInput(molecule=water, model=model, driver="energy")


@pytest.fixture(scope="function")
def optimization_input(atomic_input):
    qc_input_spec = QCInputSpecification(driver="gradient", model=atomic_input.model)
    input = OptimizationInput(
        protocols={"trajectory": "all"},
        initial_molecule=atomic_input.molecule,
        input_specification=qc_input_spec,
        keywords={"program": "psi4", "maxsteps": 2},
    )
    return input


@pytest.fixture(scope="session")
def settings():
    return get_settings()
