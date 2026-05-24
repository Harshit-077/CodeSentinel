"""
LLM-as-a-Judge Evaluator
========================
Uses the Groq LLM to holistically evaluate the quality of the final
consolidated code review report across five expert criteria.

Criteria (each scored 0–10 with rationale):
  accuracy            - Technical correctness of findings
  completeness        - Coverage across bug, security, docs, architecture
  actionability       - Are fixes specific and implementable?
  clarity             - Is the report readable and well-structured?
  severity_calibration - Are severity levels appropriately assigned?

Returns:
  {
    "accuracy":             {"score": 8, "rationale": "..."},
    "completeness":         {"score": 7, "rationale": "..."},
    "actionability":        {"score": 9, "rationale": "..."},
    "clarity":              {"score": 8, "rationale": "..."},
    "severity_calibration": {"score": 7, "rationale": "..."},
    "overall_score":        8.0,
    "summary":              "..."
  }
"""

import json
import re
from typing import Any

from langchain_groq import ChatGroq

from app.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


def _build_judge_llm() -> ChatGroq:
    """Dedicated LLM instance for judging — temperature 0 for consistency."""
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0,
        max_tokens=3000,
    )


def _extract_json_safe(text: str) -> dict:
    """Extract JSON from LLM response, returning fallback on failure."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group())
        except json.JSONDecodeError:
            pass
    return {}


# Weights for computing overall_score from individual criteria
CRITERIA_WEIGHTS = {
    "accuracy":             0.30,
    "completeness":         0.25,
    "actionability":        0.20,
    "clarity":              0.15,
    "severity_calibration": 0.10,
}


class LLMJudge:
    """
    Expert LLM judge that evaluates the final code review report
    produced by the multi-agent pipeline.
    """

    def __init__(self):
        self._llm = _build_judge_llm()

    def _build_prompt(self, report_data: dict[str, Any]) -> str:
        """Construct the evaluation prompt from report fields."""

        bugs = report_data.get("bugs", {}) or {}
        security = report_data.get("security_issues", {}) or {}
        docs = report_data.get("docs_suggestions", {}) or {}
        final = report_data.get("final_review", {}) or {}

        # Summarise key stats for the judge
        bug_count = bugs.get("total_issues", 0)
        vuln_count = security.get("total_vulnerabilities", 0)
        critical_count = security.get("critical_count", 0)
        doc_grade = docs.get("overall_documentation_grade", "?")
        executive_summary = final.get("executive_summary", "Not available")
        action_items = final.get("action_items", [])[:5]
        key_findings = final.get("key_findings", [])[:5]
        severity_score = report_data.get("severity_score", 0)
        confidence_score = report_data.get("confidence_score", 0)

        # First 3 bugs
        sample_bugs = [
            f"  - [{b.get('severity','?').upper()}] {b.get('title','?')}: {b.get('description','')[:100]}"
            for b in (bugs.get("issues", []) or [])[:3]
        ]
        # First 3 vulns
        sample_vulns = [
            f"  - [{v.get('severity','?').upper()}] {v.get('title','?')}: {v.get('description','')[:100]}"
            for v in (security.get("vulnerabilities", []) or [])[:3]
        ]

        return f"""You are a senior engineering manager and code quality expert acting as an impartial judge.
Your task is to evaluate the quality of an AI-generated code review report.

## REPORT BEING EVALUATED

### Scores
- Severity Score: {severity_score}/100
- Confidence Score: {confidence_score}/100

### Executive Summary
{executive_summary}

### Bug Analysis
- Total bugs found: {bug_count}
- Code quality: {bugs.get('overall_code_quality', 'N/A')}
- Sample findings:
{chr(10).join(sample_bugs) if sample_bugs else '  (none)'}

### Security Analysis
- Total vulnerabilities: {vuln_count} (Critical: {critical_count})
- Security posture: {security.get('overall_security_posture', 'N/A')}
- Sample findings:
{chr(10).join(sample_vulns) if sample_vulns else '  (none)'}

### Documentation Analysis
- Grade: {doc_grade}
- README score: {docs.get('readme_score', 0)}/100
- Docstring coverage: {docs.get('docstring_coverage_estimate', 'N/A')}

### Key Findings
{json.dumps(key_findings, indent=2)}

### Top Action Items
{json.dumps(action_items, indent=2)}

### Risk Assessment
{json.dumps(final.get('risk_assessment', {}), indent=2)}

## EVALUATION TASK

Score this report on each of the following criteria from 0 to 10, where:
- 0-3: Poor (major issues, not useful)
- 4-6: Acceptable (does the job but could be much better)
- 7-8: Good (solid quality, minor improvements possible)
- 9-10: Excellent (professional, comprehensive, immediately actionable)

Criteria definitions:
- **accuracy**: Are the technical findings (bugs/vulns) likely to be correct? Do descriptions match real issues?
- **completeness**: Does the report cover all major concern areas (bugs, security, docs, architecture)?
- **actionability**: Are the recommended fixes specific and implementable by a developer right now?
- **clarity**: Is the report well-organised, easy to read, and free of vague language?
- **severity_calibration**: Are severity levels (critical/high/medium/low) appropriately assigned relative to each other?

Return ONLY valid JSON in this exact schema:
{{
  "accuracy": {{
    "score": <integer 0-10>,
    "rationale": "<one to two sentences explaining the score>"
  }},
  "completeness": {{
    "score": <integer 0-10>,
    "rationale": "<one to two sentences explaining the score>"
  }},
  "actionability": {{
    "score": <integer 0-10>,
    "rationale": "<one to two sentences explaining the score>"
  }},
  "clarity": {{
    "score": <integer 0-10>,
    "rationale": "<one to two sentences explaining the score>"
  }},
  "severity_calibration": {{
    "score": <integer 0-10>,
    "rationale": "<one to two sentences explaining the score>"
  }},
  "summary": "<2-3 sentence overall assessment of this report's quality>"
}}"""

    async def evaluate(self, report_data: dict[str, Any]) -> dict[str, Any]:
        """
        Run LLM-as-a-Judge evaluation on the final report.

        Args:
            report_data: Dict containing bugs, security_issues,
                         docs_suggestions, final_review, severity_score,
                         confidence_score fields from the Report model.

        Returns:
            Dict with per-criterion scores + rationales + overall_score.
        """
        logger.info("LLM judge evaluation started")

        prompt = self._build_prompt(report_data)

        try:
            response = self._llm.invoke(prompt)
            result = _extract_json_safe(response.content)

            if not result:
                raise ValueError("LLM judge returned empty/unparseable JSON")

            # Compute weighted overall score
            overall = 0.0
            for criterion, weight in CRITERIA_WEIGHTS.items():
                criterion_data = result.get(criterion, {})
                score = float(criterion_data.get("score", 0))
                overall += score * weight

            result["overall_score"] = round(overall, 2)

            logger.info(
                "LLM judge evaluation complete",
                overall=result["overall_score"],
                accuracy=result.get("accuracy", {}).get("score"),
                completeness=result.get("completeness", {}).get("score"),
                actionability=result.get("actionability", {}).get("score"),
            )
            return result

        except Exception as e:
            error_msg = f"LLM judge evaluation failed: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "accuracy":             {"score": 0, "rationale": "Evaluation failed"},
                "completeness":         {"score": 0, "rationale": "Evaluation failed"},
                "actionability":        {"score": 0, "rationale": "Evaluation failed"},
                "clarity":              {"score": 0, "rationale": "Evaluation failed"},
                "severity_calibration": {"score": 0, "rationale": "Evaluation failed"},
                "overall_score":        0.0,
                "summary":              "Evaluation could not be completed.",
            }
