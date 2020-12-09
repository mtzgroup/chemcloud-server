import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import jwt

from terachem_cloud import config
from terachem_cloud.auth import _get_matching_rsa_key, _validate_jwt

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard", include_in_schema=False, response_class=HTMLResponse)
async def dashboard(
    id_token: str = Cookie(None),
    settings: config.Settings = Depends(config.get_settings),
):
    """Main User Dashboard"""
    if id_token:
        try:
            id_token_rsa_key = _get_matching_rsa_key(id_token, settings.jwks)
            id_payload = _validate_jwt(
                id_token,
                id_token_rsa_key,
                audience=settings.auth0_client_id,
                algorithms=settings.auth0_algorithms,
                issuer=settings.jwt_issuer,
            )
        except (jwt.JWTClaimsError, jwt.ExpiredSignatureError):
            logger.exception("Could not validate token.")
            return RedirectResponse("/users/login")

    else:
        logger.info("User not logged in. Redirecting to login...")
        return RedirectResponse("/users/login")

    return f"""
        <html>
            <head>
                <title>Dashboard</title>
                <link rel="shortcut icon" href="/favicon.ico" type="image/icon">
                <link rel="icon" href="/favicon.ico" type="image/icon">
            </head>
            <body>
                <h3>✨ You have signed up for TeraChem Cloud! Your username is: {id_payload['email']} ✨</h3>
            </body>
        </html>
    """


@router.get("/login")
def login(
    request: Request,
    redirect_path: str = "/api/v1/oauth/auth0/callback",
    signup: Optional[bool] = False,
    settings: config.Settings = Depends(config.get_settings),
    scope: str = "openid profile email offline_access",
    include_in_schema=False,
):
    """Main login link"""
    url = (
        f"https://{settings.auth0_domain}/authorize"
        "?response_type=code"
        f"&client_id={settings.auth0_client_id}"
        f"&redirect_uri="
        f"{request.scope['type']}"  # http(s)
        f"://{request.scope['server'][0]}:{request.scope['server'][1]}"  # host:port
        f"{redirect_path}"  # passed path for redirect
        # f"&audience={settings.auth0_api_audience}" # No audience because no JWT needed
        f"&scope={scope}"
    )
    if signup:
        url += "&screen_hint=signup"
    return RedirectResponse(url)


@router.get("/logout", include_in_schema=False)
def logout():
    return RedirectResponse(
        "https://dev-mtzlab.us.auth0.com/v2/logout?client_id=lQvfKdlfxLE0E9mVEIl58Wi9gX2AwWop&returnTo=http%3A%2F%2Flocalhost:8000"
    )
