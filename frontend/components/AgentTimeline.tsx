"use client";

import { useEffect, useState, useRef } from "react";
import { CheckCircle2, XCircle, Loader2, Clock } from "lucide-react";
import { getJobStatus, type JobStatus, type AgentLog } from "@/lib/api";

interface Props {
  jobId: string;
  onComplete: (reportId: string) => void;
  onFailed: () => void;
}

const AGENT_ORDER = [
  "Ingestion",
  "File Parser",
  "Chunker",
  "Embedder",
  "Repository Analysis Agent",
  "Bug Detection Agent",
  "Security Review Agent",
  "Documentation Agent",
  "Final Reviewer Agent",
];

function StatusIcon({ status }: { status: string }) {
  if (status === "done")    return <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />;
  if (status === "failed")  return <XCircle className="w-4 h-4 text-red-400 shrink-0" />;
  if (status === "started") return <Loader2 className="w-4 h-4 text-brand-400 animate-spin shrink-0" />;
  return <Clock className="w-4 h-4 text-gray-600 shrink-0" />;
}

function statusColor(status: string) {
  if (status === "done")    return "text-green-400";
  if (status === "failed")  return "text-red-400";
  if (status === "started") return "text-brand-400";
  return "text-gray-600";
}

export function AgentTimeline({ jobId, onComplete, onFailed }: Props) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState("");

  // Stable refs so the interval never restarts when parent re-renders
  const onCompleteRef = useRef(onComplete);
  const onFailedRef   = useRef(onFailed);
  useEffect(() => { onCompleteRef.current = onComplete; }, [onComplete]);
  useEffect(() => { onFailedRef.current   = onFailed;   }, [onFailed]);

  const isTerminal = useRef(false);

  useEffect(() => {
    // Reset terminal flag when jobId changes
    isTerminal.current = false;

    async function poll() {
      if (isTerminal.current) return;
      try {
        const data = await getJobStatus(jobId);
        setJob(data);

        if (data.status === "done" && data.report_id) {
          isTerminal.current = true;
          onCompleteRef.current(data.report_id);
        } else if (data.status === "failed") {
          isTerminal.current = true;
          onFailedRef.current();
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to fetch status");
      }
    }

    poll();
    const interval = setInterval(() => {
      if (isTerminal.current) {
        clearInterval(interval);
        return;
      }
      poll();
    }, 3000);
    return () => clearInterval(interval);
  }, [jobId]); // ← only jobId; callbacks accessed via stable refs

  if (error) return (
    <div className="card text-red-400 text-sm">{error}</div>
  );

  if (!job) return (
    <div className="card flex items-center gap-3 text-gray-400">
      <Loader2 className="w-5 h-5 animate-spin text-brand-500" />
      <span>Connecting to pipeline…</span>
    </div>
  );

  // Build a map of latest log per agent
  const logMap = new Map<string, AgentLog>();
  for (const log of job.agent_logs) {
    logMap.set(log.agent_name, log);
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold">Agent Pipeline</h2>
        <span className={`badge ${
          job.status === "done"      ? "bg-green-500/20 text-green-400 border border-green-500/30" :
          job.status === "failed"    ? "bg-red-500/20 text-red-400 border border-red-500/30" :
          job.status === "analyzing" ? "bg-brand-500/20 text-brand-400 border border-brand-500/30" :
                                       "bg-gray-500/20 text-gray-400 border border-gray-500/30"
        }`}>
          {job.status}
        </span>
      </div>

      {/* Timeline */}
      <div className="space-y-1">
        {AGENT_ORDER.map((agentName, idx) => {
          const log = logMap.get(agentName);
          const status = log?.status ?? "pending";
          const isLast = idx === AGENT_ORDER.length - 1;

          return (
            <div key={agentName} className="relative">
              {/* Connector line */}
              {!isLast && (
                <div className="absolute left-[7px] top-6 w-px h-full bg-gray-800" />
              )}

              <div className="flex items-start gap-3 py-2 pl-1">
                <StatusIcon status={status} />
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${
                    status === "pending" ? "text-gray-600" : "text-gray-200"
                  }`}>
                    {agentName}
                  </p>
                  {log?.message && (
                    <p className={`text-xs mt-0.5 truncate ${statusColor(status)}`}>
                      {log.message}
                    </p>
                  )}
                </div>
                {log?.created_at && (
                  <span className="text-xs text-gray-600 shrink-0">
                    {new Date(log.created_at).toLocaleTimeString()}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Error message */}
      {job.error_message && (
        <div className="mt-4 bg-red-500/10 border border-red-500/30 text-red-400
                        text-xs px-3 py-2 rounded-lg">
          {job.error_message}
        </div>
      )}
    </div>
  );
}
