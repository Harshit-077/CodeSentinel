# ============================================================
# FILE: backend/app/services/evaluation/ragas_evaluator.py
# ACTION: CREATE this new file at that exact path.
#         Also create backend/app/services/evaluation/__init__.py
#         (empty file).
# ============================================================

"""
RAGAS evaluation for CodeSentinel RAG pipeline.

Metrics used (none require ground_truth):
  - faithfulness        : answer supported by retrieved context
  - answer_relevancy    : answer relevant to the question
  - context_precision   : retrieved chunks ranked well

Each agent contributes one EvalSample (question, answer, contexts).
We average per-metric across all agents for a job-level score.

LLM backend: Groq (llama-3.3-70b-versatile) via OpenAI-compatible API.
Embeddings:  same sentence-transformers model already in the project.
"""

from __future__ import annotations
import asyncio

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision
from ragas import EvaluationDataset, SingleTurnSample

from app.config import settings

logger = logging.getLogger(__name__)


# ── Singleton wrappers (built once, reused across jobs) ─────

_ragas_llm: LangchainLLMWrapper | None = None
_ragas_embeddings: LangchainEmbeddingsWrapper | None = None


def _get_ragas_llm() -> LangchainLLMWrapper:
    global _ragas_llm
    if _ragas_llm is None:
        llm = ChatGroq(
            model=settings.ragas_llm_model,
            api_key=settings.groq_api_key,
            temperature=0,
        )
        _ragas_llm = LangchainLLMWrapper(llm)
    return _ragas_llm


def _get_ragas_embeddings() -> LangchainEmbeddingsWrapper:
    global _ragas_embeddings
    if _ragas_embeddings is None:
        emb = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        _ragas_embeddings = LangchainEmbeddingsWrapper(emb)
    return _ragas_embeddings


# ── Data class for one agent's RAG interaction ──────────────

@dataclass
class AgentEvalInput:
    """
    Collected by each agent during the pipeline run.
    Agents must populate this and append to a shared list.
    """
    agent_name: str          # e.g. "bug", "security", "docs"
    question:   str          # the query sent to Retriever.retrieve()
    answer:     str          # the LLM response text from that agent
    contexts:   list[str]    # chunk content strings from retrieve_raw()


# ── Main evaluation function ─────────────────────────────────

async def run_ragas_evaluation(
    job_id: int,
    eval_inputs: list[AgentEvalInput],
) -> dict[str, Any]:
    """
    Run RAGAS evaluation on all agent interactions for a job.

    Args:
        job_id:       The job being evaluated (for logging).
        eval_inputs:  List of AgentEvalInput, one per agent.

    Returns:
        Dict with structure:
        {
            "per_agent": {
                "bug": {"faithfulness": 0.85, "answer_relevancy": 0.91, ...},
                ...
            },
            "overall": {"faithfulness": 0.87, "answer_relevancy": 0.88, ...},
            "sample_count": 3,
            "error": null   ← or error message string if eval failed
        }
    """
    if not eval_inputs:
        logger.warning("ragas_eval_skipped: no eval inputs for job %s", job_id)
        return _empty_result("no eval inputs collected")

    try:
        # Build RAGAS dataset
        samples = []
        for inp in eval_inputs:
            if not inp.question or not inp.answer or not inp.contexts:
                logger.warning(
                    "ragas_skip_agent: missing data for agent %s job %s",
                    inp.agent_name, job_id
                )
                continue
            samples.append(
                SingleTurnSample(
                    user_input=inp.question,
                    response=inp.answer,
                    retrieved_contexts=inp.contexts,
                )
            )

        if not samples:
            return _empty_result("all agents had missing data")

        dataset = EvaluationDataset(samples=samples)

        metrics = [Faithfulness(), AnswerRelevancy(), ContextPrecision()]

        ragas_llm = _get_ragas_llm()
        ragas_emb = _get_ragas_embeddings()

        # RAGAS evaluate is synchronous — run in executor to not block loop
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None,
            lambda: evaluate(
                dataset=dataset,
                metrics=metrics,
                llm=ragas_llm,
                embeddings=ragas_emb,
            ),
        )

        # results.scores is a list of dicts, one per sample
        scores_list: list[dict] = results.to_pandas().to_dict(orient="records")

        # Map back to agent names
        per_agent: dict[str, dict[str, float]] = {}
        for i, inp in enumerate([e for e in eval_inputs if e.question and e.answer and e.contexts]):
            if i >= len(scores_list):
                break
            per_agent[inp.agent_name] = {
                k: round(float(v), 4) if v is not None else None
                for k, v in scores_list[i].items()
            }

        # Compute overall averages
        overall = _average_scores(per_agent)

        logger.info(
            "ragas_eval_complete job=%s samples=%d overall=%s",
            job_id, len(samples), overall
        )

        return {
            "per_agent":    per_agent,
            "overall":      overall,
            "sample_count": len(samples),
            "error":        None,
        }

    except Exception as exc:
        logger.error("ragas_eval_failed job=%s error=%s", job_id, exc, exc_info=True)
        return _empty_result(str(exc))


# ── Helpers ──────────────────────────────────────────────────

def _average_scores(per_agent: dict[str, dict[str, float | None]]) -> dict[str, float | None]:
    """Average each metric across all agents, skipping None."""
    if not per_agent:
        return {}
    all_keys = {k for scores in per_agent.values() for k in scores}
    overall: dict[str, float | None] = {}
    for key in all_keys:
        vals = [
            s[key]
            for s in per_agent.values()
            if s.get(key) is not None
        ]
        overall[key] = round(sum(vals) / len(vals), 4) if vals else None
    return overall


def _empty_result(reason: str) -> dict[str, Any]:
    return {
        "per_agent":    {},
        "overall":      {},
        "sample_count": 0,
        "error":        reason,
    }