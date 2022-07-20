from enum import Enum
from typing import Any, List, Optional, Union

from numpy import ndarray
from pydantic import AnyHttpUrl, BaseModel, Field
from qcelemental.models import AtomicResult, FailedOperation, OptimizationResult
from qcelemental.models.procedures import OptimizationInput
from qcelemental.models.results import AtomicInput
from qcelemental.util.serialization import json_dumps as qcel_json_dumps
from qcelemental.util.serialization import json_loads as qcel_json_loads

# Convenience types
AtomicInputOrList = Union[AtomicInput, List[AtomicInput]]
OptimizationInputOrList = Union[OptimizationInput, List[OptimizationInput]]
SuccessfulResults = Union[AtomicResult, OptimizationResult]
PossibleResults = Union[SuccessfulResults, FailedOperation]


class SupportedEngines(str, Enum):
    """Compute engines currently supported by QC Cloud"""

    PSI4 = "psi4"
    TERACHEM_FE = "terachem_fe"
    RDKIT = "rdkit"
    XTB = "xtb"
    # BigChem distributed algorithms
    BIGCHEM = "bigchem"


class SupportedProcedures(str, Enum):
    """Procedures currently supported by QC Cloud"""

    BERNY = "berny"
    GEOMETRIC = "geometric"


class TaskState(str, Enum):
    """Tasks status for a submitted compute job"""

    # States previously from https://github.com/celery/celery/blob/master/celery/states.py
    # if I revert more more specific task states look at them again.
    #: Task state is unknown (assumed pending since you know the id).
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"


class ResultBaseABC(BaseModel):
    """Result Base class. Thin wrapper around celery ResultBase"""

    state: TaskState
    result: Optional[Any] = None

    class Config:
        # These json_dumps and json_loads methods enable .json() (used by FastAPI to
        # serialize data on endpoints) to function correctly

        json_dumps = qcel_json_dumps
        json_loads = qcel_json_loads

        def _np_encoder(ar: ndarray):  # type: ignore
            # NOTE: mypy wants this to be a staticmethod, hence # type: ignore comment
            """Custom encoder taken from qcelemental.utils.serialization.JSONArrayEncoder

            Need custom encoder for ndarray types, using qcelemental.utils.serialization.json_dumps
            does not work. Unclear why? Not sure why fastapi doesn't use the serializer
            for AtomicResult which works correctly if returned by a response directly.
            The problem arises when an AtomicResult is a field of another object. The
            fastapi.encoders.jsonable_encoder is the method that raises an exception without
            this custom encoder defined.

            https://pydantic-docs.helpmanual.io/usage/exporting_models/#json_encoders

            Tracking this issue here:
            https://github.com/tiangolo/fastapi/issues/2494

            Don't love the duplicate code but moving on at this point...
            """
            if ar.shape:
                return ar.ravel().tolist()
            else:
                return ar.tolist()

        json_encoders = {
            ndarray: _np_encoder,
        }


class Result(ResultBaseABC):
    """Status and result of compute tasks. Wrapper around celery AsyncResult"""

    result: Optional[PossibleResults] = None


class ResultGroup(ResultBaseABC):
    """Status and result of compute tasks. Wrapper around celery GroupResult"""

    result: Optional[List[PossibleResults]] = None


class OAuth2Base(BaseModel):
    client_id: str
    client_secret: str


class OAuth2LoginBase(OAuth2Base):
    audience: str = ""
    scope: str = ""


class OAuth2PasswordFlow(OAuth2LoginBase):
    grant_type: str = Field("password", regex="password")
    username: str
    password: str


class OAuth2AuthorizationCodeFlow(OAuth2LoginBase):
    grant_type: str = Field("authorization_code", regex="authorization_code")
    code: str
    redirect_uri: AnyHttpUrl


class OAuth2RefreshFlow(OAuth2Base):
    grant_type: str = Field("refresh_token", regex="refresh_token")
    refresh_token: str
