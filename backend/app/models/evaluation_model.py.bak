"""
backend/app/models/evaluation_model.py

EvaluationResult ORM model — stores per-job RAGAS scores.
Uses the shared Base from app.database so the table is created by create_tables().
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database import Base


class EvaluationResult(Base):  # type: ignore[valid-type]
    """
    Stores per-job RAGAS evaluation scores.
    One row per job (upserted after evaluation completes).
    """
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True)

    # RAGAS metrics (0.0 – 1.0)
    faithfulness        = Column(Float, nullable=True)
    answer_relevancy    = Column(Float, nullable=True)
    context_precision   = Column(Float, nullable=True)
    context_recall      = Column(Float, nullable=True)

    num_samples = Column(Integer, default=0)
    error       = Column(Text, nullable=True)   # populated if evaluation failed

    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "job_id":            self.job_id,
            "faithfulness":      self.faithfulness,
            "answer_relevancy":  self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall":    self.context_recall,
            "num_samples":       self.num_samples,
            "error":             self.error,
            "updated_at":        self.updated_at.isoformat() if self.updated_at else None,
        }