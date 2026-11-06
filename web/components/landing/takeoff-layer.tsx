"use client";

import { motion, useTransform } from "framer-motion";
import { progressIn, smoothstep } from "@/lib/utils";
import { planeProgressFromTimeline, TAKEOFF_TIMELINE } from "@/lib/motion/flight-path";
import { FlyingPlane } from "@/components/ui/hero-section-3";
import { useTakeoff } from "./takeoff-context";

/**
 * Fixed overlay that hosts the cinematic part of the takeoff:
 * airliner crossing → atmosphere darkening → Flight Intelligence HUD.
 * Mounted only once the sequence starts, so it costs nothing before.
 */
export function TakeoffLayer() {
  const { phase } = useTakeoff();
  if (phase === "idle") return null;
  return <TakeoffStage />;
}

function TakeoffStage() {
  const { timeline, reduced } = useTakeoff();
  const plane = useTransform(timeline, planeProgressFromTimeline);
  const dark = useTransform(timeline, (t) => smoothstep(...TAKEOFF_TIMELINE.darken, t));
  // The darkness rolls in from the top of the sky (higher altitude) first.
  const darkTop = useTransform(timeline, (t) => smoothstep(TAKEOFF_TIMELINE.darken[0] - 0.12, TAKEOFF_TIMELINE.darken[1] - 0.2, t));
  const hud = useTransform(timeline, (t) => smoothstep(...TAKEOFF_TIMELINE.hud, t));
  const hudY = useTransform(hud, (h) => `${(1 - h) * 14}px`);
  const bar = useTransform(timeline, (t) => progressIn(t, TAKEOFF_TIMELINE.hud[0], 1));
  const tracking = useTransform(hud, (h) => `${0.6 - h * 0.28}em`);

  return (
    <div className="fixed inset-0 z-[60] overflow-hidden" role="status" aria-live="polite">
      <span className="sr-only">Taking off. Opening the Flight Intelligence dashboard.</span>

      {!reduced && (
        <div className="absolute inset-0">
          <FlyingPlane progress={plane} mode="takeoff" motionTrail />
        </div>
      )}

      {/* Atmosphere: high-altitude blue first, then deep navy */}
      <motion.div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-b from-[#0d2347] via-[#0d2347]/70 to-transparent"
        style={{ opacity: darkTop }}
      />
      <motion.div aria-hidden className="absolute inset-0 bg-navy" style={{ opacity: dark }} />

      {/* Flight Intelligence HUD */}
      <motion.div aria-hidden className="absolute inset-0" style={{ opacity: hud }}>
        <div className="hud-grid absolute inset-0" />
        <motion.div className="absolute inset-0 flex flex-col items-center justify-center gap-6" style={{ y: hudY }}>
          <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.4em] text-cyan/80">
            <span className="size-1.5 animate-pulse rounded-full bg-cyan" />
            Establishing data link
          </div>
          <motion.p
            className="text-center text-[clamp(1.5rem,4.2vw,3.25rem)] font-semibold uppercase text-ink"
            style={{ letterSpacing: tracking }}
          >
            Flight Intelligence
          </motion.p>
          <div className="h-px w-[min(320px,60vw)] overflow-hidden bg-white/10">
            <motion.div className="h-full origin-left bg-gradient-to-r from-blue to-cyan" style={{ scaleX: bar }} />
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
