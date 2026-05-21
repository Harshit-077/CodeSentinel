"""
Scoring Engine
==============

Produces two scores (0–100) from raw agent outputs:

severity_score  — how bad is the codebase overall?
confidence_score — how reliable are our findings?

Why deterministic scoring instead of asking the LLM?
- LLMs are inconsistent with numbers (say "72" one run, "68" next)
- Scoring is a pure function of structured data — no LLM needed
- Reproducible: same inputs always produce same score
- Explainable: every point deduction is traceable
"""

from dataclasses import dataclass
from typing import Any


# ── Severity weights (per issue level) ───────────────────────────────────────
SEVERITY_WEIGHTS = {
    "critical": 100,
    "high":     70,
    "medium":   35,
    "low":      10,
    "info":     2,
}

# ── Security posture modifier ─────────────────────────────────────────────────
POSTURE_MODIFIER = {
    "critical":  1.40,
    "poor":      1.20,
    "fair":      1.00,
    "good":      0.80,
    "excellent": 0.60,
}

# ── Code quality modifier ─────────────────────────────────────────────────────
QUALITY_MODIFIER = {
    "poor":      1.20,
    "fair":      1.05,
    "good":      0.90,
    "excellent": 0.75,
}


@dataclass
class ScoringResult:
    severity_score: int       # 0–100 (higher = worse)
    confidence_score: int     # 0–100 (higher = more reliable)
    breakdown: dict           # explainable sub-scores


def compute_severity(
    bugs: dict[str, Any],
    security_issues: dict[str, Any],
    docs_suggestions: dict[str, Any],
    errors: list[str],
) -> ScoringResult:
    """
    Compute severity and confidence scores from agent outputs.

    Severity formula:
      base = weighted_avg(all issue severities)
      base *= security_posture_modifier
      base *= code_quality_modifier
      penalty += 5 per critical security issue
      penalty += 2 per failed agent
      clamp to [0, 100]

    Confidence formula:
      starts at 100
      -20 per agent that returned an error dict
      -5  per pipeline error in errors list
      -10 if no issues found at all (suspicious)
      clamp to [0, 100]
    """

    bug_issues      = bugs.get("issues", []) if bugs else []
    vulns           = security_issues.get("vulnerabilities", []) if security_issues else []
    quality         = bugs.get("overall_code_quality", "fair") if bugs else "fair"
    posture         = security_issues.get("overall_security_posture", "fair") if security_issues else "fair"
    readme_score    = docs_suggestions.get("readme_score", 50) if docs_suggestions else 50
    critical_count  = security_issues.get("critical_count", 0) if security_issues else 0

    # ── Severity ──────────────────────────────────────────────────────────────
    all_severities = (
        [SEVERITY_WEIGHTS.get(i.get("severity", "low"), 10) for i in bug_issues]
        + [SEVERITY_WEIGHTS.get(v.get("severity", "low"), 10) for v in vulns]
    )

    if all_severities:
        raw_base = sum(all_severities) / len(all_severities)
        # Volume factor: many issues are worse than few, up to a point
        volume_factor = min(1.5, 1 + (len(all_severities) - 1) * 0.03)
        base = raw_base * volume_factor
    else:
        base = 0.0

    # Apply modifiers
    base *= POSTURE_MODIFIER.get(posture.lower(), 1.0)
    base *= QUALITY_MODIFIER.get(quality.lower(), 1.0)

    # Critical security penalty
    base += critical_count * 5

    # Poor documentation penalty (docs gaps often hide real issues)
    if readme_score < 30:
        base += 8
    elif readme_score < 50:
        base += 3

    severity_score = int(min(100, max(0, base)))

    # ── Confidence ────────────────────────────────────────────────────────────
    confidence = 100

    # Penalise failed agents
    agent_outputs = [bugs, security_issues, docs_suggestions]
    for output in agent_outputs:
        if not output or "error" in output:
            confidence -= 20

    # Penalise pipeline errors
    confidence -= len(errors) * 5

    # If nothing was found at all, that's suspicious — lower confidence
    if not bug_issues and not vulns:
        confidence -= 10

    confidence_score = int(min(100, max(0, confidence)))

    breakdown = {
        "bug_count":           len(bug_issues),
        "vuln_count":          len(vulns),
        "critical_vulns":      critical_count,
        "code_quality":        quality,
        "security_posture":    posture,
        "readme_score":        readme_score,
        "raw_severity_base":   round(base, 1),
        "agent_errors":        len(errors),
    }

    return ScoringResult(
        severity_score=severity_score,
        confidence_score=confidence_score,
        breakdown=breakdown,
    )