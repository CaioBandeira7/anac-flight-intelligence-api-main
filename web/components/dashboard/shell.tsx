"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, LifeBuoy, Menu, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { LogoMark } from "@/components/logo-mark";
import { ARRIVAL_KEY } from "@/lib/motion/flight-path";
import { useDataProvider } from "@/components/data-provider";
import { NAV } from "./nav";
import { DemoBadge } from "./ui";
import { SkyBackground } from "./sky-background";
import { ThemeToggle } from "./theme-toggle";
import { AnalystProvider, FloatingAnalyst } from "./analyst";
import { OVERLAY_ID } from "./overlay";
import type { NavItem } from "./nav";

export function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const reduce = useReducedMotion();

  // Close the mobile drawer on navigation / Escape.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const enter = (i: number) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 14 },
          animate: { opacity: 1, y: 0 },
          transition: { delay: 0.55 + i * 0.08, duration: 0.8, ease: [0.16, 1, 0.3, 1] as const },
        };

  return (
    <AnalystProvider>
    <div className="app-theme relative min-h-dvh bg-navy text-ink">
      <SkyBackground />
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[80] focus:rounded-lg focus:bg-ink focus:px-4 focus:py-2 focus:text-sm focus:text-navy"
      >
        Skip to content
      </a>
      <BootOverlay />

      {/* Desktop sidebar */}
      <motion.aside
        {...(reduce ? {} : { initial: { opacity: 0, x: -16 }, animate: { opacity: 1, x: 0 }, transition: { delay: 0.45, duration: 0.8, ease: [0.16, 1, 0.3, 1] } })}
        className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-line bg-glass-strong backdrop-blur-2xl lg:flex"
      >
        <SidebarContent pathname={pathname} />
      </motion.aside>

      {/* Mobile top bar */}
      <div className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-glass-strong px-4 backdrop-blur-2xl lg:hidden">
        <Brand />
        <ThemeToggle className="ml-auto mr-2" />
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open navigation"
          aria-expanded={open}
          aria-controls="mobile-nav"
          className="grid size-10 place-items-center rounded-lg text-ink-2 hover:bg-hover"
        >
          <Menu className="size-5" />
        </button>
      </div>
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/60 lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
            />
            <motion.aside
              id="mobile-nav"
              role="dialog"
              aria-modal="true"
              aria-label="Navigation"
              className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-line bg-surface lg:hidden"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 380, damping: 38 }}
            >
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close navigation"
                className="absolute right-3 top-3 grid size-9 place-items-center rounded-lg text-ink-2 hover:bg-hover"
              >
                <X className="size-5" />
              </button>
              <SidebarContent pathname={pathname} onNavigate={() => setOpen(false)} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Above the fixed sky (z-0): text outside cards would otherwise be painted under the sky's veil. */}
      <div className="relative z-10 min-w-0 lg:pl-64">
        <motion.header
          {...enter(0)}
          className="sticky top-0 z-20 hidden h-14 items-center justify-between border-b border-line bg-glass px-8 backdrop-blur-2xl lg:flex"
        >
          <Breadcrumb pathname={pathname} />
          <div className="flex items-center gap-4">
            <SourceIndicator />
            <ThemeToggle />
          </div>
        </motion.header>
        <motion.main id="content" {...enter(1)} className="mx-auto w-full max-w-[1400px] px-4 pb-28 pt-8 sm:px-6 lg:px-8 lg:pt-10">
          {children}
        </motion.main>
      </div>
      <FloatingAnalyst />
      {/* Popovers render here: inside the theme, outside every glass card. */}
      <div id={OVERLAY_ID} />
    </div>
    </AnalystProvider>
  );
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5 text-ink" aria-label="Back to the ANAC Flight Intelligence landing page">
      <span className="text-cyan">
        <LogoMark />
      </span>
      <span className="text-[13px] font-semibold tracking-[0.01em]">
        Flight Intelligence <span className="font-normal text-muted">2.0</span>
      </span>
    </Link>
  );
}

function SidebarContent({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <>
      <div className="flex h-14 items-center px-5">
        <Brand />
      </div>
      <nav aria-label="Modules" className="scrollbar-thin flex-1 overflow-y-auto px-3 py-4">
        <p className="px-3 pb-2 font-mono text-[10px] uppercase tracking-[0.28em] text-muted/70">Modules</p>
        <ul className="space-y-0.5">
          {NAV.filter((item) => item.group === "main").map((item) => (
            <NavLink key={item.href} item={item} active={pathname === item.href} onNavigate={onNavigate} />
          ))}
        </ul>
      </nav>
      <SupportSection pathname={pathname} onNavigate={onNavigate} />
      <div className="m-3 rounded-xl border border-line bg-glass p-4">
        <SourceCard />
      </div>
    </>
  );
}

function NavLink({ item, active, onNavigate, small }: { item: NavItem; active: boolean; onNavigate?: () => void; small?: boolean }) {
  return (
    <li>
      <Link
        href={item.href}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        className={cn(
          "group relative flex items-center gap-3 rounded-lg px-3 transition-colors",
          small ? "py-1.5 text-[13px]" : "py-2 text-[13.5px]",
          active ? "bg-blue/12 text-ink" : "text-ink-2/80 hover:bg-hover hover:text-ink",
        )}
      >
        {active && (
          <motion.span layoutId="nav-active" className="absolute inset-y-1.5 left-0 w-[3px] rounded-full bg-gradient-to-b from-blue to-cyan" />
        )}
        <item.icon className={cn("size-4", active ? "text-cyan" : "text-muted group-hover:text-ink-2")} strokeWidth={1.75} />
        {item.label}
        {item.planned && <span className="ml-auto text-[10px] text-muted/60">soon</span>}
      </Link>
    </li>
  );
}

/** Secondary pages, at the bottom of the menu. Open by itself when one of them is current. */
function SupportSection({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  const items = NAV.filter((item) => item.group === "support");
  const current = items.some((item) => item.href === pathname);
  const [open, setOpen] = useState(current);
  const expanded = open || current;
  return (
    <div className="px-3 pb-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={expanded}
        aria-controls="support-nav"
        className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-[13px] text-ink-2/80 transition-colors hover:bg-hover hover:text-ink"
      >
        <LifeBuoy className="size-4 text-muted" strokeWidth={1.75} aria-hidden />
        Support &amp; methodology
        <ChevronDown className={cn("ml-auto size-4 text-muted transition-transform", expanded && "rotate-180")} aria-hidden />
      </button>
      {expanded && (
        <ul id="support-nav" className="mt-0.5 space-y-0.5 pl-3">
          {items.map((item) => (
            <NavLink key={item.href} item={item} active={pathname === item.href} onNavigate={onNavigate} small />
          ))}
        </ul>
      )}
    </div>
  );
}

function SourceCard() {
  const provider = useDataProvider();
  const demo = provider.kind === "DEMO";
  return (
    <div className="text-xs">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted">Data source</span>
        {demo && <DemoBadge />}
      </div>
      <p className="mt-2 font-medium text-ink">{provider.label}</p>
      <p className="mt-1 leading-relaxed text-muted">
        {demo
          ? "Synthetic demonstration data. Real ANAC data will replace it via the FastAPI backend."
          : "Connected to the FastAPI backend."}
      </p>
    </div>
  );
}

function SourceIndicator() {
  const provider = useDataProvider();
  return (
    <div className="flex items-center gap-3 text-xs text-muted">
      <span className="flex items-center gap-2">
        <span className={cn("size-1.5 rounded-full", provider.kind === "DEMO" ? "bg-demo" : "bg-success")} aria-hidden />
        {provider.kind === "DEMO" ? "Demo mode" : "API data"}
      </span>
      {provider.kind === "DEMO" && <DemoBadge />}
    </div>
  );
}

function Breadcrumb({ pathname }: { pathname: string }) {
  const item = NAV.find((n) => n.href === pathname);
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px]">
      <Link href="/dashboard" className="text-muted hover:text-ink">
        Flight Intelligence
      </Link>
      <span className="text-muted/50">/</span>
      <span className="text-ink" aria-current="page">
        {item?.label ?? "Overview"}
      </span>
    </nav>
  );
}

/**
 * Continuation of the takeoff: the dashboard starts on the same navy + HUD
 * frame where the landing ended, then the HUD dissolves into the product.
 */
function BootOverlay() {
  const reduce = useReducedMotion();
  useEffect(() => {
    try {
      sessionStorage.removeItem(ARRIVAL_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  return (
    <motion.div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-[70] bg-navy"
      initial={{ opacity: 1 }}
      animate={{ opacity: 0, transitionEnd: { display: "none" } }}
      transition={{ delay: reduce ? 0 : 0.35, duration: reduce ? 0.2 : 0.9, ease: [0.65, 0, 0.35, 1] }}
    >
      <div className="hud-grid absolute inset-0" />
      <motion.div
        className="absolute inset-0 flex flex-col items-center justify-center gap-6"
        initial={{ opacity: 1, scale: 1 }}
        animate={{ opacity: 0, scale: 1.04 }}
        transition={{ delay: reduce ? 0 : 0.2, duration: reduce ? 0.2 : 0.7, ease: [0.65, 0, 0.35, 1] }}
      >
        <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.4em] text-cyan/80">
          <span className="size-1.5 rounded-full bg-cyan" />
          Data link established
        </div>
        <p className="text-center text-[clamp(1.5rem,4.2vw,3.25rem)] font-semibold uppercase tracking-[0.32em] text-ink">
          Flight Intelligence
        </p>
        <div className="h-px w-[min(320px,60vw)] bg-gradient-to-r from-blue to-cyan" />
      </motion.div>
    </motion.div>
  );
}
