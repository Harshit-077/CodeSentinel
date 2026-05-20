import uuid
import os
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.job import Job
from app.utils.auth import verify_token
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api", tags=["upload"])


class GithubSubmitRequest(BaseModel):
    github_url: str  # e.g. https://github.com/user/repo


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str
    message: str


async def _save_job(db: AsyncSession, source_type: str, source_ref: str) -> Job:
    """Create and persist a new Job row."""
    job = Job(
        id=uuid.uuid4(),
        status="pending",
        source_type=source_type,
        source_ref=source_ref,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def _trigger_pipeline(job_id: str):
    """
    Background task — imports and runs the full agent pipeline.
    Imported here to avoid circular imports at startup.
    """
    from app.services.agents.graph import run_pipeline
    await run_pipeline(job_id=job_id)


@router.post("/upload/github", response_model=JobCreatedResponse)
async def submit_github(
    payload: GithubSubmitRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """Accept a GitHub repo URL and kick off analysis."""
    url = payload.github_url.strip()
    if not url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Must be a valid https://github.com/ URL")

    job = await _save_job(db, source_type="github", source_ref=url)
    background_tasks.add_task(_trigger_pipeline, str(job.id))

    logger.info("GitHub job created", job_id=str(job.id), url=url)
    return JobCreatedResponse(
        job_id=str(job.id),
        status="pending",
        message="Analysis started. Poll /api/jobs/{job_id} for status.",
    )


@router.post("/upload/zip", response_model=JobCreatedResponse)
async def submit_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """Accept a ZIP file and kick off analysis."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")

    # Persist the file to disk
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    dest_path = os.path.join(settings.upload_dir, f"{file_id}.zip")

    async with aiofiles.open(dest_path, "wb") as out:
        content = await file.read()
        await out.write(content)

    job = await _save_job(db, source_type="zip", source_ref=dest_path)
    background_tasks.add_task(_trigger_pipeline, str(job.id))

    logger.info("ZIP job created", job_id=str(job.id), filename=file.filename)
    return JobCreatedResponse(
        job_id=str(job.id),
        status="pending",
        message="Analysis started. Poll /api/jobs/{job_id} for status.",
    )