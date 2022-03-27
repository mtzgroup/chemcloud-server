from enum import Enum
from typing import Any, List, Optional, Union

from celery import states
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
    """Compute engines currently supported by TeraChem Cloud"""

    PSI4 = "psi4"
    TERACHEM_FE = "terachem_fe"
    RDKIT = "rdkit"
    XTB = "xtb"
    # TeraChem Cloud specific algorithms
    TCC = "tcc"


class SupportedProcedures(str, Enum):
    """Procedures currently supported by TeraChem Cloud"""

    BERNY = "berny"
    GEOMETRIC = "geometric"


class TaskStatus(str, Enum):
    """Tasks status for a submitted compute job.

    Wrapper around celery.states so that enums can be exposed on API endpoints.
    """

    # States from https://github.com/celery/celery/blob/master/celery/states.py
    #: Task state is unknown (assumed pending since you know the id).
    PENDING = states.PENDING
    #: Task was received by a worker (only used in events).
    RECEIVED = states.RECEIVED
    #: Task was started by a worker (:setting:`task_track_started`).
    STARTED = states.STARTED
    #: Task succeeded
    SUCCESS = states.SUCCESS
    #: Task failed
    FAILURE = states.FAILURE
    #: Task was revoked.
    REVOKED = states.REVOKED
    #: Task was rejected (only used in events).
    REJECTED = states.REJECTED
    #: Task is waiting for retry.
    RETRY = states.RETRY
    IGNORED = states.IGNORED


class ResultBaseABC(BaseModel):
    """Result Base class.

    Bridges the functionality required to describe the celery task (celery task ids)
    and the results that the status and results of that celery task.

    Result data objects and methods are separate from tasks so that the /result API
    endpoint more explicitly defines inputs and outputs. I didn't want to have the
    endpoint accept FutureResult objects with their possible .result and .status
    properties, which make no sense when requesting an update.
    """

    compute_status: TaskStatus = TaskStatus.PENDING
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


class FutureResult(ResultBaseABC):
    """Represents status and result of celery AsyncResult"""

    result: Optional[PossibleResults] = None


class FutureResultGroup(ResultBaseABC):
    """Represents status and result of celery GroupResult

    Modification:
        - Added .result property that contains array of result values
    """

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
