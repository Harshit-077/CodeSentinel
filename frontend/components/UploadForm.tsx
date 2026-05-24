"use client";

import { useState, useRef } from "react";
import { Github, Upload, Loader2, FolderArchive } from "lucide-react";
import { submitGithubUrl, submitZip } from "@/lib/api";

interface Props {
  onJobCreated: (jobId: string) => void;
}

export function UploadForm({ onJobCreated }: Props) {
  const [tab, setTab] = useState<"github" | "zip">("github");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleSubmit() {
    setError("");
    setLoading(true);
    try {
      let res: { job_id: string };
      if (tab === "github") {
        if (!url.startsWith("https://github.com/"))
          throw new Error("Please enter a valid https://github.com/ URL");
        res = await submitGithubUrl(url);
      } else {
        if (!file) throw new Error("Please select a .zip file");
        res = await submitZip(file);
      }
      onJobCreated(res.job_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h2 className="text-lg font-semibold mb-4">Submit Repository</h2>

      {/* Tab switcher */}
      <div className="flex gap-1 mb-6 p-1 bg-gray-900/60 rounded-xl w-fit border border-gray-700/50 backdrop-blur-sm">
        {(["github", "zip"] as const).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setError(""); }}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold
                        transition-all duration-300
                        ${tab === t
                          ? "bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-lg shadow-brand-500/20"
                          : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"}`}
          >
            {t === "github" ? <Github className="w-4 h-4" /> : <FolderArchive className="w-4 h-4" />}
            {t === "github" ? "GitHub URL" : "ZIP Upload"}
          </button>
        ))}
      </div>

      {/* Input */}
      {tab === "github" ? (
        <div className="space-y-3">
          <input
            className="input"
            placeholder="https://github.com/username/repository"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
          <p className="text-xs text-gray-500 pl-1">Public repositories only</p>
        </div>
      ) : (
        <div
          className="relative border-2 border-dashed border-gray-600 bg-gray-900/30 rounded-2xl p-10 text-center
                     cursor-pointer hover:border-brand-500 hover:bg-brand-500/5 transition-all duration-300 group overflow-hidden"
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const dropped = e.dataTransfer.files[0];
            if (dropped?.name.endsWith(".zip")) setFile(dropped);
          }}
        >
          <div className="absolute inset-0 bg-brand-500/10 blur-[50px] opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
          <Upload className="w-8 h-8 text-gray-600 mx-auto mb-2" />
          {file ? (
            <p className="text-sm text-brand-400 font-medium">{file.name}</p>
          ) : (
            <>
              <p className="text-sm text-gray-400">Drop your ZIP here or click to browse</p>
              <p className="text-xs text-gray-600 mt-1">Only .zip files accepted</p>
            </>
          )}
          <input
            ref={fileRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
      )}

      {error && (
        <div className="mt-3 bg-red-500/10 border border-red-500/30 text-red-400
                        text-sm px-4 py-2.5 rounded-lg">
          {error}
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
      >
        {loading ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Submitting…</>
        ) : (
          "Start Analysis"
        )}
      </button>
    </div>
  );
}
