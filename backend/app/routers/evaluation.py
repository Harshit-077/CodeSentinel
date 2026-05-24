"""
Evaluation Router
=================
GET /api/evaluation/{job_id}  – Retrieve RAGAS + LLM-judge results for a job.

Returns:
  200  – Evaluation complete
  202  – Evaluation still running (pending/running)
  404  – No evaluation record found for this job
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any

from app.database import get_db
from app.models.job import EvaluationResult
from app.utils.auth import verify_token

router = APIRouter(prefix="/api", tags=["evaluation"])


class EvaluationResponse(BaseModel):
    id: str
    job_id: str
    status: str                          # pending | running | done | failed
    ragas_scores: Optional[dict]         # per-agent RAGAS metrics
    judge_scores: Optional[dict]         # LLM judge criterion scores
    overall_eval_score: Optional[float]  # 0.0 – 10.0
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/evaluation/{job_id}", response_model=EvaluationResponse)
async def get_evaluation(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(verify_token),
):
    """
    Retrieve evaluation results for a completed job.

    - 200: evaluation complete, full results returned
    - 202: evaluation still in progress (pending/running)
    - 404: no evaluation record found for this job_id
    """
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    result = await db.execute(
        select(EvaluationResult).where(EvaluationResult.job_id == uid)
    )
    eval_row = result.scalar_one_or_none()

    if not eval_row:
        raise HTTPException(
            status_code=404,
            detail="No evaluation found for this job. "
                   "Evaluation runs automatically after the analysis completes.",
        )

    response_data = EvaluationResponse(
        id=str(eval_row.id),
        job_id=str(eval_row.job_id),
        status=eval_row.status,
        ragas_scores=eval_row.ragas_scores,
        judge_scores=eval_row.judge_scores,
        overall_eval_score=eval_row.overall_eval_score,
        error_message=eval_row.error_message,
        created_at=eval_row.created_at,
        updated_at=eval_row.updated_at,
    )

    # Return 202 if still in progress so the frontend knows to keep polling
    if eval_row.status in ("pending", "running"):
        return JSONResponse(
            status_code=202,
            content=response_data.model_dump(mode="json"),
        )

    return response_data
