"use client";
import { useParams } from "next/navigation";
import RagasPanel from "../../../components/RagasPanel";

export default function AnalysisPage() {
  const params = useParams();
  const jobId = typeof params.jobId === "string" ? params.jobId : "";
  return (
    <div className="min-h-screen bg-gray-950 p-8 max-w-3xl mx-auto">
      <RagasPanel jobId={jobId} jobStatus="done" />
    </div>
  );
}