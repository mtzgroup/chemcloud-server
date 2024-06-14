import json
from typing import Any, Optional

import httpx
from bigchem.algos import parallel_frequency_analysis
from bigchem.app import bigchem as bigchem_app
from bigchem.canvas import Signature
from bigchem.tasks import compute
from celery.result import AsyncResult, GroupResult, ResultBase, result_from_tuple
from fastapi import HTTPException
from qcio import CalcType, DualProgramInput, ProgramInput

from chemcloud_server import config, models
from chemcloud_server.exceptions import ResultNotFoundError
from chemcloud_server.models import QCIOInputs

settings = config.get_settings()


async def _external_request(
    method: str,
    url: str,
    headers: Optional[dict[str, str]] = None,
    data: Optional[dict[str, Any]] = None,
) -> dict[Any, Any]:
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
) -> dict[Any, Any]:
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


def save_dag(result: AsyncResult | GroupResult) -> None:
    """Save DAG of result (including parents) to backend.

    This makes it possible to just return the result id from the compute endpoint for
    GroupResult objects and rehydrate the DAG later using just the result id.
    """
    result.backend.set(result.id, json.dumps(result.as_tuple()))


def restore_result(result_id: str) -> AsyncResult | GroupResult:
    """Restore result (including parents) from backend

    Raises:
        ResultNotFoundError if DAG not found in backend
    """
    try:
        return result_from_tuple(
            json.loads(bigchem_app.backend.get(result_id)), app=bigchem_app
        )
    except TypeError:
        raise ResultNotFoundError(result_id)


def signature_from_input(
    program: models.SupportedPrograms,
    inp_obj: QCIOInputs,
    compute_kwargs: dict[str, Any],
) -> Signature:
    """Return the celery signature for a compute task"""
    if program == models.SupportedPrograms.BIGCHEM:
        # Does not support compute_kwargs yet
        assert isinstance(inp_obj, DualProgramInput)  # for mypy
        return compute_bigchem(inp_obj)
    else:
        # Must pass program.value to underlying functions so BigChem doesn't try to
        # deserialize ChemCloud.SupportedPrograms enum.
        return compute.s(program.value, inp_obj, **compute_kwargs)


def compute_bigchem(
    inp_obj: DualProgramInput,
) -> Signature:
    """Top level function for parallelized BigChem algorithms

    Use compute_qcc and pass AtomicInput to get back a signature that can be called
    asynchronously.

    Params:
        inp_obj: DualProgramInput with BigChem as the primary program and a QC program
            for gradients specified as the subprogram.

        NOTE: Keywords for the parallel_hessian and frequency_analysis functions are
            passed as DualProgramInput.keywords.
    """
    # TODO: Maybe add "frequencies" later if I want to disambiguate from hessian
    SUPPORTED_CALCTYPES = {CalcType.hessian}
    assert inp_obj.calctype in SUPPORTED_CALCTYPES, (
        f"Calctype '{inp_obj.calctype}' not supported. Supported calctypes include: "
        f"{SUPPORTED_CALCTYPES}"
    )

    # Construct program input
    prog_inp = ProgramInput(
        calctype=inp_obj.calctype,
        molecule=inp_obj.molecule,
        **inp_obj.subprogram_args.model_dump(),
    )

    # Construct BigChem algorithm (returns Signature)
    if inp_obj.calctype == CalcType.hessian:
        # Running hessian calculation as parallel_frequency_analysis because
        # I haven't added "frequencies" as a calctype. Maybe unnecessary and
        # always do hessian as frequencies?
        return parallel_frequency_analysis(
            inp_obj.subprogram, prog_inp, **inp_obj.keywords
        )
    # NOTE: This case is not currently used
    else:
        return parallel_frequency_analysis(
            inp_obj.subprogram, prog_inp, **inp_obj.keywords
        )


def delete_result(result: ResultBase) -> None:
    """Delete Celery result(s) from backend"""
    # Remove computation DAG
    result.backend.delete(result.id)
    # Remove all results and parents
    result.forget()
