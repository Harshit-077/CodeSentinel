import chromadb
from chromadb.config import Settings as ChromaSettings
from app.services.ingestion.chunker import CodeChunk
from app.services.rag.embedder import Embedder
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

BATCH_SIZE = 100   # ChromaDB performs best with batched upserts


class VectorStore:
    """
    ChromaDB-backed vector store.

    Each analysis job gets its own isolated collection named
    by job_id — this prevents cross-job retrieval contamination
    and makes cleanup trivial.

    Architecture decision: local ChromaDB (not server mode)
    - No extra service to deploy
    - Persisted to disk via chroma_persist_dir
    - Sufficient for capstone / single-server GCP deployment
    """

    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._embedder = Embedder()

    def _collection_name(self, job_id: str) -> str:
        # ChromaDB collection names must be alphanumeric + hyphens
        return f"job-{job_id.replace('_', '-')}"

    def store_chunks(self, job_id: str, chunks: list[CodeChunk]) -> int:
        """
        Embed and store all chunks for a job.

        Args:
            job_id: UUID string — used as collection namespace
            chunks: List of CodeChunk objects from the chunker

        Returns:
            Number of chunks stored
        """
        if not chunks:
            logger.warning("No chunks to store", job_id=job_id)
            return 0

        collection = self._client.get_or_create_collection(
            name=self._collection_name(job_id),
            metadata={"hnsw:space": "cosine"},  # cosine similarity
        )

        stored = 0
        # Process in batches to avoid memory spikes
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]

            texts = [c.content for c in batch]
            ids = [c.chunk_id for c in batch]
            metadatas = [c.metadata for c in batch]

            embeddings = self._embedder.embed_texts(texts)

            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            stored += len(batch)
            logger.debug("Stored chunk batch", job_id=job_id, batch_end=i + len(batch))

        logger.info("Vector store complete", job_id=job_id, total_chunks=stored)
        return stored

    def similarity_search(
        self,
        job_id: str,
        query: str,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Retrieve the top-N most relevant chunks for a query.

        Args:
            job_id:    UUID string to scope search to this job's collection
            query:     Natural language or code query string
            n_results: How many chunks to return

        Returns:
            List of dicts with keys: content, source, language, distance
        """
        try:
            collection = self._client.get_collection(
                name=self._collection_name(job_id)
            )
        except Exception:
            logger.warning("Collection not found for job", job_id=job_id)
            return []

        query_embedding = self._embedder.embed_query(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({
                "content": doc,
                "source": meta.get("source", "unknown"),
                "language": meta.get("language", "unknown"),
                "distance": round(dist, 4),
            })

        return output

    def delete_collection(self, job_id: str):
        """Delete all vectors for a job — call after report is saved."""
        try:
            self._client.delete_collection(self._collection_name(job_id))
            logger.info("Deleted collection", job_id=job_id)
        except Exception as e:
            logger.warning("Could not delete collection", job_id=job_id, error=str(e))

    def collection_count(self, job_id: str) -> int:
        """Return number of vectors stored for a job."""
        try:
            col = self._client.get_collection(self._collection_name(job_id))
            return col.count()
        except Exception:
            return 0