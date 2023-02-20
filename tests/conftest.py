from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from qcelemental.models import (
    AtomicInput,
    AtomicResult,
    Molecule,
    OptimizationInput,
    OptimizationResult,
)

from chemcloud_server.auth import bearer_auth
from chemcloud_server.config import get_settings
from chemcloud_server.main import app


@pytest.fixture(scope="session")
def client():
    """Client for making HTTP requests to the app"""
    return TestClient(app)


@pytest.fixture(scope="function")
def fake_auth():
    """Fake authentication for webserver"""

    def fake_bearer_auth():
        return {
            "iss": "https://dev-mtzlab.us.auth0.com/",
            "sub": "auth0|5fb8828f1bda000075e14b0a",
            "aud": "https://chemcloud.dev.mtzlab.com",
            "iat": 1606866842,
            "exp": 1606953242,
            "azp": "lQvfKdlfxLE0E9mVEIl58Wi9gX2AwWop",  # pragma: allowlist secret
            "scope": "compute:public compute:private",
            "gty": "password",
        }

    app.dependency_overrides[bearer_auth] = fake_bearer_auth
    yield
    app.dependency_overrides = {}


@pytest.fixture
def test_data_dir():
    """Test data directory Path"""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def hydrogen():
    """Hydrogen Molecule"""
    return Molecule(
        **{
            "symbols": ["H", "H"],
            "geometry": [0, 0, -0.65, 0.0, 0.0, 0.65],
            "molecular_multiplicity": 1,
            "connectivity": [[0, 1, 1]],
        }
    )


@pytest.fixture
def water():
    """Water Molecule"""
    return Molecule(
        **{
            "geometry": [
                0.0,
                0.0,
                -0.1294769411935893,
                0.0,
                -1.494187339479985,
                1.0274465079245698,
                0.0,
                1.494187339479985,
                1.0274465079245698,
            ],
            "symbols": ["O", "H", "H"],
            "connectivity": [[0, 1, 1], [0, 2, 1]],
        }
    )


@pytest.fixture
def atomic_input(water):
    return AtomicInput(
        molecule=water, driver="energy", model={"method": "HF", "basis": "sto-3g"}
    )


@pytest.fixture
def opt_input(atomic_input):
    ai_dict = atomic_input.dict()
    ai_dict.pop("molecule")
    return OptimizationInput(
        input_specification={
            "driver": atomic_input.driver,
            "model": atomic_input.model,
        },
        initial_molecule=atomic_input.molecule,
    )


@pytest.fixture
def atomic_result(atomic_input):
    return AtomicResult(
        **atomic_input.dict(),
        return_result=123.4,
        success=True,
        properties={},
    )


@pytest.fixture
def opt_result(atomic_result, opt_input):
    opt_dict = opt_input.dict()
    opt_dict.pop("schema_name")
    return OptimizationResult(
        **opt_dict,
        final_molecule=atomic_result.molecule,
        trajectory=[atomic_result],
        energies=[atomic_result.return_result],
        success=True,
    )


@pytest.fixture(scope="session")
def settings():
    """QC Cloud application settings"""
    return get_settings()
