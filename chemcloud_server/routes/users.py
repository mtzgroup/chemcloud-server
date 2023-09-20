import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import jwt

from chemcloud_server import config
from chemcloud_server.auth import _get_matching_rsa_key, _validate_jwt

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
            return RedirectResponse(f"{settings.users_prefix}/login")

    else:
        logger.info("User not logged in. Redirecting to login...")
        return RedirectResponse(f"{settings.users_prefix}/login")

    return f"""
        <html>
            <head>
                <title>Dashboard</title>
                <link rel="shortcut icon" href="/favicon.ico" type="image/icon">
                <link rel="icon" href="/favicon.ico" type="image/icon">
            </head>
            <body>
                <h3>✨ You are registered for ChemCloud! Your username is: {id_payload['email']} ✨</h3>
                <ul>
                    <li>Install the <a href="https://pypi.org/project/chemcloud/" target="_blank">python client</a> and get coding!</li>
                    <li>Check out the <a href="/docs">interactive docs</a> to learn more about ChemCloud data types.</li>
                    <li>If you need to change your password please logout, then click "Dashboard", then click "Forgot Password".</li>
                    <li><a href="/users/logout">Logout</a></li>
                </ul>
            </body>
        </html>
    """  # noqa: E501


@router.get(
    "/login",
    include_in_schema=False,
)
def login(
    redirect_path: str = "api/v2/oauth/auth0/callback",
    signup: Optional[bool] = False,
    settings: config.Settings = Depends(config.get_settings),
    scope: str = "openid profile email offline_access",
):
    """Main login link"""
    url = (
        f"https://{settings.auth0_domain}/authorize"
        "?response_type=code"
        f"&client_id={settings.auth0_client_id}"
        f"&redirect_uri="
        f"{settings.base_url}{redirect_path}"
        # f"&audience={settings.auth0_api_audience}" # No audience because no JWT needed
        f"&scope={scope}"
    )
    if signup:
        url += "&screen_hint=signup"
    return RedirectResponse(url)


@router.get("/logout", include_in_schema=False, response_class=RedirectResponse)
def logout(
    settings: config.Settings = Depends(config.get_settings),
    post_logout_redirect_route=None,
) -> RedirectResponse:
    redirect_route = post_logout_redirect_route or settings.auth0_default_logout_route
    response = RedirectResponse(
        url=(
            f"https://{settings.auth0_domain}/v2/logout"
            f"?client_id={settings.auth0_client_id}"
            f"&returnTo={settings.base_url}{redirect_route}"
        )
    )
    response.delete_cookie(key=settings.id_token_cookie_key)
    response.delete_cookie(key=settings.refresh_token_cookie_key)

    return response
