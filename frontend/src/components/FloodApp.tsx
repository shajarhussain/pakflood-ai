"use client";
import { useState, useCallback, useEffect, useMemo } from "react";
import dynamic from "next/dynamic";
import type { PredictionResponse, ZonesGeoJSON, FloodEvent, WeatherData, RiverStation } from "@/lib/types";
import { predictFloodRisk, fetchWeather, fetchModelStatus, fetchZonesGeoJSON, fetchFloodEvents, sendChatMessage, fetchRiverStations, type ModelStatus } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import WeatherCard from "@/components/WeatherCard";
import AuthModal from "@/components/AuthModal";
import SearchBar from "@/components/SearchBar";
import FloodEventsPanel from "@/components/FloodEventsPanel";
import ChatPanel from "@/components/ChatPanel";
import ProfileButton from "@/components/ProfileButton";

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
  const [weather,          setWeather         ] = useState<WeatherData | null>(null);
  const [weatherLoading,   setWeatherLoading  ] = useState(false);
  const [weatherError,     setWeatherError    ] = useState<string | null>(null);
  const [prediction,       setPrediction      ] = useState<PredictionResponse | null>(null);
  const [predicting,       setPredicting      ] = useState(false);
  const [error,            setError           ] = useState<string | null>(null);
  const [modelStatus,      setModelStatus     ] = useState<ModelStatus | null>(null);

  const [zones,             setZones            ] = useState<ZonesGeoJSON | null>(null);
  const [showZones,         setShowZones        ] = useState(false);
  const [showZonePolygons,  setShowZonePolygons ] = useState(false);
  const [zonesLoading,      setZonesLoading     ] = useState(false);
  const [riskFilter,        setRiskFilter       ] = useState<string | null>(null);

  const [events,        setEvents       ] = useState<FloodEvent[]>([]);
  const [showEvents,    setShowEvents   ] = useState(false);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<FloodEvent | null>(null);

  const [aiInsight,        setAiInsight       ] = useState<string | null>(null);
  const [aiInsightLoading, setAiInsightLoading] = useState(false);
  const [aiInsightEventId, setAiInsightEventId] = useState<string | null>(null);

  const [showChat,      setShowChat     ] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);

  const [showRivers,    setShowRivers   ] = useState(false);
  const [riverStations, setRiverStations] = useState<RiverStation[]>([]);
  const [riversLoading, setRiversLoading] = useState(false);

  const { user, logout } = useAuth();

  const handleAskAI = useCallback(() => {
    setShowChat((v) => !v);
  }, [user]);

  useEffect(() => { fetchModelStatus().then(setModelStatus); }, []);

  // Auto-fetch AI insight when a signed-in user selects a flood event
  useEffect(() => {
    if (!selectedEvent || !user) {
      setAiInsight(null);
      setAiInsightLoading(false);
      setAiInsightEventId(null);
      return;
    }
    setAiInsight(null);
    setAiInsightLoading(true);
    setAiInsightEventId(selectedEvent.id);

    const ev = selectedEvent;
    const affectedStr = ev.affected_provinces.join(", ") || "multiple provinces";
    const affectedNum = ev.estimated_affected
      ? (ev.estimated_affected >= 1e6 ? `${(ev.estimated_affected / 1e6).toFixed(0)}M` : `${(ev.estimated_affected / 1e3).toFixed(0)}K`)
      : null;
    const prompt = [
      `Analyze the ${ev.year} Pakistan flood disaster: "${ev.title}".`,
      `Affected provinces: ${affectedStr}.`,
      ev.peak_month ? `Peak month: ${ev.peak_month}.` : "",
      affectedNum   ? `People affected: ${affectedNum}.` : "",
      ev.damage_usd_billion != null ? `Economic damage: $${ev.damage_usd_billion}B.` : "",
      "Cover: primary meteorological and hydrological causes, most severely impacted regions,",
      "humanitarian and infrastructure impact, and key preparedness lessons.",
      "Keep response to 4–6 concise sentences.",
    ].filter(Boolean).join(" ");

    sendChatMessage(prompt, [])
      .then(setAiInsight)
      .catch(() => setAiInsight("AI analysis unavailable for this event. Please try again."))
      .finally(() => setAiInsightLoading(false));
  }, [selectedEvent?.id, user?.user_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleToggleZones = useCallback(async () => {
    if (!showZones && !zones) {
      setZonesLoading(true);
      const data = await fetchZonesGeoJSON();
      setZones(data);
      setZonesLoading(false);
    }
    if (showZones) setRiskFilter(null);
    setShowZones((prev) => !prev);
  }, [showZones, zones]);

  const handleToggleZonePolygons = useCallback(async () => {
    if (!showZonePolygons && !zones) {
      setZonesLoading(true);
      const data = await fetchZonesGeoJSON();
      setZones(data);
      setZonesLoading(false);
    }
    if (showZonePolygons) setRiskFilter(null);
    setShowZonePolygons((prev) => !prev);
  }, [showZonePolygons, zones]);

  const handleToggleEvents = useCallback(async () => {
    if (!showEvents && events.length === 0) {
      setEventsLoading(true);
      const data = await fetchFloodEvents();
      setEvents(data);
      setEventsLoading(false);
    }
    setShowEvents((prev) => !prev);
  }, [showEvents, events]);

  const handleToggleRivers = useCallback(async () => {
    if (!showRivers && riverStations.length === 0) {
      setRiversLoading(true);
      const data = await fetchRiverStations();
      setRiverStations(data);
      setRiversLoading(false);
    }
    setShowRivers((prev) => !prev);
  }, [showRivers, riverStations]);

  const handleLocationSelect = useCallback(async (lat: number, lng: number) => {
    setSelectedLocation({ lat, lng });
    setWeather(null);
    setPrediction(null);
    setWeatherError(null);
    setError(null);
    setWeatherLoading(true);
    try {
      const w = await fetchWeather(lat, lng);
      setWeather(w);
    } catch (err) {
      setWeatherError(err instanceof Error ? err.message : "Weather unavailable");
    } finally {
      setWeatherLoading(false);
    }
  }, []);

  const handlePredict = useCallback(async () => {
    if (!selectedLocation) return;
    setPredicting(true);
    setError(null);
    try {
      const result = await predictFloodRisk(selectedLocation.lat, selectedLocation.lng);
      setPrediction(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setPredicting(false);
    }
  }, [selectedLocation]);

  const handleGeolocate = useCallback(() => {
    if (!navigator.geolocation) { setError("Geolocation not supported"); return; }
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => handleLocationSelect(pos.coords.latitude, pos.coords.longitude),
      () => setError("Location access denied — click on the map instead")
    );
  }, [handleLocationSelect]);

  const handleDismiss = useCallback(() => {
    setSelectedLocation(null); setWeather(null); setPrediction(null);
    setWeatherError(null); setError(null);
  }, []);

  const modelUnavailable = modelStatus !== null && !modelStatus.artifact_ready;
  const zonesAge   = zones?.metadata?.computed_at ? formatAge(zones.metadata.computed_at) : null;
  const zonesCount = zones?.metadata?.total_points ?? 0;

  const riskCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const f of zones?.features ?? []) {
      const lvl = f.properties.risk_level as string;
      counts[lvl] = (counts[lvl] ?? 0) + 1;
    }
    return counts;
  }, [zones]);

  return (
    <div className="relative w-screen h-screen bg-slate-950 overflow-hidden">
      {/* Full-screen map */}
      <FloodMap
        selectedLocation={selectedLocation}
        onLocationSelect={handleLocationSelect}
        zones={zones}
        showZones={showZones}
        showZonePolygons={showZonePolygons}
        riskFilter={riskFilter}
        selectedEvent={selectedEvent}
        showRivers={showRivers}
        riverStations={riverStations}
      />

      {/* Search bar — hidden when events panel is open to avoid overlap */}
      {!showEvents && <SearchBar onSelect={(lat, lng) => handleLocationSelect(lat, lng)} />}

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
          {/* Rivers toggle */}
          <button
            onClick={handleToggleRivers}
            disabled={riversLoading}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              showRivers
                ? "bg-blue-500/20 border-blue-500/40 text-blue-300"
                : "bg-slate-800/60 border-white/10 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60"
            }`}
            title="Major Pakistan rivers with live discharge animation"
          >
            {riversLoading ? (
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M3 6c3 0 3 3 6 3s3-3 6-3 3 3 6 3M3 12c3 0 3 3 6 3s3-3 6-3 3 3 6 3M3 18c3 0 3 3 6 3s3-3 6-3 3 3 6 3"/>
              </svg>
            )}
            {riversLoading ? "Loading…" : showRivers ? "Hide Rivers" : "Rivers"}
          </button>

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

          {/* Zone map toggle */}
          <button
            onClick={handleToggleZonePolygons}
            disabled={zonesLoading}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              showZonePolygons
                ? "bg-violet-500/20 border-violet-500/40 text-violet-300"
                : "bg-slate-800/60 border-white/10 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60"
            }`}
            title="District risk zones — coloured by dominant severity"
          >
            {zonesLoading && !showZones ? (
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9 20.999H5a2 2 0 0 1-2-2v-4m6 6 6-6m-6 6V9m6-8H5a2 2 0 0 0-2 2v4m18 4v4a2 2 0 0 1-2 2h-4m6-6-6 6m6-6H15m0 0V9m0 6 6-6M15 3h4a2 2 0 0 1 2 2v4"/>
              </svg>
            )}
            {showZonePolygons ? "Hide Zones" : "Zones"}
          </button>

          {/* My Location */}
          <button
            onClick={handleGeolocate}
            disabled={weatherLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-medium hover:bg-cyan-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
            </svg>
            My Location
          </button>

          {/* Profile button — always visible */}
          <div className="w-px h-4 bg-white/10 shrink-0" />
          <ProfileButton
            email={user?.email ?? null}
            onSignIn={() => setShowAuthModal(true)}
            onSignOut={logout}
          />
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

      {/* Risk filter panel */}
      {(showZones || showZonePolygons) && !zonesLoading && (() => {
        const LEVELS = [
          { key: "Severe",   color: "#ef4444" },
          { key: "High",     color: "#f97316" },
          { key: "Moderate", color: "#eab308" },
          { key: "Low",      color: "#22c55e" },
        ] as const;
        return (
          <div className={`absolute bottom-8 z-[1000] transition-all ${showEvents ? "left-[292px]" : "left-4"}`}>
            <div className="rounded-xl bg-slate-900/90 border border-white/10 backdrop-blur-sm overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between px-3 pt-2.5 pb-1.5 border-b border-white/5">
                <span className="text-slate-500 text-[10px] uppercase tracking-wider">
                  Risk Filter
                  {zonesCount > 0 && <span className="ml-1 text-slate-600">· {zonesCount} pts</span>}
                </span>
                {riskFilter && (
                  <button
                    onClick={() => setRiskFilter(null)}
                    className="text-[9px] text-slate-500 hover:text-slate-300 uppercase tracking-wider ml-3 transition-colors"
                  >
                    Clear
                  </button>
                )}
              </div>

              {/* Level buttons */}
              <div className="flex flex-col p-1.5 gap-0.5">
                {LEVELS.map(({ key, color }) => {
                  const active  = riskFilter === key;
                  const dimmed  = !!riskFilter && !active;
                  const count   = riskCounts[key] ?? 0;
                  return (
                    <button
                      key={key}
                      onClick={() => setRiskFilter(active ? null : key)}
                      className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-all"
                      style={{
                        background:  active ? `${color}18` : "transparent",
                        border:      active ? `1px solid ${color}50` : "1px solid transparent",
                        opacity:     dimmed ? 0.4 : 1,
                      }}
                    >
                      <div
                        className="w-2.5 h-2.5 rounded-full shrink-0 transition-transform"
                        style={{
                          backgroundColor: color,
                          transform: active ? "scale(1.3)" : "scale(1)",
                          boxShadow: active ? `0 0 8px ${color}80` : "none",
                        }}
                      />
                      <span className="text-[11px] font-medium flex-1" style={{ color: active ? color : "#94a3b8" }}>
                        {key}
                      </span>
                      {count > 0 && (
                        <span className="text-[10px] tabular-nums" style={{ color: active ? color : "#475569" }}>
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {zones?.metadata?.is_fresh === false && (
                <p className="text-amber-500/70 text-[10px] px-3 pb-2 border-t border-white/5 pt-1.5">Stale — refresh queued</p>
              )}
            </div>
          </div>
        );
      })()}

      {/* Hint */}
      {!selectedLocation && !weatherLoading && !showEvents && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[1000]">
          <div className="px-4 py-2 rounded-full bg-slate-900/90 border border-white/10 text-slate-400 text-xs backdrop-blur-sm">
            Click anywhere in Pakistan · or use My Location
          </div>
        </div>
      )}

      {/* Weather loading */}
      {weatherLoading && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[1000]">
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900/90 border border-white/10 backdrop-blur-sm">
            <svg className="w-4 h-4 text-cyan-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <span className="text-slate-400 text-xs">Fetching weather…</span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && !predicting && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[1000] max-w-sm w-full px-4">
          <div className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-red-900/40 border border-red-500/30 backdrop-blur-sm">
            <p className="text-red-300 text-xs">{error}</p>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 text-lg leading-none shrink-0">×</button>
          </div>
        </div>
      )}

      {/* Weather + prediction card — sits above the Ask AI FAB */}
      {selectedLocation && !weatherLoading && !showEvents && (
        <div className="absolute bottom-20 right-4 z-[1000]">
          <WeatherCard
            location={selectedLocation}
            weather={weather}
            weatherError={weatherError}
            prediction={prediction}
            predicting={predicting}
            onPredict={handlePredict}
            onDismiss={handleDismiss}
          />
        </div>
      )}

      {/* Ask AI floating button */}
      {!showChat && (
        <button
          onClick={handleAskAI}
          className="absolute bottom-6 right-6 z-[1010] flex items-center gap-2 px-4 py-3 rounded-2xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 text-sm font-semibold hover:bg-cyan-500/25 shadow-lg backdrop-blur-sm transition-all hover:scale-105 active:scale-95"
          title={user ? "Ask PakFlood AI" : "Sign in to use AI assistant"}
        >
          <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          Ask AI
          {/* {!user && (
            <span className="text-[10px] text-slate-500 font-normal">· Sign in</span>
          )} */}
        </button>
      )}

      {/* Chat open — small collapse button */}
      {showChat && (
        <button
          onClick={() => setShowChat(false)}
          className="absolute bottom-6 right-6 z-[1010] w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 flex items-center justify-center hover:bg-cyan-500/25 shadow-lg backdrop-blur-sm transition-all"
          title="Close AI chat"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M18 6 6 18M6 6l12 12"/>
          </svg>
        </button>
      )}

      {/* AI Chat panel */}
      {showChat && (
        <ChatPanel
          onClose={() => setShowChat(false)}
          isSignedIn={!!user}
          onRequestSignIn={() => { setShowChat(false); setShowAuthModal(true); }}
        />
      )}

      {/* Auth modal */}
      {showAuthModal && (
        <AuthModal
          onClose={() => setShowAuthModal(false)}
          onSuccess={() => { setShowAuthModal(false); setShowChat(true); }}
        />
      )}

      {/* AI Chat panel */}
      {showChat && (
        <ChatPanel
          onClose={() => setShowChat(false)}
          isSignedIn={!!user}
          onRequestSignIn={() => setShowAuthModal(true)}
        />
      )}

      {/* Historical flood events panel */}
      {showEvents && (
        <FloodEventsPanel
          events={events}
          onClose={() => { setShowEvents(false); setSelectedEvent(null); }}
          selectedEventId={selectedEvent?.id ?? null}
          onEventSelect={setSelectedEvent}
          isSignedIn={!!user}
          onRequestSignIn={() => setShowAuthModal(true)}
          aiInsight={aiInsight}
          aiInsightLoading={aiInsightLoading}
          aiInsightEventId={aiInsightEventId}
        />
      )}
    </div>
  );
}
