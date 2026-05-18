"use client";
import { useState, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import type { PredictionResponse, ZonesGeoJSON, FloodEvent } from "@/lib/types";
import { predictFloodRisk, fetchModelStatus, fetchZonesGeoJSON, fetchFloodEvents, type ModelStatus } from "@/lib/api";
import PredictionCard from "@/components/PredictionCard";
import SearchBar from "@/components/SearchBar";
import FloodEventsPanel from "@/components/FloodEventsPanel";

const FloodMap = dynamic(() => import("@/components/FloodMap"), { ssr: false });

interface SelectedLocation { lat: number; lng: number }

function formatAge(isoString: string | null): string {
  if (!isoString) return "unknown";
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1)  return "just now";
  if (mins < 60) return `${mins}m ago`;
  return `${Math.round(mins / 60)}h ago`;
}

export default function FloodApp() {
  const [selectedLocation, setSelectedLocation] = useState<SelectedLocation | null>(null);
  const [prediction,       setPrediction      ] = useState<PredictionResponse | null>(null);
  const [loading,          setLoading         ] = useState(false);
  const [error,            setError           ] = useState<string | null>(null);
  const [modelStatus,      setModelStatus     ] = useState<ModelStatus | null>(null);

  const [zones,        setZones       ] = useState<ZonesGeoJSON | null>(null);
  const [showZones,    setShowZones   ] = useState(false);
  const [zonesLoading, setZonesLoading] = useState(false);

  const [events,        setEvents       ] = useState<FloodEvent[]>([]);
  const [showEvents,    setShowEvents   ] = useState(false);
  const [eventsLoading, setEventsLoading] = useState(false);

  useEffect(() => { fetchModelStatus().then(setModelStatus); }, []);

  const handleToggleZones = useCallback(async () => {
    if (!showZones && !zones) {
      setZonesLoading(true);
      const data = await fetchZonesGeoJSON();
      setZones(data);
      setZonesLoading(false);
    }
    setShowZones((prev) => !prev);
  }, [showZones, zones]);

  const handleToggleEvents = useCallback(async () => {
    if (!showEvents && events.length === 0) {
      setEventsLoading(true);
      const data = await fetchFloodEvents();
      setEvents(data);
      setEventsLoading(false);
    }
    setShowEvents((prev) => !prev);
  }, [showEvents, events]);

  const runPrediction = useCallback(async (lat: number, lng: number) => {
    setSelectedLocation({ lat, lng });
    setPrediction(null);
    setError(null);
    setLoading(true);
    try {
      const result = await predictFloodRisk(lat, lng);
      setPrediction(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get prediction");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleGeolocate = useCallback(() => {
    if (!navigator.geolocation) { setError("Geolocation not supported"); return; }
    setLoading(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => runPrediction(pos.coords.latitude, pos.coords.longitude),
      () => { setLoading(false); setError("Location access denied — click on the map instead"); }
    );
  }, [runPrediction]);

  const handleDismiss = useCallback(() => {
    setPrediction(null); setError(null); setSelectedLocation(null);
  }, []);

  const modelUnavailable = modelStatus !== null && !modelStatus.artifact_ready;
  const zonesAge   = zones?.metadata?.computed_at ? formatAge(zones.metadata.computed_at) : null;
  const zonesCount = zones?.metadata?.total_points ?? 0;

  return (
    <div className="relative w-screen h-screen bg-slate-950 overflow-hidden">
      {/* Full-screen map */}
      <FloodMap
        selectedLocation={selectedLocation}
        onLocationSelect={runPrediction}
        zones={zones}
        showZones={showZones}
      />

      {/* Search bar — floats below top bar, left side */}
      <SearchBar onSelect={(lat, lng) => runPrediction(lat, lng)} />

      {/* ── Top bar ─────────────────────────────────────────────────────────── */}
      <div className="absolute top-0 left-0 right-0 z-[1000] flex items-center justify-between px-4 py-3 bg-slate-950/80 backdrop-blur-sm border-b border-white/10">
        {/* Brand + model badge */}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-cyan-400 font-bold text-sm tracking-wider shrink-0">PAKFLOOD AI</span>
          <span className="text-slate-600 text-xs shrink-0 hidden sm:inline">|</span>
          <span className="text-slate-400 text-xs shrink-0 hidden sm:inline">Flood Risk Intelligence</span>
          {modelStatus && (
            <span className={`ml-1 px-2 py-0.5 rounded text-[10px] font-medium border shrink-0 ${
              modelStatus.artifact_ready
                ? "bg-green-500/10 border-green-500/30 text-green-400"
                : "bg-amber-500/10 border-amber-500/30 text-amber-400"
            }`}>
              {modelStatus.artifact_ready ? "Model: Live" : "Model: Fallback"}
            </span>
          )}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2 shrink-0">
          {/* History toggle */}
          <button
            onClick={handleToggleEvents}
            disabled={eventsLoading}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              showEvents
                ? "bg-rose-500/20 border-rose-500/40 text-rose-300"
                : "bg-slate-800/60 border-white/10 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60"
            }`}
            title="Historical flood events (2010–2022)"
          >
            {eventsLoading ? (
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
              </svg>
            )}
            {eventsLoading ? "Loading…" : showEvents ? "Hide History" : "History"}
          </button>

          {/* Heatmap toggle */}
          <button
            onClick={handleToggleZones}
            disabled={zonesLoading}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              showZones
                ? "bg-amber-500/20 border-amber-500/40 text-amber-300"
                : "bg-slate-800/60 border-white/10 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60"
            }`}
            title={zonesAge ? `${zonesCount} points · ${zonesAge}` : "Nationwide risk heatmap"}
          >
            {zonesLoading ? (
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="3"/>
                <path d="M3 12h3m12 0h3M12 3v3m0 12v3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1M5.6 18.4l2.1-2.1m8.6-8.6 2.1-2.1"/>
              </svg>
            )}
            {zonesLoading ? "Loading…" : showZones ? "Hide Heatmap" : "Heatmap"}
            {showZones && zonesAge && (
              <span className="text-amber-500/70 text-[10px]">{zonesAge}</span>
            )}
          </button>

          {/* My Location */}
          <button
            onClick={handleGeolocate}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-medium hover:bg-cyan-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
            </svg>
            My Location
          </button>
        </div>
      </div>

      {/* Model unavailable warning */}
      {modelUnavailable && (
        <div className="absolute top-14 left-1/2 -translate-x-1/2 z-[1000] max-w-md w-full px-4">
          <div className="px-4 py-2.5 rounded-xl bg-amber-900/40 border border-amber-500/30 backdrop-blur-sm text-center">
            <p className="text-amber-300 text-xs">
              <strong>Model not loaded</strong> — predictions return placeholder 50%.
              Check backend logs for the load error.
            </p>
          </div>
        </div>
      )}

      {/* Heatmap legend */}
      {showZones && !zonesLoading && !showEvents && (
        <div className="absolute bottom-8 left-4 z-[1000]">
          <div className="px-3 py-2.5 rounded-xl bg-slate-900/90 border border-white/10 backdrop-blur-sm">
            <p className="text-slate-500 text-[10px] uppercase tracking-wider mb-2">
              Risk Heatmap
              {zonesCount > 0 && <span className="ml-1 text-slate-600">· {zonesCount} pts</span>}
            </p>
            {(["Severe", "High", "Moderate", "Low"] as const).map((level) => (
              <div key={level} className="flex items-center gap-2 mb-1 last:mb-0">
                <div className="w-3 h-3 rounded-full shrink-0"
                  style={{ backgroundColor: { Severe: "#ef4444", High: "#f97316", Moderate: "#eab308", Low: "#22c55e" }[level] }}
                />
                <span className="text-slate-400 text-[11px]">{level}</span>
              </div>
            ))}
            {zones?.metadata?.is_fresh === false && (
              <p className="text-amber-500/70 text-[10px] mt-2 border-t border-white/5 pt-2">Stale — refresh queued</p>
            )}
          </div>
        </div>
      )}

      {/* Hint */}
      {!selectedLocation && !loading && !showEvents && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[1000]">
          <div className="px-4 py-2 rounded-full bg-slate-900/90 border border-white/10 text-slate-400 text-xs backdrop-blur-sm">
            Click anywhere in Pakistan · or use My Location
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[1000]">
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900/90 border border-white/10 backdrop-blur-sm">
            <svg className="w-4 h-4 text-cyan-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <span className="text-slate-400 text-xs">Analysing flood risk…</span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[1000] max-w-sm w-full px-4">
          <div className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-red-900/40 border border-red-500/30 backdrop-blur-sm">
            <p className="text-red-300 text-xs">{error}</p>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 text-lg leading-none shrink-0">×</button>
          </div>
        </div>
      )}

      {/* Prediction card */}
      {prediction && selectedLocation && !loading && !showEvents && (
        <div className="absolute bottom-8 right-4 z-[1000]">
          <PredictionCard prediction={prediction} location={selectedLocation} onDismiss={handleDismiss} />
        </div>
      )}

      {/* Historical flood events panel */}
      {showEvents && (
        <FloodEventsPanel events={events} onClose={() => setShowEvents(false)} />
      )}
    </div>
  );
}
