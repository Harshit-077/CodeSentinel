import os
from dataclasses import dataclass
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Extensions we care about ──────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    # Web / JS
    ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
    # Python
    ".py",
    # Backend / systems
    ".go", ".rs", ".java", ".kt", ".scala", ".cs", ".cpp", ".c", ".h",
    # Config / infra
    ".yaml", ".yml", ".toml", ".json", ".env.example", ".dockerfile",
    # Docs
    ".md", ".txt", ".rst",
    # Shell
    ".sh", ".bash",
    # SQL
    ".sql",
    # Ruby / PHP
    ".rb", ".php",
}

# ── Directories to always skip ────────────────────────────────────────────────
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "vendor", "target", "bin", "obj",
    ".idea", ".vscode", "eggs", "*.egg-info",
}

# ── Files to always skip ─────────────────────────────────────────────────────
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", "Gemfile.lock",
    ".DS_Store", "Thumbs.db",
}

MAX_FILE_SIZE_BYTES = 500 * 1024   # 500 KB — skip huge generated files
MAX_FILES_PER_REPO = 300           # Hard cap to prevent runaway processing


@dataclass
class ParsedFile:
    path: str           # Absolute path
    relative_path: str  # Path relative to repo root (for display)
    content: str        # Raw file content
    language: str       # Detected language (from extension)
    size_bytes: int


EXTENSION_TO_LANGUAGE = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".vue": "Vue",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".cs": "C#", ".cpp": "C++", ".c": "C", ".h": "C/C++ Header",
    ".rb": "Ruby", ".php": "PHP", ".scala": "Scala",
    ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML",
    ".json": "JSON", ".md": "Markdown", ".sh": "Shell",
    ".sql": "SQL", ".txt": "Text", ".rst": "reStructuredText",
    ".svelte": "Svelte",
}


class FileParser:
    """
    Walks a repository directory tree and returns a flat list of
    ParsedFile objects for all readable source files.
    """

    def parse(self, repo_dir: str) -> list[ParsedFile]:
        """
        Walk repo_dir and return all parseable files.

        Args:
            repo_dir: Absolute path to cloned/extracted repository

        Returns:
            List of ParsedFile dataclasses, capped at MAX_FILES_PER_REPO
        """
        results: list[ParsedFile] = []
        skipped = 0

        for root, dirs, files in os.walk(repo_dir):
            # Prune skip dirs IN PLACE so os.walk doesn't descend into them
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS and not d.startswith(".")
            ]

            for filename in files:
                if len(results) >= MAX_FILES_PER_REPO:
                    logger.warning(
                        "File cap reached, stopping parse",
                        cap=MAX_FILES_PER_REPO,
                        skipped_remaining=True,
                    )
                    return results

                if filename in SKIP_FILES:
                    skipped += 1
                    continue

                ext = os.path.splitext(filename)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    skipped += 1
                    continue

                abs_path = os.path.join(root, filename)
                file_size = os.path.getsize(abs_path)

                if file_size > MAX_FILE_SIZE_BYTES:
                    logger.debug("Skipping oversized file", path=abs_path, size=file_size)
                    skipped += 1
                    continue

                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    logger.warning("Could not read file", path=abs_path, error=str(e))
                    skipped += 1
                    continue

                # Skip effectively empty files
                if len(content.strip()) < 10:
                    skipped += 1
                    continue

                rel_path = os.path.relpath(abs_path, repo_dir)
                results.append(
                    ParsedFile(
                        path=abs_path,
                        relative_path=rel_path,
                        content=content,
                        language=EXTENSION_TO_LANGUAGE.get(ext, "Unknown"),
                        size_bytes=file_size,
                    )
                )

        logger.info(
            "File parsing complete",
            total_parsed=len(results),
            skipped=skipped,
            repo_dir=repo_dir,
        )
        return results

    def get_structure_summary(self, files: list[ParsedFile]) -> dict:
        """
        Summarise the repo for the Repo Analysis agent — languages,
        file counts, directory tree overview.
        """
        lang_counts: dict[str, int] = {}
        dirs: set[str] = set()

        for f in files:
            lang_counts[f.language] = lang_counts.get(f.language, 0) + 1
            top_dir = f.relative_path.split(os.sep)[0]
            dirs.add(top_dir)

        return {
            "total_files": len(files),
            "languages": lang_counts,
            "top_level_dirs": sorted(dirs),
            "total_size_kb": round(sum(f.size_bytes for f in files) / 1024, 1),
        }