import json
import re
import uuid
from abc import ABC, abstractmethod

from langchain_groq import ChatGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.job import AgentLog
from app.services.agents.state import AgentState
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


def build_llm(temperature: float = 0.2) -> ChatGroq:
    """
    Single factory for the Groq LLM.

    Model: llama-3.3-70b-versatile
    - Best open-weight model on Groq as of 2024
    - 128k context window — can fit large code chunks
    - Free tier: 6000 tokens/min, 500k tokens/day

    Temperature 0.2:
    - Low enough for consistent structured JSON output
    - High enough to avoid repetitive phrasing
    """
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature,
        max_tokens=4096,
    )


def extract_json(text: str) -> dict:
    """
    Robustly extract a JSON object from an LLM response.

    LLMs often wrap JSON in markdown code fences — this handles:
    - ```json ... ```
    - ``` ... ```
    - Raw JSON with no fences
    - JSON embedded in surrounding explanation text
    """
    # Try stripping markdown fences first
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding the outermost JSON object directly
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    # Last resort — return error dict rather than crash the pipeline
    logger.warning("Could not extract JSON from LLM response", preview=text[:200])
    return {"error": "Failed to parse LLM response", "raw": text[:500]}


class BaseAgent(ABC):
    """
    Abstract base for all pipeline agents.

    Each concrete agent implements:
    - name: display name for logging and timeline UI
    - run(state, db): reads from state, returns partial state update dict
    """

    name: str = "BaseAgent"

    def __init__(self):
        self.llm = build_llm()

    async def _log(
        self,
        db: AsyncSession,
        job_id: str,
        status: str,
        message: str,
    ):
        """Write an AgentLog row — drives the frontend timeline."""
        log = AgentLog(
            job_id=uuid.UUID(job_id),
            agent_name=self.name,
            status=status,
            message=message,
        )
        db.add(log)
        await db.commit()

    @abstractmethod
    async def run(self, state: AgentState, db: AsyncSession) -> dict:
        """
        Execute this agent's analysis.

        Args:
            state: Full current pipeline state
            db:    Async DB session for logging

        Returns:
            Dict of keys to merge into AgentState
            (only the keys this agent is responsible for)
        """
        ...