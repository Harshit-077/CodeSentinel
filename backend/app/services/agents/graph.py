import uuid
from app.database import AsyncSessionLocal
from app.models.job import Job
from sqlalchemy import select
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_pipeline(job_id: str):
    """
    Entry point called by FastAPI background task.
    Phase 3: runs full ingestion pipeline.
    Phase 4: will add LangGraph agents after ingestion.
    """
    async with AsyncSessionLocal() as db:
        try:
            from app.services.ingestion.orchestrator import run_ingestion

            files, structure_summary = await run_ingestion(job_id=job_id, db=db)

            # Mark job done (agents will replace this in Phase 4)
            uid = uuid.UUID(job_id)
            result = await db.execute(select(Job).where(Job.id == uid))
            job = result.scalar_one_or_none()
            if job:
                job.status = "done"
                await db.commit()

            logger.info("Pipeline complete (ingestion only)", job_id=job_id)

        except Exception as e:
            logger.error("Pipeline failed", job_id=job_id, error=str(e))
            async with AsyncSessionLocal() as err_db:
                uid = uuid.UUID(job_id)
                result = await err_db.execute(select(Job).where(Job.id == uid))
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    await err_db.commit()