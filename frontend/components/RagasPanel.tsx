/**
 * frontend/components/RagasPanel.tsx
 *
 * Drop this inside the analysis/[jobId]/page.tsx result page.
 * Shows RAGAS metric scores with visual gauge bars and a run button.
 *
 * Usage:
 *   import RagasPanel from "@/components/RagasPanel";
 *   <RagasPanel jobId={jobId} jobStatus={job.status} />
 */

"use client";

import { useCallback, useEffect, useState } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RAGASScores {
  faithfulness: number | null;
  answer_relevancy: number | null;
  context_precision: number | null;
  context_recall: number | null;
  num_samples: number;
  error: string | null;
  updated_at: string | null;
}

type PanelState = "idle" | "loading" | "running" | "done" | "error";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch(path: string, token: string, options?: RequestInit) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

function getToken(): string {
  return typeof window !== "undefined"
    ? localStorage.getItem("access_token") ?? ""
    : "";
}

// ─── Score colour helper ───────────────────────────────────────────────────

function scoreColor(score: number | null): string {
  if (score === null) return "#6b7280"; // gray-500
  if (score >= 0.8) return "#22c55e";  // green-500
  if (score >= 0.6) return "#f59e0b";  // amber-500
  return "#ef4444";                     // red-500
}

function scoreLabel(score: number | null): string {
  if (score === null) return "N/A";
  if (score >= 0.8) return "Good";
  if (score >= 0.6) return "Fair";
  return "Poor";
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface MetricBarProps {
  label: string;
  description: string;
  value: number | null;
}

function MetricBar({ label, description, value }: MetricBarProps) {
  const pct = value !== null ? Math.round(value * 100) : 0;
  const color = scoreColor(value);

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-baseline">
        <div>
          <span className="text-sm font-medium text-gray-200">{label}</span>
          <span className="ml-2 text-xs text-gray-500">{description}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium" style={{ color }}>
            {scoreLabel(value)}
          </span>
          <span className="text-sm font-bold" style={{ color }}>
            {value !== null ? `${pct}%` : "—"}
          </span>
        </div>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-700 overflow-hidden">
        <div
          className="h-2 rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface RagasPanelProps {
  jobId: string;
  jobStatus: string; // "done" required to run evaluation
}

export default function RagasPanel({ jobId, jobStatus }: RagasPanelProps) {
  const [state, setState] = useState<PanelState>("loading");
  const [scores, setScores] = useState<RAGASScores | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  // ── Fetch existing evaluation on mount ──────────────────────────────────
  const fetchScores = useCallback(async () => {
    try {
      const data: RAGASScores = await apiFetch(
        `/api/evaluation/${jobId}`,
        getToken()
      );
      setScores(data);
      setState(data.error ? "error" : "done");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("404")) {
        setState("idle"); // never run yet
      } else {
        setErrorMsg(msg);
        setState("error");
      }
    }
  }, [jobId]);

  useEffect(() => {
    fetchScores();
  }, [fetchScores]);

  // ── Poll after triggering a run ─────────────────────────────────────────
  useEffect(() => {
    if (state !== "running") return;
    const interval = setInterval(async () => {
      try {
        const data: RAGASScores = await apiFetch(
          `/api/evaluation/${jobId}`,
          getToken()
        );
        setScores(data);
        setState(data.error ? "error" : "done");
        clearInterval(interval);
      } catch {
        // still 404 → keep polling
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [state, jobId]);

  // ── Trigger evaluation ───────────────────────────────────────────────────
  async function handleRunEvaluation() {
    setState("running");
    setErrorMsg("");
    try {
      await apiFetch(`/api/evaluation/${jobId}/run`, getToken(), {
        method: "POST",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMsg(msg);
      setState("error");
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────

  const metrics: MetricBarProps[] = scores
    ? [
        {
          label: "Faithfulness",
          description: "Answer grounded in context",
          value: scores.faithfulness,
        },
        {
          label: "Answer Relevancy",
          description: "Answer addresses the question",
          value: scores.answer_relevancy,
        },
        {
          label: "Context Precision",
          description: "Relevant chunks ranked first",
          value: scores.context_precision,
        },
        {
          label: "Context Recall",
          description: "Context covers ground truth",
          value: scores.context_recall,
        },
      ]
    : [];

  const overallScore =
    scores &&
    scores.faithfulness !== null &&
    scores.answer_relevancy !== null &&
    scores.context_precision !== null &&
    scores.context_recall !== null
      ? (scores.faithfulness +
          scores.answer_relevancy +
          scores.context_precision +
          scores.context_recall) /
        4
      : null;

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-900 p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-600/20">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-violet-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path d="M9 19v-6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2z" />
              <path d="M15 3v18a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-2" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">
              RAG Evaluation{" "}
              <span className="text-xs font-normal text-gray-400">
                powered by RAGAS
              </span>
            </h3>
            {scores?.updated_at && (
              <p className="text-xs text-gray-500">
                Last run:{" "}
                {new Date(scores.updated_at).toLocaleString(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
            )}
          </div>
        </div>

        {/* Overall score badge */}
        {overallScore !== null && (
          <div
            className="flex flex-col items-center justify-center rounded-lg px-4 py-2"
            style={{ backgroundColor: scoreColor(overallScore) + "22" }}
          >
            <span
              className="text-2xl font-bold"
              style={{ color: scoreColor(overallScore) }}
            >
              {Math.round(overallScore * 100)}
            </span>
            <span className="text-xs text-gray-400">Overall</span>
          </div>
        )}
      </div>

      {/* Body */}
      {state === "loading" && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-500 border-t-violet-400" />
          Loading evaluation…
        </div>
      )}

      {state === "idle" && (
        <div className="rounded-lg border border-dashed border-gray-700 p-4 text-center space-y-3">
          <p className="text-sm text-gray-400">
            No evaluation results yet. Run RAGAS to measure retrieval and
            answer quality for this analysis.
          </p>
          <button
            onClick={handleRunEvaluation}
            disabled={jobStatus !== "done"}
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white
                       hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Run Evaluation
          </button>
          {jobStatus !== "done" && (
            <p className="text-xs text-amber-500">
              Job must finish before evaluation can run.
            </p>
          )}
        </div>
      )}

      {state === "running" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-violet-300">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-violet-700 border-t-violet-300" />
            Evaluation running… this takes ~30–60 s
          </div>
          {/* Skeleton bars */}
          {["Faithfulness", "Answer Relevancy", "Context Precision", "Context Recall"].map(
            (m) => (
              <div key={m} className="space-y-1">
                <div className="h-3 w-40 animate-pulse rounded bg-gray-700" />
                <div className="h-2 w-full animate-pulse rounded-full bg-gray-700" />
              </div>
            )
          )}
        </div>
      )}

      {(state === "done" || state === "error") && scores && (
        <div className="space-y-4">
          {scores.error && (
            <div className="rounded-lg bg-red-900/30 border border-red-800 p-3 text-xs text-red-300">
              Evaluation error: {scores.error}
            </div>
          )}

          {!scores.error && (
            <>
              <div className="space-y-3">
                {metrics.map((m) => (
                  <MetricBar key={m.label} {...m} />
                ))}
              </div>
              <p className="text-xs text-gray-600">
                Averaged over {scores.num_samples} agent sample
                {scores.num_samples !== 1 ? "s" : ""}.
              </p>
            </>
          )}

          {/* Re-run button */}
          <button
            onClick={handleRunEvaluation}
            className="text-xs text-gray-500 hover:text-violet-400 underline transition-colors"
          >
            Re-run evaluation
          </button>
        </div>
      )}

      {state === "error" && !scores && (
        <div className="rounded-lg bg-red-900/30 border border-red-800 p-3 text-sm text-red-300 space-y-2">
          <p>{errorMsg}</p>
          <button
            onClick={fetchScores}
            className="text-xs text-red-400 underline hover:text-red-300"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}