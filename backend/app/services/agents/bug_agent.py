from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.base_agent import BaseAgent, extract_json
from app.services.agents.state import AgentState
from app.services.rag.retriever import Retriever
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BugAgent(BaseAgent):
    """
    Bug Detection Agent

    Responsibilities:
    - Detect logical errors and off-by-one mistakes
    - Find null/undefined dereference risks
    - Identify unhandled exceptions and missing error handling
    - Spot anti-patterns and code smells
    - Flag runtime risks (type mismatches, infinite loops, etc.)
    - Suggest test cases for edge cases found

    RAG strategy:
    - Queries for error-prone patterns: exception handling, loops, type checks
    - Also queries for test files to understand what's already covered
    """

    name = "Bug Detection Agent"

    async def run(self, state: AgentState, db: AsyncSession) -> dict:
        job_id = state["job_id"]
        await self._log(db, job_id, "started", "Scanning codebase for bugs and logic errors")

        try:
            retriever = Retriever(job_id=job_id)
            repo_summary = state.get("repo_summary", {})

            BUG_QUERY = "try catch except error handling exception raise throw if else condition loop null undefined"

            error_handling_ctx = retriever.retrieve(
                "try catch except error handling exception raise throw",
                n_results=5,
            )
            logic_ctx = retriever.retrieve(
                "if else condition loop iteration index null undefined None check",
                n_results=5,
            )
            type_ctx = retriever.retrieve(
                "type cast conversion parse int float string boolean",
                n_results=3,
            )
            async_ctx = retriever.retrieve(
                "async await promise callback threading race condition",
                n_results=3,
            )

            # For RAGAS — raw chunks from the primary query
            raw_chunks = retriever.retrieve_raw(BUG_QUERY, n_results=8)
            context_texts = [c["content"] for c in raw_chunks]

            prompt = f"""You are a senior software engineer specialising in bug detection and code quality.

## Project Context
- Project: {repo_summary.get('project_name', 'unknown')}
- Language(s): {repo_summary.get('languages', [])}
- Architecture: {repo_summary.get('architecture_style', 'unknown')}

## Code Sample — Error Handling Patterns
{error_handling_ctx}

## Code Sample — Logic & Control Flow
{logic_ctx}

## Code Sample — Type Handling
{type_ctx}

## Code Sample — Async / Concurrency
{async_ctx}

## Task
Analyse the code samples above for bugs, logic errors, and runtime risks.
Be specific — cite the file and describe exactly what the bug is.

Return ONLY valid JSON in this exact schema:
{{
  "total_issues": number,
  "issues": [
    {{
      "id": "BUG-001",
      "title": "short descriptive title",
      "description": "detailed explanation of the bug",
      "file": "relative/path/to/file.py",
      "severity": "critical | high | medium | low",
      "category": "null_reference | unhandled_exception | logic_error | type_error | race_condition | anti_pattern | other",
      "code_snippet": "the problematic code (max 5 lines)",
      "suggested_fix": "concrete fix description or corrected code",
      "test_case_suggestion": "a unit test that would catch this bug"
    }}
  ],
  "anti_patterns_detected": ["list", "of", "general", "anti-patterns"],
  "overall_code_quality": "poor | fair | good | excellent",
  "testing_gaps": "description of what test coverage appears to be missing"
}}"""

            response = self.llm.invoke(prompt)
            result = extract_json(response.content)

            # ── RAGAS eval collection ─────────────────────────
            from app.services.evaluation.ragas_evaluator import AgentEvalInput
            state["eval_inputs"].append(
                AgentEvalInput(
                    agent_name="bug",
                    question=BUG_QUERY,
                    answer=response.content,
                    contexts=context_texts,
                )
            )
            
            issue_count = result.get("total_issues", len(result.get("issues", [])))
            await self._log(
                db, job_id, "done",
                f"Found {issue_count} bug(s) — code quality: {result.get('overall_code_quality', 'unknown')}"
            )

            logger.info("BugAgent complete", job_id=job_id, issues=issue_count)
            return {"bugs": result}

        except Exception as e:
            error_msg = f"BugAgent failed: {str(e)}"
            logger.error(error_msg, job_id=job_id)
            await self._log(db, job_id, "failed", error_msg)
            return {
                "bugs": {"error": error_msg, "issues": []},
                "errors": state.get("errors", []) + [error_msg],
            }