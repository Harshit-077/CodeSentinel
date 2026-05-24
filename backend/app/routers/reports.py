import uuid
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models.job import Report
from app.utils.auth import verify_token
from app.config import get_settings

settings = get_settings()
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
    pdf_ready: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
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
        pdf_ready=bool(report.pdf_path and os.path.exists(report.pdf_path)),
        created_at=report.created_at,
    )


@router.get("/reports/{report_id}/pdf")
async def download_report_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """Download the generated PDF. Auth via Bearer header or ?token= query param."""
    try:
        uid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")

    result = await db.execute(select(Report).where(Report.id == uid))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.pdf_path or not os.path.exists(report.pdf_path):
        raise HTTPException(status_code=404,
            detail="PDF not yet generated. Wait for job to complete.")

    return FileResponse(
        path=report.pdf_path,
        media_type="application/pdf",
        filename=f"code-review-{str(report_id)[:8]}.pdf",
    )


 
@router.get("/reports/{report_id}/evaluation")
async def get_evaluation_scores(
    report_id: str,
    _user: str = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns RAGAS evaluation scores for a completed report.
 
    Response shape:
    {
        "report_id": 42,
        "job_id": 7,
        "langsmith_url": "https://smith.langchain.com/...",
        "evaluation": {
            "per_agent": {
                "bug":      {"faithfulness": 0.85, "answer_relevancy": 0.91, "context_precision": 0.78},
                "security": {"faithfulness": 0.90, ...},
                "docs":     {"faithfulness": 0.80, ...}
            },
            "overall":      {"faithfulness": 0.85, "answer_relevancy": 0.90, "context_precision": 0.78},
            "sample_count": 3,
            "error":        null
        }
    }
    """
    # Fetch the report
    try:
        uid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")

    result = await db.execute(
        select(Report).where(Report.id == uid)
    )
    report = result.scalar_one_or_none()
 
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
 
    if report.evaluation_scores is None:
        raise HTTPException(
            status_code=202,
            detail="Evaluation scores not yet available. Pipeline may still be running.",
        )
 
    # Build LangSmith trace URL
    # The run is named "codesentinel-job-{job_id}" in graph.py
    langsmith_url = (
        f"https://smith.langchain.com/projects/{settings.langchain_project}"
        if settings.langchain_api_key
        else None
    )
 
    return {
        "report_id":     str(report.id),
        "job_id":        str(report.job_id),
        "langsmith_url": langsmith_url,
        "evaluation":    report.evaluation_scores,
    }
