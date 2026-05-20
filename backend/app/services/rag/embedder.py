from sentence_transformers import SentenceTransformer
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class Embedder:
    """
    Wraps HuggingFace sentence-transformers for local, free embeddings.

    Model: all-MiniLM-L6-v2
    - 384-dimensional vectors
    - ~22M parameters, very fast on CPU
    - Good semantic quality for code + text

    Why not OpenAI embeddings?
    - Costs money per token
    - Requires internet on every embed call
    - all-MiniLM-L6-v2 is sufficient for a capstone demo
    """

    _instance: "Embedder | None" = None
    _model: SentenceTransformer | None = None

    def __new__(cls):
        # Singleton — load model once, reuse across requests
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is None:
            logger.info("Loading embedding model", model=settings.embedding_model)
            self._model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of text strings.

        Args:
            texts: List of strings to embed

        Returns:
            List of float vectors (one per input text)
        """
        self._load_model()
        if not texts:
            return []

        vectors = self._model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,  # cosine similarity works best normalised
        )
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string for retrieval."""
        return self.embed_texts([query])[0]