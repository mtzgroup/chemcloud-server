import pytest
import qcelemental as qcel
from fastapi.testclient import TestClient
from qcelemental.models import AtomicInput
from qcelemental.models.common_models import Model

from terachem_cloud.auth import bearer_auth
from terachem_cloud.config import get_settings
from terachem_cloud.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def fake_auth():
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
        -1 2
        O 0 0 0
        H 0 0 1
        H 0 1 0
        """
    )


@pytest.fixture(scope="function")
def atomic_input(water):
    model = Model(method="B3LYP", basis="6-31g")
    return AtomicInput(molecule=water, model=model, driver="energy")


@pytest.fixture(scope="session")
def settings():
    return get_settings()
