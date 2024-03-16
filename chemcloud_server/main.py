"""Main module for the FastAPI app. Also contains convenience paths that route """

from typing import Optional

from fastapi import FastAPI, Security
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from chemcloud_server import __version__

from .auth import bearer_auth
from .config import get_settings
from .routes import compute, oauth, users

settings = get_settings()

tags_metadata = [
    {
        "name": "auth",
        "description": "Authentication endpoints to obtain JWTs for API access.",
    },
    {
        "name": "compute",
        "description": "Submit computations and obtain results.",
    },
    {
        "name": "hello world",
        "description": "Try out the interactive docs using this endpoint!",
    },
]


app = FastAPI(
    title="ChemCloud",
    description=(
        "⚛ Computational Chemistry at Cloud Scale ⚛ [Signup here](/signup) or visit "
        "your [Dashboard](/users/dashboard)"
    ),
    version=__version__,
    openapi_tags=tags_metadata,
)

# Add routes
app.include_router(
    oauth.router,
    prefix=f"{settings.api_v2_str}{settings.api_oauth_prefix}",
    tags=["auth"],
)
app.include_router(
    compute.router,
    prefix=f"{settings.api_v2_str}{settings.api_compute_prefix}",
    dependencies=[Security(bearer_auth, scopes=["compute:public"])],
    tags=["compute"],
)
app.include_router(users.router, prefix=f"{settings.users_prefix}")


@app.get("/", include_in_schema=False)
async def index():
    return RedirectResponse("/docs")


@app.get("/hello-world", tags=["hello world"])
async def hello_world(name: Optional[str] = None):
    return f"Welcome to ChemCloud, {name or 'friend'}!"


@app.get("/signup", include_in_schema=False)
def signup(redirect_path: Optional[str] = None):
    """Convenience URL to sign up for QCC"""
    destination_url = "users/login?signup=true"
    if redirect_path:
        destination_url += f"&redirect_path={redirect_path}"
    return RedirectResponse(destination_url)


app.mount("/", StaticFiles(directory="static", html=True), name="static")


# Append max_batch_inputs limit to OpenAPI schema so clients are aware of it
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description=app.description,
    )
    openapi_schema["tags"] = tags_metadata
    openapi_schema["info"]["x-max_batch_inputs"] = settings.max_batch_inputs
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Ok to assign to a method here
app.openapi = custom_openapi  # type: ignore
