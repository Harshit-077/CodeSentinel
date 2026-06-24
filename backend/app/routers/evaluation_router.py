# """
# backend/app/routers/evaluation.py

# Endpoints:
#   POST /api/evaluation/{job_id}/run   — trigger RAGAS evaluation for a completed job
#   GET  /api/evaluation/{job_id}       — fetch stored evaluation results

# Wire into main.py:
#     from app.routers.evaluation import router as evaluation_router
#     app.include_router(evaluation_router, prefix="/api/evaluation", tags=["evaluation"])
# """

# from uuid import UUID

# from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.database import get_db
# from app.models.job import Job, AgentLog , EvaluationResult         # existing ORM models
# # from app.services.evaluation.ragas_evaluator import (
# #     RagasEvaluator,
# #     RagSample,
# #     RAGASReport,
# #     get_ragas_evaluator,
# # )
# from app.utils.auth import verify_token

# router = APIRouter()


# # ---------------------------------------------------------------------------
# # Helper: build RAGSample list from stored AgentLogs
# # ---------------------------------------------------------------------------

# def _build_samples_from_logs(agent_logs: list[AgentLog]) -> list[RAGSample]:
#     """
#     Reconstructs RAGSample objects from persisted agent log entries.

#     Each AgentLog row is expected to have:
#         agent_name  : str
#         rag_question: str  (the query sent to the retriever)
#         rag_answer  : str  (the LLM's answer)
#         rag_contexts: list[str]  (retrieved chunk texts, stored as JSON)

#     If your AgentLog model doesn't have these columns yet, add them
#     (see the note at the bottom of this file).
#     """
#     samples: list[RAGSample] = []
#     for log in agent_logs:
#         # Guard: skip logs that don't carry RAG data yet
#         if not getattr(log, "rag_question", None) or not getattr(log, "rag_answer", None):
#             # Fallback: synthesise a minimal sample from whatever is stored
#             if log.message:
#                 samples.append(
#                     RAGSample(
#                         question=f"What did the {log.agent_name} find?",
#                         answer=log.message,
#                         contexts=[log.message],
#                     )
#                 )
#             continue

#         samples.append(
#             RAGSample(
#                 question=log.rag_question,
#                 answer=log.rag_answer,
#                 contexts=log.rag_contexts or [log.rag_answer],
#             )
#         )

#     return samples


# # ---------------------------------------------------------------------------
# # Routes
# # ---------------------------------------------------------------------------

# @router.post("/{job_id}/run", summary="Trigger RAGAS evaluation for a job")
# async def run_evaluation(
#     job_id: UUID,
#     background_tasks: BackgroundTasks,
#     db: AsyncSession = Depends(get_db),
#     evaluator: RAGASEvaluator = Depends(get_ragas_evaluator),
#     _user=Depends(verify_token),
# ):
#     """
#     Triggers RAGAS evaluation in the background for the given completed job.
#     Returns immediately; poll GET /api/evaluation/{job_id} for results.
#     """
#     # Verify job exists and is done
#     result = await db.execute(select(Job).where(Job.id == str(job_id)))
#     job = result.scalars().first()
#     if not job:
#         raise HTTPException(status_code=404, detail="Job not found")
#     if job.status != "done":
#         raise HTTPException(
#             status_code=400,
#             detail=f"Job status is '{job.status}'; evaluation requires status 'done'",
#         )

#     # Fetch agent logs for this job
#     logs_result = await db.execute(
#         select(AgentLog).where(AgentLog.job_id == str(job_id))
#     )
#     agent_logs = logs_result.scalars().all()
#     samples = _build_samples_from_logs(agent_logs)

#     # Run evaluation asynchronously so the endpoint returns fast
#     background_tasks.add_task(evaluator.evaluate_job, job_id, samples, db)

#     return {
#         "message": "RAGAS evaluation started in background",
#         "job_id": str(job_id),
#         "num_samples": len(samples),
#     }


# @router.get("/{job_id}", summary="Fetch RAGAS evaluation results for a job")
# async def get_evaluation(
#     job_id: UUID,
#     db: AsyncSession = Depends(get_db),
#     _user=Depends(verify_token),
# ):
#     """Returns stored RAGAS scores for the given job, or 404 if not yet run."""
#     result = await db.execute(
#         select(EvaluationResult).where(EvaluationResult.job_id == str(job_id))
#     )
#     row = result.scalars().first()
#     if not row:
#         raise HTTPException(
#             status_code=404,
#             detail="No evaluation found for this job. POST /api/evaluation/{job_id}/run first.",
#         )
#     return row.to_dict()


# # ---------------------------------------------------------------------------
# # NOTE — AgentLog model additions (add to app/models/job.py)
# # ---------------------------------------------------------------------------
# # class AgentLog(Base):
# #     ...existing columns...
# #     rag_question = Column(Text, nullable=True)   # query sent to retriever
# #     rag_answer   = Column(Text, nullable=True)   # LLM response
# #     rag_contexts = Column(JSON, nullable=True)   # list[str] of chunk texts
# #
# # In each agent (e.g. bug_agent.py), after calling retriever.retrieve():
# #
# #   log.rag_question = query
# #   log.rag_answer   = llm_response
# #   log.rag_contexts = [doc.page_content for doc in retrieved_docs]
# #   await db.commit()
