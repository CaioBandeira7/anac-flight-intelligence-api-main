"use client";

import { useCallback, useEffect, useState } from "react";
import type { Envelope, ResponseMeta } from "@/lib/data/contracts";

export type Resource<T> =
  | { status: "loading"; data?: undefined; meta?: undefined; error?: undefined }
  | { status: "success"; data: T; meta: ResponseMeta; error?: undefined }
  | { status: "error"; error: Error; data?: undefined; meta?: undefined };

/**
 * Minimal async-resource hook with loading / error / retry.
 * `load` must be stable (wrap in useCallback or pass a provider method bound once).
 */
export function useResource<T>(load: () => Promise<Envelope<T>>): Resource<T> & { retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{ attempt: number; value: Resource<T> }>({
    attempt: -1,
    value: { status: "loading" },
  });

  useEffect(() => {
    let alive = true;
    load().then(
      (res) => alive && setState({ attempt, value: { status: "success", data: res.data, meta: res.meta } }),
      (err: unknown) =>
        alive &&
        setState({ attempt, value: { status: "error", error: err instanceof Error ? err : new Error(String(err)) } }),
    );
    return () => {
      alive = false;
    };
  }, [load, attempt]);

  const retry = useCallback(() => setAttempt((a) => a + 1), []);
  // A pending retry shows loading until its own result arrives.
  const value: Resource<T> = state.attempt === attempt ? state.value : { status: "loading" };
  return { ...value, retry };
}
