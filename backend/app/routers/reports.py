import uuid
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models.job import Report
from app.utils.auth import verify_token

router = APIRouter(prefix="/api", tags=["reports"])


class ReportResponse(BaseModel):
    id: str
    job_id: str
    repo_summary: Optional[dict]
    bugs: Optional[dict]
    security_issues: Optional[dict]
    docs_suggestions: Optional[dict]
    final_review: Optional[dict]
    severity_score: Optional[int]
    confidence_score: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """Fetch the full structured report for a completed job."""
    try:
        uid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")

    result = await db.execute(select(Report).where(Report.id == uid))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse(
        id=str(report.id),
        job_id=str(report.job_id),
        repo_summary=report.repo_summary,
        bugs=report.bugs,
        security_issues=report.security_issues,
        docs_suggestions=report.docs_suggestions,
        final_review=report.final_review,
        severity_score=report.severity_score,
        confidence_score=report.confidence_score,
        created_at=report.created_at,
    )


@router.get("/reports/{report_id}/pdf")
async def download_report_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """Download the generated PDF report."""
    try:
        uid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")

    result = await db.execute(select(Report).where(Report.id == uid))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.pdf_path or not os.path.exists(report.pdf_path):
        raise HTTPException(status_code=404, detail="PDF not yet generated")

    return FileResponse(
        path=report.pdf_path,
        media_type="application/pdf",
        filename=f"report_{report_id[:8]}.pdf",
    )