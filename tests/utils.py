from time import sleep
from typing import Union

from terachem_cloud.models import (
    FutureResult,
    FutureResultGroup,
    GroupTask,
    Task,
    TaskStatus,
)


def _get_result(client, settings, task) -> Union[FutureResult, FutureResultGroup]:
    # Check Status upon submission
    result = client.post(
        f"{settings.api_v1_str}/compute/result",
        data=task.json(),
    )
    as_dict = result.json()
    if isinstance(as_dict["result"], list):
        return FutureResultGroup(**as_dict)
    return FutureResult(**as_dict)


def _make_job_completion_assertions(task_as_dict, client, settings) -> None:
    """All the assertions I want to make as a compute job procedes.

    This starts at task retrieval (response from a /compute or /compute-procedure
    endpoint) and carries through to results retrieval

    """
    task: Union[Task, GroupTask]

    if task_as_dict.get("subtasks"):
        task = GroupTask(**task_as_dict)
    else:
        task = Task(**task_as_dict)

    future_result = _get_result(client, settings, task)

    # Check that work gets done, AtomicResult-compatible data is returned
    while future_result.compute_status in {TaskStatus.PENDING, TaskStatus.STARTED}:
        # No result while computation is happening
        assert future_result.result is None
        sleep(0.5)
        future_result = _get_result(client, settings, task)

    assert future_result.compute_status == TaskStatus.SUCCESS
    assert future_result.result is not None

    if isinstance(future_result.result, list):
        for ar in future_result.result:
            assert ar.success is True
    else:
        assert future_result.result.success is True

    # Assert result deleted from backend after retrieval
    future_result = _get_result(client, settings, task)
    assert future_result.compute_status == TaskStatus.PENDING
    assert future_result.result is None
