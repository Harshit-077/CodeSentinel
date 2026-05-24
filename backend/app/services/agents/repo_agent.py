from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.base_agent import BaseAgent, extract_json
from app.services.agents.state import AgentState
from app.services.rag.retriever import Retriever
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RepoAgent(BaseAgent):
    """
    Repository Analysis Agent

    Responsibilities:
    - Summarise the repository's purpose and architecture
    - Identify languages, frameworks, and libraries
    - Analyse entry points and project structure
    - Detect dependency management approach
    - Provide context for all downstream agents

    Why it runs first:
    The repo summary is injected into every other agent's prompt,
    giving them architectural context before they analyse code.
    """

    name = "Repository Analysis Agent"

    async def run(self, state: AgentState, db: AsyncSession) -> dict:
        job_id = state["job_id"]
        await self._log(db, job_id, "started", "Analysing repository structure and architecture")

        try:
            retriever = Retriever(job_id=job_id)

            # Retrieve the most structurally significant files
            config_context = retriever.retrieve(
                "package.json requirements.txt pyproject.toml go.mod build.gradle dependencies",
                n_results=4,
            )
            entry_context = retriever.retrieve(
                "main entry point application setup server index app",
                n_results=4,
            )
            readme_context = retriever.retrieve(
                "README project description overview documentation",
                n_results=2,
            )

            structure = state.get("structure_summary", {})

            prompt = f"""You are a senior software architect performing a repository analysis.

## Repository Structure Metadata
- Total files: {structure.get('total_files', 'unknown')}
- Languages detected: {structure.get('languages', {})}
- Top-level directories: {structure.get('top_level_dirs', [])}
- Total size: {structure.get('total_size_kb', 'unknown')} KB

## Configuration & Dependency Files (RAG Retrieved)
{config_context}

## Entry Points & Application Setup (RAG Retrieved)
{entry_context}

## README / Documentation (RAG Retrieved)
{readme_context}

## Task
Analyse this repository and produce a structured JSON report.

Return ONLY valid JSON in this exact schema:
{{
  "project_name": "string — inferred project name",
  "purpose": "string — 2-3 sentence description of what this project does",
  "architecture_style": "string — e.g. MVC, microservices, monolith, CLI tool, library",
  "primary_language": "string",
  "languages": ["list", "of", "all", "languages"],
  "frameworks": ["list", "of", "detected", "frameworks"],
  "dependency_manager": "string — npm/pip/cargo/gradle/etc or unknown",
  "entry_points": ["list", "of", "main", "entry", "files"],
  "key_directories": {{
    "dirname": "purpose description"
  }},
  "complexity_assessment": "low | medium | high",
  "architecture_notes": "string — notable patterns, concerns, or strengths in the architecture"
}}"""

            response = self.llm.invoke(prompt)
            result = extract_json(response.content)

            await self._log(
                db, job_id, "done",
                f"Identified {result.get('primary_language', 'unknown')} project — "
                f"{result.get('architecture_style', 'unknown')} architecture — "
                f"complexity: {result.get('complexity_assessment', 'unknown')}"
            )

            logger.info("RepoAgent complete", job_id=job_id, project=result.get("project_name"))
            
            existing_contexts = state.get("retrieved_contexts") or {}
            return {
                "repo_summary": result,
                "retrieved_contexts": {
                    **existing_contexts,
                    "repo": [config_context, entry_context, readme_context],
                },
            }

        except Exception as e:
            error_msg = f"RepoAgent failed: {str(e)}"
            logger.error(error_msg, job_id=job_id)
            await self._log(db, job_id, "failed", error_msg)
            return {
                "repo_summary": {"error": error_msg},
                "errors": state.get("errors", []) + [error_msg],
            }