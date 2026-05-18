"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { sendChatMessage, type ChatMessage } from "@/lib/api";

interface Props {
  onClose: () => void;
  isSignedIn: boolean;
  onRequestSignIn: () => void;
}

const SUGGESTIONS = [
  "What are the most flood-prone areas in Pakistan?",
  "Tell me about the 2022 floods",
  "What is the current weather situation?",
  "How does the flood prediction model work?",
];

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}

export default function ChatPanel({ onClose, isSignedIn, onRequestSignIn }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input,    setInput   ] = useState("");
  const [loading,  setLoading ] = useState(false);
  const [error,    setError   ] = useState<string | null>(null);
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (isSignedIn) {
      inputRef.current?.focus();
    }
  }, [isSignedIn]);

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: ChatMessage = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setError(null);
    setLoading(true);

    try {
      // Only pass last 5 exchanges (10 messages) to keep tokens low
      const history = [...messages, userMsg].slice(-10);
      const reply = await sendChatMessage(trimmed, history.slice(0, -1));
      setMessages((prev) => [...prev, { role: "model", content: reply }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get response");
    } finally {
      setLoading(false);
    }
  }, [loading, messages]);

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <div className="absolute bottom-0 right-0 z-[1100] w-80 sm:w-96 flex flex-col bg-slate-950/97 border border-white/10 backdrop-blur-sm rounded-tl-2xl shadow-2xl animate-fade-up"
      style={{ maxHeight: "calc(100vh - 72px)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-live-blink" />
          <span className="text-slate-200 text-sm font-semibold">PakFlood AI</span>
          {/* <span className="text-slate-600 text-[10px]">powered by Gemini</span> */}
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 transition-colors p-1 rounded"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-3 min-h-0">
        {messages.length === 0 && isSignedIn && (
          <div className="flex flex-col gap-2 mt-1">
            <p className="text-slate-500 text-xs text-center mb-1">
              Ask me about Pakistan flood risk, predictions, or history.
            </p>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-left text-xs px-3 py-2 rounded-lg bg-slate-800/60 border border-white/5 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.length === 0 && !isSignedIn && (
          <div className="flex-1 flex items-center justify-center px-2 py-6">
            <div className="w-full rounded-2xl border border-cyan-500/15 bg-cyan-500/5 px-4 py-5 text-center">
              <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <p className="text-slate-200 text-sm font-semibold">Sign in to talk</p>
              <p className="mt-1 text-slate-500 text-xs leading-relaxed">
                Your chat window is ready. Sign in to ask questions about floods, weather, and risk updates.
              </p>
              <button
                onClick={onRequestSignIn}
                className="mt-4 inline-flex items-center justify-center rounded-xl bg-cyan-500/20 border border-cyan-500/30 px-4 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/30 transition-colors"
              >
                Sign in
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-cyan-500/20 border border-cyan-500/30 text-slate-200 rounded-br-sm"
                  : "bg-slate-800/80 border border-white/5 text-slate-300 rounded-bl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/80 border border-white/5 rounded-2xl rounded-bl-sm">
              <ThinkingDots />
            </div>
          </div>
        )}

        {error && (
          <div className="text-red-400 text-[10px] text-center px-2 py-1 bg-red-900/20 rounded-lg border border-red-500/20">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-3 pb-3 pt-2 border-t border-white/5 shrink-0">
        <div className="flex items-end gap-2 bg-slate-800/60 border border-white/10 rounded-xl px-3 py-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={isSignedIn ? "Ask about floods, risk zones, weather…" : "Sign in to talk"}
            rows={1}
            disabled={loading || !isSignedIn}
            className="flex-1 bg-transparent text-slate-200 text-xs placeholder-slate-600 resize-none outline-none leading-relaxed disabled:opacity-50"
            style={{ maxHeight: "80px" }}
          />
          <button
            onClick={isSignedIn ? () => send(input) : onRequestSignIn}
            disabled={isSignedIn ? (!input.trim() || loading) : false}
            className="shrink-0 p-1.5 rounded-lg bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/30 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
        <p className="text-slate-700 text-[9px] text-center mt-1.5">
          AI estimates only · Not official warnings · NDMA/PMD for emergencies
        </p>
      </div>
    </div>
  );
}
