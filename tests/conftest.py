from pathlib import Path

import pytest
import qcengine as qcng
from fastapi.testclient import TestClient

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


@pytest.fixture
def test_data_dir():
    """Test data directory Path"""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def hydrogen():
    """Hydrogen Molecule"""
    return qcng.get_molecule("hydrogen")


@pytest.fixture
def water():
    """Water Molecule"""
    return qcng.get_molecule("water")


@pytest.fixture(scope="session")
def settings():
    """TeraChem Cloud application settings"""
    return get_settings()
