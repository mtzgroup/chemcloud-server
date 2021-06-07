from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Union

import celery
import httpx
from celery import group
from fastapi import HTTPException
from fastapi import status as status_codes

from terachem_cloud import config, models

settings = config.get_settings()


async def _external_request(
    method: str, url: str, headers: Dict[str, str] = None, data: Dict[str, Any] = None
) -> Dict[Any, Any]:
    async with httpx.AsyncClient() as client:
        # Has default timeout of 5 seconds
        response = await client.request(
            method,
            url,
            headers=headers,
            data=data,
        )
    try:
        response_data = response.json()
    except JSONDecodeError:
        response_data = response.text

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=response.status_code,
            # Getting response_data["error_description"] is specific to Auth0 responses
            # NOTE: May need to generalize at some future date
            detail=response_data,
        )
    return response_data


async def _auth0_token_request(
    flow_model: models.OAuth2Base, settings: config.Settings = config.get_settings()
) -> Dict[Any, Any]:
    """Main method for requesting tokens from Auth0

    Set audience to get back JWT instead of Opaque Token
    https://community.auth0.com/t/why-is-my-access-token-not-a-jwt-opaque-token/31028

    Scopes:
        openid: get back id_token
        offline_access: get back refresh_token
        other scopes: whatever we want for permissions
    """
    return await _external_request(
        "post",
        f"https://{settings.auth0_domain}/oauth/token",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data=dict(flow_model),
    )


def validate_group_length(input_data: List[Any]) -> None:
    """Validate length of input_data does not exceed limits"""
    if len(input_data) > settings.max_batch_inputs:
        raise HTTPException(
            status_code=status_codes.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Cannot submit more than {settings.max_batch_inputs} inputs at once",
        )


def compute_inputs_async(
    input_data: Union[models.AtomicInputOrList, models.OptimizationInputOrList],
    package: Union[models.SupportedEngines, models.SupportedProcedures],
    celery_task: celery.Task,
    queue: Optional[str] = None,
) -> Union[models.GroupTask, models.Task]:
    """Accept inputs_data and celery_task, begins task, return Task models"""
    task: Union[models.GroupTask, models.Task]

    if isinstance(input_data, list):
        validate_group_length(input_data)
        c_task = group(celery_task.s(inp, package) for inp in input_data).apply_async(
            queue=queue
        )
        task = models.GroupTask.from_celery(c_task)
    else:
        c_task = celery_task.apply_async(args=[input_data, package], queue=queue)
        task = models.Task.from_celery(c_task)
    return task
