# PakFlood AI — Frontend API Integration Guide

> This document is for a frontend developer implementing or extending the PakFlood AI Next.js dashboard.  
> It covers how to wire every API endpoint to a UI component, what state to manage, and how to handle edge cases.
>
> **Read alongside:** `API_REFERENCE.md` for full request/response shapes.

---

## Table of Contents

1. [Project Setup](#1-project-setup)
2. [API Client Pattern](#2-api-client-pattern)
3. [Existing Feature Wiring (Already Implemented)](#3-existing-feature-wiring-already-implemented)
4. [District Search (Active Work)](#4-district-search-active-work)
5. [Zone Grid Map Layer](#5-zone-grid-map-layer)
6. [Authentication — Implementing Login/Register](#6-authentication--implementing-loginregister)
7. [Education Module](#7-education-module)
8. [Learning Bot (Gemini)](#8-learning-bot-gemini)
9. [Help Bot (Gemini)](#9-help-bot-gemini)
10. [State Management Overview](#10-state-management-overview)
11. [Error Handling & Fallbacks](#11-error-handling--fallbacks)
12. [Safety Disclaimer Rules](#12-safety-disclaimer-rules)
13. [Environment Variables](#13-environment-variables)
14. [File Structure](#14-file-structure)

---

## 1. Project Setup

**Tech stack:** Next.js 15 (App Router), TypeScript, Tailwind CSS, Leaflet (react-leaflet), shadcn/ui

**Install dependencies**
```bash
cd frontend
npm install
```

**Run dev server**
```bash
npm run dev
# Runs on http://localhost:3000
```

**Backend must be running** at `http://localhost:8000` for live data.  
The frontend falls back to mock data automatically when the backend is unreachable.

**Environment file:** create `frontend/.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 2. API Client Pattern

All API calls go through `src/lib/api.ts`. The pattern is:

```typescript
// Generic fetch helper — returns null on any error or non-2xx status
async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// For POST/PATCH/DELETE with a body
async function apiPost<T>(path: string, body: unknown, token?: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
```

**Rules:**
- Never throw to the caller — return `null` and let the component handle it
- Always fall back to mock data when `null` is returned
- Never use `cache: "no-store"` for GET requests that can be stale — use `next: { revalidate: N }`

---

## 3. Existing Feature Wiring (Already Implemented)

These features are already working. This section documents how they work so you don't break them.

### Health check

Not called by the UI directly — it is checked by the deployment health probe.  
If you want to show a "Backend offline" banner, poll `GET /health` in a `useEffect`.

### Model status

Called by `src/lib/useModelStatus.ts`. The hook fetches `/model/status` once on mount and exposes `isV3Available(status)`. This gates whether the UI shows "Real prediction v3" or "Model unavailable".

```typescript
// Usage in any component:
import { useModelStatus } from "@/lib/useModelStatus";

const status = useModelStatus();
const label = modelBadgeLabel(status); // e.g. "Real prediction v3 · 72h"
```

### Flood events timeline

`FloodTimeline` calls `fetchFloodEvents()` from `api.ts`, which hits `GET /flood-events`.  
If the DB is empty (no seed data), it falls back to `MOCK_FLOOD_EVENTS` from `src/data/mock.ts`.

### District risk explanation (copilot panel)

`CopilotPanel` calls `fetchExplanation(districtId)` which hits `GET /explain-risk/by-boundary/{id}`.  
If the backend returns null, it builds a mock explanation with `buildMockExplanation(district)`.

---

## 4. District Search (Active Work)

### How it works

The search bar in `MissionHeader` calls `searchDistricts(q)` which hits `GET /districts/search?q=`.

**Response for each result includes:**
- `center` — `{lat, lng}` object to fly the map to
- `boundary` — GeoJSON Feature polygon to highlight on the map
- `summary` — flood risk computed from zone grid points inside the district

### Wiring the map fly-to

When a user selects a search result, `MapDashboard.handleDistrictSearch` is called:

```typescript
const handleDistrictSearch = useCallback((result: ApiLocationResult, districtData?: DistrictSearchResult) => {
  setSelectedDistrictId(result.district_id);
  setSelectedGridCell(null);
  setSelectedCity(null);
  // Fly map to the district center
  mapRef.current?.flyTo(result.center[0], result.center[1], 9);
}, []);
```

The `mapRef.flyTo` is implemented in `MapController` inside `PakistanMap.tsx`:
```typescript
mapRef.current = {
  flyTo: (lat, lng, zoom = 9) => map.flyTo([lat, lng], zoom, { duration: 1.2 }),
};
```

### Showing the district boundary highlight

The district polygon is already on the map via `districts.json` (the static file). When `selectedDistrictId` is set, `featureStyle()` in `PakistanMap` applies the highlight style:

```typescript
const isSelected = id === selectedId;
return {
  fillOpacity: isSelected ? 0.85 : 0.55,
  color: isSelected ? "#22D3EE" : "rgba(255,255,255,0.14)",
  weight: isSelected ? 2.5 : 0.9,
};
```

### Showing risk data from the search result

The `summary.dominant_risk` from the search result is used as the `risk_level` in the search dropdown. It is currently shown in the search dropdown but not yet pushed into the CopilotPanel — that still uses mock data.

**To-do for full wiring:** When a district is selected via search and `districtData.summary` exists, pass the summary into the CopilotPanel as the risk source instead of the mock.

---

## 5. Zone Grid Map Layer

### Component: `GridRiskLayer`

Located at `src/components/map/GridRiskLayer.tsx`

Fetches `GET /zones/geojson` and renders 952 circle markers across Pakistan, coloured by risk level.

```typescript
// Inside GridRiskLayer.tsx
useEffect(() => {
  fetch(`${API_BASE}/zones/geojson`)
    .then(r => r.json())
    .then((data) => {
      setGeoJson(data);
      setIsFresh(data.metadata?.is_fresh ?? false);
    });
}, []);
```

**Props**

| Prop           | Type                   | Description                                          |
|----------------|------------------------|------------------------------------------------------|
| `visible`      | boolean                | Show/hide the layer (controlled by LayerRail toggle) |
| `onCellClick`  | `(cell: GridCell) => void` | Fired when user clicks a zone point              |
| `selectedCellId` | string \| null       | Highlights this cell with a different colour         |

**When the zone data is stale** (`is_fresh: false`), the layer shows a subtle amber border on each cell. When `total_points === 0`, it shows a "Data loading..." placeholder.

### Polling for zone status

To show a "Refreshing zones..." indicator, poll `GET /zones/status` every 30 seconds:

```typescript
const [zonesStatus, setZonesStatus] = useState(null);

useEffect(() => {
  const poll = async () => {
    const status = await apiFetch("/zones/status");
    setZonesStatus(status);
  };
  poll();
  const interval = setInterval(poll, 30_000);
  return () => clearInterval(interval);
}, []);
```

---

## 6. Authentication — Implementing Login/Register

> **These APIs are not built yet.** This section describes how to implement the frontend once the backend is ready.

### Files to create

```
src/
  app/
    login/
      page.tsx         ← Login page
    register/
      page.tsx         ← Register page
    profile/
      page.tsx         ← User profile page
  lib/
    auth.ts            ← Auth API functions
    useAuth.ts         ← Auth state hook
  components/
    auth/
      LoginForm.tsx
      RegisterForm.tsx
      AuthGuard.tsx    ← Wrapper to protect pages
```

### Auth state hook

```typescript
// src/lib/useAuth.ts
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthStore {
  token: string | null;
  user: UserProfile | null;
  setAuth: (token: string, user: UserProfile) => void;
  clearAuth: () => void;
}

export const useAuth = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      clearAuth: () => set({ token: null, user: null }),
    }),
    { name: "pakflood-auth" }
  )
);
```

### Login form wiring

```typescript
// src/lib/auth.ts
export async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });

  if (res.status === 401) throw new Error("Wrong email or password.");
  if (res.status === 403) throw new Error("Please verify your email first.");
  if (!res.ok) throw new Error("Login failed. Try again.");

  return res.json() as Promise<{ access_token: string; refresh_token: string; user: UserProfile }>;
}

export async function register(email: string, password: string, fullName: string) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
    cache: "no-store",
  });

  if (res.status === 409) throw new Error("This email is already registered.");
  if (!res.ok) throw new Error("Registration failed. Try again.");

  return res.json();
}
```

### LoginForm component

```tsx
// src/components/auth/LoginForm.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/auth";
import { useAuth } from "@/lib/useAuth";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuth();
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await login(email, password);
      setAuth(data.access_token, data.user);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-full max-w-sm">
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        className="rounded-lg px-3 py-2 bg-slate-800 text-white"
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        className="rounded-lg px-3 py-2 bg-slate-800 text-white"
      />
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="rounded-lg py-2 bg-cyan-500 text-white font-semibold disabled:opacity-50"
      >
        {loading ? "Signing in…" : "Sign In"}
      </button>
    </form>
  );
}
```

### Protecting pages with AuthGuard

```tsx
// src/components/auth/AuthGuard.tsx
"use client";

import { useAuth } from "@/lib/useAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!token) router.push("/login");
  }, [token, router]);

  if (!token) return null;
  return <>{children}</>;
}

// Usage on a protected page:
// export default function ProfilePage() {
//   return <AuthGuard><ProfileContent /></AuthGuard>;
// }
```

### Token refresh

```typescript
// src/lib/auth.ts
export async function refreshToken(refreshToken: string): Promise<string | null> {
  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: "no-store",
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.access_token;
}
```

---

## 7. Education Module

> **These APIs are not built yet.** This section describes the planned implementation.

### Files to create

```
src/
  app/
    education/
      page.tsx               ← Article listing page
      [slug]/
        page.tsx             ← Article detail page
  lib/
    education.ts             ← Education API functions
  components/
    education/
      ArticleCard.tsx        ← Card used in the listing grid
      ArticleReader.tsx      ← Full article with markdown rendering
      CategoryFilter.tsx     ← Filter tabs (Hydrology, Climate, etc.)
      ProgressBar.tsx        ← Shows reading progress for logged-in users
```

### Fetching articles

```typescript
// src/lib/education.ts

export async function fetchArticles(category?: string, page = 0): Promise<ArticleListResponse | null> {
  const params = new URLSearchParams({ limit: "20", offset: String(page * 20) });
  if (category) params.set("category", category);
  return apiFetch<ArticleListResponse>(`/education/articles?${params}`);
}

export async function fetchArticle(slug: string): Promise<Article | null> {
  return apiFetch<Article>(`/education/articles/${encodeURIComponent(slug)}`);
}

export async function markArticleRead(articleId: string, token: string): Promise<void> {
  await apiPost(`/education/progress/${articleId}`, {}, token);
}
```

### Article listing page

```tsx
// src/app/education/page.tsx
"use client";

import { useEffect, useState } from "react";
import { fetchArticles } from "@/lib/education";
import { ArticleCard } from "@/components/education/ArticleCard";

const CATEGORIES = ["All", "hydrology", "climate", "disaster-risk", "pakistan-history", "preparedness"];

export default function EducationPage() {
  const [category, setCategory] = useState<string | undefined>();
  const [articles, setArticles] = useState([]);

  useEffect(() => {
    fetchArticles(category).then((data) => {
      if (data) setArticles(data.articles);
    });
  }, [category]);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-6">Flood Education</h1>
      <div className="flex gap-2 mb-6">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c === "All" ? undefined : c)}
            className={`px-3 py-1 rounded-full text-sm ${
              (category ?? "All") === c
                ? "bg-cyan-500 text-white"
                : "bg-slate-800 text-slate-400"
            }`}
          >
            {c}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {articles.map((article) => (
          <ArticleCard key={article.article_id} article={article} />
        ))}
      </div>
    </div>
  );
}
```

### Article detail page

```tsx
// src/app/education/[slug]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { fetchArticle } from "@/lib/education";
import ReactMarkdown from "react-markdown";

export default function ArticlePage({ params }: { params: { slug: string } }) {
  const [article, setArticle] = useState(null);

  useEffect(() => {
    fetchArticle(params.slug).then(setArticle);
  }, [params.slug]);

  if (!article) return <div className="text-slate-400 p-6">Loading…</div>;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-bold text-white mb-2">{article.title}</h1>
      <p className="text-slate-400 text-sm mb-6">
        {article.author} · {article.reading_time_minutes} min read
      </p>
      <div className="prose prose-invert">
        <ReactMarkdown>{article.content_md}</ReactMarkdown>
      </div>
    </div>
  );
}
```

> **Install:** `npm install react-markdown` for markdown rendering.

---

## 8. Learning Bot (Gemini)

> **These APIs are not built yet.** This section describes the planned chat UI.

### Files to create

```
src/
  app/
    learn/
      page.tsx             ← Learning bot chat page
  lib/
    chat.ts                ← Bot API functions
  components/
    chat/
      ChatWindow.tsx       ← Scrolling message history
      ChatInput.tsx        ← Message input with send button
      BotMessage.tsx       ← AI response with source links
      UserMessage.tsx      ← User's message bubble
      SessionList.tsx      ← Previous sessions sidebar
```

### API functions

```typescript
// src/lib/chat.ts

export async function askLearningBot(message: string, sessionId?: string, token?: string) {
  const res = await fetch(`${API_BASE}/chat/learn`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      language: "en",
    }),
    cache: "no-store",
  });

  if (!res.ok) throw new Error("Learning bot unavailable.");
  return res.json() as Promise<BotResponse>;
}

export async function fetchLearningSessions(token: string) {
  return apiFetch<SessionListResponse>("/chat/learn/sessions");
  // Note: attach auth header once implemented
}

export async function deleteLearningSession(sessionId: string, token: string) {
  await fetch(`${API_BASE}/chat/learn/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
}
```

### Chat component

```tsx
// src/components/chat/ChatWindow.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { askLearningBot } from "@/lib/chat";
import { useAuth } from "@/lib/useAuth";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ name: string; url: string }>;
}

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const { token } = useAuth();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    if (!input.trim() || loading) return;
    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const response = await askLearningBot(userMessage, sessionId, token ?? undefined);
      setSessionId(response.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer, sources: response.sources },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, the learning bot is unavailable right now." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-slate-400 text-sm text-center mt-8">
            Ask me anything about floods, rainfall, rivers, or Pakistan's flood history.
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-cyan-600 text-white"
                  : "bg-slate-800 text-slate-200"
              }`}
            >
              <p>{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 space-y-1">
                  {msg.sources.map((s) => (
                    <a
                      key={s.url}
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-xs text-cyan-400 underline"
                    >
                      {s.name} →
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 rounded-xl px-3 py-2 text-slate-400 text-sm animate-pulse">
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-slate-800 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask about floods…"
          className="flex-1 rounded-lg px-3 py-2 bg-slate-800 text-white text-sm focus:outline-none"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="px-4 py-2 rounded-lg bg-cyan-500 text-white text-sm font-semibold disabled:opacity-40"
        >
          Send
        </button>
      </div>

      {/* Disclaimer */}
      <p className="text-[10px] text-slate-500 text-center px-3 pb-2">
        Educational only. For emergencies contact NDMA: 1700
      </p>
    </div>
  );
}
```

---

## 9. Help Bot (Gemini)

> **These APIs are not built yet.** The Help Bot is embedded inside the map dashboard as a floating panel, not a separate page.

### Placement

Add the Help Bot as a tab inside `CopilotPanel` or as a separate floating button in the bottom-right corner of the map.

### Key difference from Learning Bot

The Help Bot receives a `context` object with the current app state — current page and selected district. This lets it give context-aware answers like "You've selected Lahore, which currently shows Moderate risk because…"

### API function

```typescript
// src/lib/chat.ts

export async function askHelpBot(
  message: string,
  context: { current_page: string; selected_district?: string | null },
  sessionId?: string,
  token?: string
) {
  const res = await fetch(`${API_BASE}/chat/help`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId, context }),
    cache: "no-store",
  });

  if (!res.ok) throw new Error("Help bot unavailable.");
  return res.json() as Promise<HelpBotResponse>;
}
```

### Handling quick_actions

The Help Bot can return `quick_actions` that the frontend can wire up as buttons:

```tsx
// In your chat renderer:
{response.quick_actions?.map((action) => (
  <button
    key={action.label}
    onClick={() => handleQuickAction(action)}
    className="mt-2 text-xs text-cyan-400 border border-cyan-800 px-2 py-1 rounded-full"
  >
    {action.label}
  </button>
))}

// Handler:
function handleQuickAction(action: QuickAction) {
  switch (action.action) {
    case "select_district":
      setSelectedDistrictId(action.payload);
      break;
    case "open_panel":
      setActivePanel(action.payload);
      break;
    case "navigate":
      router.push(action.payload);
      break;
  }
}
```

---

## 10. State Management Overview

The app uses React `useState` + `useCallback` (no Redux/Zustand for map state). Auth state uses Zustand with `localStorage` persistence.

### MapDashboard state

| State variable          | Type               | Purpose                                      |
|-------------------------|--------------------|----------------------------------------------|
| `selectedDistrictId`    | `string \| null`   | Which district is highlighted on the map     |
| `selectedGridCell`      | `GridCell \| null` | Which zone point is selected                 |
| `selectedCity`          | `CityWeather \| null` | Which city weather marker is active       |
| `activeYear`            | `number \| null`   | Which historical flood year is highlighted   |
| `layers`                | `LayerVisibility`  | Which map layers are visible                 |
| `floodEvents`           | `MockFloodEvent[]` | Historical events for the timeline           |
| `liveExplanation`       | `RiskExplanation \| null` | AI explanation from backend            |

### Adding auth state

```typescript
// Add to MapDashboard.tsx when auth is implemented:
import { useAuth } from "@/lib/useAuth";
const { token, user } = useAuth();
```

### Adding chat panel state

```typescript
// Add to MapDashboard.tsx:
const [chatOpen, setChatOpen] = useState(false);
const [chatMode, setChatMode] = useState<"learn" | "help">("help");
```

---

## 11. Error Handling & Fallbacks

### Pattern: silent fallback

```typescript
// Always return mock data if API fails — never show a crash
export async function fetchFloodEvents(districtName?: string): Promise<ApiFloodEvent[]> {
  const data = await apiFetch<ApiFloodEvent[]>("/flood-events");
  if (data) return data;
  // Silent fallback to mock
  return MOCK_FLOOD_EVENTS.map(mockToApiEvent);
}
```

### Pattern: show a warning badge

When live data is unavailable, show an amber "Using cached data" badge rather than nothing:

```tsx
{!isFresh && (
  <div className="text-xs text-amber-400 bg-amber-900/30 px-2 py-1 rounded">
    Showing cached data · Refreshing…
  </div>
)}
```

### Pattern: skeleton loaders

Use skeleton divs while data is loading — never show a blank panel:

```tsx
{isLoading ? (
  <div className="animate-pulse space-y-2">
    <div className="h-4 bg-slate-700 rounded w-3/4" />
    <div className="h-4 bg-slate-700 rounded w-1/2" />
  </div>
) : (
  <ArticleCard article={article} />
)}
```

### Bot error handling

```typescript
// Never let a bot error crash the chat UI
try {
  const response = await askLearningBot(message, sessionId);
  // ...
} catch {
  setMessages(prev => [...prev, {
    role: "assistant",
    content: "I'm temporarily unavailable. Please try again in a moment. For emergencies, call NDMA: 1700."
  }]);
}
```

---

## 12. Safety Disclaimer Rules

**These are non-negotiable.** Violating them makes the app unsafe.

1. **Every risk level display** must be accompanied by the disclaimer.
2. **Both bots** must end every response with an emergency contact.
3. **The disclaimer component** `SafetyDisclaimer` renders at the bottom of every page.
4. **Bot answers** must never say "there will be flooding" — only "the model predicts X probability".

```tsx
// The disclaimer is already implemented in src/components/layout/SafetyDisclaimer.tsx
// It is included in MapDashboard and must be included in all new pages.

// For bot messages, add this under every assistant response:
<p className="text-[10px] text-slate-500 mt-2">
  Educational only — not an official warning. Emergencies: NDMA 1700 · PMD pmd.gov.pk
</p>
```

---

## 13. Environment Variables

**`frontend/.env.local`**

| Variable                | Required | Default                         | Description                              |
|-------------------------|----------|---------------------------------|------------------------------------------|
| `NEXT_PUBLIC_API_URL`   | Yes      | `http://localhost:8000/api/v1`  | Backend API base URL                     |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | No    | —                               | Only needed if switching from Leaflet to Mapbox |

---

## 14. File Structure

```
frontend/src/
├── app/
│   ├── page.tsx                    ← Root page — renders MapDashboard
│   ├── layout.tsx                  ← Root layout with fonts + metadata
│   ├── login/page.tsx              ← (planned) Login page
│   ├── register/page.tsx           ← (planned) Register page
│   ├── profile/page.tsx            ← (planned) User profile
│   ├── education/
│   │   ├── page.tsx                ← (planned) Article listing
│   │   └── [slug]/page.tsx         ← (planned) Article detail
│   └── learn/page.tsx              ← (planned) Learning bot page
│
├── components/
│   ├── layout/
│   │   ├── MissionHeader.tsx       ← Top nav + district search
│   │   ├── StatusBar.tsx           ← Active layer indicators
│   │   └── SafetyDisclaimer.tsx    ← PMD/NDMA/PDMA disclaimer bar
│   ├── map/
│   │   ├── MapDashboard.tsx        ← Root map component with all state
│   │   ├── PakistanMap.tsx         ← Leaflet map + district layer
│   │   ├── GridRiskLayer.tsx       ← Zone grid circles from /zones/geojson
│   │   ├── CityWeatherLabels.tsx   ← City weather markers
│   │   ├── WindVectorLayer.tsx     ← Wind arrow layer
│   │   └── MapLegend.tsx           ← Risk level legend
│   ├── copilot/
│   │   └── CopilotPanel.tsx        ← Right-side AI analysis panel
│   ├── auth/                       ← (planned) LoginForm, RegisterForm, AuthGuard
│   ├── education/                  ← (planned) ArticleCard, ArticleReader
│   └── chat/                       ← (planned) ChatWindow, BotMessage
│
├── lib/
│   ├── api.ts                      ← All API functions (single source of truth)
│   ├── auth.ts                     ← (planned) Login/register/refresh functions
│   ├── chat.ts                     ← (planned) Bot API functions
│   ├── education.ts                ← (planned) Article fetch functions
│   ├── useAuth.ts                  ← (planned) Zustand auth store
│   ├── useModelStatus.ts           ← Fetches /model/status
│   ├── risk-colors.ts              ← Risk level → colour mapping
│   ├── grid-risk.ts                ← GridCell type + zone utilities
│   └── types.ts                    ← Shared TypeScript types
│
├── data/
│   ├── mock.ts                     ← Mock risk + event data (fallback)
│   ├── districts.json              ← Static district GeoJSON (local, fast)
│   └── pakistan-cities-weather.ts  ← City weather mock data
│
└── tests/
    ├── e2e/                        ← Playwright end-to-end tests
    └── *.test.tsx                  ← Vitest component tests
```

---

## Quick Reference — API Endpoints by Feature

| Feature                    | Method | Endpoint                        | Auth Required |
|----------------------------|--------|---------------------------------|---------------|
| Health check               | GET    | `/health`                       | No            |
| Zone grid (map)            | GET    | `/zones/geojson`                | No            |
| Zone cache status          | GET    | `/zones/status`                 | No            |
| Trigger recompute          | POST   | `/zones/compute`                | No            |
| Point prediction (live)    | GET    | `/predict`                      | No            |
| GeoJSON prediction         | GET    | `/risk/by-location`             | No            |
| Model status               | GET    | `/model/status`                 | No            |
| District search            | GET    | `/districts/search?q=`          | No            |
| District detail + zones    | GET    | `/districts/{id}`               | No            |
| All boundaries (legacy)    | GET    | `/admin-boundaries`             | No            |
| Location search (legacy)   | GET    | `/location/search?q=`           | No            |
| Flood events               | GET    | `/flood-events`                 | No            |
| Admin refresh zones        | POST   | `/zones/admin/refresh-zones`    | X-Api-Key     |
| Register                   | POST   | `/auth/register`                | No            |
| Login                      | POST   | `/auth/login`                   | No            |
| Refresh token              | POST   | `/auth/refresh`                 | No            |
| Logout                     | POST   | `/auth/logout`                  | Bearer token  |
| Get profile                | GET    | `/auth/me`                      | Bearer token  |
| Update profile             | PATCH  | `/auth/me`                      | Bearer token  |
| Delete account             | DELETE | `/auth/me`                      | Bearer token  |
| Forgot password            | POST   | `/auth/forgot-password`         | No            |
| Reset password             | POST   | `/auth/reset-password`          | No            |
| List articles              | GET    | `/education/articles`           | No            |
| Get article                | GET    | `/education/articles/{slug}`    | No            |
| Create article             | POST   | `/education/articles`           | Admin token   |
| Update article             | PATCH  | `/education/articles/{id}`      | Admin token   |
| Delete article             | DELETE | `/education/articles/{id}`      | Admin token   |
| Reading progress           | GET    | `/education/progress`           | Bearer token  |
| Mark article read          | POST   | `/education/progress/{id}`      | Bearer token  |
| Learning bot               | POST   | `/chat/learn`                   | Optional      |
| Learning sessions          | GET    | `/chat/learn/sessions`          | Bearer token  |
| Learning session detail    | GET    | `/chat/learn/sessions/{id}`     | Bearer token  |
| Delete learning session    | DELETE | `/chat/learn/sessions/{id}`     | Bearer token  |
| Help bot                   | POST   | `/chat/help`                    | Optional      |
| Help sessions              | GET    | `/chat/help/sessions`           | Bearer token  |
| Help session detail        | GET    | `/chat/help/sessions/{id}`      | Bearer token  |
| Delete help session        | DELETE | `/chat/help/sessions/{id}`      | Bearer token  |
