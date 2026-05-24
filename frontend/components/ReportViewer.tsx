"use client";

import { useState } from "react";
import { type Report } from "@/lib/api";
import { SeverityBadge } from "./SeverityBadge";
import { EvaluationPanel } from "./EvaluationPanel";
import {
  Bug, Shield, BookOpen, Star,
<<<<<<< HEAD
  AlertTriangle, CheckCircle2, TrendingUp, FileText, FlaskConical,
=======
  AlertTriangle, CheckCircle2, TrendingUp,
>>>>>>> 8323db3e7cc4c2ac2de0a792685aae25f1be5dfe
} from "lucide-react";

interface Props { report: Report }

const TABS = [
  { key: "overview",  label: "Overview",     icon: Star },
  { key: "bugs",      label: "Bugs",         icon: Bug },
  { key: "security",  label: "Security",     icon: Shield },
  { key: "docs",      label: "Docs",         icon: BookOpen },
  { key: "actions",   label: "Action Items", icon: TrendingUp },
  { key: "evaluation", label: "Evaluation",  icon: FlaskConical },
] as const;

type Tab = typeof TABS[number]["key"];

function ScoreRing({ score, label, color }: { score: number; label: string; color: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`text-3xl font-bold ${color}`}>{score}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
    </div>
  );
}

export function ReportViewer({ report }: Props) {
  const [tab, setTab] = useState<Tab>("overview");
  const fr      = report.final_review ?? {};
  const metrics = fr.metrics_summary  ?? {};
  const rid     = report.id;

  return (
    <div className="card animate-fade-in">

      {/* ── Score header ── */}
      <div className="flex items-center justify-between mb-6 pb-5 border-b border-gray-800">
        <div>
          <h2 className="text-xl font-bold">
            {report.repo_summary?.project_name ?? "Analysis Report"}
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">
            {report.repo_summary?.primary_language} ·{" "}
            {report.repo_summary?.architecture_style}
          </p>
        </div>
        <div className="flex gap-8">
          <ScoreRing
            score={report.severity_score ?? 0}
            label="Severity"
            color={
              (report.severity_score ?? 0) > 70 ? "text-red-400" :
              (report.severity_score ?? 0) > 40 ? "text-yellow-400" : "text-green-400"
            }
          />
          <ScoreRing score={report.confidence_score ?? 0} label="Confidence" color="text-brand-400" />
          <ScoreRing score={metrics.overall_health_score ?? 0} label="Health" color="text-emerald-400" />
        </div>
      </div>

<<<<<<< HEAD
      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 bg-gray-900/60 rounded-xl overflow-x-auto border border-gray-700/50 backdrop-blur-sm w-fit shadow-inner shadow-black/20">
=======
      {/* ── Tabs ── */}
      <div className="flex gap-1 mb-5 overflow-x-auto">
>>>>>>> 8323db3e7cc4c2ac2de0a792685aae25f1be5dfe
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm
                        font-semibold whitespace-nowrap transition-all duration-300
                        ${tab === key
                          ? "bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-lg shadow-brand-500/20"
                          : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"}`}
          >
            <Icon className="w-4 h-4" />
            {label}
            {key === "bugs" && (
              <span className={`ml-1 text-[11px] px-1.5 rounded-full ${tab === key ? "bg-white/20 text-white" : "bg-orange-500/20 text-orange-400"}`}>
                {report.bugs?.total_issues ?? 0}
              </span>
            )}
            {key === "security" && (
              <span className={`ml-1 text-[11px] px-1.5 rounded-full ${tab === key ? "bg-white/20 text-white" : "bg-red-500/20 text-red-400"}`}>
                {report.security_issues?.total_vulnerabilities ?? 0}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════
          OVERVIEW TAB
      ══════════════════════════════════════════════ */}
      {tab === "overview" && (
        <div className="space-y-5 animate-fade-in">

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-800/50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Risk Assessment</h3>
              {fr.risk_assessment && Object.entries(fr.risk_assessment).map(([k, v]) => (
                <div key={k} className="flex justify-between text-sm py-1 border-b border-gray-700/50 last:border-0">
                  <span className="text-gray-500 capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="text-gray-300 font-medium">{String(v)}</span>
                </div>
              ))}
            </div>
            <div className="bg-gray-800/50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Strengths</h3>
              <ul className="space-y-1.5">
                {(fr.strengths ?? []).map((s: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-400 mt-0.5 shrink-0" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="bg-gray-800/50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">Key Findings</h3>
            <div className="space-y-2">
              {(fr.key_findings ?? []).map((f: { category: string; finding: string; severity: string }, i: number) => (
                <div key={i} className="flex items-start gap-3 text-sm">
                  <SeverityBadge severity={f.severity} />
                  <span className="text-gray-400">{f.finding}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════
          BUGS TAB
      ══════════════════════════════════════════════ */}
      {tab === "bugs" && (
        <div className="space-y-3 animate-fade-in">
          <div className="flex gap-4 text-sm text-gray-500 mb-2">
            <span>Quality: <strong className="text-gray-300">{report.bugs?.overall_code_quality}</strong></span>
            <span>Anti-patterns: <strong className="text-gray-300">{report.bugs?.anti_patterns_detected?.length ?? 0}</strong></span>
          </div>

          {(report.bugs?.issues ?? []).map((bug) => (
            <div key={bug.id} className="bg-gray-800/50 rounded-xl p-4 space-y-2">
              {/* Header row */}
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-gray-200">{bug.title}</span>
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={bug.severity} />
                </div>
              </div>

              <p className="text-xs text-gray-500 font-mono">{bug.file}</p>
              <p className="text-sm text-gray-400">{bug.description}</p>

              {bug.code_snippet && (
                <pre className="text-xs bg-gray-900 rounded-lg p-3 overflow-x-auto
                                text-gray-300 border border-gray-700">
                  {bug.code_snippet}
                </pre>
              )}

              <div className="text-xs text-green-400 bg-green-500/10 rounded-lg p-2.5
                              border border-green-500/20">
                💡 {bug.suggested_fix}
              </div>
            </div>
          ))}
          {!report.bugs?.issues?.length && (
            <p className="text-gray-500 text-sm text-center py-8">No bugs detected</p>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════
          SECURITY TAB
      ══════════════════════════════════════════════ */}
      {tab === "security" && (
        <div className="space-y-3 animate-fade-in">
          <div className="flex gap-4 text-sm mb-2">
            {[
              { label: "Critical", count: report.security_issues?.critical_count, color: "text-red-400" },
              { label: "High",     count: report.security_issues?.high_count,     color: "text-orange-400" },
              { label: "Medium",   count: report.security_issues?.medium_count,   color: "text-yellow-400" },
              { label: "Low",      count: report.security_issues?.low_count,      color: "text-blue-400" },
            ].map(({ label, count, color }) => (
              <span key={label} className="text-gray-500">
                {label}: <strong className={color}>{count ?? 0}</strong>
              </span>
            ))}
          </div>

          {(report.security_issues?.vulnerabilities ?? []).map((v) => (
            <div key={v.id} className="bg-gray-800/50 rounded-xl p-4 space-y-2">
              {/* Header row */}
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-gray-200">{v.title}</span>
                <div className="flex items-center gap-2">
                  <span className="badge bg-purple-500/20 text-purple-400 border border-purple-500/20">
                    {v.owasp_category}
                  </span>
                  <SeverityBadge severity={v.severity} />
                </div>
              </div>
              <p className="text-xs text-gray-500 font-mono">{v.file}</p>
              <p className="text-xs text-gray-500">{v.owasp_name} · {v.cwe_reference}</p>
              <p className="text-sm text-gray-400">{v.description}</p>
              {v.code_snippet && (
                <pre className="text-xs bg-gray-900 rounded-lg p-3 overflow-x-auto
                                text-gray-300 border border-gray-700">
                  {v.code_snippet}
                </pre>
              )}

              <div className="text-xs text-green-400 bg-green-500/10 rounded-lg p-2.5
                              border border-green-500/20">
                🔒 {v.remediation}
              </div>
            </div>
          ))}
          {!report.security_issues?.vulnerabilities?.length && (
            <p className="text-gray-500 text-sm text-center py-8">No vulnerabilities detected</p>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════
          DOCS TAB
      ══════════════════════════════════════════════ */}
      {tab === "docs" && (
        <div className="space-y-4 animate-fade-in">
          <div className="flex gap-6 items-center">
            <div className="text-center">
              <div className="text-3xl font-bold text-brand-400">
                {report.docs_suggestions?.overall_documentation_grade}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">Grade</div>
            </div>
            <div className="flex-1">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>README Score</span>
                <span>{report.docs_suggestions?.readme_score}/100</span>
              </div>
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 rounded-full transition-all"
                  style={{ width: `${report.docs_suggestions?.readme_score ?? 0}%` }}
                />
              </div>
            </div>
          </div>

          <div className="bg-gray-800/50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">Quick Wins</h3>
            <ul className="space-y-1.5">
              {(report.docs_suggestions?.quick_wins ?? []).map((w: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                  <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 mt-0.5 shrink-0" />
                  {w}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-gray-800/50 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">README Improvements</h3>
            <div className="space-y-2">
              {(report.docs_suggestions?.readme_improvements ?? []).map(
                (imp: { section: string; suggestion: string; priority: string }, i: number) => (
                  <div key={i} className="text-sm flex items-start gap-2">
                    <SeverityBadge severity={imp.priority} />
                    <span className="text-gray-400">{imp.section}: {imp.suggestion}</span>
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════
          ACTION ITEMS TAB
      ══════════════════════════════════════════════ */}
      {tab === "actions" && (
        <div className="space-y-3 animate-fade-in">
          <p className="text-sm text-gray-500 mb-3">Sorted by priority — tackle these first</p>
          {(fr.action_items ?? [])
            .sort((a: { priority: number }, b: { priority: number }) => a.priority - b.priority)
            .map((item: { priority: number; action: string; category: string; effort: string; impact: string }, i: number) => (
              <div key={i} className="bg-gray-800/50 rounded-xl p-4 flex items-start gap-4">
                <div className="text-2xl font-bold text-gray-700 w-6 shrink-0">
                  {item.priority}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-200">{item.action}</p>
                  <div className="flex gap-3 mt-1.5 text-xs text-gray-500">
                    <span className="badge bg-gray-700 text-gray-400">{item.category}</span>
                    <span>Effort: <strong className="text-gray-400">{item.effort}</strong></span>
                    <span>Impact: <strong className="text-gray-400">{item.impact}</strong></span>
                  </div>
                </div>
              </div>
            ))}
        </div>
      )}

      {/* ── Evaluation Tab ── */}
      {tab === "evaluation" && (
        <EvaluationPanel jobId={report.job_id} />
      )}
    </div>
  );
}