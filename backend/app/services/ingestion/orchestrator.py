import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import Job, AgentLog
from app.services.ingestion.github_loader import GitHubLoader
from app.services.ingestion.zip_loader import ZipLoader
from app.services.ingestion.file_parser import FileParser
from app.services.ingestion.chunker import CodeChunker
from app.services.rag.vector_store import VectorStore
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def _log_agent(
    db: AsyncSession,
    job_id: str,
    agent_name: str,
    status: str,
    message: str,
):
    """Persist an agent log row — drives the frontend timeline."""
    log = AgentLog(
        job_id=uuid.UUID(job_id),
        agent_name=agent_name,
        status=status,
        message=message,
    )
    db.add(log)
    await db.commit()


async def run_ingestion(
    job_id: str,
    db: AsyncSession,
) -> tuple[list, dict]:
    """
    Full ingestion pipeline for one job:

    1. Load source (GitHub clone or ZIP extract)
    2. Parse files
    3. Chunk code
    4. Embed + store in ChromaDB

    Args:
        job_id: UUID string of the job
        db:     Async SQLAlchemy session

    Returns:
        Tuple of (parsed_files, structure_summary)
        Agents use structure_summary; RAG uses the stored vectors.

    Raises:
        RuntimeError: propagated on clone/extract failure
    """
    uid = uuid.UUID(job_id)
    result = await db.execute(select(Job).where(Job.id == uid))
    job = result.scalar_one_or_none()

    if not job:
        raise RuntimeError(f"Job {job_id} not found in database")

    # ── Step 1: Update job status ─────────────────────────────────────────────
    job.status = "ingesting"
    await db.commit()

    await _log_agent(db, job_id, "Ingestion", "started", f"Loading {job.source_type} source")

    # ── Step 2: Load source ───────────────────────────────────────────────────
    repo_dir: str

    if job.source_type == "github":
        loader = GitHubLoader(upload_dir=settings.upload_dir)
        repo_dir = loader.clone(github_url=job.source_ref, job_id=job_id)
    elif job.source_type == "zip":
        loader = ZipLoader(upload_dir=settings.upload_dir)
        repo_dir = loader.extract(zip_path=job.source_ref, job_id=job_id)
    else:
        raise RuntimeError(f"Unknown source_type: {job.source_type}")

    await _log_agent(db, job_id, "Ingestion", "done", "Source loaded successfully")

    # ── Step 3: Parse files ───────────────────────────────────────────────────
    await _log_agent(db, job_id, "File Parser", "started", "Scanning and reading source files")

    parser = FileParser()
    files = parser.parse(repo_dir)
    structure_summary = parser.get_structure_summary(files)

    await _log_agent(
        db, job_id, "File Parser", "done",
        f"Parsed {structure_summary['total_files']} files across "
        f"{len(structure_summary['languages'])} languages"
    )

    # ── Step 4: Chunk ─────────────────────────────────────────────────────────
    await _log_agent(db, job_id, "Chunker", "started", "Splitting files into semantic chunks")

    chunker = CodeChunker()
    chunks = chunker.chunk_files(files)

    await _log_agent(
        db, job_id, "Chunker", "done",
        f"Created {len(chunks)} chunks from {len(files)} files"
    )

    # ── Step 5: Embed + Store ─────────────────────────────────────────────────
    await _log_agent(db, job_id, "Embedder", "started", "Generating embeddings and storing in ChromaDB")

    store = VectorStore()
    stored_count = store.store_chunks(job_id=job_id, chunks=chunks)

    await _log_agent(
        db, job_id, "Embedder", "done",
        f"Stored {stored_count} vectors in ChromaDB"
    )

    logger.info(
        "Ingestion complete",
        job_id=job_id,
        files=len(files),
        chunks=len(chunks),
        vectors=stored_count,
    )

    return files, structure_summary