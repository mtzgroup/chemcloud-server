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
        "description": "Authentication endpoints to obtain JWTs to access API.",
    },
    {
        "name": "compute",
        "description": "Perform computations and obtain results using TeraChem Cloud.",
    },
]


app = FastAPI(
    title="TeraChem Cloud",
    description="Quantum chemistry at cloud scale",
    version="0.1.0",
    openapi_tags=tags_metadata,
)

# Add routes
app.include_router(oauth.router, prefix=f"{settings.api_v1_str}/oauth", tags=["auth"])
app.include_router(
    compute.router,
    prefix=f"{settings.api_v1_str}/compute",
    dependencies=[Security(bearer_auth, scopes=["compute:public"])],
    tags=["compute"],
)
app.include_router(users.router, prefix="/users")


@app.get("/")
async def index():
    return {"TeraChem": "Cloud"}


@app.get("/signup", include_in_schema=False)
def signup(redirect_path: str = "/users/dashboard"):
    """Convenience URL to sign up for TCC"""
    return RedirectResponse(f"login/?signup=true&redirect_path={redirect_path}")


app.mount("/", StaticFiles(directory="static", html=True), name="static")
