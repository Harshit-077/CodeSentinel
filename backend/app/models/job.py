import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
        # pending | ingesting | analyzing | done | failed
    )
    source_type: Mapped[str] = mapped_column(
        String(10), nullable=False
        # github | zip
    )
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="job", uselist=False)
    logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog", back_populates="job", order_by="AgentLog.created_at"
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )

    # Agent outputs stored as JSONB
    repo_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    bugs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    security_issues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    docs_suggestions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    final_review: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Scoring
    severity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # PDF path on disk
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="report")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
        # started | done | failed
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    # Relationship
    job: Mapped["Job"] = relationship("Job", back_populates="logs")