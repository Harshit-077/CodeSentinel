from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.base_agent import BaseAgent, extract_json
from app.services.agents.state import AgentState
from app.services.rag.retriever import Retriever
from app.utils.logger import get_logger

logger = get_logger(__name__)

# OWASP Top 10 2021 — injected into prompt as domain knowledge
OWASP_CONTEXT = """
OWASP Top 10 2021 Reference:
A01 - Broken Access Control: missing auth checks, privilege escalation, CORS misconfiguration
A02 - Cryptographic Failures: plaintext secrets, weak hashing (MD5/SHA1), HTTP instead of HTTPS
A03 - Injection: SQL injection, command injection, LDAP injection, XSS
A04 - Insecure Design: missing rate limiting, no input validation architecture
A05 - Security Misconfiguration: default credentials, verbose error messages, debug mode in prod
A06 - Vulnerable Components: outdated dependencies with known CVEs
A07 - Auth Failures: weak passwords, broken session management, missing MFA
A08 - Integrity Failures: unsigned code, insecure deserialization
A09 - Logging Failures: no audit logs, logging sensitive data (passwords, tokens)
A10 - SSRF: user-controlled URLs fetched server-side without validation
"""


class SecurityAgent(BaseAgent):
    """
    Security Review Agent

    Responsibilities:
    - OWASP Top 10 2021 aligned vulnerability detection
    - Secret / credential exposure in code
    - SQL injection and command injection risks
    - Authentication and authorisation flaws
    - Insecure dependencies and configurations
    - Unsafe deserialization and input validation gaps

    RAG strategy:
    - Targets auth, DB, API, config, and environment code
    - Each query is tuned to surface a specific vulnerability class
    """

    name = "Security Review Agent"

    async def run(self, state: AgentState, db: AsyncSession) -> dict:
        job_id = state["job_id"]
        await self._log(db, job_id, "started", "Running OWASP-aligned security review")

        try:
            retriever = Retriever(job_id=job_id)
            repo_summary = state.get("repo_summary", {})

            # Target security-sensitive code areas
            auth_ctx = retriever.retrieve(
                "authentication login password token JWT session cookie auth middleware",
                n_results=5,
            )
            db_ctx = retriever.retrieve(
                "database query SQL execute cursor raw query string interpolation",
                n_results=4,
            )
            secrets_ctx = retriever.retrieve(
                "API key secret password token credential env config hardcoded",
                n_results=4,
            )
            input_ctx = retriever.retrieve(
                "user input request body form data validation sanitize escape",
                n_results=4,
            )
            config_ctx = retriever.retrieve(
                "CORS debug production settings environment configuration",
                n_results=3,
            )

            prompt = f"""You are a senior application security engineer conducting a code security review.

{OWASP_CONTEXT}

## Project Context
- Project: {repo_summary.get('project_name', 'unknown')}
- Language(s): {repo_summary.get('languages', [])}
- Frameworks: {repo_summary.get('frameworks', [])}

## Authentication & Session Code (RAG Retrieved)
{auth_ctx}

## Database & Query Code (RAG Retrieved)
{db_ctx}

## Secrets & Configuration (RAG Retrieved)
{secrets_ctx}

## Input Handling (RAG Retrieved)
{input_ctx}

## Application Configuration (RAG Retrieved)
{config_ctx}

## Task
Identify security vulnerabilities mapped to OWASP Top 10 categories.
Be precise — cite the file and exact vulnerability pattern.

Return ONLY valid JSON in this exact schema:
{{
  "total_vulnerabilities": number,
  "critical_count": number,
  "high_count": number,
  "medium_count": number,
  "low_count": number,
  "vulnerabilities": [
    {{
      "id": "SEC-001",
      "title": "short descriptive title",
      "description": "detailed explanation of the vulnerability",
      "file": "relative/path/to/file",
      "severity": "critical | high | medium | low",
      "owasp_category": "A01 | A02 | A03 | A04 | A05 | A06 | A07 | A08 | A09 | A10",
      "owasp_name": "e.g. Broken Access Control",
      "code_snippet": "the vulnerable code (max 5 lines)",
      "remediation": "specific fix recommendation",
      "cwe_reference": "CWE-XXX if applicable"
    }}
  ],
  "secrets_exposed": ["list any hardcoded secrets or credential patterns found"],
  "security_strengths": ["list any good security practices observed"],
  "overall_security_posture": "critical | poor | fair | good | excellent"
}}"""

            response = self.llm.invoke(prompt)
            result = extract_json(response.content)

            vuln_count = result.get("total_vulnerabilities", len(result.get("vulnerabilities", [])))
            await self._log(
                db, job_id, "done",
                f"Found {vuln_count} vulnerabilities — "
                f"posture: {result.get('overall_security_posture', 'unknown')} — "
                f"critical: {result.get('critical_count', 0)}"
            )

            logger.info("SecurityAgent complete", job_id=job_id, vulns=vuln_count)
            return {"security_issues": result}

        except Exception as e:
            error_msg = f"SecurityAgent failed: {str(e)}"
            logger.error(error_msg, job_id=job_id)
            await self._log(db, job_id, "failed", error_msg)
            return {
                "security_issues": {"error": error_msg, "vulnerabilities": []},
                "errors": state.get("errors", []) + [error_msg],
            }