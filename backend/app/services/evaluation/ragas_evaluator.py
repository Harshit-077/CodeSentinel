"""
RAGAS-Style RAG Evaluation
==========================
Implements three RAG quality metrics using the existing Groq LLM —
no external ragas package required.

Metrics (all returned in [0.0, 1.0]):
- faithfulness:         Are answer claims grounded in the retrieved context?
- answer_relevancy:     Is the answer on-topic for the posed question?
- context_utilisation:  What fraction of retrieved chunks actually contributed?

Usage:
    evaluator = RagasEvaluator()
    scores = await evaluator.evaluate_agent(
        agent_name="Bug Detection Agent",
        question="Find all bugs in this Python codebase",
        answer="{ ... bug agent JSON output ... }",
        contexts=["chunk1 code ...", "chunk2 code ..."],
    )
    # => {"faithfulness": 0.82, "answer_relevancy": 0.91, "context_utilisation": 0.60}
"""

import json
import re
from typing import Any

from langchain_groq import ChatGroq

from app.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


def _build_eval_llm() -> ChatGroq:
    """Separate LLM instance for evaluation — temperature 0 for determinism."""
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0,
        max_tokens=2048,
    )


def _extract_json_safe(text: str) -> dict:
    """Extract JSON from LLM response, returning fallback on failure."""
    # Try markdown fence
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    # Try bare JSON object
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group())
        except json.JSONDecodeError:
            pass
    return {}


class RagasEvaluator:
    """
    RAGAS-style evaluator that uses the existing Groq LLM to score
    RAG pipeline quality for each analysis agent.
    """

    def __init__(self):
        self._llm = _build_eval_llm()

    # ── Faithfulness ────────────────────────────────────────────────────────────

    async def _faithfulness(
        self, answer: str, contexts: list[str]
    ) -> float:
        """
        Decompose the answer into atomic claims and check each against contexts.
        Score = supported_claims / total_claims
        """
        if not contexts or not answer.strip():
            return 0.0

        context_block = "\n\n".join(
            f"[Context {i+1}]:\n{c}" for i, c in enumerate(contexts[:6])
        )

        prompt = f"""You are an expert evaluator assessing faithfulness of an AI response.

RETRIEVED CONTEXTS:
{context_block}

AI ANSWER (code analysis output):
{answer[:2000]}

Task:
1. Extract up to 10 atomic factual claims made in the AI answer.
2. For each claim, determine if it is supported by the retrieved contexts above.

Return ONLY valid JSON:
{{
  "claims": [
    {{"claim": "...", "supported": true}},
    {{"claim": "...", "supported": false}}
  ]
}}"""

        try:
            response = self._llm.invoke(prompt)
            result = _extract_json_safe(response.content)
            claims = result.get("claims", [])
            if not claims:
                return 0.5  # neutral fallback
            supported = sum(1 for c in claims if c.get("supported", False))
            return round(supported / len(claims), 3)
        except Exception as e:
            logger.warning("Faithfulness evaluation failed", error=str(e))
            return 0.0

    # ── Answer Relevancy ────────────────────────────────────────────────────────

    async def _answer_relevancy(
        self, question: str, answer: str
    ) -> float:
        """
        Ask the LLM to rate how relevant the answer is to the question (0–1).
        """
        if not answer.strip():
            return 0.0

        prompt = f"""You are an expert evaluator assessing answer relevancy.

QUESTION (analysis task):
{question}

ANSWER (agent output):
{answer[:2000]}

Rate how relevant and on-topic this answer is to the question.
Consider: Does it address the question? Does it stay focused? Does it avoid irrelevant content?

Return ONLY valid JSON:
{{
  "relevancy_score": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence>"
}}"""

        try:
            response = self._llm.invoke(prompt)
            result = _extract_json_safe(response.content)
            score = float(result.get("relevancy_score", 0.5))
            return round(min(1.0, max(0.0, score)), 3)
        except Exception as e:
            logger.warning("Answer relevancy evaluation failed", error=str(e))
            return 0.0

    # ── Context Utilisation ─────────────────────────────────────────────────────

    async def _context_utilisation(
        self, answer: str, contexts: list[str]
    ) -> float:
        """
        Determine what fraction of retrieved chunks meaningfully contributed
        to the answer. Score = used_chunks / total_chunks
        """
        if not contexts or not answer.strip():
            return 0.0

        context_list = "\n".join(
            f"[Context {i+1}]: {c[:300]}" for i, c in enumerate(contexts[:6])
        )

        prompt = f"""You are evaluating whether retrieved code chunks were actually used in an analysis.

RETRIEVED CHUNKS:
{context_list}

ANALYSIS OUTPUT:
{answer[:2000]}

For each context chunk, determine if it contributed to (was used in) the analysis output.

Return ONLY valid JSON:
{{
  "chunk_usage": [
    {{"chunk_id": 1, "used": true}},
    {{"chunk_id": 2, "used": false}}
  ]
}}"""

        try:
            response = self._llm.invoke(prompt)
            result = _extract_json_safe(response.content)
            usages = result.get("chunk_usage", [])
            if not usages:
                return 0.5
            used = sum(1 for u in usages if u.get("used", False))
            return round(used / len(usages), 3)
        except Exception as e:
            logger.warning("Context utilisation evaluation failed", error=str(e))
            return 0.0

    # ── Public API ──────────────────────────────────────────────────────────────

    async def evaluate_agent(
        self,
        agent_name: str,
        question: str,
        answer: str,
        contexts: list[str],
    ) -> dict[str, float]:
        """
        Run all three RAGAS-style metrics for a single agent's output.

        Returns:
            {
                "faithfulness": float,
                "answer_relevancy": float,
                "context_utilisation": float,
            }
        """
        logger.info("RAGAS evaluation started", agent=agent_name)

        faithfulness = await self._faithfulness(answer, contexts)
        relevancy = await self._answer_relevancy(question, answer)
        utilisation = await self._context_utilisation(answer, contexts)

        scores = {
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
            "context_utilisation": utilisation,
        }

        logger.info(
            "RAGAS evaluation complete",
            agent=agent_name,
            **scores,
        )
        return scores

    async def evaluate_all_agents(
        self,
        agent_data: list[dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        """
        Evaluate multiple agents sequentially.

        Args:
            agent_data: list of dicts with keys:
                - name:     agent display name
                - question: task description
                - answer:   serialised output
                - contexts: list of retrieved code chunk strings

        Returns:
            { agent_name: { metric: score, ... }, ... }
        """
        results: dict[str, dict[str, float]] = {}
        for agent in agent_data:
            scores = await self.evaluate_agent(
                agent_name=agent["name"],
                question=agent["question"],
                answer=agent["answer"],
                contexts=agent.get("contexts", []),
            )
            results[agent["name"]] = scores
        return results
