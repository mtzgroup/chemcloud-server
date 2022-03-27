from base64 import b64decode, b64encode
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Union

import httpx
from celery import group
from celery.canvas import Signature
from fastapi import HTTPException
from fastapi import status as status_codes
from qcelemental.models import (
    AtomicInput,
    AtomicResult,
    OptimizationInput,
    OptimizationResult,
)
from tcpb.config import settings as tcpb_settings

from terachem_cloud import config, models, task_models
from terachem_cloud.workers import tasks
from terachem_cloud.workers.task_canvas import compute_tcc

settings = config.get_settings()
B64_POSTFIX = "_b64"


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


def _bytes_to_b64(
    result: Union[models.PossibleResults, List[models.PossibleResults]]
) -> None:
    """Convert binary native_files to b64 encoded strings

    Converts key for the file to {key}_b64 and encodes the bytes as b64 string
    """
    # Cast all objects as list to simplify processing
    if not isinstance(result, list):
        result = [result]

    successful_results: list[AtomicResult] = []
    for obj in result:
        # May be AtomicInput, OptimizationResult, FailedOperation
        if isinstance(obj, models.FailedOperation):
            continue
        elif isinstance(obj, OptimizationResult):
            successful_results.extend(obj.trajectory)
        else:
            successful_results.append(obj)

    for res in successful_results:
        # Collect binary native files keys
        if res.native_files:
            binary_files = [
                key
                for key, value in res.native_files.items()
                if isinstance(value, bytes)
            ]
            # Convert binary files to b64 encoded version of the bytes
            for key in binary_files:
                file_bytes = res.native_files.pop(key)
                res.native_files[f"{key}{B64_POSTFIX}"] = b64encode(file_bytes).decode()


def _b64_to_bytes(input_data: Union[AtomicInput, OptimizationInput]) -> None:
    """Convert base64 encoded string values to bytes. Modifies inputs in place.

    Because JSON does not have a bytes data type, binary data sent to TCC for
    processing is first encoded in a b64 string. This function converts these fields
    from to bytes before passing them to the celery backend, which currently operates
    on the pickle serializer and so can handle binary data.
    """

    if isinstance(input_data, OptimizationInput):
        input_obj = input_data.input_specification
    else:
        input_obj = input_data

    tcfe_config = input_obj.extras.get(tcpb_settings.tcfe_keywords, {})

    b64_strings = [key for key in tcfe_config if key.endswith(B64_POSTFIX)]
    for key in b64_strings:
        value = tcfe_config.pop(key)
        tcfe_config[key.split(B64_POSTFIX)[0]] = b64decode(value)


def compute_inputs_async(
    input_data: Union[models.AtomicInputOrList, models.OptimizationInputOrList],
    package: Union[models.SupportedEngines, models.SupportedProcedures],
    queue: Optional[str] = None,
) -> Union[task_models.GroupTask, task_models.Task]:
    """Accept inputs_data and celery_task, begins task, return Task models"""
    task: Union[task_models.GroupTask, task_models.Task]

    if isinstance(input_data, list):
        validate_group_length(input_data)
        for inp in input_data:
            _b64_to_bytes(inp)

        c_task = group(
            signature_from_input(inp, package) for inp in input_data
        ).apply_async(queue=queue)
        task = task_models.GroupTask.from_celery(c_task)

    else:
        _b64_to_bytes(input_data)
        c_task = signature_from_input(input_data, package).apply_async(queue=queue)
        task = task_models.Task.from_celery(c_task)
    return task


def signature_from_input(
    input_data: Union[AtomicInput, models.OptimizationInput],
    package: Union[models.SupportedEngines, models.SupportedProcedures],
) -> Signature:
    """Return the celery signature for a compute task"""
    if package == models.SupportedEngines.TCC:
        tcc_kwargs = input_data.extras.get(settings.tcc_kwargs_extras_key, {})
        engine = tcc_kwargs.pop("gradient_engine", models.SupportedEngines.TERACHEM_FE)
        return compute_tcc(input_data, engine, **tcc_kwargs)

    elif isinstance(input_data, AtomicInput):
        return tasks.compute.s(input_data, package)
    else:
        return tasks.compute_procedure.s(input_data, package)
