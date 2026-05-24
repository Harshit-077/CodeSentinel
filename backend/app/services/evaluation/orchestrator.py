"""
Evaluation Orchestrator
=======================
Coordinates RAGAS + LLM-as-a-Judge evaluation and persists results.

Called as an asyncio background task after the main pipeline completes.
Creates an EvaluationResult row immediately (status=pending) so the
frontend can show a loading state while evaluation runs.
"""

import uuid
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.job import EvaluationResult, Report
from app.services.evaluation.ragas_evaluator import RagasEvaluator
from app.services.evaluation.llm_judge import LLMJudge, CRITERIA_WEIGHTS
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Agent task descriptions (questions for RAGAS) ────────────────────────────

AGENT_QUESTIONS = {
    "Repository Analysis Agent": (
        "Analyse the repository structure, identify the project purpose, "
        "primary language, architecture style, frameworks, and complexity."
    ),
    "Bug Detection Agent": (
        "Identify all bugs, logic errors, anti-patterns, and code quality issues "
        "in the codebase. Provide severity ratings and suggested fixes."
    ),
    "Security Review Agent": (
        "Find all security vulnerabilities using OWASP Top 10 as a framework. "
        "Identify exposed secrets, injection risks, and authentication issues."
    ),
    "Documentation Agent": (
        "Evaluate documentation quality including README completeness, "
        "docstring coverage, and provide actionable improvement suggestions."
    ),
    "Final Reviewer Agent": (
        "Synthesise all agent findings into a comprehensive engineering report "
        "with executive summary, prioritised action items, and risk assessment."
    ),
}


def _build_agent_eval_data(final_state: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Build the list of agent evaluation inputs for the RAGAS evaluator.
    Pulls outputs and retrieved contexts from the pipeline final state.
    """
    retrieved = final_state.get("retrieved_contexts") or {}

    agents = [
        {
            "name":     "Repository Analysis Agent",
            "question": AGENT_QUESTIONS["Repository Analysis Agent"],
            "answer":   json.dumps(final_state.get("repo_summary") or {}),
            "contexts": retrieved.get("repo", []),
        },
        {
            "name":     "Bug Detection Agent",
            "question": AGENT_QUESTIONS["Bug Detection Agent"],
            "answer":   json.dumps(final_state.get("bugs") or {}),
            "contexts": retrieved.get("bug", []),
        },
        {
            "name":     "Security Review Agent",
            "question": AGENT_QUESTIONS["Security Review Agent"],
            "answer":   json.dumps(final_state.get("security_issues") or {}),
            "contexts": retrieved.get("security", []),
        },
        {
            "name":     "Documentation Agent",
            "question": AGENT_QUESTIONS["Documentation Agent"],
            "answer":   json.dumps(final_state.get("docs_suggestions") or {}),
            "contexts": retrieved.get("docs", []),
        },
    ]
    return agents


def _compute_overall_eval_score(
    ragas_scores: dict[str, dict[str, float]],
    judge_scores: dict[str, Any],
) -> float:
    """
    Compute a single [0.0, 10.0] overall evaluation score combining
    RAGAS metrics (normalised to 0–10) and LLM judge scores.

    Weights:
    - RAGAS average:  40%
    - Judge overall:  60%
    """
    # Average RAGAS scores across all agents and metrics, normalise to 0–10
    all_ragas = []
    for agent_scores in ragas_scores.values():
        all_ragas.extend(agent_scores.values())
    ragas_avg_10 = (sum(all_ragas) / len(all_ragas) * 10) if all_ragas else 0.0

    judge_overall = float(judge_scores.get("overall_score", 0.0))

    combined = (ragas_avg_10 * 0.40) + (judge_overall * 0.60)
    return round(min(10.0, max(0.0, combined)), 2)


async def run_evaluation(job_id: str, final_state: dict[str, Any]) -> None:
    """
    Main entry point — called as asyncio.create_task() from graph.py.

    Creates EvaluationResult row (pending), runs RAGAS + judge,
    updates row to done/failed.
    """
    logger.info("Starting evaluation pipeline", job_id=job_id)
    uid = uuid.UUID(job_id)

    # ── Step 1: Create pending row ────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        eval_row = EvaluationResult(
            job_id=uid,
            status="pending",
        )
        db.add(eval_row)
        await db.commit()
        eval_id = eval_row.id

    # ── Step 2: Fetch the saved Report for judge input ────────────────────────
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Report).where(Report.job_id == uid)
        )
        report = result.scalar_one_or_none()

    if not report:
        logger.error("Evaluation: report not found for job", job_id=job_id)
        await _mark_failed(eval_id, "Report not found for this job")
        return

    # Build report_data dict for the judge
    report_data = {
        "bugs":             report.bugs,
        "security_issues":  report.security_issues,
        "docs_suggestions": report.docs_suggestions,
        "final_review":     report.final_review,
        "severity_score":   report.severity_score,
        "confidence_score": report.confidence_score,
    }

    # ── Step 3: Mark running ──────────────────────────────────────────────────
    await _update_status(eval_id, "running")

    # ── Step 4: Run RAGAS evaluation ──────────────────────────────────────────
    ragas_scores: dict[str, dict[str, float]] = {}
    try:
        ragas_eval = RagasEvaluator()
        agent_data = _build_agent_eval_data(final_state)
        ragas_scores = await ragas_eval.evaluate_all_agents(agent_data)
        logger.info("RAGAS evaluation complete", job_id=job_id)
    except Exception as e:
        logger.error("RAGAS evaluation failed", job_id=job_id, error=str(e))
        # Non-fatal — continue to judge

    # ── Step 5: Run LLM-as-a-Judge ────────────────────────────────────────────
    judge_scores: dict[str, Any] = {}
    try:
        judge = LLMJudge()
        judge_scores = await judge.evaluate(report_data)
        logger.info("LLM judge evaluation complete", job_id=job_id)
    except Exception as e:
        logger.error("LLM judge evaluation failed", job_id=job_id, error=str(e))
        # Non-fatal — save what we have

    # ── Step 6: Compute overall score and persist ─────────────────────────────
    overall = _compute_overall_eval_score(ragas_scores, judge_scores)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EvaluationResult).where(EvaluationResult.id == eval_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.ragas_scores = ragas_scores
            row.judge_scores = judge_scores
            row.overall_eval_score = overall
            row.status = "done"
            await db.commit()

    logger.info(
        "Evaluation pipeline complete",
        job_id=job_id,
        overall=overall,
    )


async def _update_status(eval_id: uuid.UUID, status: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EvaluationResult).where(EvaluationResult.id == eval_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.status = status
            await db.commit()


async def _mark_failed(eval_id: uuid.UUID, error_msg: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EvaluationResult).where(EvaluationResult.id == eval_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.status = "failed"
            row.error_message = error_msg[:500]
            await db.commit()
