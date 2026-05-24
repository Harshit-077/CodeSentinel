"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, saveToken } from "@/lib/api";
import { Shield, Zap, Lock } from "lucide-react";

type LoginPageProps = {
  params?: {
    jobId?: string;
  };
};

export default function LoginPage({ params }: LoginPageProps) {
  const router = useRouter();

  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
      const res = await login(username, password);

      saveToken(res.access_token);

      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      {/* Background animated orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-brand-600/20 rounded-full blur-[120px] animate-float opacity-50" />
        <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[100px] animate-float opacity-40" style={{ animationDelay: "2s" }} />
      </div>

      <div className="w-full max-w-md relative z-10 animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-10">
          <div
            className="
              inline-flex items-center justify-center
              w-20 h-20 relative
              bg-gray-900/50 backdrop-blur-md rounded-3xl mb-6
              border border-gray-700/50 shadow-2xl shadow-brand-500/20
            "
          >
            <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-brand-400/20 to-transparent pointer-events-none" />
            <Shield className="w-10 h-10 text-brand-400 drop-shadow-[0_0_15px_rgba(139,92,246,0.5)]" />
          </div>

          <h1 className="text-2xl font-bold text-white">
            CodeSentinel
          </h1>

          <p className="text-gray-400 text-sm mt-1">
            Multi-agent autonomous code intelligence
          </p>

          {params?.jobId && (
            <p className="text-brand-400 text-sm mt-2">
              Job ID: {params.jobId}
            </p>
          )}
        </div>

        {/* Features */}
        <div className="flex justify-center gap-6 mb-8">
          {[
            { icon: Zap, label: "5 AI Agents" },
            { icon: Shield, label: "OWASP Security" },
            { icon: Lock, label: "RAG-Powered" },
          ].map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-1.5 text-xs text-gray-500"
            >
              <Icon className="w-3.5 h-3.5 text-brand-500" />
              <span>{label}</span>
            </div>
          ))}
        </div>

        {/* Login Card */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-6 text-gray-100">
            Sign in
          </h2>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">
                Username
              </label>

              <input
                type="text"
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                autoComplete="username"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1.5">
                Password
              </label>

              <input
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div
                className="
                  bg-red-500/10
                  border border-red-500/30
                  text-red-400
                  text-sm
                  px-4 py-2.5
                  rounded-lg
                "
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              className="btn-primary w-full mt-2"
              disabled={loading}
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="text-xs text-gray-600 text-center mt-4">
            Demo credentials pre-filled above
          </p>
        </div>
      </div>
    </div>
  );
}