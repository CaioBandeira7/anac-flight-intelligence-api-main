"use client";

import { motion, useMotionValue, useReducedMotion, useScroll, useTransform, type MotionValue } from "framer-motion";
import { useCallback, useLayoutEffect, useMemo, useRef, useState, useEffect } from "react";
import Image from "next/image";
import { BarChart3, BrainCircuit, Database, Plane, Route, TowerControl } from "lucide-react";
import { ScrollFlyIn } from "@/components/ui/hero-section-3";
import { seeded } from "@/lib/data/mock-provider";
import { RouteNetwork } from "./route-network";
import LunarBoardingPass from "@/components/ui/lunar-boarding-pass";
import { ticketCondensed, ticketDisplay, ticketMono } from "./ticket-fonts";
import { useTakeoff } from "./takeoff-context";

const USING_REAL_DATA = process.env.NEXT_PUBLIC_DATA_SOURCE?.toLowerCase() === "api";

const useIsoLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

function Eyebrow({ index, children }: { index: string; children: React.ReactNode }) {
  return (
    <p className="mb-5 flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.36em] text-white/70">
      <span className="text-white/45">{index}</span>
      <span className="h-px w-8 bg-white/35" />
      {children}
    </p>
  );
}

const fadeUp = {
  initial: { opacity: 0, y: 32 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.5 },
  transition: { duration: 1.1, ease: [0.16, 1, 0.3, 1] as const },
};

/* ───────────────────────── 01 · Discover the skies ───────────────────────── */

export function DiscoverSkies() {
  return (
    <section aria-labelledby="discover-title">
      <ScrollFlyIn className="h-[200vh]" imageAlt="">
        <div className="mx-auto grid text-left w-full max-w-6xl items-center gap-10 px-6 md:grid-cols-[1.05fr_1fr] md:gap-16">
          <motion.div {...fadeUp}>
            <Eyebrow index="01">Discover the skies</Eyebrow>
            <h2
              id="discover-title"
              className="text-sky-shadow text-balance text-[clamp(2.4rem,5.6vw,4.75rem)] font-semibold leading-[0.98] tracking-[-0.035em] text-white"
            >
              Every flight <span className="font-display font-normal italic">leaves a trace.</span>
            </h2>
            <p className="text-sky-shadow mt-6 max-w-md text-pretty text-lg leading-relaxed text-white/85">
              Two decades of Brazilian air transport records — airports, routes, airlines and seats — reorganised into
              a single, navigable picture of the national network.
            </p>
          </motion.div>
          <RouteNetwork />
        </div>
      </ScrollFlyIn>
    </section>
  );
}

/* ───────────────────────── 02 · Intelligence in motion ───────────────────────── */

const IMG = "/images/flight-intelligence-five-images/flight-intelligence-assets/";

// The photos (1200×900) carry a low-res icon badge baked into their top strip.
// Cards are 5:3 with the photo anchored to the bottom, which hides exactly that
// strip (the top 180 px); the icon and number are drawn on top as crisp vectors.
const MODULES = [
  { icon: TowerControl, title: "Airports Intelligence", body: "Movements, seasonality and capacity pressure for every aerodrome in the network.", image: IMG + "01-airports-intelligence.webp", alt: "Control tower and terminal at dusk" },
  { icon: Route, title: "Routes Explorer", body: "Origin–destination flows, competition and load factor along each corridor.", image: IMG + "02-routes-explorer.webp", alt: "Airliner wing above the clouds at sunset" },
  { icon: Plane, title: "Airlines Analytics", body: "Market share, fleet deployment and punctuality, carrier by carrier.", image: IMG + "03-airlines-analytics.webp", alt: "Tail fin of a commercial jet" },
  { icon: BrainCircuit, title: "ML Studio", body: "Demand and occupancy models, with their evaluation on held-out data.", image: IMG + "04-ml-studio.webp", alt: "Glowing neural-network surface" },
  { icon: Database, title: "Data & Methodology", body: "Sources, ingestion pipeline, feature engineering and model cards, documented.", image: IMG + "05-data-methodology.webp", alt: "Analytics dashboard with charts and a map of Brazil" },
];

export function IntelligenceInMotion() {
  const ref = useRef<HTMLElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const [distance, setDistance] = useState(0);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });

  useIsoLayoutEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    const measure = () => setDistance(Math.max(0, track.scrollWidth - document.documentElement.clientWidth));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(track);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  const x = useTransform(scrollYProgress, [0.08, 0.92], [0, -distance]);
  const progress = useTransform(scrollYProgress, [0.08, 0.92], [0, 1]);
  const headOpacity = useTransform(scrollYProgress, [0, 0.12, 0.85, 1], [0, 1, 1, 0.4]);

  return (
    <section ref={ref} aria-labelledby="motion-title" className="relative h-[320vh]">
      <div className="sticky top-0 flex h-dvh flex-col justify-center overflow-hidden">
        <motion.div style={{ opacity: headOpacity }} className="mx-auto mb-12 w-full max-w-6xl px-6">
          <Eyebrow index="02">Intelligence in motion</Eyebrow>
          <h2
            id="motion-title"
            className="text-sky-shadow max-w-3xl text-balance text-[clamp(2.2rem,5vw,4.25rem)] font-semibold leading-[1] tracking-[-0.035em] text-white"
          >
            Five instruments. <span className="font-display font-normal italic">One cockpit.</span>
          </h2>
        </motion.div>
        <motion.div
          ref={trackRef}
          style={{ x }}
          className="flex w-max gap-5 pl-[max(1.5rem,calc((100vw-72rem)/2+1.5rem))] pr-[10vw] will-change-transform"
        >
          {MODULES.map((m, i) => (
            <article
              key={m.title}
              className="group relative aspect-[5/3] w-[min(86vw,600px)] shrink-0 overflow-hidden rounded-[28px] border border-white/25 bg-[#0b1a33] shadow-[0_30px_80px_-30px_rgba(5,15,35,0.7)] sm:w-[min(72vw,600px)]"
            >
              <Image
                src={m.image}
                alt={m.alt}
                fill
                sizes="(max-width: 640px) 86vw, 600px"
                className="origin-bottom object-cover object-bottom transition-transform duration-[1200ms] ease-[var(--ease-out-expo)] group-hover:scale-[1.045] motion-reduce:transition-none"
                priority={i < 2}
              />
              {/* Legibility: soft top shade for the badge, dark wash rising from the bottom */}
              <div aria-hidden className="absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-[#050b17]/55 to-transparent" />
              <div
                aria-hidden
                className="absolute inset-0 bg-gradient-to-t from-[#050b17]/95 via-[#050b17]/45 via-45% to-transparent to-75%"
              />
              <div className="absolute inset-x-0 top-0 flex items-start justify-between p-5 sm:p-6">
                <span className="grid size-12 place-items-center rounded-2xl border border-white/20 bg-white/10 text-white shadow-[0_8px_24px_-8px_rgba(0,0,0,0.5)] backdrop-blur-md">
                  <m.icon className="size-6" strokeWidth={1.5} aria-hidden />
                </span>
                <span className="font-mono text-sm tracking-[0.12em] text-white/85">{String(i + 1).padStart(2, "0")}</span>
              </div>
              <div className="absolute inset-x-0 bottom-0 p-6 sm:p-7">
                <h3 className="text-[clamp(1.3rem,2.2vw,1.65rem)] font-semibold tracking-[-0.02em] text-white">{m.title}</h3>
                <p className="mt-2 max-w-[42ch] text-[14.5px] leading-relaxed text-white/85">{m.body}</p>
              </div>
            </article>
          ))}
        </motion.div>
        {/* Navigation cue: the track is scroll-driven, so show how far along it is */}
        <div className="mx-auto mt-8 flex w-full max-w-6xl items-center gap-4 px-6" aria-hidden>
          <div className="h-px flex-1 overflow-hidden bg-white/20">
            <motion.div className="h-full origin-left bg-white/80" style={{ scaleX: progress }} />
          </div>
          <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-white/60">Scroll · 05 modules</span>
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────── 03 · From data to decisions ───────────────────────── */

const DOTS = 64;

function useDots() {
  return useMemo(() => {
    const r = seeded(91);
    return Array.from({ length: DOTS }, (_, i) => {
      const t = i / (DOTS - 1);
      // Illustrative signal: a smooth seasonal curve (shape only, no real values).
      const line = 0.55 - 0.22 * Math.sin(t * Math.PI * 2.1 + 0.4) - t * 0.18;
      return {
        sx: r(), // scattered (raw records)
        sy: r(),
        gx: (i % 8) / 7, // grid (structured)
        gy: Math.floor(i / 8) / 7,
        lx: t, // line (decision-ready signal)
        ly: line,
      };
    });
  }, []);
}

const STAGES = ["Raw records", "Structured signals", "Decisions"];

export function DataToDecisions() {
  const ref = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  const dots = useDots();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const stage = useTransform(scrollYProgress, [0.1, 0.45, 0.8], [0, 1, 2]);
  const axis = useTransform(scrollYProgress, [0.7, 0.85], [0, 1]);
  const lineOpacity = useTransform(scrollYProgress, [0.74, 0.9], [0, 1]);
  // Reduced motion: show the final, decision-ready state without travel.
  const settled = useMotionValue(2);
  const dotStage = reduce ? settled : stage;

  return (
    <section ref={ref} aria-labelledby="decisions-title" className="relative h-[300vh]">
      <div className="sticky top-0 flex h-dvh items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-10 px-6 md:grid-cols-[1fr_1.15fr] md:gap-16">
          <div>
            <Eyebrow index="03">From data to decisions</Eyebrow>
            <h2
              id="decisions-title"
              className="text-balance text-[clamp(2.2rem,5vw,4.25rem)] font-semibold leading-[1] tracking-[-0.035em] text-white"
            >
              Millions of rows. <span className="font-display font-normal italic">One clear signal.</span>
            </h2>
            <ol className="mt-10 space-y-4">
              {STAGES.map((s, i) => (
                <StageRow key={s} index={i} label={s} stage={stage} />
              ))}
            </ol>
          </div>

          <div className="relative aspect-[4/3] w-full rounded-[28px] border border-white/10 bg-[#0b1a33]/50 p-6 backdrop-blur-md">
            <svg viewBox="0 0 400 300" className="h-full w-full overflow-visible" aria-hidden>
              <motion.g style={{ opacity: axis }} stroke="rgba(255,255,255,0.18)" strokeWidth={1}>
                <line x1={0} y1={300} x2={400} y2={300} />
                <line x1={0} y1={0} x2={0} y2={300} />
                {[75, 150, 225].map((y) => (
                  <line key={y} x1={0} y1={y} x2={400} y2={y} strokeDasharray="2 6" />
                ))}
              </motion.g>
              <motion.path
                style={{ opacity: lineOpacity }}
                d={dots.map((d, i) => `${i ? "L" : "M"}${d.lx * 400} ${d.ly * 300}`).join(" ")}
                fill="none"
                stroke="url(#sig)"
                strokeWidth={2}
              />
              <defs>
                <linearGradient id="sig" x1="0" x2="1">
                  <stop offset="0" stopColor="#3b82f6" />
                  <stop offset="1" stopColor="#22d3ee" />
                </linearGradient>
              </defs>
              {dots.map((d, i) => (
                <Dot key={i} d={d} stage={dotStage} />
              ))}
            </svg>
            <p className="absolute bottom-4 right-6 font-mono text-[10px] uppercase tracking-[0.3em] text-white/40">
              Illustrative
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function StageRow({ index, label, stage }: { index: number; label: string; stage: MotionValue<number> }) {
  const opacity = useTransform(stage, [index - 0.6, index, index + 0.6], [0.35, 1, index === 2 ? 1 : 0.35]);
  const width = useTransform(stage, [index - 0.6, index], [0.15, 1]);
  return (
    <motion.li style={{ opacity }} className="flex items-center gap-4 text-lg text-white">
      <span className="font-mono text-xs text-white/60">0{index + 1}</span>
      <span className="relative h-px w-10 overflow-hidden bg-white/20">
        <motion.span className="absolute inset-0 origin-left bg-cyan" style={{ scaleX: width }} />
      </span>
      {label}
    </motion.li>
  );
}

type DotDef = ReturnType<typeof useDots>[number];

function Dot({ d, stage: src }: { d: DotDef; stage: MotionValue<number> }) {
  const x = useTransform(src, [0, 1, 2], [d.sx * 400, 40 + d.gx * 320, d.lx * 400]);
  const y = useTransform(src, [0, 1, 2], [d.sy * 300, 30 + d.gy * 240, d.ly * 300]);
  const r = useTransform(src, [0, 1, 2], [2.2, 3, 2.6]);
  const fill = useTransform(src, [0, 1, 2], ["rgba(255,255,255,0.55)", "rgba(165,243,252,0.85)", "#22d3ee"]);
  return <motion.circle cx={0} cy={0} style={{ x, y, fill }} r={r} />;
}

/* ───────────────────────── 04 · Explore the platform: boarding pass ───────────────────────── */

const TEAR_HOLD_MS = 1150; // stub falls away + BOARDED stamp lands before the takeoff starts
const TEAR_HOLD_REDUCED_MS = 300;

export function ExplorePlatform() {
  const { start, phase, reduced } = useTakeoff();
  const boarded = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  // The torn stub is the way in: let the tear and the stamp play, then run the
  // same takeoff the "Enter Flight Intelligence" button used (→ /dashboard).
  const onTear = useCallback(
    (torn: boolean) => {
      if (!torn || boarded.current || phase !== "idle") return;
      boarded.current = true;
      timer.current = setTimeout(start, reduced ? TEAR_HOLD_REDUCED_MS : TEAR_HOLD_MS);
    },
    [phase, reduced, start],
  );

  return (
    <section aria-labelledby="explore-title" className="relative flex min-h-dvh items-center justify-center px-4 py-28 sm:px-6">
      <motion.div {...fadeUp} className="flex w-full max-w-5xl flex-col items-center text-center">
        <Eyebrow index="04">Explore the platform</Eyebrow>
        <h2 id="explore-title" className="sr-only">
          Your boarding pass to Flight Intelligence
        </h2>
        <p className="mb-10 max-w-lg text-pretty text-base text-white/75">
          Tear off the stub to board. {USING_REAL_DATA ? "ANAC flight records from 2000 to 2025 are waiting inside." : "This build runs on demonstration data, labelled as such on every screen."}
        </p>
        <div className={`w-full text-white ${ticketCondensed.variable} ${ticketMono.variable} ${ticketDisplay.variable}`}>
          <LunarBoardingPass
            defaultSide="back"
            title="Board your next discovery"
            tier="Explorer"
            date="06 Nov '26"
            welcome={"Welcome\naboard"}
            eyebrow={"Your journey into\naviation intelligence"}
            words={["Flight", "Intelligence"]}
            notes={["Explorer pass · Intelligence access", "Intro → Flight Intelligence"]}
            passenger="Explorer"
            from="Intro"
            to="Flight Intelligence"
            craftLabel="Pass number"
            craft="FI-3.0-EXP"
            dateCode="06NOV26"
            gate="FI"
            group="A"
            seat="01A"
            boardingTime="NOW"
            siteLabel="Class"
            site="Intelligence access"
            lat={-15.7939}
            lon={-47.8828}
            seq="SEQ 030 ANACFI  261106BSB"
            featuring="Flight Intelligence · Explorer pass"
            headline="Explorer"
            stamp="Boarded"
            sideLabels={["Explorer pass", "Boarding pass"]}
            night="#0b1426"
            starInk="#eef3fb"
            paper="#d6dce6"
            paperInk="#13213a"
            stampColor="#2b5ea6"
            fontCondensed={`var(--font-ticket-condensed), "Oswald", "Arial Narrow", sans-serif`}
            fontMono={`var(--font-ticket-mono), "Courier Prime", "Courier New", monospace`}
            fontDisplay={`var(--font-ticket-display), "Futura", "Century Gothic", sans-serif`}
            lockTorn
            detach
            onTear={onTear}
          />
        </div>
        <p className="mt-12 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.3em] text-white/45">
          <BarChart3 className="size-3.5" aria-hidden /> Data: {USING_REAL_DATA ? "ANAC open data" : "DEMO"} · Visuals on this page: illustrative
        </p>
      </motion.div>
    </section>
  );
}
