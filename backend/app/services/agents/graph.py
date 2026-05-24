"""
LangGraph Multi-Agent Pipeline
==============================
START → repo → bug → security → docs → reviewer → END
"""

import uuid
import os
from langgraph.graph import StateGraph, START, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.agents.state import AgentState
from app.services.agents.repo_agent import RepoAgent
from app.services.agents.bug_agent import BugAgent
from app.services.agents.security_agent import SecurityAgent
from app.services.agents.docs_agent import DocsAgent
from app.services.agents.reviewer_agent import ReviewerAgent
from app.database import AsyncSessionLocal
from app.models.job import Job, Report
from app.config import get_settings
from app.utils.logger import get_logger
from app.services.evaluation.ragas_evaluator import AgentEvalInput, run_ragas_evaluation

logger = get_logger(__name__)
settings = get_settings()

# ── LangSmith tracing (must be set before graph compiles) ────
os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
os.environ["LANGCHAIN_API_KEY"]    = settings.langchain_api_key
os.environ["LANGCHAIN_PROJECT"]    = settings.langchain_project

_repo_agent     = RepoAgent()
_bug_agent      = BugAgent()
_security_agent = SecurityAgent()
_docs_agent     = DocsAgent()
_reviewer_agent = ReviewerAgent()


def make_nodes(db: AsyncSession):
    async def repo_node(state: AgentState) -> dict:
        return await _repo_agent.run(state, db)
    async def bug_node(state: AgentState) -> dict:
        return await _bug_agent.run(state, db)
    async def security_node(state: AgentState) -> dict:
        return await _security_agent.run(state, db)
    async def docs_node(state: AgentState) -> dict:
        return await _docs_agent.run(state, db)
    async def reviewer_node(state: AgentState) -> dict:
        return await _reviewer_agent.run(state, db)
    return repo_node, bug_node, security_node, docs_node, reviewer_node


def build_graph(db: AsyncSession):
    repo_node, bug_node, security_node, docs_node, reviewer_node = make_nodes(db)
    graph = StateGraph(AgentState)
    graph.add_node("repo",     repo_node)
    graph.add_node("bug",      bug_node)
    graph.add_node("security", security_node)
    graph.add_node("docs",     docs_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_edge(START,      "repo")
    graph.add_edge("repo",     "bug")
    graph.add_edge("bug",      "security")
    graph.add_edge("security", "docs")
    graph.add_edge("docs",     "reviewer")
    graph.add_edge("reviewer", END)
    return graph.compile()


async def _generate_pdf_for_report(report: Report) -> str | None:
    """
    Generate PDF after agents complete and save path to report row.
    Returns pdf_path or None on failure.
    """
    try:
        from app.services.report.pdf_generator import generate_pdf
        from app.services.report.scorer import compute_severity

        # Build the data dict the PDF generator expects
        report_data = {
            "severity_score":   report.severity_score,
            "confidence_score": report.confidence_score,
            "repo_summary":     report.repo_summary,
            "bugs":             report.bugs,
            "security_issues":  report.security_issues,
            "docs_suggestions": report.docs_suggestions,
            "final_review":     report.final_review,
        }

        pdf_filename = f"report_{report.id}.pdf"
        pdf_path = os.path.join(settings.report_dir, pdf_filename)
        os.makedirs(settings.report_dir, exist_ok=True)

        generate_pdf(report_data, pdf_path)
        logger.info("PDF generated", report_id=str(report.id), path=pdf_path)
        return pdf_path

    except Exception as e:
        logger.error("PDF generation failed", error=str(e))
        return None


async def _save_report(db: AsyncSession, job_id: str, final_state: AgentState, eval_scores: dict | None = None) -> Report:
    """Persist agent outputs + trigger PDF generation."""
    uid = uuid.UUID(job_id)

    # ── Re-score using deterministic scorer ───────────────────────────────────
    from app.services.report.scorer import compute_severity
    scoring = compute_severity(
        bugs=final_state.get("bugs") or {},
        security_issues=final_state.get("security_issues") or {},
        docs_suggestions=final_state.get("docs_suggestions") or {},
        errors=final_state.get("errors") or [],
    )

    report = Report(
        job_id=uid,
        repo_summary=final_state.get("repo_summary"),
        bugs=final_state.get("bugs"),
        security_issues=final_state.get("security_issues"),
        docs_suggestions=final_state.get("docs_suggestions"),
        final_review=final_state.get("final_review"),
        severity_score=scoring.severity_score,
        confidence_score=scoring.confidence_score,
        evaluation_scores=eval_scores,        # ← NEW
    )
    db.add(report)
    await db.flush()   # get report.id before PDF generation

    # Mark job done
    result = await db.execute(select(Job).where(Job.id == uid))
    job = result.scalar_one_or_none()
    if job:
        job.status = "done"

    await db.commit()
    await db.refresh(report)

    # ── Generate PDF (non-blocking on failure) ────────────────────────────────
    pdf_path = await _generate_pdf_for_report(report)
    if pdf_path:
        report.pdf_path = pdf_path
        await db.commit()

    logger.info("Report saved",
        job_id=job_id,
        report_id=str(report.id),
        severity=scoring.severity_score,
        confidence=scoring.confidence_score,
        pdf=pdf_path or "failed",
    )
    return report


async def run_pipeline(job_id: str):
    """Entry point called by FastAPI BackgroundTasks."""
    async with AsyncSessionLocal() as db:
        try:
            uid = uuid.UUID(job_id)
            result = await db.execute(select(Job).where(Job.id == uid))
            job = result.scalar_one_or_none()

            if not job:
                logger.error("Job not found", job_id=job_id)
                return

            # ── Ingestion ──────────────────────────────────────────────────────
            from app.services.ingestion.orchestrator import run_ingestion
            files, structure_summary = await run_ingestion(job_id=job_id, db=db)

            await db.refresh(job)
            job.status = "analyzing"
            await db.commit()

            # ── Initial state ──────────────────────────────────────────────────
            eval_inputs: list = []          # shared collector for RAGAS

            initial_state: AgentState = {
                "job_id":            job_id,
                "source_type":       job.source_type,
                "source_ref":        job.source_ref,
                "structure_summary": structure_summary,
                "repo_summary":      None,
                "bugs":              None,
                "security_issues":   None,
                "docs_suggestions":  None,
                "final_review":      None,
                "severity_score":    None,
                "confidence_score":  None,
                "errors":            [],
                "eval_inputs":       eval_inputs,
            }

            # ── LangGraph ──────────────────────────────────────────────────────
            logger.info("Starting LangGraph pipeline", job_id=job_id)
            compiled_graph = build_graph(db)
            final_state = await compiled_graph.ainvoke(
                initial_state,
                config={
                    "run_name": f"codesentinel-job-{job_id}",
                    "tags":     ["codesentinel", "code-review"],
                    "metadata": {"job_id": job_id, "source_type": job.source_type},
                },
            )
             # ── RAGAS evaluation ───────────────────────────────────────────────
            eval_scores = await run_ragas_evaluation(job_id, eval_inputs)
            logger.info("RAGAS evaluation complete", job_id=job_id, overall=eval_scores.get("overall"))

            # ── Save report + generate PDF ─────────────────────────────────────
            await _save_report(db, job_id, final_state)
            logger.info("Pipeline complete", job_id=job_id)

        except Exception as e:
            logger.error("Pipeline failed", job_id=job_id, error=str(e), exc_info=True)
            async with AsyncSessionLocal() as err_db:
                result = await err_db.execute(
                    select(Job).where(Job.id == uuid.UUID(job_id))
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)[:500]
                    await err_db.commit()