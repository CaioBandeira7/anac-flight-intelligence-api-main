"use client";

import { useCallback, useEffect, useState } from "react";
import type { Envelope, ResponseMeta } from "@/lib/data/contracts";

export type Resource<T> =
  | { status: "loading"; data?: undefined; meta?: undefined; error?: undefined }
  | { status: "success"; data: T; meta: ResponseMeta; error?: undefined }
  | { status: "error"; error: Error; data?: undefined; meta?: undefined };

type Loader<T> = (signal: AbortSignal) => Promise<Envelope<T>>;

/**
 * Minimal async-resource hook with loading / error / retry.
 * `load` must be stable (wrap in useCallback): a new `load`, e.g. after a filter
 * changes, cancels the previous request and never shows its result.
 */
export function useResource<T>(load: Loader<T>): Resource<T> & { retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{ load: Loader<T> | null; attempt: number; value: Resource<T> }>({
    load: null,
    attempt: -1,
    value: { status: "loading" },
  });

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).then(
      (res) => {
        if (!controller.signal.aborted) setState({ load, attempt, value: { status: "success", data: res.data, meta: res.meta } });
      },
      (err: unknown) => {
        if (controller.signal.aborted) return;
        setState({ load, attempt, value: { status: "error", error: err instanceof Error ? err : new Error(String(err)) } });
      },
    );
    return () => controller.abort();
  }, [load, attempt]);

  const retry = useCallback(() => setAttempt((a) => a + 1), []);
  // Until the result for the current loader and attempt arrives, show loading, never stale data.
  const value: Resource<T> = state.attempt === attempt && state.load === load ? state.value : { status: "loading" };
  return { ...value, retry };
}
