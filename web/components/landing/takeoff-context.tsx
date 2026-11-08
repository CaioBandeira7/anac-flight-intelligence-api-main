"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { animate, useMotionValue, useReducedMotion, type MotionValue } from "framer-motion";
import { ARRIVAL_KEY, DASHBOARD_HREF, TAKEOFF_TIMELINE } from "@/lib/motion/flight-path";

export { ARRIVAL_KEY, DASHBOARD_HREF };

export type TakeoffPhase = "idle" | "takeoff" | "arrived";

interface TakeoffCtx {
  phase: TakeoffPhase;
  /** Global 0→1 timeline. Every layer derives its state from it. */
  timeline: MotionValue<number>;
  reduced: boolean;
  start: () => void;
}

const Ctx = createContext<TakeoffCtx | null>(null);


export function TakeoffProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const reduced = Boolean(useReducedMotion());
  const timeline = useMotionValue(0);
  const [phase, setPhase] = useState<TakeoffPhase>("idle");
  const running = useRef(false);

  useEffect(() => {
    router.prefetch(DASHBOARD_HREF);
  }, [router]);

  // Lock scroll during the sequence; always restored on unmount.
  useEffect(() => {
    if (phase === "idle") return;
    const root = document.documentElement;
    const prev = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      root.style.overflow = prev;
    };
  }, [phase]);

  const start = useCallback(() => {
    if (running.current) return;
    running.current = true;
    setPhase("takeoff");
    const duration = (reduced ? TAKEOFF_TIMELINE.reducedDurationMs : TAKEOFF_TIMELINE.durationMs) / 1000;
    animate(timeline, 1, {
      duration,
      ease: "linear",
      onComplete: () => {
        try {
          sessionStorage.setItem(ARRIVAL_KEY, "takeoff");
        } catch {
          /* storage unavailable — dashboard falls back to its default entrance */
        }
        setPhase("arrived");
        router.push(DASHBOARD_HREF);
      },
    });
  }, [reduced, router, timeline]);

  const value = useMemo(() => ({ phase, timeline, reduced, start }), [phase, timeline, reduced, start]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTakeoff() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTakeoff must be used inside <TakeoffProvider>");
  return ctx;
}
