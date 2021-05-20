from enum import Enum
from typing import Optional, Union

from numpy import ndarray
from pydantic import AnyHttpUrl, BaseModel, Field
from qcelemental.models import AtomicResult, FailedOperation, OptimizationResult
from qcelemental.util.serialization import json_dumps as qc_json_dumps
from qcelemental.util.serialization import json_loads as qc_json_loads


class TaskStatus(str, Enum):
    """Tasks status for a submitted compute job."""

    # States from https://github.com/celery/celery/blob/master/celery/states.py
    #: Task state is unknown (assumed pending since you know the id).
    PENDING = "PENDING"
    #: Task was received by a worker (only used in events).
    RECEIVED = "RECEIVED"
    #: Task was started by a worker (:setting:`task_track_started`).
    STARTED = "STARTED"
    #: Task succeeded
    SUCCESS = "SUCCESS"
    #: Task failed
    FAILURE = "FAILURE"
    #: Task was revoked.
    REVOKED = "REVOKED"
    #: Task was rejected (only used in events).
    REJECTED = "REJECTED"
    #: Task is waiting for retry.
    RETRY = "RETRY"
    IGNORED = "IGNORED"


class TaskResult(BaseModel):
    status: TaskStatus
    result: Optional[Union[AtomicResult, OptimizationResult, FailedOperation]] = None

    class Config:
        # These json_dumps and json_loads methods enable TaskResult.json() to function correctly
        def _qc_json_dumps(data, **kwargs):
            """Use QCElemental encoders, accept default={default_encoder} argument"""
            return qc_json_dumps(data)

        def _qc_json_loads(data, **kwargs):
            """Use QCElemental decoders, accept default={default_decoder} argument"""
            return qc_json_loads(data)

        json_dumps = _qc_json_dumps
        json_loads = _qc_json_loads

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
