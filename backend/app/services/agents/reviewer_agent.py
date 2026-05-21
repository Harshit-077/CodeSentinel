from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.base_agent import BaseAgent, extract_json
from app.services.agents.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReviewerAgent(BaseAgent):
    """
    Final Reviewer Agent

    Responsibilities:
    - Synthesise outputs from all 4 upstream agents
    - Validate consistency and remove duplicates/contradictions
    - Assign global severity score (0-100) and confidence score (0-100)
    - Generate prioritised action items
    - Write the executive summary for the PDF report

    Why no RAG here:
    This agent's job is synthesis, not retrieval. It works entirely
    from the structured outputs of the previous agents — adding another
    retrieval step would dilute its focus and add latency.

    Scoring methodology:
    - severity_score: weighted average of vulnerability severity levels
      (critical=100, high=75, medium=40, low=10)
    - confidence_score: based on how many agents produced clean outputs
      and consistency between agent findings
    """

    name = "Final Reviewer Agent"

    async def run(self, state: AgentState, db: AsyncSession) -> dict:
        job_id = state["job_id"]
        await self._log(db, job_id, "started", "Synthesising all agent outputs into final report")

        try:
            repo_summary = state.get("repo_summary", {})
            bugs = state.get("bugs", {})
            security_issues = state.get("security_issues", {})
            docs_suggestions = state.get("docs_suggestions", {})
            errors = state.get("errors", [])

            # ── Pre-compute scoring inputs ────────────────────────────────────
            bug_issues = bugs.get("issues", [])
            vulns = security_issues.get("vulnerabilities", [])

            # Severity weights
            WEIGHTS = {"critical": 100, "high": 75, "medium": 40, "low": 10}

            all_severities = (
                [WEIGHTS.get(i.get("severity", "low"), 10) for i in bug_issues]
                + [WEIGHTS.get(v.get("severity", "low"), 10) for v in vulns]
            )

            raw_severity = (
                int(sum(all_severities) / len(all_severities))
                if all_severities else 0
            )
            # Dampen: a single critical in a clean repo shouldn't score 100
            severity_score = min(100, int(raw_severity * (1 + len(all_severities) * 0.02)))

            # Confidence: penalise for agent errors and empty outputs
            agent_results = [repo_summary, bugs, security_issues, docs_suggestions]
            failed_agents = sum(1 for r in agent_results if "error" in r or not r)
            confidence_score = max(0, 100 - (failed_agents * 20) - (len(errors) * 5))

            prompt = f"""You are a principal engineer writing the final engineering review report.

## Agent Outputs Summary

### Repository Analysis
- Project: {repo_summary.get('project_name', 'unknown')}
- Purpose: {repo_summary.get('purpose', 'N/A')}
- Architecture: {repo_summary.get('architecture_style', 'unknown')}
- Complexity: {repo_summary.get('complexity_assessment', 'unknown')}
- Architecture notes: {repo_summary.get('architecture_notes', 'N/A')}

### Bug Detection Results
- Total bugs: {bugs.get('total_issues', 0)}
- Code quality: {bugs.get('overall_code_quality', 'unknown')}
- Anti-patterns: {bugs.get('anti_patterns_detected', [])}
- Testing gaps: {bugs.get('testing_gaps', 'N/A')}
- Top bugs: {[i.get('title') for i in bug_issues[:5]]}

### Security Review Results
- Total vulnerabilities: {security_issues.get('total_vulnerabilities', 0)}
- Critical: {security_issues.get('critical_count', 0)}
- High: {security_issues.get('high_count', 0)}
- Overall posture: {security_issues.get('overall_security_posture', 'unknown')}
- Secrets exposed: {security_issues.get('secrets_exposed', [])}
- Top vulns: {[v.get('title') for v in vulns[:5]]}

### Documentation Results
- Grade: {docs_suggestions.get('overall_documentation_grade', '?')}
- README score: {docs_suggestions.get('readme_score', 0)}/100
- Docstring coverage: {docs_suggestions.get('docstring_coverage_estimate', 'unknown')}
- Quick wins: {docs_suggestions.get('quick_wins', [])}

### Pipeline Health
- Computed severity score: {severity_score}/100
- Computed confidence score: {confidence_score}/100
- Agent errors: {errors if errors else 'none'}

## Task
Write the final engineering review synthesising all findings above.

Return ONLY valid JSON in this exact schema:
{{
  "executive_summary": "3-5 sentence professional summary of the overall codebase health",
  "key_findings": [
    {{
      "category": "Security | Bugs | Documentation | Architecture",
      "finding": "specific finding statement",
      "severity": "critical | high | medium | low | info"
    }}
  ],
  "action_items": [
    {{
      "priority": 1,
      "action": "specific actionable task",
      "category": "Security | Bugs | Documentation | Architecture",
      "effort": "low | medium | high",
      "impact": "low | medium | high"
    }}
  ],
  "strengths": ["list of genuine strengths observed in the codebase"],
  "risk_assessment": {{
    "production_readiness": "not ready | needs work | nearly ready | ready",
    "top_risk": "the single highest priority risk to address",
    "security_risk_level": "critical | high | medium | low",
    "maintainability_risk": "high | medium | low"
  }},
  "recommended_next_steps": ["ordered list of the 5 most important next steps"],
  "metrics_summary": {{
    "total_bugs": number,
    "total_vulnerabilities": number,
    "critical_issues": number,
    "documentation_grade": "letter grade",
    "overall_health_score": number (0-100)
  }}
}}"""

            response = self.llm.invoke(prompt)
            result = extract_json(response.content)

            await self._log(
                db, job_id, "done",
                f"Report complete — severity: {severity_score}/100 — "
                f"confidence: {confidence_score}/100 — "
                f"production readiness: {result.get('risk_assessment', {}).get('production_readiness', 'unknown')}"
            )

            logger.info(
                "ReviewerAgent complete",
                job_id=job_id,
                severity=severity_score,
                confidence=confidence_score,
            )

            return {
                "final_review": result,
                "severity_score": severity_score,
                "confidence_score": confidence_score,
            }

        except Exception as e:
            error_msg = f"ReviewerAgent failed: {str(e)}"
            logger.error(error_msg, job_id=job_id)
            await self._log(db, job_id, "failed", error_msg)
            return {
                "final_review": {"error": error_msg},
                "severity_score": 0,
                "confidence_score": 0,
                "errors": state.get("errors", []) + [error_msg],
            }