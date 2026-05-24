"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, LogOut, Github } from "lucide-react";
import { getToken, clearToken, getReport, type Report } from "@/lib/api";
import { UploadForm } from "@/components/UploadForm";
import { AgentTimeline } from "@/components/AgentTimeline";
import { ReportViewer } from "@/components/ReportViewer";
import { DownloadButton } from "@/components/DownloadButton";

type Stage = "idle" | "polling" | "done" | "failed";

export default function DashboardPage() {
  const router = useRouter();
  const [stage, setStage]       = useState<Stage>("idle");
  const [jobId, setJobId]       = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);
  const [report, setReport]     = useState<Report | null>(null);

  // Auth guard
  useEffect(() => {
    if (!getToken()) router.replace("/");
  }, [router]);

  function handleJobCreated(id: string) {
    setJobId(id);
    setStage("polling");
    setReport(null);
    setReportId(null);
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
    <div className="min-h-screen bg-gray-950 relative overflow-hidden">
      {/* Background orbs for glassmorphism */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0 fixed">
        <div className="absolute top-0 right-1/4 w-[600px] h-[600px] bg-brand-600/10 rounded-full blur-[120px] animate-float" />
        <div className="absolute bottom-0 -left-1/4 w-[800px] h-[800px] bg-purple-600/10 rounded-full blur-[150px] animate-float" style={{ animationDelay: "3s" }} />
      </div>

      {/* Navbar */}
      <nav className="border-b border-gray-700/50 bg-gray-950/50 backdrop-blur-xl sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between relative">
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

      <main className="max-w-6xl mx-auto px-4 py-10 relative z-10">
        {/* ── Hero (idle only) ── */}
        {stage === "idle" && (
          <div className="text-center mb-12 animate-fade-in">
            <h1 className="text-5xl font-extrabold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-purple-400 drop-shadow-sm">
              Code Sentinel
            </h1>
            <h2 className="text-xl font-semibold text-gray-200 mb-4">
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

          {/* Right column — report */}
          {stage === "done" && report && (
            <div className="animate-fade-in">
              <ReportViewer report={report} />
            </div>
          )}

          {stage === "polling" && (
            <div className="card flex flex-col items-center justify-center py-24 text-center">
              <div className="w-20 h-20 rounded-3xl bg-brand-500/10 border border-brand-500/30
                              flex items-center justify-center mb-6 animate-pulse-glow">
                <Shield className="w-10 h-10 text-brand-400" />
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