from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.param_functions import Form
from starlette.responses import RedirectResponse

from terachem_cloud import config, models
from terachem_cloud.auth import _get_matching_rsa_key, _validate_jwt
from terachem_cloud.utils import _auth0_token_request

router = APIRouter()


class OAuth2RequestForm:
    """
    This is a dependency class, modeled after
    fastapi.security.OAuth2PasswordRequestFormStrict; see fastapi objet for reference.
    """

    def __init__(
        self,
        grant_type: str = Form(..., regex=r"password|refresh_token"),
        username: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        refresh_token: Optional[str] = Form(None),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None),
        scope: str = Form(""),
    ):
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.refresh_token = refresh_token
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret


@router.post("/token")
async def token(
    form_data: OAuth2RequestForm = Depends(),
    settings: config.Settings = Depends(config.get_settings),
):
    """Route for OAuth2 requests to TeraChem Cloud"""
    if form_data.grant_type == "password":
        flow_model = models.OAuth2PasswordFlow(
            audience=settings.auth0_api_audience,
            client_id=settings.auth0_client_id,
            client_secret=settings.auth0_client_secret,
            username=form_data.username,
            password=form_data.password,
            scope=" ".join(form_data.scopes),
        )
    elif form_data.grant_type == "refresh_token":
        flow_model = models.OAuth2RefreshFlow(
            client_id=settings.auth0_client_id,
            client_secret=settings.auth0_client_secret,
            refresh_token=form_data.refresh_token,
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
