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
      <div className="flex gap-2 mb-5 bg-gray-800 p-1 rounded-lg w-fit">
        {(["github", "zip"] as const).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setError(""); }}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium
                        transition-colors duration-150
                        ${tab === t
                          ? "bg-brand-500 text-white"
                          : "text-gray-400 hover:text-gray-200"}`}
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
          <p className="text-xs text-gray-500">Public repositories only</p>
        </div>
      ) : (
        <div
          className="border-2 border-dashed border-gray-700 rounded-xl p-8 text-center
                     cursor-pointer hover:border-brand-500/50 transition-colors"
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const dropped = e.dataTransfer.files[0];
            if (dropped?.name.endsWith(".zip")) setFile(dropped);
          }}
        >
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
