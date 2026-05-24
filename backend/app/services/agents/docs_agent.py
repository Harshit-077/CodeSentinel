from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.base_agent import BaseAgent, extract_json
from app.services.agents.state import AgentState
from app.services.rag.retriever import Retriever
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocsAgent(BaseAgent):
    """
    Documentation Agent

    Responsibilities:
    - Evaluate existing README completeness
    - Identify functions/classes missing docstrings
    - Suggest API documentation improvements
    - Recommend setup guide additions
    - Generate example docstrings for key functions

    RAG strategy:
    - Queries README and public-facing interfaces
    - Targets functions without docstrings
    - Checks for API route documentation
    """

    name = "Documentation Agent"

    async def run(self, state: AgentState, db: AsyncSession) -> dict:
        job_id = state["job_id"]
        await self._log(db, job_id, "started", "Evaluating documentation coverage and quality")

        try:
            retriever = Retriever(job_id=job_id)
            repo_summary = state.get("repo_summary", {})
            DOCS_QUERY = "README docstring documentation function description param return API endpoint"
            readme_ctx = retriever.retrieve(
                "README installation setup usage configuration getting started",
                n_results=4,
            )
            public_api_ctx = retriever.retrieve(
                "function def class public method API endpoint route handler",
                n_results=6,
            )
            docstring_ctx = retriever.retrieve(
                "docstring comment description param return type annotation",
                n_results=4,
            )

            prompt = f"""You are a senior technical writer and software engineer reviewing code documentation.

## Project Context
- Project: {repo_summary.get('project_name', 'unknown')}
- Purpose: {repo_summary.get('purpose', 'unknown')}
- Language(s): {repo_summary.get('languages', [])}
- Frameworks: {repo_summary.get('frameworks', [])}

## README & Setup Documentation (RAG Retrieved)
{readme_ctx}

## Public Functions & API Interfaces (RAG Retrieved)
{public_api_ctx}

## Existing Docstrings & Comments (RAG Retrieved)
{docstring_ctx}

## Task
Evaluate the documentation quality and provide actionable improvement suggestions.

Return ONLY valid JSON in this exact schema:
{{
  "readme_score": number (0-100),
  "docstring_coverage_estimate": "low | medium | high",
  "readme_evaluation": {{
    "has_installation_guide": true | false,
    "has_usage_examples": true | false,
    "has_api_reference": true | false,
    "has_contributing_guide": true | false,
    "has_license": true | false,
    "missing_sections": ["list of missing important sections"]
  }},
  "undocumented_functions": [
    {{
      "function_name": "name",
      "file": "relative/path",
      "suggested_docstring": "a generated docstring for this function"
    }}
  ],
  "readme_improvements": [
    {{
      "section": "section name",
      "suggestion": "specific improvement description",
      "priority": "high | medium | low"
    }}
  ],
  "api_documentation_gaps": ["list of API endpoints or interfaces missing documentation"],
  "overall_documentation_grade": "A | B | C | D | F",
  "quick_wins": ["list of fast documentation improvements that would have high impact"]
}}"""
            raw_chunks = retriever.retrieve_raw(DOCS_QUERY, n_results=8)
            context_texts = [c["content"] for c in raw_chunks]

            response = self.llm.invoke(prompt)
            result = extract_json(response.content)

            # ── RAGAS eval collection ─────────────────────────
            from app.services.evaluation.ragas_evaluator import AgentEvalInput
            state["eval_inputs"].append(
                AgentEvalInput(
                    agent_name="docs",
                    question=DOCS_QUERY,
                    answer=response.content,
                    contexts=context_texts,
                )
            )
            await self._log(
                db, job_id, "done",
                f"Documentation grade: {result.get('overall_documentation_grade', '?')} — "
                f"README score: {result.get('readme_score', '?')}/100 — "
                f"docstring coverage: {result.get('docstring_coverage_estimate', 'unknown')}"
            )

            logger.info("DocsAgent complete", job_id=job_id, grade=result.get("overall_documentation_grade"))
            return {"docs_suggestions": result}

        except Exception as e:
            error_msg = f"DocsAgent failed: {str(e)}"
            logger.error(error_msg, job_id=job_id)
            await self._log(db, job_id, "failed", error_msg)
            return {
                "docs_suggestions": {"error": error_msg},
                "errors": state.get("errors", []) + [error_msg],
            }