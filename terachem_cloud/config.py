"""Settings and Configuration. Read more: https://fastapi.tiangolo.com/advanced/settings/"""
from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException
from pydantic import BaseSettings


def _get_jwks(domain: str) -> List[Dict[str, str]]:
    """Get JSON Web Keys used to validate tokens"""
    url = f"https://{domain}/.well-known/jwks.json"
    response = httpx.get(url)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()["keys"]


class Settings(BaseSettings):
    """Main Settings object for application.

    Never instantiate this class directly. Use the get_settings() method below.

    Will read environment variables and docker secrets automatically and map to lowercase
    https://pydantic-docs.helpmanual.io/usage/settings/
    """

    api_v1_str: str = "/api/v1"

    auth0_domain: Optional[str] = None
    auth0_client_id: Optional[str] = None
    auth0_client_secret: Optional[str] = None
    auth0_api_audience: Optional[str] = None
    auth0_algorithms: List[str] = ["RS256"]
    jwks: Optional[List[Dict[str, Any]]] = None
    jwt_issuer: Optional[str] = None
    celery_broker_connection_string: str = "amqp://localhost"
    celery_backend_connection_string: str = "redis://localhost/0"

    class Config:
        _docker_secrets_dir = "/run/secrets"
        env_file = ".env"
        if Path(_docker_secrets_dir).is_dir():
            secrets_dir = _docker_secrets_dir


@lru_cache()
def get_settings():
    """Settings object to use throughout the app as a dependency
    https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru_cache
    """
    # Add JWKs using envars if available
    jwks = None
    jwt_issuer = None
    auth0_domain = getenv("AUTH0_DOMAIN")
    if auth0_domain:
        jwks = _get_jwks(auth0_domain)
        jwt_issuer = f"https://{auth0_domain}/"
    return Settings(jwks=jwks, jwt_issuer=jwt_issuer)
