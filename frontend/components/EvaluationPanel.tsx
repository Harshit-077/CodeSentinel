"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getEvaluation,
  type EvaluationResult,
  type RagasAgentScores,
  type JudgeScores,
  type JudgeCriterion,
} from "@/lib/api";
import {
  FlaskConical, RefreshCw, AlertTriangle, CheckCircle2,
  Info, TrendingUp, Target, Zap, Eye, BarChart3,
} from "lucide-react";

interface Props {
  jobId: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(val: number) {
  return Math.round(val * 100);
}

function scoreColor(score: number, max = 10): string {
  const ratio = score / max;
  if (ratio >= 0.75) return "text-emerald-400";
  if (ratio >= 0.5)  return "text-yellow-400";
  return "text-red-400";
}

function scoreBg(score: number, max = 10): string {
  const ratio = score / max;
  if (ratio >= 0.75) return "bg-emerald-500";
  if (ratio >= 0.5)  return "bg-yellow-500";
  return "bg-red-500";
}

function ragasColor(val: number): string {
  if (val >= 0.75) return "bg-emerald-500";
  if (val >= 0.5)  return "bg-yellow-500";
  return "bg-red-500";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function GaugeBar({
  label,
  value,
  max = 1,
  tooltip,
}: {
  label: string;
  value: number;
  max?: number;
  tooltip?: string;
}) {
  const pctWidth = Math.round((value / max) * 100);
  const displayVal = max === 1 ? `${pct(value)}%` : value.toFixed(1);
  const barColor = max === 1 ? ragasColor(value) : scoreBg(value, max);

  return (
    <div className="space-y-1" title={tooltip}>
      <div className="flex justify-between items-center text-xs">
        <span className="text-gray-400">{label}</span>
        <span className={`font-semibold ${max === 1 ? scoreColor(value, 1) : scoreColor(value, max)}`}>
          {displayVal}
        </span>
      </div>
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${pctWidth}%` }}
        />
      </div>
    </div>
  );
}

function JudgeCard({
  icon: Icon,
  label,
  criterion,
}: {
  icon: React.ElementType;
  label: string;
  criterion: JudgeCriterion;
}) {
  const [showRationale, setShowRationale] = useState(false);
  const score = criterion.score ?? 0;

  return (
    <div className="bg-gray-800/60 rounded-xl p-4 border border-gray-700/50 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-200">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xl font-bold ${scoreColor(score, 10)}`}>
            {score}
          </span>
          <span className="text-xs text-gray-500">/10</span>
        </div>
      </div>

      {/* Score bar */}
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${scoreBg(score, 10)}`}
          style={{ width: `${score * 10}%` }}
        />
      </div>

      {/* Rationale toggle */}
      <button
        onClick={() => setShowRationale((p) => !p)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        <Info className="w-3 h-3" />
        {showRationale ? "Hide" : "Show"} rationale
      </button>

      {showRationale && (
        <p className="text-xs text-gray-400 leading-relaxed bg-gray-900/50 rounded-lg p-2 border border-gray-700/40">
          {criterion.rationale}
        </p>
      )}
    </div>
  );
}

function AgentRagasCard({
  agentName,
  scores,
}: {
  agentName: string;
  scores: RagasAgentScores;
}) {
  const shortName = agentName.replace(" Agent", "");
  const avg = (scores.faithfulness + scores.answer_relevancy + scores.context_utilisation) / 3;

  return (
    <div className="bg-gray-800/60 rounded-xl p-4 border border-gray-700/50 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-200">{shortName}</span>
        <span className={`text-sm font-bold ${scoreColor(avg, 1)}`}>
          avg {pct(avg)}%
        </span>
      </div>
      <GaugeBar
        label="Faithfulness"
        value={scores.faithfulness}
        tooltip="Are answer claims grounded in the retrieved code?"
      />
      <GaugeBar
        label="Answer Relevancy"
        value={scores.answer_relevancy}
        tooltip="Is the output on-topic for the analysis task?"
      />
      <GaugeBar
        label="Context Utilisation"
        value={scores.context_utilisation}
        tooltip="What fraction of retrieved chunks contributed to the answer?"
      />
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="flex items-center gap-3 bg-brand-500/10 border border-brand-500/20 rounded-xl p-4">
        <RefreshCw className="w-5 h-5 text-brand-400 animate-spin" />
        <div>
          <p className="text-sm font-medium text-brand-300">Evaluation in progress…</p>
          <p className="text-xs text-gray-500 mt-0.5">
            RAGAS metrics + LLM judge are running in the background. This takes ~30s.
          </p>
        </div>
      </div>

      {/* RAGAS skeleton */}
      <div>
        <div className="h-4 bg-gray-800 rounded w-32 mb-3" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-gray-800/60 rounded-xl p-4 space-y-3 border border-gray-700/30">
              <div className="h-3 bg-gray-700 rounded w-3/4" />
              {[...Array(3)].map((_, j) => (
                <div key={j} className="space-y-1">
                  <div className="flex justify-between">
                    <div className="h-2.5 bg-gray-700 rounded w-1/3" />
                    <div className="h-2.5 bg-gray-700 rounded w-8" />
                  </div>
                  <div className="h-1.5 bg-gray-700 rounded-full" />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Judge skeleton */}
      <div>
        <div className="h-4 bg-gray-800 rounded w-40 mb-3" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-gray-800/60 rounded-xl p-4 space-y-2 border border-gray-700/30">
              <div className="flex justify-between">
                <div className="h-3 bg-gray-700 rounded w-2/5" />
                <div className="h-4 bg-gray-700 rounded w-8" />
              </div>
              <div className="h-1.5 bg-gray-700 rounded-full" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

const JUDGE_CRITERIA: {
  key: keyof Omit<JudgeScores, "overall_score" | "summary">;
  label: string;
  icon: React.ElementType;
}[] = [
  { key: "accuracy",             label: "Technical Accuracy",     icon: Target },
  { key: "completeness",         label: "Completeness",           icon: BarChart3 },
  { key: "actionability",        label: "Actionability",          icon: Zap },
  { key: "clarity",              label: "Clarity & Structure",    icon: Eye },
  { key: "severity_calibration", label: "Severity Calibration",   icon: TrendingUp },
];

export function EvaluationPanel({ jobId }: Props) {
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [polling, setPolling]       = useState(false);

  const fetchEvaluation = useCallback(async () => {
    try {
      const data = await getEvaluation(jobId);
      if (data && data.status === "done") {
        setEvaluation(data);
        setPolling(false);
        setLoading(false);
      } else if (data && data.status === "failed") {
        setError(data.error_message ?? "Evaluation failed");
        setPolling(false);
        setLoading(false);
      } else {
        // null = 404/202 → still running
        setPolling(true);
        setLoading(true);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load evaluation");
      setPolling(false);
      setLoading(false);
    }
  }, [jobId]);

  // Initial fetch + polling every 5s while pending/running
  useEffect(() => {
    fetchEvaluation();
  }, [fetchEvaluation]);

  useEffect(() => {
    if (!polling) return;
    const timer = setInterval(fetchEvaluation, 5000);
    return () => clearInterval(timer);
  }, [polling, fetchEvaluation]);

  // ── Error state ───────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-5 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-red-300">Evaluation failed</p>
          <p className="text-xs text-red-400/70 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  // ── Loading / polling state ───────────────────────────────────────────────
  if (loading || !evaluation) {
    return <LoadingSkeleton />;
  }

  const { ragas_scores, judge_scores, overall_eval_score } = evaluation;

  // ── Results ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-8 animate-fade-in">

      {/* ── Overall Score Hero ── */}
      <div className="bg-gradient-to-br from-brand-500/10 to-purple-500/10 border border-brand-500/20
                      rounded-2xl p-6 flex flex-col sm:flex-row items-center gap-6">
        <div className="flex flex-col items-center shrink-0">
          <div className={`text-6xl font-bold ${scoreColor(overall_eval_score ?? 0, 10)}`}>
            {(overall_eval_score ?? 0).toFixed(1)}
          </div>
          <div className="text-xs text-gray-500 uppercase tracking-widest mt-1">/ 10</div>
          <div className="text-sm text-gray-400 mt-0.5 font-medium">Overall Quality</div>
        </div>

        <div className="flex-1 space-y-3 w-full">
          <div className="flex items-center gap-2 mb-1">
            <FlaskConical className="w-4 h-4 text-brand-400" />
            <span className="text-sm font-semibold text-gray-200">Evaluation Summary</span>
          </div>
          {judge_scores?.summary && (
            <p className="text-sm text-gray-400 leading-relaxed">{judge_scores.summary}</p>
          )}
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>RAGAS metrics (40%) + LLM-as-a-Judge (60%)</span>
          </div>
        </div>
      </div>

      {/* ── RAGAS Metrics ── */}
      {ragas_scores && Object.keys(ragas_scores).length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1.5 h-4 bg-brand-500 rounded-full" />
            <h3 className="text-sm font-semibold text-gray-200">RAGAS Pipeline Quality</h3>
            <span className="text-xs text-gray-600 ml-1">
              (faithfulness · answer relevancy · context utilisation)
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(ragas_scores).map(([agentName, scores]) => (
              <AgentRagasCard
                key={agentName}
                agentName={agentName}
                scores={scores}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── LLM Judge Scores ── */}
      {judge_scores && (
        <section>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1.5 h-4 bg-purple-500 rounded-full" />
            <h3 className="text-sm font-semibold text-gray-200">LLM-as-a-Judge Assessment</h3>
            <span className="text-xs text-gray-600 ml-1">(scored 0–10 per criterion)</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {JUDGE_CRITERIA.map(({ key, label, icon }) => {
              const criterion = judge_scores[key];
              if (!criterion) return null;
              return (
                <JudgeCard
                  key={key}
                  icon={icon}
                  label={label}
                  criterion={criterion}
                />
              );
            })}
          </div>

          {/* Judge overall gauge */}
          <div className="mt-3 bg-gray-800/60 rounded-xl p-4 border border-gray-700/50">
            <GaugeBar
              label="Judge Overall Score"
              value={judge_scores.overall_score ?? 0}
              max={10}
              tooltip="Weighted average of all five judge criteria"
            />
          </div>
        </section>
      )}

      {/* ── Legend ── */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-600 pt-2 border-t border-gray-800">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
          Good (≥ 75%)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-yellow-500 inline-block" />
          Acceptable (50–74%)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" />
          Needs work (&lt; 50%)
        </span>
      </div>
    </div>
  );
}
