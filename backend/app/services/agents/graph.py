"""
LangGraph Multi-Agent Pipeline
==============================

Graph structure (linear sequential):

  START → repo_node → bug_node → security_node → docs_node → reviewer_node → END

Why sequential (not parallel)?
- Each agent prompt includes repo_summary for context — repo must run first
- Final Reviewer needs ALL outputs — must run last
- Bug/Security/Docs are independent but share RAG retriever;
  sequential avoids ChromaDB concurrency issues on local disk
- Groq free tier has rate limits — sequential is safer than parallel bursts
"""

import uuid
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
from app.utils.logger import get_logger

logger = get_logger(__name__)

_repo_agent = RepoAgent()
_bug_agent = BugAgent()
_security_agent = SecurityAgent()
_docs_agent = DocsAgent()
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
    graph.add_node("repo", repo_node)
    graph.add_node("bug", bug_node)
    graph.add_node("security", security_node)
    graph.add_node("docs", docs_node)
    graph.add_node("reviewer", reviewer_node)

    graph.add_edge(START, "repo")
    graph.add_edge("repo", "bug")
    graph.add_edge("bug", "security")
    graph.add_edge("security", "docs")
    graph.add_edge("docs", "reviewer")
    graph.add_edge("reviewer", END)

    return graph.compile()


async def _save_report(db: AsyncSession, job_id: str, final_state: AgentState):
    uid = uuid.UUID(job_id)
    report = Report(
        job_id=uid,
        repo_summary=final_state.get("repo_summary"),
        bugs=final_state.get("bugs"),
        security_issues=final_state.get("security_issues"),
        docs_suggestions=final_state.get("docs_suggestions"),
        final_review=final_state.get("final_review"),
        severity_score=final_state.get("severity_score"),
        confidence_score=final_state.get("confidence_score"),
    )
    db.add(report)
    await db.flush()

    result = await db.execute(select(Job).where(Job.id == uid))
    job = result.scalar_one_or_none()
    if job:
        job.status = "done"

    await db.commit()
    await db.refresh(report)
    logger.info("Report saved", job_id=job_id, report_id=str(report.id))
    return report


async def run_pipeline(job_id: str):
    async with AsyncSessionLocal() as db:
        try:
            uid = uuid.UUID(job_id)
            result = await db.execute(select(Job).where(Job.id == uid))
            job = result.scalar_one_or_none()

            if not job:
                logger.error("Job not found", job_id=job_id)
                return

            from app.services.ingestion.orchestrator import run_ingestion
            files, structure_summary = await run_ingestion(job_id=job_id, db=db)

            await db.refresh(job)
            job.status = "analyzing"
            await db.commit()

            initial_state: AgentState = {
                "job_id": job_id,
                "source_type": job.source_type,
                "source_ref": job.source_ref,
                "structure_summary": structure_summary,
                "repo_summary": None,
                "bugs": None,
                "security_issues": None,
                "docs_suggestions": None,
                "final_review": None,
                "severity_score": None,
                "confidence_score": None,
                "errors": [],
            }

            logger.info("Starting LangGraph pipeline", job_id=job_id)
            compiled_graph = build_graph(db)
            final_state = await compiled_graph.ainvoke(initial_state)

            await _save_report(db, job_id, final_state)
            logger.info("Pipeline complete", job_id=job_id)

        except Exception as e:
            logger.error("Pipeline failed", job_id=job_id, error=str(e), exc_info=True)
            async with AsyncSessionLocal() as err_db:
                result = await err_db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)[:500]
                    await err_db.commit()