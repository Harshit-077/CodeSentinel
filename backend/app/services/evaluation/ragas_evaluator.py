"""
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