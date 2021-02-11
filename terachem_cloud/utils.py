from json.decoder import JSONDecodeError
from typing import Any, Dict

import httpx
from fastapi import HTTPException
from qcelemental.models import Molecule

from terachem_cloud import config, models


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


def pubchem_molecule_lookup(name: str) -> Molecule:
    """Get a molecule from Pubchem given a name"""
    return Molecule.from_data(f"pubchem:{name}")
