"use client";

import { useEffect, useState } from "react";
import { fetchModelStatus, type ModelStatus } from "./api";

/**
 * Subscribes once to /api/v1/model/status. Returns null while loading or when
 * the backend is unreachable — UI must default to the unavailable message in
 * that case (never fake "Real prediction v3").
 */
export function useModelStatus(): ModelStatus | null {
  const [status, setStatus] = useState<ModelStatus | null>(null);
  useEffect(() => {
    let alive = true;
    fetchModelStatus().then((s) => {
      if (alive) setStatus(s);
    });
    return () => {
      alive = false;
    };
  }, []);
  return status;
}
