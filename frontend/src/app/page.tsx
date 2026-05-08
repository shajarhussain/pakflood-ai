"use client";
import dynamic from "next/dynamic";

const WindyCommandCenter = dynamic(
  () => import("@/components/map/WindyCommandCenter"),
  {
    ssr: false,
    loading: () => (
      <div className="h-screen flex items-center justify-center bg-slate-950">
        <p className="text-slate-400 text-sm animate-pulse">Initialising PakFlood AI…</p>
      </div>
    ),
  }
);

export default function Home() {
  return <WindyCommandCenter />;
}
