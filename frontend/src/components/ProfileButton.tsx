"use client";
import { useState, useRef, useEffect } from "react";

interface Props {
  email: string | null;
  onSignIn: () => void;
  onSignOut: () => void;
}

export default function ProfileButton({ email, onSignIn, onSignOut }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Derive a consistent hue from the email string
  const hue = email
    ? email.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360
    : 220; // default blue-ish for guests

  const initial = email ? email[0].toUpperCase() : null;

  return (
    <div ref={ref} className="relative shrink-0">
      {/* Avatar button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all hover:scale-105 active:scale-95 focus:outline-none"
        style={{
          background:  email ? `hsl(${hue}, 60%, 18%)` : "rgba(148,163,184,0.1)",
          borderColor: email ? `hsl(${hue}, 70%, 45%)` : "rgba(148,163,184,0.3)",
          color:       email ? `hsl(${hue}, 80%, 75%)` : "#94a3b8",
          boxShadow:   open  ? `0 0 0 3px hsl(${hue}, 60%, 25%)` : "none",
        }}
        title={email ?? "Sign in"}
      >
        {initial ?? (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
          </svg>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-[calc(100%+8px)] z-[2000] w-56 rounded-xl bg-slate-900 border border-white/10 shadow-2xl overflow-hidden animate-fade-up">

          {email ? (
            /* ── Signed-in state ───────────────────────────────────────── */
            <>
              <div className="px-4 py-3 border-b border-white/5 flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-base font-bold shrink-0"
                  style={{
                    background: `hsl(${hue}, 60%, 18%)`,
                    border:     `2px solid hsl(${hue}, 70%, 45%)`,
                    color:      `hsl(${hue}, 80%, 75%)`,
                  }}
                >
                  {initial}
                </div>
                <div className="min-w-0">
                  <p className="text-slate-200 text-xs font-semibold truncate">{email}</p>
                  <p className="text-slate-500 text-[10px] mt-0.5">Signed in</p>
                </div>
              </div>

              <div className="p-1.5">
                <button
                  onClick={() => { setOpen(false); onSignOut(); }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors text-left"
                >
                  <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
                  </svg>
                  Sign Out
                </button>
              </div>
            </>
          ) : (
            /* ── Signed-out state ──────────────────────────────────────── */
            <>
              <div className="px-4 py-3 border-b border-white/5">
                <p className="text-slate-300 text-xs font-semibold">Welcome</p>
                <p className="text-slate-500 text-[10px] mt-0.5">Sign in to access AI features</p>
              </div>

              <div className="p-1.5">
                <button
                  onClick={() => { setOpen(false); onSignIn(); }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-cyan-400 hover:bg-cyan-500/10 transition-colors text-left font-semibold"
                >
                  <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3"/>
                  </svg>
                  Sign In
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
