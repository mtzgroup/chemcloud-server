from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestFormStrict
from starlette.responses import RedirectResponse

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

    flow_model = models.OAuth2PasswordFlow(
        audience=settings.auth0_api_audience,
        client_id=settings.auth0_client_id,
        client_secret=settings.auth0_client_secret,
        username=form_data.username,
        password=form_data.password,
        scope=" ".join(form_data.scopes),
    )
    return await _auth0_token_request(flow_model)


@router.get("/auth0/callback", include_in_schema=False, response_class=RedirectResponse)
async def auth0_callback(
    code: str,
    settings: config.Settings = Depends(config.get_settings),
) -> RedirectResponse:
    """Callback for Auth0 Authorization Code Flow"""
    # Trade username and password for token(s) from Auth0
    flow_model = models.OAuth2AuthorizationCodeFlow(
        client_id=settings.auth0_client_id,
        client_secret=settings.auth0_client_secret,
        audience=settings.auth0_api_audience,
        code=code,
        redirect_uri=settings.base_url,
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
    response = RedirectResponse(url="/users/dashboard")
    response.set_cookie(
        key=settings.id_token_cookie_key, value=tokens["id_token"], httponly=True
    )
    response.set_cookie(
        key=settings.refresh_token_cookie_key,
        value=tokens["refresh_token"],
        httponly=True,
    )
    return response
