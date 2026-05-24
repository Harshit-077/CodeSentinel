"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, LogOut, Github } from "lucide-react";
import { getToken, clearToken, getReport, type Report } from "@/lib/api";
import { UploadForm } from "@/components/UploadForm";
import { AgentTimeline } from "@/components/AgentTimeline";
import { ReportViewer } from "@/components/ReportViewer";
import { DownloadButton } from "@/components/DownloadButton";
import RagasPanel from "@/components/RagasPanel";

type Stage = "idle" | "polling" | "done" | "failed";
type RightTab = "report" | "evaluation";

export default function DashboardPage() {
  const router = useRouter();
  const [stage, setStage]       = useState<Stage>("idle");
  const [jobId, setJobId]       = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);
  const [report, setReport]     = useState<Report | null>(null);
  const [rightTab, setRightTab] = useState<RightTab>("report");

  // Auth guard
  useEffect(() => {
    if (!getToken()) router.replace("/");
  }, [router]);

  function handleJobCreated(id: string) {
    setJobId(id);
    setStage("polling");
    setReport(null);
    setReportId(null);
    setRightTab("report");
  }

  async function handleComplete(rid: string) {
    setReportId(rid);
    try {
      const data = await getReport(rid);
      setReport(data);
      setStage("done");
    } catch {
      setStage("failed");
    }
  }

  function handleFailed() {
    setStage("failed");
  }

  function handleReset() {
    setStage("idle");
    setJobId(null);
    setReportId(null);
    setReport(null);
  }

  function handleLogout() {
    clearToken();
    router.push("/");
  }

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Navbar */}
      <nav className="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Shield className="w-5 h-5 text-brand-500" />
            <span className="font-semibold text-gray-100">Code Sentinel</span>
            {/* <span className="badge bg-brand-500/20 text-brand-400 border border-brand-500/30 ml-2">
              Beta
            </span> */}
          </div>
          <div className="flex items-center gap-3">
            {(stage === "done" || stage === "failed") && (
              <button onClick={handleReset} className="btn-secondary">
                New Analysis
              </button>
            )}
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-gray-500 hover:text-gray-300
                         text-sm transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* ── Hero (idle only) ── */}
        {stage === "idle" && (
          <div className="text-center mb-10 animate-fade-in">
            <h1 className="text-4xl font-bold text-white mb-3">
              Code Sentinel
            </h1>
            <h2 className="text-xl font-semibold text-gray-300 mb-3">
              AI-Powered Code Review
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              Submit any GitHub repository or ZIP archive. Five specialised AI agents
              will analyse it for bugs, security vulnerabilities, and documentation gaps —
              then generate a full engineering report.
            </p>
            <div className="flex justify-center gap-6 mt-6 text-sm text-gray-600">
              {["Repository Analysis", "Bug Detection", "OWASP Security", "Documentation", "Final Review"].map((a) => (
                <span key={a} className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-500" />
                  {a}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ── Layout ── */}
        <div className={`grid gap-6 ${
          stage !== "idle" ? "grid-cols-1 lg:grid-cols-[380px_1fr]" : "max-w-xl mx-auto"
        }`}>
          {/* Left column */}
          <div className="space-y-4">
            {stage === "idle" && (
              <UploadForm onJobCreated={handleJobCreated} />
            )}

            {(stage === "polling" || stage === "done" || stage === "failed") && jobId && (
              <>
                {/* Job metadata card */}
                <div className="card text-sm space-y-1">
                  <p className="text-gray-500">Job ID</p>
                  <p className="font-mono text-xs text-gray-400 break-all">{jobId}</p>
                </div>

                <AgentTimeline
                  jobId={jobId}
                  onComplete={handleComplete}
                  onFailed={handleFailed}
                />

                {stage === "done" && reportId && (
                  <DownloadButton reportId={reportId} />
                )}
              </>
            )}

            {stage === "failed" && (
              <div className="card bg-red-500/10 border-red-500/30">
                <p className="text-red-400 text-sm font-medium">Analysis failed</p>
                <p className="text-red-400/70 text-xs mt-1">
                  Check the agent timeline for error details.
                </p>
              </div>
            )}
          </div>

          {/* Right column — tabbed: report / evaluation */}
          {stage === "done" && report && jobId && (
            <div className="animate-fade-in space-y-4">
              {/* Tab bar */}
              <div className="flex gap-1 rounded-lg bg-gray-900 border border-gray-800 p-1 w-fit">
                {(["report", "evaluation"] as RightTab[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setRightTab(tab)}
                    className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${
                      rightTab === tab
                        ? "bg-brand-500 text-white shadow"
                        : "text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    {tab === "evaluation" ? "RAG Evaluation" : "Report"}
                  </button>
                ))}
              </div>

              {rightTab === "report" && <ReportViewer report={report} />}
              {rightTab === "evaluation" && (
                <RagasPanel jobId={jobId} jobStatus="done" />
              )}
            </div>
          )}

          {stage === "polling" && (
            <div className="card flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20
                              flex items-center justify-center mb-4 animate-pulse-slow">
                <Shield className="w-8 h-8 text-brand-500" />
              </div>
              <p className="text-gray-300 font-medium">Agents are working…</p>
              <p className="text-gray-600 text-sm mt-1">
                This takes 1–3 minutes depending on repo size
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}