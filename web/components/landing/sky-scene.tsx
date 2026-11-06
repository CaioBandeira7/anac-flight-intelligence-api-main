"use client";

import { motion, useTransform, type MotionValue } from "framer-motion";
import type { CSSProperties } from "react";
import { easeInCubic, progressIn } from "@/lib/utils";
import { TAKEOFF_TIMELINE } from "@/lib/motion/flight-path";
import { useTakeoff } from "./takeoff-context";

/**
 * Layered, volumetric-looking cloud deck. Each layer:
 *  - drifts with a CSS keyframe (compositor only, no JS loop),
 *  - moves with scroll at its own depth (parallax),
 *  - accelerates and drops during takeoff (camera climbing).
 */
interface Layer {
  src: string;
  ratio: number; // tile width / height
  height: string; // CSS length
  bottom: string;
  speed: string; // drift duration
  depth: number; // 0 far → 1 near
  opacity?: number;
}

const LAYERS: Layer[] = [
  { src: "/images/sky/clouds-far.webp", ratio: 2400 / 420, height: "30vh", bottom: "21vh", speed: "260s", depth: 0.2, opacity: 0.95 },
  { src: "/images/sky/clouds-mid.webp", ratio: 2400 / 640, height: "44vh", bottom: "8vh", speed: "170s", depth: 0.5 },
  { src: "/images/sky/clouds-near.webp", ratio: 2400 / 760, height: "52vh", bottom: "-14vh", speed: "110s", depth: 1 },
];

export function SkyScene({ scroll }: { scroll: MotionValue<number> }) {
  const { timeline } = useTakeoff();

  // Camera push during takeoff
  const sceneScale = useTransform(timeline, (t) => 1 + 0.07 * easeInCubic(progressIn(t, ...TAKEOFF_TIMELINE.clouds)));
  // The deck dissolves as the hero scrolls away — no hard edge between scenes.
  const sceneOpacity = useTransform(scroll, [0.35, 0.8], [1, 0]);

  return (
    <motion.div aria-hidden className="absolute inset-0 overflow-hidden" style={{ scale: sceneScale, opacity: sceneOpacity }}>
      {/* Sun */}
      <div className="sun-glow absolute -right-[12vw] -top-[22vh] h-[90vh] w-[90vh] opacity-90" />
      <div className="absolute inset-x-0 bottom-0 h-[55vh] bg-gradient-to-t from-white/45 via-white/10 to-transparent" />

      {/* High wisps */}
      <CloudLayer
        layer={{ src: "/images/sky/clouds-wisp.webp", ratio: 2400 / 520, height: "34vh", bottom: "58vh", speed: "320s", depth: 0.1, opacity: 0.75 }}
        scroll={scroll}
        timeline={timeline}
      />
      {LAYERS.map((l) => (
        <CloudLayer key={l.src} layer={l} scroll={scroll} timeline={timeline} />
      ))}
    </motion.div>
  );
}

function CloudLayer({ layer, scroll, timeline }: { layer: Layer; scroll: MotionValue<number>; timeline: MotionValue<number> }) {
  // Parallax on scroll: near layers rise faster as the hero scrolls away.
  const scrollY = useTransform(scroll, [0, 1], ["0vh", `${-12 - layer.depth * 38}vh`]);
  // Takeoff: clouds rush past (left) and fall away (down) — strongest up close.
  const tx = useTransform(timeline, (t) => {
    const k = easeInCubic(progressIn(t, ...TAKEOFF_TIMELINE.clouds));
    return `${-k * (25 + layer.depth * 70)}vw`;
  });
  const ty = useTransform(timeline, (t) => {
    const k = easeInCubic(progressIn(t, ...TAKEOFF_TIMELINE.clouds));
    return `${k * (10 + layer.depth * 45)}vh`;
  });

  const style = {
    "--cloud-h": layer.height,
    "--cloud-ratio": layer.ratio,
    "--cloud-src": `url(${layer.src})`,
    "--cloud-speed": layer.speed,
    opacity: layer.opacity ?? 1,
  } as CSSProperties;

  return (
    <motion.div className="absolute inset-x-0" style={{ bottom: layer.bottom, height: layer.height, y: scrollY }}>
      <motion.div className="absolute inset-0" style={{ x: tx, y: ty }}>
        <div className="cloud-strip" style={style} />
      </motion.div>
    </motion.div>
  );
}
