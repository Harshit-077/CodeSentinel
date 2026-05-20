from dataclasses import dataclass
from app.services.ingestion.file_parser import ParsedFile
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Chunking config — tuned for code
CHUNK_SIZE = 1200        # characters per chunk (≈ 300 tokens)
CHUNK_OVERLAP = 200      # overlap to preserve context across boundaries
MIN_CHUNK_SIZE = 100     # discard tiny leftover chunks


@dataclass
class CodeChunk:
    chunk_id: str           # unique: "{relative_path}::chunk_{n}"
    relative_path: str      # source file path (for citation)
    language: str           # programming language
    content: str            # raw chunk text
    chunk_index: int        # position in file
    total_chunks: int       # total chunks for this file
    metadata: dict          # passed directly to ChromaDB


class CodeChunker:
    """
    Splits ParsedFile objects into overlapping text chunks suitable
    for embedding and vector search.

    Strategy:
    - Try to split on newlines first (keeps logical code blocks intact)
    - Fall back to character-level splitting if needed
    - Always includes file path and language in metadata for citation
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_files(self, files: list[ParsedFile]) -> list[CodeChunk]:
        """
        Chunk all parsed files and return a flat list of CodeChunks.
        """
        all_chunks: list[CodeChunk] = []
        for f in files:
            chunks = self._chunk_file(f)
            all_chunks.extend(chunks)

        logger.info(
            "Chunking complete",
            total_files=len(files),
            total_chunks=len(all_chunks),
        )
        return all_chunks

    def _chunk_file(self, file: ParsedFile) -> list[CodeChunk]:
        """Split a single file's content into overlapping chunks."""
        content = file.content
        raw_chunks = self._split_text(content)

        if not raw_chunks:
            return []

        total = len(raw_chunks)
        result = []

        for idx, text in enumerate(raw_chunks):
            chunk_id = f"{file.relative_path}::chunk_{idx}"
            result.append(
                CodeChunk(
                    chunk_id=chunk_id,
                    relative_path=file.relative_path,
                    language=file.language,
                    content=text,
                    chunk_index=idx,
                    total_chunks=total,
                    metadata={
                        "source": file.relative_path,
                        "language": file.language,
                        "chunk_index": idx,
                        "total_chunks": total,
                        "chunk_id": chunk_id,
                    },
                )
            )
        return result

    def _split_text(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks.

        Prefers splitting on blank lines (paragraph/function boundaries)
        for more semantically coherent chunks.
        """
        if len(text) <= self.chunk_size:
            stripped = text.strip()
            return [stripped] if len(stripped) >= MIN_CHUNK_SIZE else []

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            if end >= len(text):
                # Last chunk — take everything remaining
                chunk = text[start:].strip()
                if len(chunk) >= MIN_CHUNK_SIZE:
                    chunks.append(chunk)
                break

            # Try to find a clean split point (newline) near the end boundary
            split_point = text.rfind("\n", start, end)
            if split_point == -1 or split_point <= start:
                split_point = end  # fallback to hard split

            chunk = text[start:split_point].strip()
            if len(chunk) >= MIN_CHUNK_SIZE:
                chunks.append(chunk)

            # Move start forward by chunk_size - overlap
            start = split_point - self.chunk_overlap
            if start < 0:
                start = 0

        return chunks