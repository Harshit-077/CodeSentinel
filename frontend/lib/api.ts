const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface AgentLog {
  agent_name: string;
  status: "started" | "done" | "failed";
  message: string | null;
  created_at: string;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "ingesting" | "analyzing" | "done" | "failed";
  source_type: string;
  source_ref: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  agent_logs: AgentLog[];
  report_id: string | null;
}

export interface BugIssue {
  id: string;
  title: string;
  description: string;
  file: string;
  severity: "critical" | "high" | "medium" | "low";
  category: string;
  code_snippet: string;
  suggested_fix: string;
  test_case_suggestion: string;
}

export interface SecurityVuln {
  id: string;
  title: string;
  description: string;
  file: string;
  severity: "critical" | "high" | "medium" | "low";
  owasp_category: string;
  owasp_name: string;
  code_snippet: string;
  remediation: string;
  cwe_reference: string;
}

export interface Report {
  id: string;
  job_id: string;
  severity_score: number;
  confidence_score: number;
  repo_summary: {
    project_name: string;
    purpose: string;
    architecture_style: string;
    primary_language: string;
    languages: string[];
    frameworks: string[];
    complexity_assessment: string;
    architecture_notes: string;
  };
  bugs: {
    total_issues: number;
    issues: BugIssue[];
    overall_code_quality: string;
    anti_patterns_detected: string[];
    testing_gaps: string;
  };
  security_issues: {
    total_vulnerabilities: number;
    critical_count: number;
    high_count: number;
    medium_count: number;
    low_count: number;
    vulnerabilities: SecurityVuln[];
    secrets_exposed: string[];
    overall_security_posture: string;
  };
  docs_suggestions: {
    readme_score: number;
    overall_documentation_grade: string;
    docstring_coverage_estimate: string;
    quick_wins: string[];
    readme_improvements: { section: string; suggestion: string; priority: string }[];
  };
  final_review: {
    executive_summary: string;
    key_findings: { category: string; finding: string; severity: string }[];
    action_items: { priority: number; action: string; category: string; effort: string; impact: string }[];
    strengths: string[];
    risk_assessment: {
      production_readiness: string;
      top_risk: string;
      security_risk_level: string;
    };
    recommended_next_steps: string[];
    metrics_summary: {
      total_bugs: number;
      total_vulnerabilities: number;
      critical_issues: number;
      documentation_grade: string;
      overall_health_score: number;
    };
  };
  created_at: string;
}

// ── Token helpers ──────────────────────────────────────────────────────────────

export const saveToken = (token: string) =>
  localStorage.setItem("auth_token", token);

export const getToken = () =>
  typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

export const clearToken = () => localStorage.removeItem("auth_token");

// ── Fetch helper ───────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (authenticated) {
    const token = getToken();
    if (!token) throw new Error("Not authenticated");
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── API calls ──────────────────────────────────────────────────────────────────

export async function login(username: string, password: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>(
    "/api/auth/login",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    },
    false
  );
}

export async function submitGithubUrl(githubUrl: string): Promise<{ job_id: string }> {
  return apiFetch("/api/upload/github", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl }),
  });
}

export async function submitZip(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch("/api/upload/zip", { method: "POST", body: form });
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  return apiFetch(`/api/jobs/${jobId}`);
}

export async function getReport(reportId: string): Promise<Report> {
  return apiFetch(`/api/reports/${reportId}`);
}

export function getPdfUrl(reportId: string): string {
  const token = getToken();
  return `${API_URL}/api/reports/${reportId}/pdf?token=${token}`;
}