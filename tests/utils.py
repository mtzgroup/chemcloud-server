from time import sleep
from typing import Union

import pytest
from requests.exceptions import HTTPError

from qccloud_server.models import Result, ResultGroup, TaskState


def _get_result(client, settings, task_id) -> Union[Result, ResultGroup]:
    # Check Status upon submission
    result = client.get(
        f"{settings.api_v1_str}/compute/result/{task_id}",
    )
    result.raise_for_status()
    as_dict = result.json()
    if isinstance(as_dict["result"], list):
        return ResultGroup(**as_dict)
    return Result(**as_dict)


def _make_job_completion_assertions(task_id, client, settings) -> None:
    """All the assertions I want to make as a compute job procedes.

    This starts at task retrieval (response from a /compute or /compute-procedure
    endpoint) and carries through to results retrieval

    """

    future_result = _get_result(client, settings, task_id)

    # Check that work gets done, AtomicResult-compatible data is returned
    while future_result.state != TaskState.COMPLETE:
        # No result while computation is happening
        assert future_result.result is None
        sleep(0.5)
        future_result = _get_result(client, settings, task_id)

    assert future_result.state == TaskState.COMPLETE
    assert future_result.result is not None

    if isinstance(future_result.result, list):
        for ar in future_result.result:
            assert ar.success is True
    else:
        assert future_result.result.success is True

    # Assert result deleted from backend after retrieval
    with pytest.raises(HTTPError):
        future_result = _get_result(client, settings, task_id)
