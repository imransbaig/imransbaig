"""FastAPI application entry point for the Agentic Health Coach."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import action, coach, cue, feedback, state, sync
from app.schemas import HealthResponse
from app.sms_gatekeeper.router import router as sms_router
import app.sms_gatekeeper.models  # noqa: F401  -- register model with Base

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    On startup: creates all database tables (if they don't exist).
    On shutdown: performs any necessary cleanup.
    """
    logger.info("Starting Agentic Health Coach API")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")
    yield
    logger.info("Shutting down Agentic Health Coach API")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agentic Health Coach API",
    description=(
        "Backend API for the Agentic Health Coach. Ingests wearable sensor "
        "data, infers physiological states, recommends actions with full "
        "reason traces, and captures user feedback for continuous improvement."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(sync.router)
app.include_router(state.router)
app.include_router(action.router)
app.include_router(cue.router)
app.include_router(feedback.router)
app.include_router(coach.router)
app.include_router(sms_router)

# ---------------------------------------------------------------------------
# Static Files & PWA
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check",
    description="Returns the API health status and version.",
)
def health_check() -> HealthResponse:
    """Return a simple health-check response."""
    return HealthResponse()


@app.get("/", include_in_schema=False)
def serve_pwa() -> FileResponse:
    """Serve the PWA index.html at the root URL."""
    return FileResponse(str(_STATIC_DIR / "index.html"), media_type="text/html")
