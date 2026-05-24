from typing import TypedDict, Optional


class AgentState(TypedDict):
    """
    The single shared state object that flows through every node
    in the LangGraph pipeline.

    Why TypedDict?
    - LangGraph requires a typed state schema at graph definition time
    - Gives full type safety across all agent functions
    - Each agent reads what it needs and writes its own output key
    - The Final Reviewer reads ALL output keys to synthesize the report

    Flow:
        START
          → repo_agent        (fills repo_summary)
          → bug_agent         (fills bugs)
          → security_agent    (fills security_issues)
          → docs_agent        (fills docs_suggestions)
          → reviewer_agent    (fills final_review, severity_score, confidence_score)
        END
    """

    # ── Job context (set before graph starts) ────────────────────────────────
    job_id: str
    source_type: str                        # "github" | "zip"
    source_ref: str                         # URL or file path
    structure_summary: dict                 # from FileParser.get_structure_summary()

    # ── Agent outputs (filled progressively) ─────────────────────────────────
    repo_summary: Optional[dict]            # Repository Analysis Agent
    bugs: Optional[dict]                    # Bug Detection Agent
    security_issues: Optional[dict]         # Security Review Agent
    docs_suggestions: Optional[dict]        # Documentation Agent

    # ── Final outputs ─────────────────────────────────────────────────────────
    final_review: Optional[dict]            # Final Reviewer Agent
    severity_score: Optional[int]           # 0–100
    confidence_score: Optional[int]         # 0–100

    # ── Error tracking ────────────────────────────────────────────────────────
    errors: list[str]  
    eval_inputs: list                      # non-fatal agent errors accumulate here