"use client";

import { useEffect, useRef } from "react";
import type { RiskLevel } from "@/lib/types";
import { CITY_WEATHER } from "@/data/pakistan-cities-weather";

interface Props {
  active: boolean;
  riskLevel?: RiskLevel;
  panelOpen?: boolean;
}

// Lower density — primary visualization is now RainfallStationLayer; this is just ambient atmosphere
const DENSITY: Record<RiskLevel, number> = {
  Low: 35, Moderate: 75, High: 125, Severe: 175,
};

// Aggregate 24h rainfall across all stations for the "active" badge
const AVG_RAINFALL_MM = Math.round(
  CITY_WEATHER.reduce((s, c) => s + c.rainfall_mm_24h, 0) / CITY_WEATHER.length
);
const HEAVIEST = CITY_WEATHER.reduce((a, c) => c.rainfall_mm_24h > a.rainfall_mm_24h ? c : a, CITY_WEATHER[0]);
const MAX_RAINFALL_MM = HEAVIEST.rainfall_mm_24h;
const HEAVIEST_NAME   = HEAVIEST.name;
const HIGH_STATIONS   = CITY_WEATHER.filter((c) => c.rainfall_mm_24h >= 25).length;
const TOTAL_STATIONS  = CITY_WEATHER.length;

interface Particle {
  x: number;
  y: number;
  speed: number;
  length: number;
  opacity: number;
}

export function RainCanvas({ active, riskLevel = "Moderate", panelOpen = false }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const rafRef = useRef<number>(0);
  const lastFrameRef = useRef<number>(0);

  useEffect(() => {
    if (!active) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    function resize() {
      if (!canvas) return;
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      initParticles();
    }

    function initParticles() {
      if (!canvas) return;
      const count = DENSITY[riskLevel] ?? 100;
      particlesRef.current = Array.from({ length: count }, () =>
        spawnParticle(canvas!.width, canvas!.height, true)
      );
    }

    function spawnParticle(w: number, h: number, randomY = false): Particle {
      return {
        x:       Math.random() * w * 1.4 - w * 0.2,
        y:       randomY ? Math.random() * h : -20,
        speed:   3.5 + Math.random() * 5.0,
        length:  55 + Math.random() * 85,
        opacity: 0.45 + Math.random() * 0.45,
      };
    }

    const ANGLE  = 17 * (Math.PI / 180);
    const SIN    = Math.sin(ANGLE);
    const COS    = Math.cos(ANGLE);
    const FPS_CAP = 40;
    const FRAME_MS = 1000 / FPS_CAP;

    function draw(now: number) {
      if (!canvas || !ctx) return;
      const delta = now - lastFrameRef.current;
      if (delta < FRAME_MS) { rafRef.current = requestAnimationFrame(draw); return; }
      lastFrameRef.current = now;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (const p of particlesRef.current) {
        const x2 = p.x + SIN * p.length;
        const y2 = p.y + COS * p.length;

        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(x2, y2);

        const grad = ctx.createLinearGradient(p.x, p.y, x2, y2);
        grad.addColorStop(0,   `rgba(0,212,255,0)`);
        grad.addColorStop(0.3, `rgba(0,212,255,${p.opacity})`);
        grad.addColorStop(1,   `rgba(60,130,255,${p.opacity * 0.8})`);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1.2;
        ctx.stroke();

        p.x += SIN * p.speed * 0.5;
        p.y += COS * p.speed;

        if (p.y - p.length > canvas.height || p.x > canvas.width + 50) {
          const reset = spawnParticle(canvas.width, canvas.height, false);
          p.x = reset.x; p.y = reset.y; p.speed = reset.speed;
          p.length = reset.length; p.opacity = reset.opacity;
        }
      }

      rafRef.current = requestAnimationFrame(draw);
    }

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();
    rafRef.current = requestAnimationFrame(draw);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(rafRef.current);
    };
  }, [active, riskLevel]);

  if (!active) return null;

  const overlayIntensity =
    riskLevel === "Severe"   ? "rgba(0,120,255,0.22)"
    : riskLevel === "High"   ? "rgba(0,160,255,0.18)"
    : riskLevel === "Moderate" ? "rgba(0,180,255,0.14)"
    : "rgba(0,200,255,0.10)";

  return (
    <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 200 }}>
      {/* Static blue/cyan gradient overlay — visible in screenshots */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute", inset: 0,
          background: `linear-gradient(160deg, ${overlayIntensity} 0%, rgba(14,165,233,0.10) 55%, rgba(59,130,246,0.13) 100%)`,
        }}
      />

      {/* Rain particle canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full"
        aria-hidden="true"
      />

      {/* Live Station Feed card — top-right, separated from legend with 16px gap */}
      <div
        aria-label="Rainfall Intelligence Active"
        style={{
          position: "absolute",
          bottom: 156,
          right: panelOpen ? 316 : 16,
          background: "rgba(8,14,26,0.92)",
          border: "1px solid rgba(0,212,255,0.35)",
          borderRadius: 10,
          padding: "9px 13px",
          backdropFilter: "blur(12px)",
          boxShadow: "0 0 18px rgba(0,212,255,0.18), 0 2px 12px rgba(0,0,0,0.5)",
          minWidth: 200,
          transition: "right 0.22s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 7 }}>
          <span
            style={{
              width: 7, height: 7, borderRadius: "50%",
              background: "#00D4FF",
              boxShadow: "0 0 6px #00D4FF",
              display: "inline-block",
              animation: "live-blink 2s ease-in-out infinite",
            }}
          />
          <span style={{ fontSize: 10, fontWeight: 700, color: "#00D4FF", letterSpacing: "0.10em", textTransform: "uppercase", fontFamily: "var(--font-geist-mono, monospace)" }}>
            Live Station Feed
          </span>
        </div>

        <div style={{ display: "flex", gap: 5, marginBottom: 7 }}>
          {[
            { label: "stations", value: `${TOTAL_STATIONS}`,         color: "#00D4FF" },
            { label: "24h avg",  value: `${AVG_RAINFALL_MM}mm`,       color: AVG_RAINFALL_MM >= 25 ? "#F97316" : "#00D4FF" },
            { label: "alerts",   value: `${HIGH_STATIONS}≥25mm`,      color: HIGH_STATIONS >= 3 ? "#EF4444" : "#F59E0B" },
          ].map((b) => (
            <div
              key={b.label}
              style={{
                background: `${b.color}18`,
                border: `1px solid ${b.color}44`,
                borderRadius: 6,
                padding: "3px 7px",
                textAlign: "center",
                flex: 1,
              }}
            >
              <div style={{ fontSize: 8, color: "#64748B", letterSpacing: "0.08em", textTransform: "uppercase" }}>{b.label}</div>
              <div style={{ fontSize: 11, fontWeight: 800, color: b.color, fontFamily: "var(--font-geist-mono, monospace)" }}>{b.value}</div>
            </div>
          ))}
        </div>

        <div style={{ fontSize: 9, color: "#94A3B8", marginBottom: 3 }}>
          Heaviest: <span style={{ color: "#FCA5A5", fontWeight: 700 }}>{HEAVIEST_NAME} {MAX_RAINFALL_MM}mm</span>
        </div>
        <div style={{ fontSize: 8, color: "#4B6280" }}>
          Demo monsoon snapshot · IMERG/CHIRPS feed planned
        </div>
      </div>
    </div>
  );
}
