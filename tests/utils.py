import json
from time import sleep
from typing import Union

import pytest
from celery.states import READY_STATES
from httpx import HTTPStatusError
from pydantic import BaseModel

from chemcloud_server.models import Output, TaskState


def json_dumps(obj: Union[BaseModel, list[BaseModel]]):
    """Convenience function for serializing pydantic models to JSON"""
    if isinstance(obj, list):
        return json.dumps([m.model_dump() for m in obj])
    return obj.model_dump_json()


def _get_result(client, settings, task_id) -> Output:
    # Check Status upon submission
    result = client.get(
        f"{settings.api_v2_str}/compute/output/{task_id}",
    )
    result.raise_for_status()
    as_dict = result.json()
    return Output(**as_dict)


def _make_job_completion_assertions(
    task_id, client, settings, failure: bool = False
) -> None:
    """All the assertions I want to make as a compute job proceeds.

    This starts at task retrieval (response from a /compute or /compute-procedure
    endpoint) and carries through to results retrieval

    """

    output = _get_result(client, settings, task_id)

    # Check that work gets done, AtomicResult-compatible data is returned

    while output.state not in READY_STATES:
        # No result while computation is happening
        assert output.result is None
        sleep(0.5)
        output = _get_result(client, settings, task_id)

    assert output.state == (TaskState.SUCCESS if not failure else TaskState.FAILURE)
    assert output.result is not None

    if isinstance(output.result, list):
        for ar in output.result:
            assert ar.success is True
    else:
        assert output.result.success is (True if not failure else False)

    # Assert result deleted from backend after retrieval
    with pytest.raises(HTTPStatusError):
        output = _get_result(client, settings, task_id)
