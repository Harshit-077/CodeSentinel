import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models.job import Job, AgentLog
from app.utils.auth import verify_token

router = APIRouter(prefix="/api", tags=["jobs"])

from sqlalchemy.orm import selectinload



class AgentLogOut(BaseModel):
    agent_name: str
    status: str
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    source_type: str
    source_ref: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    agent_logs: list[AgentLogOut]
    report_id: Optional[str]


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """Poll this endpoint every 3s from the frontend to track progress."""
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    result = await db.execute(
        select(Job)
        .options(selectinload(Job.report))
        .where(Job.id == uid)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Fetch agent logs
    logs_result = await db.execute(
        select(AgentLog).where(AgentLog.job_id == uid).order_by(AgentLog.created_at)
    )
    logs = logs_result.scalars().all()

    report_id = str(job.report.id) if job.report else None

    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        source_type=job.source_type,
        source_ref=job.source_ref,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        agent_logs=[AgentLogOut.model_validate(log) for log in logs],
        report_id=report_id,
    )