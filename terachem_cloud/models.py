import re
from abc import ABC, abstractclassmethod, abstractmethod
from enum import Enum
from typing import Any, List, Optional, Union

from celery import states
from celery.result import AsyncResult, GroupResult, ResultBase
from numpy import ndarray
from pydantic import AnyHttpUrl, BaseModel, Field, validator
from qcelemental.models import AtomicResult, FailedOperation, OptimizationResult
from qcelemental.models.procedures import OptimizationInput
from qcelemental.models.results import AtomicInput
from qcelemental.util.serialization import json_dumps as qcel_json_dumps
from qcelemental.util.serialization import json_loads as qcel_json_loads

from terachem_cloud.workers.tasks import celery_app

# Convenience types
AtomicInputOrList = Union[AtomicInput, List[AtomicInput]]
OptimizationInputOrList = Union[OptimizationInput, List[OptimizationInput]]
PossibleResults = Union[AtomicResult, OptimizationResult, FailedOperation]


class SupportedEngines(str, Enum):
    """Compute engines currently supported by TeraChem Cloud"""

    PSI4 = "psi4"
    TERACHEM_PBS = "terachem_pbs"
    RDKIT = "rdkit"
    XTB = "xtb"


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


class TaskBase(BaseModel, ABC):
    """Base Task model

    This base class and subsequent child classes mimic Celery's Result objects with
    modifications that make them more amenable to HTTP response/request cycles. See
    "Modifications" section in each class for description of design choices that vary
    from the functionality in the celery object each class mimics.

    Task objects are defined as just the task_ids that can be used to retrieve status
    and results. Result objects define the retrieved celery status and possible
    computation results.
    """

    task_id: str

    @validator("task_id")
    def validate_task_id(cls, v):
        """Assert task_id matches valid celery task UUID"""
        assert re.match(
            "^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$", v
        ), f"Invalid task id '{v}'"
        return v

    @abstractmethod
    def to_result(self) -> "ResultBase":
        """Return the corresponding Result object for this Task"""
        raise NotImplementedError

    @abstractclassmethod
    def from_celery(cls, celery_result: ResultBase) -> "TaskBase":
        raise NotImplementedError

    def forget(self) -> None:
        """Forget a result from the backend"""
        c_result = self.to_celery()
        c_result.forget()

    @abstractmethod
    def to_celery(self, app=celery_app) -> ResultBase:
        """Convert task to Celery Result Base"""
        raise NotImplementedError


class Task(TaskBase):
    """Represents the task definition of celery AsyncResult"""

    def to_result(self, app=celery_app) -> "FutureResult":
        """Convert to result object that containing celery status and possible result"""
        celery_task = self.to_celery(app=celery_app)
        status = celery_task.status

        fr = {"compute_status": status}
        if status in states.READY_STATES:
            fr["result"] = celery_task.result

        return FutureResult(**fr)

    @classmethod
    def from_celery(cls, async_result: AsyncResult) -> "Task":
        """Instantiate Task from celery AsyncResult"""
        return cls(task_id=async_result.id)

    def to_celery(self, app=celery_app) -> AsyncResult:
        """Return celery AsyncResult from Task"""
        return AsyncResult(id=self.task_id, app=celery_app)


class GroupTask(TaskBase):
    """Represents the task definition of celery GroupResult"""

    subtasks: List[Task]

    def to_result(self, app=celery_app) -> "FutureResultGroup":
        """Convert to result object that containing celery status and possible result"""
        group_result = self.to_celery(app)

        result = None
        if group_result.ready():
            result = group_result.get()
            if group_result.successful():
                compute_status = TaskStatus.SUCCESS
            else:
                compute_status = TaskStatus.FAILURE

        else:
            if group_result.completed_count() > 0:
                compute_status = TaskStatus.STARTED
            else:
                compute_status = TaskStatus.PENDING
        return FutureResultGroup(compute_status=compute_status, result=result)

    @classmethod
    def from_celery(cls, group_result: GroupResult) -> "GroupTask":
        """Create TaskSetBase from celery GroupResult"""
        subtasks = [Task.from_celery(ar) for ar in group_result.results]
        return cls(task_id=group_result.id, subtasks=subtasks)

    def to_celery(self, app=celery_app) -> GroupResult:
        """Return celery GroupResult from Task"""
        results = [task.to_celery(app) for task in self.subtasks]
        return GroupResult(id=self.task_id, results=results)


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
