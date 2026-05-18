"use client";
import { useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export default function AuthModal({ onClose, onSuccess }: Props) {
  const { login, signup } = useAuth();
  const [tab, setTab]         = useState<"login" | "signup">("login");
  const [email, setEmail]     = useState("");
  const [password, setPassword]     = useState("");
  const [confirm, setConfirm]       = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const [info, setInfo]             = useState<string | null>(null);

  const switchTab = (t: "login" | "signup") => {
    setTab(t); setError(null); setInfo(null);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null); setInfo(null);

    if (tab === "signup" && password !== confirm) {
      setError("Passwords do not match"); return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters"); return;
    }

    setSubmitting(true);
    if (tab === "login") {
      const err = await login(email, password);
      setSubmitting(false);
      if (err) { setError(err); return; }
      onSuccess();
    } else {
      const res = await signup(email, password);
      setSubmitting(false);
      if (res.error) { setError(res.error); return; }
      if (res.needsConfirm) {
        setInfo("Account created — check your email to confirm, then sign in.");
        switchTab("login");
        return;
      }
      onSuccess();
    }
  };

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative w-full max-w-sm bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-white/10">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-slate-100 font-bold text-base">
                {tab === "login" ? "Sign in to PakFlood AI" : "Create an account"}
              </h2>
              <p className="text-slate-500 text-xs mt-0.5">
                {tab === "login"
                  ? "Required to use the AI assistant"
                  : "Free account — get access to AI chat"}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-slate-500 hover:text-slate-300 text-xl leading-none mt-0.5 transition-colors"
            >×</button>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4">
            {(["login", "signup"] as const).map((t) => (
              <button
                key={t}
                onClick={() => switchTab(t)}
                className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  tab === t
                    ? "bg-cyan-500/15 border border-cyan-500/30 text-cyan-300"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {t === "login" ? "Sign In" : "Sign Up"}
              </button>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-3">

          {info && (
            <div className="px-3 py-2.5 rounded-lg bg-green-900/30 border border-green-500/30">
              <p className="text-green-300 text-xs">{info}</p>
            </div>
          )}
          {error && (
            <div className="px-3 py-2.5 rounded-lg bg-red-900/30 border border-red-500/30">
              <p className="text-red-300 text-xs">{error}</p>
            </div>
          )}

          <div>
            <label className="block text-slate-400 text-[11px] uppercase tracking-wider mb-1.5">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full px-3 py-2.5 rounded-xl bg-slate-800/60 border border-white/10 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 focus:bg-slate-800 transition-colors"
            />
          </div>

          <div>
            <label className="block text-slate-400 text-[11px] uppercase tracking-wider mb-1.5">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2.5 rounded-xl bg-slate-800/60 border border-white/10 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 focus:bg-slate-800 transition-colors"
            />
          </div>

          {tab === "signup" && (
            <div>
              <label className="block text-slate-400 text-[11px] uppercase tracking-wider mb-1.5">Confirm Password</label>
              <input
                type="password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2.5 rounded-xl bg-slate-800/60 border border-white/10 text-slate-200 text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 focus:bg-slate-800 transition-colors"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 text-sm font-semibold hover:bg-cyan-500/25 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-1"
          >
            {submitting ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                {tab === "login" ? "Signing in…" : "Creating account…"}
              </>
            ) : tab === "login" ? "Sign In" : "Create Account"}
          </button>

          <p className="text-center text-slate-600 text-[10px] pt-1">
            {tab === "login" ? "No account? " : "Already have one? "}
            <button
              type="button"
              onClick={() => switchTab(tab === "login" ? "signup" : "login")}
              className="text-cyan-500/70 hover:text-cyan-400 transition-colors"
            >
              {tab === "login" ? "Sign up free" : "Sign in"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
