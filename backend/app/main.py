import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_tables
from app.utils.logger import setup_logging, get_logger
from app.routers import upload, jobs, reports, auth, evaluation_router as evaluation

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # ── Startup ──────────────────────────────────────
    setup_logging()
    logger.info("Starting Code Review Platform", env=settings.app_env)

    # Create upload/report directories
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.report_dir, exist_ok=True)

    # Create DB tables (idempotent)
    await create_tables()
    logger.info("Database tables ready")

    yield

    # ── Shutdown ─────────────────────────────────────
    logger.info("Shutting down")


app = FastAPI(
    title="Code Sentinel",
    description="Multi-agent autonomous code review and security intelligence",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(jobs.router)
app.include_router(reports.router)
app.include_router(evaluation.router, prefix="/api/evaluation", tags=["evaluation"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "env": settings.app_env}