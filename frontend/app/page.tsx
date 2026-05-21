"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, saveToken } from "@/lib/api";
import { Shield, Zap, Lock } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
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
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px]
                        bg-brand-500/10 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16
                          bg-brand-500/20 rounded-2xl mb-4 border border-brand-500/30">
            <Shield className="w-8 h-8 text-brand-500" />
          </div>
          <h1 className="text-2xl font-bold text-white">CodeSentinel</h1>
          <p className="text-gray-400 text-sm mt-1">
            Multi-agent autonomous code intelligence
          </p>
        </div>

        {/* Features row */}
        <div className="flex justify-center gap-6 mb-8">
          {[
            { icon: Zap, label: "5 AI Agents" },
            { icon: Shield, label: "OWASP Security" },
            { icon: Lock, label: "RAG-Powered" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-1.5 text-xs text-gray-500">
              <Icon className="w-3.5 h-3.5 text-brand-500" />
              {label}
            </div>
          ))}
        </div>

        {/* Login card */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-6 text-gray-100">Sign in</h2>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Username</label>
              <input
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                autoComplete="username"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Password</label>
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
              <div className="bg-red-500/10 border border-red-500/30 text-red-400
                              text-sm px-4 py-2.5 rounded-lg">
                {error}
              </div>
            )}

            <button type="submit" className="btn-primary w-full mt-2" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
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