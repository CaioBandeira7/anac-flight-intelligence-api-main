"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { progressIn, smoothstep } from "@/lib/utils";
import { TAKEOFF_TIMELINE } from "@/lib/motion/flight-path";
import { SkyScene } from "./sky-scene";
import { GetStartedButton } from "./get-started-button";
import { useTakeoff } from "./takeoff-context";

const reveal = {
  hidden: { opacity: 0, y: 24, filter: "blur(8px)" },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { delay: 0.25 + i * 0.14, duration: 1.2, ease: [0.16, 1, 0.3, 1] as const },
  }),
};

export function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { timeline, start, phase } = useTakeoff();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });

  // Scroll: copy recedes gently as the camera rises through the deck.
  const scrollOpacity = useTransform(scrollYProgress, [0, 0.45], [1, 0]);
  const scrollScale = useTransform(scrollYProgress, [0, 0.5], [1, 0.94]);
  const scrollY = useTransform(scrollYProgress, [0, 0.5], ["0vh", "-6vh"]);
  // Takeoff: copy dissolves first.
  const takeoffOpacity = useTransform(timeline, (t) => 1 - smoothstep(...TAKEOFF_TIMELINE.text, t));
  const takeoffY = useTransform(timeline, (t) => `${-progressIn(t, ...TAKEOFF_TIMELINE.text) * 3}vh`);
  const cueOpacity = useTransform(scrollYProgress, [0, 0.12], [1, 0]);

  return (
    <section ref={ref} aria-labelledby="hero-title" className="relative h-[170vh]">
      <div className="sticky top-0 h-dvh overflow-hidden">
        <SkyScene scroll={scrollYProgress} />

        <motion.div
          className="relative z-10 flex h-full flex-col items-center justify-center px-6 pb-[14vh] text-center"
          style={{ opacity: scrollOpacity, scale: scrollScale, y: scrollY }}
        >
          <motion.div style={{ opacity: takeoffOpacity, y: takeoffY }} className="flex flex-col items-center">
            <motion.p
              variants={reveal}
              initial="hidden"
              animate="show"
              custom={0}
              className="mb-6 font-mono text-[11px] uppercase tracking-[0.42em] text-white/85 text-sky-shadow"
            >
              ANAC Flight Intelligence 2.0
            </motion.p>
            <motion.h1
              id="hero-title"
              variants={reveal}
              initial="hidden"
              animate="show"
              custom={1}
              className="text-sky-shadow text-balance text-[clamp(3.25rem,11vw,10.5rem)] font-semibold leading-[0.9] tracking-[-0.045em] text-white"
            >
              READY TO <span className="font-display font-normal italic tracking-[-0.02em]">fly?</span>
            </motion.h1>
            <motion.p
              variants={reveal}
              initial="hidden"
              animate="show"
              custom={2}
              className="text-sky-shadow mt-7 max-w-xl text-pretty text-[clamp(1.05rem,1.6vw,1.35rem)] font-normal text-white/90"
            >
              Discover the intelligence behind every flight.
            </motion.p>
            <motion.div variants={reveal} initial="hidden" animate="show" custom={3} className="mt-11">
              <GetStartedButton onLaunch={start} disabled={phase !== "idle"} />
              <p id="launch-hint" className="sr-only">
                Starts a short takeoff animation, then opens the Flight Intelligence dashboard.
              </p>
            </motion.div>
          </motion.div>
        </motion.div>

        <motion.div
          aria-hidden
          style={{ opacity: cueOpacity }}
          className="absolute inset-x-0 bottom-7 z-10 flex flex-col items-center gap-2 text-[10px] uppercase tracking-[0.35em] text-[#0b1f3f]/55"
        >
          <span>Scroll to explore</span>
          <span className="relative h-9 w-px overflow-hidden bg-[#0b1f3f]/15">
            <motion.span
              className="absolute inset-x-0 top-0 h-3 bg-[#0b1f3f]/60"
              animate={{ y: [-12, 36] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: [0.65, 0, 0.35, 1] }}
            />
          </span>
        </motion.div>
      </div>
    </section>
  );
}
