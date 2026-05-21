"use client";

import { Download, Loader2 } from "lucide-react";
import { useState } from "react";
import { getToken } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function DownloadButton({ reportId }: { reportId: string }) {
  const [loading, setLoading] = useState(false);

  async function handleDownload() {
    setLoading(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/api/reports/${reportId}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("PDF not ready");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${reportId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("PDF not yet generated. Try again in a moment.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleDownload}
      disabled={loading}
      className="btn-secondary flex items-center gap-2"
    >
      {loading
        ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating…</>
        : <><Download className="w-4 h-4" /> Download PDF</>
      }
    </button>
  );
}
