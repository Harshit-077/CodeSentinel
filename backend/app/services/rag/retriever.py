from app.services.rag.vector_store import VectorStore
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Retriever:
    """
    High-level retrieval interface used by all agents.

    Agents call retrieve() with a natural language query and get back
    formatted context + citations ready to inject into prompts.
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        self._store = VectorStore()

    def retrieve(self, query: str, n_results: int = 5) -> str:
        """
        Retrieve relevant code chunks and format them as a
        prompt-injectable context block with citations.

        Args:
            query:     What the agent is looking for
            n_results: Number of chunks to retrieve

        Returns:
            Formatted string ready for injection into an LLM prompt
        """
        chunks = self._store.similarity_search(
            job_id=self.job_id,
            query=query,
            n_results=n_results,
        )

        if not chunks:
            return "No relevant code context found."

        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"[Source {i}: {chunk['source']} ({chunk['language']})]"
                f"\n```\n{chunk['content']}\n```"
            )

        return "\n\n".join(parts)

    def retrieve_raw(self, query: str, n_results: int = 5) -> list[dict]:
        """Return raw chunk dicts (used when agents need source metadata)."""
        return self._store.similarity_search(
            job_id=self.job_id,
            query=query,
            n_results=n_results,
        )