import json
from base64 import b64decode, b64encode
from typing import Any, Dict, List, Optional, Union

import httpx
from bigchem import tasks
from bigchem.algos import parallel_frequency_analysis, parallel_hessian
from bigchem.app import bigchem
from celery.canvas import Signature, group
from celery.result import AsyncResult, GroupResult, ResultBase, result_from_tuple
from fastapi import HTTPException
from fastapi import status as status_codes
from qcelemental.models import (
    AtomicInput,
    AtomicResult,
    DriverEnum,
    OptimizationInput,
    OptimizationResult,
)
from tcpb.config import settings as tcpb_settings

from chemcloud_server import config, models

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
    except json.JSONDecodeError:
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


def _b64_encode_dict_values(d: Dict[str, Any]) -> None:
    """Convert all bytes in dictionary values to b64 encoded string"""
    bytes_keys = [key for key, value in d.items() if isinstance(value, bytes)]
    for key in bytes_keys:
        value_bytes = d.pop(key)
        d[f"{key}{B64_POSTFIX}"] = b64encode(value_bytes).decode()


def _bytes_to_b64(
    result: Union[models.PossibleResults, List[models.PossibleResults]]
) -> None:
    """Convert binary native_files and tcfe:keywords to b64 encoded strings

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
        # Encode natives files
        if res.native_files:
            _b64_encode_dict_values(res.native_files)

        # Encode any supplied bytes inputs
        _b64_encode_dict_values(res.extras.get(tcpb_settings.tcfe_keywords, {}))


def _b64_to_bytes(input_data: Union[AtomicInput, OptimizationInput]) -> None:
    """Convert base64 encoded string values to bytes. Modifies inputs in place.

    Because JSON does not have a bytes data type, binary data sent to QCC for
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


def save_result(result: Union[AsyncResult, GroupResult]) -> None:
    """Save result compute structure to backend"""
    result.backend.set(result.id, json.dumps(result.as_tuple()))


def restore_result(result_id: str) -> Union[AsyncResult, GroupResult]:
    """Restore result (including parents) from backend

    Raises:
        ValueError if result not found in backend
    """
    try:
        return result_from_tuple(json.loads(bigchem.backend.get(result_id)))
    except TypeError:
        raise ValueError(f"Result id '{result_id}', not found.")


def compute_inputs_async(
    input_data: Union[models.AtomicInputOrList, models.OptimizationInputOrList],
    package: Union[models.SupportedEngines, models.SupportedProcedures],
    queue: Optional[str] = None,
) -> str:
    """Accept inputs_data and celery_task, begins task, return Task models"""
    if isinstance(input_data, list):
        validate_group_length(input_data)
        for inp in input_data:
            _b64_to_bytes(inp)

        result = group(
            signature_from_input(inp, package) for inp in input_data
        ).apply_async(queue=queue)

    else:
        _b64_to_bytes(input_data)
        result = signature_from_input(input_data, package).apply_async(queue=queue)

    # Save result structure to DB so can be rehydrated using only id
    save_result(result)
    return result.id


def signature_from_input(
    input_data: Union[AtomicInput, models.OptimizationInput],
    package: Union[models.SupportedEngines, models.SupportedProcedures],
) -> Signature:
    """Return the celery signature for a compute task

    NOTE: Must pass enum.value to underlying functions so that celery doesn't try to
        deserialize an object containing references to Enums that live in chemcloud_server
    """
    if package == models.SupportedEngines.BIGCHEM:
        bigchem_kwargs = input_data.extras.get(settings.bigchem_keywords, {})
        engine = bigchem_kwargs.pop(
            "gradient_engine", models.SupportedEngines.TERACHEM_FE.value
        )
        return compute_bigchem(input_data, engine, **bigchem_kwargs)

    elif isinstance(input_data, AtomicInput):
        return tasks.compute.s(input_data, package.value)
    else:
        return tasks.compute_procedure.s(input_data, package.value)


def compute_bigchem(
    input_data: AtomicInput,
    engine: str = models.SupportedEngines.TERACHEM_FE.value,
    **kwargs,
) -> Signature:
    """Top level function for parallelized BigChem algorithms

    Use compute_qcc and pass AtomicInput to get back a signature that can be called
    asynchronously.

    Params:
        input_data: Input specification; driver may be hessian or properties
        engine: Compute engine to use for gradient calculations. Must pass string rather
            than Enum so that BigChem deserialization doesn't try to deserialize an object
            containing Enums from chemcloud package.
        kwargs: kwargs for parallel_hessian or parallel_frequency_analysis
    """

    SUPPORTED_DRIVERS = [DriverEnum.hessian, DriverEnum.properties]
    assert input_data.driver in SUPPORTED_DRIVERS, (
        f"Driver '{input_data.driver}' not supported. Supported drivers include: "
        f"{SUPPORTED_DRIVERS}"
    )

    if input_data.driver == DriverEnum.hessian:
        return parallel_hessian(input_data, engine, **kwargs)
    else:
        return parallel_frequency_analysis(input_data, engine, **kwargs)


def delete_result(result: ResultBase) -> None:
    """Delete Celery result(s) from backend"""
    # Remove result definition
    result.backend.delete(result.id)
    # Remove all results and parents
    result.forget()
