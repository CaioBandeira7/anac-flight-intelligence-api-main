"use client";

import { motion, useReducedMotion } from "framer-motion";
import { AIRPORTS, ILLUSTRATIVE_ROUTES, project } from "@/lib/data/airports";

const W = 640;
const H = 620;

function arc(a: { x: number; y: number }, b: { x: number; y: number }) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy);
  // Bow each route perpendicular to its chord, like a great-circle on a flat map.
  const k = Math.min(0.22, 40 / Math.max(len, 1)) * len;
  const cx = mx - (dy / len) * k;
  const cy = my + (dx / len) * k;
  return `M${a.x.toFixed(1)} ${a.y.toFixed(1)} Q${cx.toFixed(1)} ${cy.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
}

const HUBS = new Set(["GRU", "BSB", "GIG", "CGH"]);

/** Airports at their real coordinates with an illustrative route network. */
export function RouteNetwork() {
  const reduce = useReducedMotion();
  const pts = new Map(AIRPORTS.map((a) => [a.iata, project(a.lat, a.lon, W, H)]));

  return (
    <figure className="relative mx-auto w-full max-w-[560px]">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full overflow-visible" role="img" aria-labelledby="net-title net-desc">
        <title id="net-title">Brazilian airport network</title>
        <desc id="net-desc">
          Major Brazilian airports plotted at their geographic positions, connected by an illustrative set of
          domestic routes.
        </desc>
        <defs>
          <linearGradient id="route" x1="0" x2="1">
            <stop offset="0" stopColor="#ffffff" stopOpacity="0.15" />
            <stop offset="0.5" stopColor="#ffffff" stopOpacity="0.85" />
            <stop offset="1" stopColor="#a5f3fc" stopOpacity="0.4" />
          </linearGradient>
        </defs>
        <g fill="none" stroke="url(#route)" strokeWidth={1.4} strokeLinecap="round">
          {ILLUSTRATIVE_ROUTES.map(([o, d], i) => {
            const a = pts.get(o);
            const b = pts.get(d);
            if (!a || !b) return null;
            return (
              <motion.path
                key={`${o}-${d}`}
                d={arc(a, b)}
                initial={reduce ? false : { pathLength: 0, opacity: 0 }}
                whileInView={{ pathLength: 1, opacity: 1 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 1.6, delay: 0.2 + i * 0.06, ease: [0.65, 0, 0.35, 1] }}
              />
            );
          })}
        </g>
        {AIRPORTS.map((a, i) => {
          const p = pts.get(a.iata)!;
          const hub = HUBS.has(a.iata);
          // Avoid overlapping labels for the São Paulo / Rio pairs.
          const dx = a.iata === "CGH" || a.iata === "SDU" ? 10 : a.iata === "VCP" ? -34 : 9;
          const dy = a.iata === "CGH" ? 14 : a.iata === "SDU" ? 12 : 4;
          return (
            <motion.g
              key={a.iata}
              initial={reduce ? false : { opacity: 0, scale: 0.6 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.8, delay: 0.1 + i * 0.03, ease: [0.16, 1, 0.3, 1] }}
              style={{ transformOrigin: `${p.x}px ${p.y}px` }}
            >
              {hub && <circle cx={p.x} cy={p.y} r={10} fill="#ffffff" opacity={0.12} />}
              <circle cx={p.x} cy={p.y} r={hub ? 4.5 : 3} fill="#ffffff" />
              <text
                x={p.x + dx}
                y={p.y + dy}
                className="fill-white/80 font-mono"
                fontSize={hub ? 13 : 11}
                letterSpacing="0.08em"
              >
                {a.iata}
              </text>
            </motion.g>
          );
        })}
        {/* Hint of planes travelling along two trunk routes */}
        {!reduce &&
          (["GRU-BSB", "BSB-MAO"] as const).map((key, i) => {
            const [o, d] = key.split("-");
            const a = pts.get(o)!;
            const b = pts.get(d)!;
            return (
              <circle key={key} r={2.6} fill="#a5f3fc">
                <animateMotion dur={`${7 + i * 3}s`} repeatCount="indefinite" path={arc(a, b)} />
              </circle>
            );
          })}
      </svg>
      <figcaption className="mt-3 text-center font-mono text-[10px] uppercase tracking-[0.3em] text-white/55">
        Airport positions: real · Routes: illustrative
      </figcaption>
    </figure>
  );
}

