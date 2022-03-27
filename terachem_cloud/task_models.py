"""This module exists because the Task models reference the celery_app object.
terachem_cloud.workers.helpers needs to reference various model objects and
tasks.py imports these helpers. Keeping Task models in the models.py file
creates a circular import
TODO: Maybe rethink the layout of these modules
"""
import re
from abc import ABC, abstractclassmethod, abstractmethod
from typing import List

from celery import states
from celery.result import AsyncResult, GroupResult, ResultBase
from pydantic import BaseModel, validator

from terachem_cloud.models import FutureResult, FutureResultGroup, TaskStatus
from terachem_cloud.workers.tasks import celery_app


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
        """Convert to result object that contains celery status and possible result"""
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
