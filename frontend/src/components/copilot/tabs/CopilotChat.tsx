"use client";

import { useState } from "react";
import type { MockRiskEntry } from "@/data/mock";
import type { RiskExplanation } from "@/lib/types";
import { useModelStatus } from "@/lib/useModelStatus";
import { isV3Available, MODEL_UNAVAILABLE_MESSAGE } from "@/lib/api";

interface Props {
  district: MockRiskEntry;
  explanation: RiskExplanation;
}

type QuickAction = {
  id: string;
  label: string;
  icon: string;
  response: (d: MockRiskEntry, e: RiskExplanation) => string;
};

const QUICK_ACTIONS: QuickAction[] = [
  {
    id: "explain",
    icon: "📢",
    label: "Explain simply",
    response: (d, e) =>
      `${d.name} is at ${e.risk_level.toLowerCase()} flood risk. The main reason is ${d.top_factors[0] ?? "extreme conditions"} — compounded by ${d.top_factors[1] ?? "geographic factors"} and a history of flooding. Risk score: ${(d.risk_score * 100).toFixed(0)}% with ${(e.confidence * 100).toFixed(0)}% model confidence.`,
  },
  {
    id: "citizens",
    icon: "🏃",
    label: "What should citizens do?",
    response: (d) =>
      `For ${d.name} residents:\n• Store 72-hour water supply in sealed containers\n• Charge all devices and power banks now\n• Prepare emergency kit: documents, medicine, cash\n• Know your nearest elevated evacuation shelter\n• Avoid travel on low-lying flood roads\n• Follow NDMA, PDMA, and local authority alerts\n• Do not wait for water to enter your home before evacuating`,
  },
  {
    id: "authority",
    icon: "🏛",
    label: "What should authorities monitor?",
    response: (d) =>
      `Priority monitoring for ${d.name} district authorities:\n• River gauge readings at nearest barrage (FFD/IRSA data)\n• Pre-position rescue boats at identified high-risk wards\n• Review historical evacuation routes from 2010/2022 events\n• Alert PDMA for resource pre-staging and logistics\n• Ensure hospitals and emergency facilities have backup power tested\n• Coordinate with NDMA on national early warning timeline`,
  },
  {
    id: "confidence",
    icon: "❓",
    label: "Why is confidence limited?",
    response: (d, e) =>
      `Confidence is ${(e.confidence * 100).toFixed(0)}% for ${d.name} due to:\n• IMERG satellite rainfall data has ~4h latency (stale in demo)\n• Model trained on synthetic data — not real measured flood events\n• No live PMD/FFD bulletins available in demo mode\n• Only 10 districts in MVP — limited spatial context\n• Operational readiness requires official satellite + river gauge datasets\n\nThis is a baseline educational model. Expert validation needed before real use.`,
  },
  {
    id: "missing",
    icon: "📊",
    label: "What data is missing?",
    response: (d) =>
      `Key data gaps for ${d.name}:\n• Live river gauge readings (FFD/IRSA)\n• Current PMD weather bulletin (requires API auth)\n• Real-time SAR/Sentinel-1 flood extent imagery\n• GloFAS live discharge (simulated in demo)\n• Soil moisture saturation (SMAP/ESA)\n• Road accessibility data for evacuation routing\n• Population vulnerability mapping at ward level\n\nSources labelled "demo mode" or "planned" indicate unavailable live feeds.`,
  },
  {
    id: "advisory",
    icon: "📄",
    label: "Generate draft advisory",
    response: (d, e) =>
      `[EDUCATIONAL DRAFT — NOT OFFICIAL]\n\nFLOOD INTELLIGENCE ALERT\n${d.name.toUpperCase()} DISTRICT, ${d.province.toUpperCase()}\nIssued by: PakFlood AI Command Center (Educational Prototype)\n\nCurrent risk level: ${e.risk_level.toUpperCase()} (score ${(d.risk_score * 100).toFixed(0)}%)\nModel confidence: ${(e.confidence * 100).toFixed(0)}% | Version: baseline-v1.0\n\nKey risk factors:\n${d.top_factors.map((f) => `• ${f}`).join("\n")}\n\nHistorical context:\n${e.historical_evidence.join("\n")}\n\nRecommended actions:\n${e.suggested_actions.map((a) => `• ${a}`).join("\n")}\n\n⚠ FOLLOW PMD · FFD · NDMA · PDMA FOR OFFICIAL EMERGENCY INSTRUCTIONS.\nThis is an educational AI prototype. Not an official warning system.`,
  },
];

export function CopilotChat({ district, explanation }: Props) {
  const modelStatus = useModelStatus();
  const v3Ready = isV3Available(modelStatus);
  const chatFooter = v3Ready
    ? `Real prediction v3 · ${modelStatus?.calibration_method ?? "sigmoid"}-calibrated`
    : MODEL_UNAVAILABLE_MESSAGE;
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [response, setResponse] = useState<string | null>(null);

  function handleAction(action: QuickAction) {
    if (activeAction === action.id) {
      setActiveAction(null);
      setResponse(null);
      return;
    }
    setActiveAction(action.id);
    setResponse(action.response(district, explanation));
  }

  return (
    <div className="flex flex-col gap-3 animate-fade-up">
      {/* Intro message */}
      <div
        className="rounded-xl p-3.5"
        style={{
          background: "rgba(59,130,246,0.08)",
          border: "1px solid rgba(59,130,246,0.20)",
        }}
      >
        <div className="flex items-start gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-sm shrink-0 mt-0.5 font-black"
            style={{ background: "linear-gradient(135deg, #22D3EE, #3B82F6)" }}
          >
            ⬡
          </div>
          <div>
            <p
              className="text-[10px] font-semibold uppercase tracking-widest mb-1"
              style={{ color: "#60A5FA" }}
            >
              Flood Copilot · {district.name}
            </p>
            <p className="text-xs leading-relaxed" style={{ color: "#CBD5E1" }}>
              {district.name} has a <strong style={{ color: "#F1F5F9" }}>{explanation.risk_level.toLowerCase()} flood risk</strong> — score {(district.risk_score * 100).toFixed(0)}% with {(explanation.confidence * 100).toFixed(0)}% confidence. The primary driver is <em>{district.top_factors[0] ?? "extreme conditions"}</em>. Select an action below to explore further.
            </p>
            <p className="text-[10px] mt-1.5" style={{ color: v3Ready ? "#4B6280" : "#FCA5A5" }}>
              {chatFooter}
            </p>
          </div>
        </div>
      </div>

      {/* Quick action buttons */}
      <div>
        <p
          className="text-[9px] font-bold uppercase tracking-[0.12em] mb-2"
          style={{ color: "#4B6280" }}
        >
          Quick Actions
        </p>
        <div className="grid grid-cols-2 gap-1.5">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.id}
              onClick={() => handleAction(action)}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-left transition"
              style={{
                background: activeAction === action.id
                  ? "rgba(34,211,238,0.12)"
                  : "rgba(255,255,255,0.04)",
                border: activeAction === action.id
                  ? "1px solid rgba(34,211,238,0.30)"
                  : "1px solid rgba(255,255,255,0.08)",
                color: activeAction === action.id ? "#F1F5F9" : "#94A3B8",
              }}
              onMouseEnter={(e) =>
                activeAction !== action.id &&
                (e.currentTarget.style.background = "rgba(255,255,255,0.07)")
              }
              onMouseLeave={(e) =>
                activeAction !== action.id &&
                (e.currentTarget.style.background = "rgba(255,255,255,0.04)")
              }
            >
              <span className="text-sm">{action.icon}</span>
              <span className="text-[11px] font-medium leading-tight">{action.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Response display */}
      {response && (
        <div
          className="rounded-xl p-3.5 animate-fade-up"
          style={{
            background: "rgba(13,21,38,0.90)",
            border: "1px solid rgba(255,255,255,0.10)",
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <span
              className="text-[9px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full"
              style={{ background: "rgba(34,211,238,0.12)", color: "#22D3EE" }}
            >
              Copilot Response
            </span>
          </div>
          <p
            className="text-xs leading-relaxed whitespace-pre-line"
            style={{ color: "#CBD5E1" }}
          >
            {response}
          </p>
          <p className="text-[10px] mt-2 pt-2" style={{ color: "#4B6280", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
            ⚠ Educational AI response. Always follow official PMD · FFD · NDMA · PDMA guidance.
          </p>
        </div>
      )}

      {/* Input (non-functional, styled placeholder) */}
      <div
        className="flex items-center gap-2 rounded-lg px-3 py-2.5"
        style={{
          background: "#1A2845",
          border: "1px solid rgba(255,255,255,0.10)",
        }}
      >
        <input
          type="text"
          placeholder={`Ask about ${district.name}…`}
          disabled
          className="flex-1 bg-transparent text-xs outline-none"
          style={{ color: "#4B6280" }}
        />
        <span
          className="text-[10px] px-2 py-1 rounded-md"
          style={{ background: "rgba(255,255,255,0.05)", color: "#4B6280" }}
        >
          v2
        </span>
      </div>
      <p className="text-[10px] text-center" style={{ color: "#4B6280" }}>
        Free-form AI chat · coming in v2
      </p>
    </div>
  );
}
