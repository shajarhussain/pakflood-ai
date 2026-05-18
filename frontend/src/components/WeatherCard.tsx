"use client";
import type { WeatherData, PredictionResponse } from "@/lib/types";
import { RISK_COLORS, RISK_BG, RISK_ICONS } from "@/lib/risk-colors";

interface Props {
  location: { lat: number; lng: number };
  weather: WeatherData | null;
  weatherError: string | null;
  prediction: PredictionResponse | null;
  predicting: boolean;
  onPredict: () => void;
  onDismiss: () => void;
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-slate-500 text-[10px] uppercase tracking-wider">{label}</span>
      <span className="text-slate-200 text-xs font-semibold">{value}</span>
    </div>
  );
}

export default function WeatherCard({
  location, weather, weatherError, prediction, predicting, onPredict, onDismiss,
}: Props) {
  const safeLevel = prediction
    ? ((prediction.risk_level === "Unknown" ? "Low" : prediction.risk_level) as keyof typeof RISK_COLORS)
    : null;
  const riskColor  = safeLevel ? RISK_COLORS[safeLevel] : null;
  const riskBg     = safeLevel ? RISK_BG[safeLevel]     : null;
  const riskIcon   = safeLevel ? (prediction!.risk_level === "Unknown" ? "?" : RISK_ICONS[safeLevel]) : null;
  const pct        = prediction ? Math.round(prediction.flood_probability * 100) : 0;
  const confPct    = prediction ? Math.round(prediction.confidence * 100) : 0;

  return (
    <div className="animate-fade-up w-80 bg-slate-900/95 border border-white/10 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-sm">

      {/* ── Dismiss ────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 pt-3 pb-0">
        <span className="text-slate-500 text-[10px]">
          {location.lat.toFixed(4)}°N, {location.lng.toFixed(4)}°E
        </span>
        <button onClick={onDismiss} className="text-slate-500 hover:text-slate-300 text-lg leading-none transition-colors">×</button>
      </div>

      {/* ── Weather section ─────────────────────────────────────────────────── */}
      {weatherError ? (
        <div className="px-4 py-3">
          <p className="text-slate-500 text-xs">{weatherError}</p>
        </div>
      ) : !weather ? (
        <div className="px-4 py-4 flex items-center gap-2">
          <svg className="w-4 h-4 text-cyan-400 animate-spin shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span className="text-slate-400 text-xs">Fetching weather…</span>
        </div>
      ) : (
        <div className="px-4 pb-3 border-b border-white/10">
          {/* Location + icon row */}
          <div className="flex items-center justify-between mb-1">
            <div>
              <p className="text-slate-200 text-sm font-semibold leading-tight">
                {weather.location || "Pakistan"}
                {weather.country ? <span className="text-slate-500 font-normal">, {weather.country}</span> : null}
              </p>
              <p className="text-slate-400 text-xs">{weather.description}</p>
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`https://openweathermap.org/img/wn/${weather.icon}@2x.png`}
              alt={weather.description}
              width={52}
              height={52}
              className="shrink-0"
            />
          </div>

          {/* Big temperature */}
          <div className="flex items-end gap-2 mb-3">
            <span className="text-4xl font-black text-slate-100 leading-none">{weather.temp}°</span>
            <span className="text-slate-500 text-sm mb-1">
              Feels {weather.feels_like}° · {weather.temp_min}° / {weather.temp_max}°
            </span>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-x-3 gap-y-2.5 bg-slate-800/40 rounded-xl px-3 py-2.5">
            <StatBox label="Humidity"    value={`${weather.humidity}%`} />
            <StatBox label="Wind"        value={`${weather.wind_speed} km/h ${weather.wind_dir}`} />
            <StatBox label="Pressure"    value={`${weather.pressure} hPa`} />
            <StatBox label="Clouds"      value={`${weather.clouds}%`} />
            <StatBox label="Visibility"  value={`${weather.visibility} km`} />
            <StatBox label="Condition"   value={weather.weather} />
          </div>
        </div>
      )}

      {/* ── Predict button ─────────────────────────────────────────────────── */}
      {!prediction && (
        <div className="px-4 py-3 border-b border-white/10">
          <button
            onClick={onPredict}
            disabled={predicting}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 text-xs font-semibold hover:bg-cyan-500/25 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {predicting ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Analysing flood risk…
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>
                Predict Flood Risk
              </>
            )}
          </button>
        </div>
      )}

      {/* ── Prediction section ─────────────────────────────────────────────── */}
      {prediction && riskColor && riskBg && (
        <>
          {/* Risk badge */}
          <div className="px-4 py-3 flex items-center justify-between border-b border-white/10">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold border ${riskBg}`} style={{ color: riskColor }}>
              <span>{riskIcon}</span>
              {prediction.risk_level === "Unknown" ? "Model Unavailable" : `${prediction.risk_level} Risk`}
            </span>
            <button
              onClick={onPredict}
              className="text-slate-600 hover:text-slate-400 text-[10px] transition-colors"
              title="Re-run prediction"
            >
              ↺ Refresh
            </button>
          </div>

          {/* Flood probability */}
          <div className="px-4 py-3 border-b border-white/10">
            <div className="flex items-end justify-between mb-1.5">
              <span className="text-slate-400 text-[10px] uppercase tracking-wider">Flood Probability</span>
              <span className="text-2xl font-bold" style={{ color: riskColor }}>{pct}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
              <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: riskColor }} />
            </div>
          </div>

          {/* Confidence */}
          <div className="px-4 py-2.5 border-b border-white/10">
            <div className="flex items-center justify-between mb-1">
              <span className="text-slate-400 text-[10px] uppercase tracking-wider">Model Confidence</span>
              <span className="text-slate-300 text-xs font-semibold">{confPct}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div className="h-full rounded-full bg-slate-400 transition-all duration-700" style={{ width: `${confPct}%` }} />
            </div>
          </div>

          {/* Top factors */}
          {prediction.top_factors?.length > 0 && (
            <div className="px-4 py-3 border-b border-white/10">
              <p className="text-slate-400 text-[10px] uppercase tracking-wider mb-2">Key Factors</p>
              <ul className="space-y-2">
                {prediction.top_factors.slice(0, 3).map((f, i) => {
                  const impPct = Math.round(Math.min((f.importance ?? 0) * 100, 100));
                  return (
                    <li key={i}>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-slate-300 text-[11px]">{f.name}</span>
                        <span className="text-slate-500 text-[10px]">{impPct}%</span>
                      </div>
                      <div className="h-1 rounded-full bg-slate-800 overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${impPct}%`, background: riskColor }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Disclaimer */}
      <div className="px-4 py-2.5">
        <p className="text-slate-600 text-[9px] leading-relaxed">
          {prediction?.disclaimer ?? "Weather data from OpenWeatherMap. Not an official warning — consult NDMA/PMD for emergencies."}
        </p>
      </div>
    </div>
  );
}
