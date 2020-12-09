from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestFormStrict

from terachem_cloud import config, models
from terachem_cloud.auth import _get_matching_rsa_key, _validate_jwt
from terachem_cloud.utils import _auth0_token_request

router = APIRouter()


@router.post("/token")
async def token(
    form_data: OAuth2PasswordRequestFormStrict = Depends(),
    settings: config.Settings = Depends(config.get_settings),
):
    """Route for Resource Owner Password Flow OAuth token generation

    https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/
    https://auth0.com/docs/flows/resource-owner-password-flow
    """
    # NOTE: Maybe add "compute:public" scope to all tokens by default initially?
    flow_model = models.OAuth2PasswordFlow(
        audience=settings.auth0_api_audience,
        client_id=settings.auth0_client_id,
        client_secret=settings.auth0_client_secret,
        username=form_data.username,
        password=form_data.password,
        scope=" ".join(form_data.scopes),
    )
    return await _auth0_token_request(flow_model)


@router.get("/auth0/callback", include_in_schema=False)
async def auth0_callback(
    code: str,
    request: Request,
    response: Response,
    settings: config.Settings = Depends(config.get_settings),
):
    """Callback for Auth0 Authorization Code Flow"""
    # Trade username and password for token(s) from Auth0
    redirect_uri = (
        f"{request.scope['type']}"
        f"://{request.scope['server'][0]}:{request.scope['server'][1]}"
        f"{request.scope['path']}"
    )
    flow_model = models.OAuth2AuthorizationCodeFlow(
        client_id=settings.auth0_client_id,
        client_secret=settings.auth0_client_secret,
        audience=settings.auth0_api_audience,
        code=code,
        redirect_uri=redirect_uri,
    )
    tokens = await _auth0_token_request(flow_model)

    # Validate Tokens
    id_token_rsa_key = _get_matching_rsa_key(tokens["id_token"], settings.jwks)
    _validate_jwt(
        tokens["id_token"],
        id_token_rsa_key,
        audience=settings.auth0_client_id,
        algorithms=settings.auth0_algorithms,
        issuer=settings.jwt_issuer,
    )

    # Set tokens as cookies
    response.set_cookie(key="id_token", value=tokens["id_token"], httponly=True)
    response.set_cookie(
        key="refresh_token", value=tokens["refresh_token"], httponly=True
    )

    # Manually make redirect response
    response.status_code = 307
    response.headers["location"] = "/users/dashboard"

    return response
