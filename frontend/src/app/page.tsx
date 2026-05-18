"use client";
import dynamic from "next/dynamic";
import { AuthProvider } from "@/lib/auth-context";

const FloodApp = dynamic(() => import("@/components/FloodApp"), {
  ssr: false,
  loading: () => (
    <div className="h-screen flex items-center justify-center bg-slate-950">
      <p className="text-slate-400 text-sm animate-pulse">Loading PakFlood AI…</p>
    </div>
  ),
});

export default function Home() {
  return (
    <AuthProvider>
      <FloodApp />
    </AuthProvider>
  );
}
