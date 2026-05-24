"""
<<<<<<< HEAD
RAGAS-Style RAG Evaluation
==========================
Implements three RAG quality metrics using the existing Groq LLM —
no external ragas package required.

Metrics (all returned in [0.0, 1.0]):
- faithfulness:         Are answer claims grounded in the retrieved context?
- answer_relevancy:     Is the answer on-topic for the posed question?
- context_utilisation:  What fraction of retrieved chunks actually contributed?

Usage:
    evaluator = RagasEvaluator()
    scores = await evaluator.evaluate_agent(
        agent_name="Bug Detection Agent",
        question="Find all bugs in this Python codebase",
        answer="{ ... bug agent JSON output ... }",
        contexts=["chunk1 code ...", "chunk2 code ..."],
    )
    # => {"faithfulness": 0.82, "answer_relevancy": 0.91, "context_utilisation": 0.60}
"""

import json
import re
from typing import Any

from langchain_groq import ChatGroq

from app.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


def _build_eval_llm() -> ChatGroq:
    """Separate LLM instance for evaluation — temperature 0 for determinism."""
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0,
        max_tokens=2048,
    )


def _extract_json_safe(text: str) -> dict:
    """Extract JSON from LLM response, returning fallback on failure."""
    # Try markdown fence
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    # Try bare JSON object
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group())
        except json.JSONDecodeError:
            pass
    return {}


class RagasEvaluator:
    """
    RAGAS-style evaluator that uses the existing Groq LLM to score
    RAG pipeline quality for each analysis agent.
    """

    def __init__(self):
        self._llm = _build_eval_llm()

    # ── Faithfulness ────────────────────────────────────────────────────────────

    async def _faithfulness(
        self, answer: str, contexts: list[str]
    ) -> float:
        """
        Decompose the answer into atomic claims and check each against contexts.
        Score = supported_claims / total_claims
        """
        if not contexts or not answer.strip():
            return 0.0

        context_block = "\n\n".join(
            f"[Context {i+1}]:\n{c}" for i, c in enumerate(contexts[:6])
        )

        prompt = f"""You are an expert evaluator assessing faithfulness of an AI response.

RETRIEVED CONTEXTS:
{context_block}

AI ANSWER (code analysis output):
{answer[:2000]}

Task:
1. Extract up to 10 atomic factual claims made in the AI answer.
2. For each claim, determine if it is supported by the retrieved contexts above.

Return ONLY valid JSON:
{{
  "claims": [
    {{"claim": "...", "supported": true}},
    {{"claim": "...", "supported": false}}
  ]
}}"""

        try:
            response = self._llm.invoke(prompt)
            result = _extract_json_safe(response.content)
            claims = result.get("claims", [])
            if not claims:
                return 0.5  # neutral fallback
            supported = sum(1 for c in claims if c.get("supported", False))
            return round(supported / len(claims), 3)
        except Exception as e:
            logger.warning("Faithfulness evaluation failed", error=str(e))
            return 0.0

    # ── Answer Relevancy ────────────────────────────────────────────────────────

    async def _answer_relevancy(
        self, question: str, answer: str
    ) -> float:
        """
        Ask the LLM to rate how relevant the answer is to the question (0–1).
        """
        if not answer.strip():
            return 0.0

        prompt = f"""You are an expert evaluator assessing answer relevancy.

QUESTION (analysis task):
{question}

ANSWER (agent output):
{answer[:2000]}

Rate how relevant and on-topic this answer is to the question.
Consider: Does it address the question? Does it stay focused? Does it avoid irrelevant content?

Return ONLY valid JSON:
{{
  "relevancy_score": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence>"
}}"""

        try:
            response = self._llm.invoke(prompt)
            result = _extract_json_safe(response.content)
            score = float(result.get("relevancy_score", 0.5))
            return round(min(1.0, max(0.0, score)), 3)
        except Exception as e:
            logger.warning("Answer relevancy evaluation failed", error=str(e))
            return 0.0

    # ── Context Utilisation ─────────────────────────────────────────────────────

    async def _context_utilisation(
        self, answer: str, contexts: list[str]
    ) -> float:
        """
        Determine what fraction of retrieved chunks meaningfully contributed
        to the answer. Score = used_chunks / total_chunks
        """
        if not contexts or not answer.strip():
            return 0.0

        context_list = "\n".join(
            f"[Context {i+1}]: {c[:300]}" for i, c in enumerate(contexts[:6])
        )

        prompt = f"""You are evaluating whether retrieved code chunks were actually used in an analysis.

RETRIEVED CHUNKS:
{context_list}

ANALYSIS OUTPUT:
{answer[:2000]}

For each context chunk, determine if it contributed to (was used in) the analysis output.

Return ONLY valid JSON:
{{
  "chunk_usage": [
    {{"chunk_id": 1, "used": true}},
    {{"chunk_id": 2, "used": false}}
  ]
}}"""

        try:
            response = self._llm.invoke(prompt)
            result = _extract_json_safe(response.content)
            usages = result.get("chunk_usage", [])
            if not usages:
                return 0.5
            used = sum(1 for u in usages if u.get("used", False))
            return round(used / len(usages), 3)
        except Exception as e:
            logger.warning("Context utilisation evaluation failed", error=str(e))
            return 0.0

    # ── Public API ──────────────────────────────────────────────────────────────

    async def evaluate_agent(
        self,
        agent_name: str,
        question: str,
        answer: str,
        contexts: list[str],
    ) -> dict[str, float]:
        """
        Run all three RAGAS-style metrics for a single agent's output.

        Returns:
            {
                "faithfulness": float,
                "answer_relevancy": float,
                "context_utilisation": float,
            }
        """
        logger.info("RAGAS evaluation started", agent=agent_name)

        faithfulness = await self._faithfulness(answer, contexts)
        relevancy = await self._answer_relevancy(question, answer)
        utilisation = await self._context_utilisation(answer, contexts)

        scores = {
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
            "context_utilisation": utilisation,
        }

        logger.info(
            "RAGAS evaluation complete",
            agent=agent_name,
            **scores,
        )
        return scores

    async def evaluate_all_agents(
        self,
        agent_data: list[dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        """
        Evaluate multiple agents sequentially.

        Args:
            agent_data: list of dicts with keys:
                - name:     agent display name
                - question: task description
                - answer:   serialised output
                - contexts: list of retrieved code chunk strings

        Returns:
            { agent_name: { metric: score, ... }, ... }
        """
        results: dict[str, dict[str, float]] = {}
        for agent in agent_data:
            scores = await self.evaluate_agent(
                agent_name=agent["name"],
                question=agent["question"],
                answer=agent["answer"],
                contexts=agent.get("contexts", []),
            )
            results[agent["name"]] = scores
        return results
=======
backend/app/services/evaluation/ragas_evaluator.py

RAGAS evaluation service for CodeSentinel RAG pipeline.
Evaluates retrieval quality and answer quality per analysis job.

Metrics computed:
- Faithfulness:       Does the answer stay grounded in retrieved context?
- Answer Relevancy:   How relevant is the answer to the question?
- Context Precision:  Are retrieved chunks ranked with relevant ones first?
- Context Recall:     Does retrieved context cover the ground-truth answer?
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from datasets import Dataset
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.evaluation_model import EvaluationResult  # ORM model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RAGSample:
    """Single question/answer/context tuple used for one RAGAS evaluation."""
    question: str
    answer: str                        # LLM-generated answer
    contexts: list[str]                # retrieved chunk texts fed to the LLM
    ground_truth: Optional[str] = ""   # optional; needed for context_recall


@dataclass
class RAGASReport:
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    num_samples: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "faithfulness": round(self.faithfulness, 4),
            "answer_relevancy": round(self.answer_relevancy, 4),
            "context_precision": round(self.context_precision, 4),
            "context_recall": round(self.context_recall, 4),
            "num_samples": self.num_samples,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class RAGASEvaluator:
    """
    Wraps RAGAS evaluate() with the same LLM / embeddings used in CodeSentinel
    so that scores are computed in a consistent model environment.
    """

    def __init__(self) -> None:
        _settings = get_settings()
        # Reuse Groq LLM already configured in the project
        self._llm = ChatGroq(
            model=_settings.groq_model,
            api_key=_settings.groq_api_key,
            temperature=0,
        )
        # Reuse the same embedding model used for ChromaDB
        self._embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate_job(
        self,
        job_id: UUID,
        samples: list[RAGSample],
        db: AsyncSession,
    ) -> RAGASReport:
        """
        Run RAGAS evaluation for a completed analysis job and persist results.

        Args:
            job_id:  The UUID of the completed analysis job.
            samples: List of RAGSample objects collected during agent execution.
                     Typically 1 sample per agent (5 agents → 5 samples).
            db:      Async SQLAlchemy session for persisting results.

        Returns:
            RAGASReport with averaged metric scores.
        """
        if not samples:
            logger.warning("evaluate_job called with no samples for job %s", job_id)
            return RAGASReport(error="No samples provided")

        try:
            report = await asyncio.get_event_loop().run_in_executor(
                None, self._run_ragas, samples
            )
        except Exception as exc:
            logger.exception("RAGAS evaluation failed for job %s", job_id)
            report = RAGASReport(error=str(exc))

        await self._persist(job_id, report, db)
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_ragas(self, samples: list[RAGSample]) -> RAGASReport:
        """Synchronous RAGAS computation (run in thread executor)."""
        dataset = Dataset.from_dict(
            {
                "question":   [s.question for s in samples],
                "answer":     [s.answer for s in samples],
                "contexts":   [s.contexts for s in samples],
                "ground_truth": [s.ground_truth or "" for s in samples],
            }
        )

        result = evaluate(
            dataset=dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
            llm=self._llm,
            embeddings=self._embeddings,
            raise_exceptions=False,
        )

        df = result.to_pandas()
        return RAGASReport(
            faithfulness=float(df["faithfulness"].mean()),
            answer_relevancy=float(df["answer_relevancy"].mean()),
            context_precision=float(df["context_precision"].mean()),
            context_recall=float(df["context_recall"].mean()),
            num_samples=len(samples),
        )

    @staticmethod
    async def _persist(
        job_id: UUID,
        report: RAGASReport,
        db: AsyncSession,
    ) -> None:
        """Upsert evaluation results into PostgreSQL."""
        from sqlalchemy import select

        existing = await db.execute(
            select(EvaluationResult).where(EvaluationResult.job_id == str(job_id))
        )
        row = existing.scalars().first()

        if row:
            row.faithfulness = report.faithfulness
            row.answer_relevancy = report.answer_relevancy
            row.context_precision = report.context_precision
            row.context_recall = report.context_recall
            row.num_samples = report.num_samples
            row.error = report.error
        else:
            db.add(
                EvaluationResult(
                    job_id=str(job_id),
                    faithfulness=report.faithfulness,
                    answer_relevancy=report.answer_relevancy,
                    context_precision=report.context_precision,
                    context_recall=report.context_recall,
                    num_samples=report.num_samples,
                    error=report.error,
                )
            )

        await db.commit()
        logger.info("Persisted RAGAS evaluation for job %s: %s", job_id, report.to_dict())


# ---------------------------------------------------------------------------
# Singleton for DI
# ---------------------------------------------------------------------------

_evaluator: Optional[RAGASEvaluator] = None


def get_ragas_evaluator() -> RAGASEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = RAGASEvaluator()
    return _evaluator
>>>>>>> 8323db3e7cc4c2ac2de0a792685aae25f1be5dfe
