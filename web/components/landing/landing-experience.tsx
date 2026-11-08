"use client";

import Link from "next/link";
import { motion, useScroll, useTransform } from "framer-motion";
import { LogoMark } from "@/components/logo-mark";
import { TakeoffProvider, DASHBOARD_HREF } from "./takeoff-context";
import { TakeoffLayer } from "./takeoff-layer";
import { Hero } from "./hero";
import { DataToDecisions, DiscoverSkies, ExplorePlatform, IntelligenceInMotion } from "./story";

/**
 * One continuous landing: a single fixed atmosphere behind every section.
 * As you scroll, the camera climbs — the sky deepens from daylight blue
 * toward high-altitude navy, so there are no hard section boundaries.
 */
export function LandingExperience() {
  return (
    <TakeoffProvider>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[80] focus:rounded-full focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:text-navy"
      >
        Skip to content
      </a>
      <Atmosphere />
      <TopBar />
      <main id="main" className="relative">
        <Hero />
        <DiscoverSkies />
        <IntelligenceInMotion />
        <DataToDecisions />
        <ExplorePlatform />
      </main>
      <TakeoffLayer />
    </TakeoffProvider>
  );
}

function Atmosphere() {
  const { scrollYProgress } = useScroll();
  // Opacity-only layers (compositor friendly) stacked over the daylight sky.
  const altitude = useTransform(scrollYProgress, [0.08, 0.55], [0, 1]);
  const stratosphere = useTransform(scrollYProgress, [0.5, 0.97], [0, 1]);
  const wispY = useTransform(scrollYProgress, [0, 1], ["0vh", "-60vh"]);
  const wispOpacity = useTransform(scrollYProgress, [0, 0.12, 0.45, 0.7], [0, 0.4, 0.3, 0]);

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10">
      <div className="absolute inset-0 bg-[linear-gradient(180deg,var(--sky-zenith)_0%,#4b8fd9_38%,var(--sky-mid)_62%,var(--sky-horizon)_100%)]" />
      <motion.div
        className="absolute inset-0 bg-[linear-gradient(180deg,#123a73_0%,#1f5aa6_45%,#5a93cf_100%)]"
        style={{ opacity: altitude }}
      />
      <motion.div
        className="absolute inset-0 bg-[linear-gradient(180deg,#060b17_0%,#0b1c3a_50%,#16376a_100%)]"
        style={{ opacity: stratosphere }}
      />
      <motion.div
        className="absolute inset-x-0 top-[70vh] h-[34vh]"
        style={{
          y: wispY,
          opacity: wispOpacity,
          backgroundImage: "url(/images/sky/clouds-wisp.webp)",
          backgroundSize: "auto 100%",
          backgroundRepeat: "repeat-x",
        }}
      />
    </div>
  );
}

function TopBar() {
  return (
    <header className="fixed inset-x-0 top-0 z-50">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 md:px-8">
        <Link href="/" className="flex items-center gap-2.5 text-white" aria-label="ANAC Flight Intelligence home">
          <LogoMark />
          <span className="text-[13px] font-semibold tracking-[0.02em] text-sky-shadow">
            Flight Intelligence <span className="font-normal text-white/70">2.0</span>
          </span>
        </Link>
        <Link
          href={DASHBOARD_HREF}
          className="rounded-full border border-white/30 bg-white/10 px-4 py-1.5 text-[13px] text-white backdrop-blur-md transition-colors hover:bg-white/20"
        >
          Skip intro
        </Link>
      </div>
    </header>
  );
}
