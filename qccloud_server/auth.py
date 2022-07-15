from typing import Any, Dict, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.oauth2 import SecurityScopes
from jose import jwt

from qccloud_server import config

from .config import get_settings

oauth2_password_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/oauth/token",
    scopes={
        "compute:public": "Perform computations and retrieve results as a public user.",
        "compute:private": "Perform computations and retrieve results computed on private Quantum Chemistry Connect instances.",
    },
)


def _validate_jwt(
    token: str,
    rsa_key: Dict[str, str],
    *,
    algorithms: List[str],
    issuer: str,
    audience: str = None,
    security_scopes: SecurityScopes = None,
) -> Dict[str, Any]:
    """Validate JWT using rsa_key; check scopes, return payload."""
    payload = jwt.decode(
        token,
        rsa_key,
        algorithms=algorithms,
        audience=audience,
        issuer=issuer,
    )
    token_scopes = payload.get("scope", "").split()

    # Validate scopes
    if security_scopes:
        for scope in security_scopes.scopes:
            if scope not in token_scopes:
                raise jwt.JWTClaimsError("Insufficient scopes")
    return payload


def _get_matching_rsa_key(token: str, jwks: List[Dict[str, str]]) -> Dict[str, str]:
    """Find matching key, return fields for JWT decode"""
    # Return JWT header as dict
    unverified_header = jwt.get_unverified_header(token)
    for key in jwks:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
        return rsa_key
    raise ValueError(f"No matching key found for token '{token}' in keys {jwks}")


async def bearer_auth(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_password_scheme),
    settings: config.Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """Validates access token"""
    # Determine WWW-Authenticate header value
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    # Define main credentials exception
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    # Find correct key to verify signature
    try:
        rsa_key = _get_matching_rsa_key(token, settings.jwks)

    except jwt.JWTError:
        credentials_exception.detail = "Invalid token"
        raise credentials_exception

    # Decode token and validate
    if rsa_key:
        try:
            payload = _validate_jwt(
                token,
                rsa_key,
                algorithms=settings.auth0_algorithms,
                audience=settings.auth0_api_audience,
                issuer=settings.jwt_issuer,
                security_scopes=security_scopes,
            )
        except jwt.ExpiredSignatureError:
            credentials_exception.detail = "token is expired"
            raise credentials_exception
        except jwt.JWTClaimsError:
            credentials_exception.detail = (
                "incorrect claims, please check the audience, issuer, and/or scope"
            )
            raise credentials_exception
        except Exception:
            credentials_exception.detail = "Unable to parse authentication token."
            raise credentials_exception
    else:
        credentials_exception.detail = "Unable to find appropriate key"
        raise credentials_exception

    return payload
