"""Main module for the FastAPI app. Also contains convenience paths that route """
from fastapi import FastAPI, Security
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

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
        "description": "Submit compute requests and obtain results.",
    },
    {
        "name": "default",
        "description": "Try out the interactive docs using this endpoint!",
    },
]


app = FastAPI(
    title="TeraChem Cloud",
    description="⚛ Quantum Chemistry at Cloud Scale ⚛",
    version="0.1.0",
    openapi_tags=tags_metadata,
)

# Add routes
app.include_router(
    oauth.router,
    prefix=f"{settings.api_v1_str}{settings.api_oauth_prefix}",
    tags=["auth"],
)
app.include_router(
    compute.router,
    prefix=f"{settings.api_v1_str}{settings.api_compute_prefix}",
    dependencies=[Security(bearer_auth, scopes=["compute:public"])],
    tags=["compute"],
)
app.include_router(users.router, prefix=f"{settings.users_prefix}")


@app.get("/", include_in_schema=False)
async def index():
    return RedirectResponse("/docs")


@app.get("/hello-world")
async def hello_world():
    return {"Welcome to": "TeraChem Cloud"}


@app.get("/signup", include_in_schema=False)
def signup(redirect_path: str = None):
    """Convenience URL to sign up for TCC"""
    destination_url = "users/login?signup=true"
    if redirect_path:
        destination_url += f"&redirect_path={redirect_path}"
    return RedirectResponse(destination_url)


@app.get("/buddy-groups")
def buddy_groups():
    "Buddy group method!"

    return {"Buddy groups": "rock!"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
