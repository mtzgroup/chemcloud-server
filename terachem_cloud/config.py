"""Settings and Configuration. Read more: https://fastapi.tiangolo.com/advanced/settings/"""
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException
from pydantic import AnyHttpUrl, BaseSettings


class Settings(BaseSettings):
    """Main Settings object for application.

    Never instantiate this class directly. Use the get_settings() method below.

    Will read environment variables and docker secrets automatically and map to lowercase
    https://pydantic-docs.helpmanual.io/usage/settings/
    """

    api_v1_str: str = "/api/v1"
    api_compute_prefix: str = "/compute"
    api_oauth_prefix: str = "/oauth"
    users_prefix: str = "/users"
    # NOTE: AnyHttpUrl usage seems correct; not sure why mypy doesn't like it
    # https://pydantic-docs.helpmanual.io/usage/settings/
    base_url: AnyHttpUrl = "http://localhost:8000"  # type: ignore
    id_token_cookie_key: str = "id_token"
    refresh_token_cookie_key: str = "refresh_token"
    max_batch_inputs: int = 100

    # NOTE: Adding "" values as defaults so tests can run on CircleCi without having
    # to set these auth0 values
    auth0_domain: str = ""
    auth0_client_id: str = ""
    auth0_client_secret: str = ""
    auth0_api_audience: str = ""
    auth0_default_logout_route: str = "/docs"
    auth0_algorithms: List[str] = ["RS256"]
    jwks: List[Dict[str, Any]] = [{}]
    jwt_issuer: str = ""

    class Config:
        _docker_secrets_dir = "/run/secrets"
        env_file = ".env"
        if Path(_docker_secrets_dir).is_dir():
            secrets_dir = _docker_secrets_dir


def _get_jwks(domain: str) -> List[Dict[str, str]]:
    """Get JSON Web Keys used to validate tokens"""
    url = f"https://{domain}/.well-known/jwks.json"
    response = httpx.get(url)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()["keys"]


@lru_cache()
def get_settings():
    """Settings object to use throughout the app as a dependency
    https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru_cache
    """
    # Add JWKs using auth0 settings
    initial_settings = Settings()
    as_dict = initial_settings.dict()
    if initial_settings.auth0_domain:
        as_dict["jwks"] = _get_jwks(initial_settings.auth0_domain)
        as_dict["jwt_issuer"] = f"https://{initial_settings.auth0_domain}/"
    return Settings(**as_dict)
