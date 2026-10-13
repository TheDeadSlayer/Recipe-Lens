import logging
import logging.config
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.db.session import engine
from app.services import get_providers

settings = get_settings()

# ── Structured JSON logging ───────────────────────────────────────────────────
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            }
        },
        "root": {
            "handlers": ["console"],
            "level": settings.log_level.upper(),
        },
    }
)

logger = logging.getLogger(__name__)


# ── Application lifespan ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Instantiate providers once at startup — avoids per-request construction
    # and ensures the OpenAI HTTP client (when active) is created once.
    transcript_provider, recipe_extractor = get_providers()
    app.state.transcript_provider = transcript_provider
    app.state.recipe_extractor = recipe_extractor
    logger.info(
        "Providers initialised transcript=%s llm=%s",
        settings.transcript_provider,
        settings.llm_provider,
    )
    yield
    # Cleanup (close any provider connections) can go here in future


# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(title="RecipeLens", version="0.1.0", lifespan=lifespan)

# CORS must be added before any other middleware so the OPTIONS pre-flight
# response is returned before the request reaches application code.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


# ── Request ID middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Health / readiness probes ─────────────────────────────────────────────────
@app.get("/health", tags=["observability"])
def health() -> dict:
    """Liveness probe — always returns 200 if the process is alive."""
    return {"status": "ok"}


@app.get("/ready", tags=["observability"])
def ready() -> dict:
    """Readiness probe — returns 200 only when the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
