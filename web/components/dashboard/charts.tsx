"use client";

import { useId, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { cn, formatCompact, formatNumber } from "@/lib/utils";

/* Chart tokens — single blue series on the navy surface (validated: ≥3:1 vs surface). */
/* Chart tokens come from the theme (see globals.css: --chart-1, --grid). */
const SERIES = "var(--chart-1)";
const GRID = "var(--grid)";

/** Runs of consecutive known values. A `null` (month without data) breaks the line. */
function segments(values: (number | null)[]): { start: number; values: number[] }[] {
  const out: { start: number; values: number[] }[] = [];
  values.forEach((v, i) => {
    if (v === null) return;
    const last = out[out.length - 1];
    if (last && last.start + last.values.length === i) last.values.push(v);
    else out.push({ start: i, values: [v] });
  });
  return out;
}

export function Sparkline({ values, className, label }: { values: (number | null)[]; className?: string; label: string }) {
  const id = useId();
  const { line, area } = useMemo(() => {
    const known = values.filter((v): v is number => v !== null);
    const min = Math.min(...known);
    const max = Math.max(...known);
    const span = max - min || 1;
    const x = (i: number) => (i / Math.max(1, values.length - 1)) * 100;
    const y = (v: number) => 28 - ((v - min) / span) * 24 - 2;
    let line = "";
    let area = "";
    for (const run of segments(values)) {
      const path = run.values.map((v, k) => `${k ? "L" : "M"}${x(run.start + k).toFixed(2)} ${y(v).toFixed(2)}`).join(" ");
      line += path;
      area += `${path} L${x(run.start + run.values.length - 1).toFixed(2)} 30 L${x(run.start).toFixed(2)} 30 Z`;
    }
    return { line, area };
  }, [values]);
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" className={cn("h-9 w-full", className)} role="img" aria-label={label}>
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" style={{ stopColor: SERIES, stopOpacity: 0.28 }} />
          <stop offset="1" style={{ stopColor: SERIES, stopOpacity: 0 }} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={line} fill="none" style={{ stroke: SERIES }} strokeWidth={1.75} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
}

interface Point {
  label: string;
  /** `null` is a month without data: drawn as a gap, never as zero. */
  value: number | null;
}

/** Smallest "round" number at or above `value`, so small series and ratios get a readable scale. */
function niceCeil(value: number) {
  if (value <= 0) return 1;
  const exp = 10 ** Math.floor(Math.log10(value));
  const step = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].find((s) => s * exp >= value) ?? 10;
  return step * exp;
}

const NO_DATA = "No data for this month";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const monthLabel = (ym: string) => {
  const [y, m] = ym.split("-");
  return `${MONTHS[Number(m) - 1]} ${y.slice(2)}`;
};

/**
 * Area/line chart with crosshair + tooltip on hover, arrow-key navigation,
 * and a visually hidden data table for screen readers.
 */
export function TrendChart({
  data,
  valueLabel,
  height = 280,
  valueFormat = formatNumber,
  tickFormat = formatCompact,
}: {
  data: Point[];
  valueLabel: string;
  height?: number;
  /** Tooltip and screen-reader value. */
  valueFormat?: (n: number) => string;
  /** Y-axis labels. */
  tickFormat?: (n: number) => string;
}) {
  const W = 760;
  const H = height;
  const pad = { t: 16, r: 12, b: 28, l: 52 };
  const gradId = useId();
  const svgRef = useRef<SVGSVGElement>(null);
  const [active, setActive] = useState<number | null>(null);

  const geo = useMemo(() => {
    const max = Math.max(0, ...data.map((d) => d.value ?? 0));
    const niceMax = niceCeil(max * 1.08);
    const x = (i: number) => pad.l + (i / Math.max(1, data.length - 1)) * (W - pad.l - pad.r);
    const y = (v: number) => pad.t + (1 - v / niceMax) * (H - pad.t - pad.b);
    const runs = segments(data.map((d) => d.value));
    let line = "";
    let area = "";
    for (const run of runs) {
      const path = run.values.map((v, k) => `${k ? "L" : "M"}${x(run.start + k).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
      line += path;
      area += `${path} L${x(run.start + run.values.length - 1).toFixed(1)} ${H - pad.b} L${x(run.start).toFixed(1)} ${H - pad.b} Z`;
    }
    // A known month between two gaps has no line to sit on, so it is drawn as a dot.
    const dots = runs.filter((run) => run.values.length === 1).map((run) => ({ cx: x(run.start), cy: y(run.values[0]) }));
    const gaps = data.flatMap((d, i) => (d.value === null ? [x(i)] : []));
    const ticks = [0, 0.25, 0.5, 0.75, 1].map((k) => ({ v: niceMax * k, y: y(niceMax * k) }));
    const every = Math.max(1, Math.ceil(data.length / 8));
    return { x, y, line, area, ticks, dots, gaps, every };
  }, [data, H, pad.b, pad.l, pad.r, pad.t]);

  const onMove = (e: PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (data.length - 1));
    setActive(Math.max(0, Math.min(data.length - 1, i)));
  };

  const onKey = (e: KeyboardEvent<SVGSVGElement>) => {
    if (e.key === "ArrowRight") setActive((a) => Math.min(data.length - 1, (a ?? -1) + 1));
    else if (e.key === "ArrowLeft") setActive((a) => Math.max(0, (a ?? data.length) - 1));
    else if (e.key === "Escape") setActive(null);
    else return;
    e.preventDefault();
  };

  const a = active !== null ? data[active] : null;
  const tipLeftPct = active !== null ? (geo.x(active) / W) * 100 : 0;

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full touch-pan-y select-none overflow-visible"
        role="img"
        aria-label={`${valueLabel}, ${data.length} months. Use left and right arrow keys to inspect values.`}
        tabIndex={0}
        onPointerMove={onMove}
        onPointerLeave={() => setActive(null)}
        onKeyDown={onKey}
        onBlur={() => setActive(null)}
      >
        <defs>
          <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" style={{ stopColor: SERIES, stopOpacity: 0.24 }} />
            <stop offset="1" style={{ stopColor: SERIES, stopOpacity: 0 }} />
          </linearGradient>
        </defs>
        {geo.ticks.map((t) => (
          <g key={t.v}>
            <line x1={pad.l} x2={W - pad.r} y1={t.y} y2={t.y} style={{ stroke: GRID }} />
            <text x={pad.l - 10} y={t.y + 4} textAnchor="end" className="fill-muted text-[11px]">
              {tickFormat(t.v)}
            </text>
          </g>
        ))}
        {geo.gaps.map((gx) => (
          <line key={`gap-${gx}`} x1={gx} x2={gx} y1={pad.t} y2={H - pad.b} style={{ stroke: GRID }} strokeDasharray="3 4" />
        ))}
        {data.map((d, i) =>
          i % geo.every === 0 ? (
            <text key={d.label} x={geo.x(i)} y={H - 8} textAnchor="middle" className="fill-muted text-[11px]">
              {d.label}
            </text>
          ) : null,
        )}
        <path d={geo.area} fill={`url(#${gradId})`} />
        <path d={geo.line} fill="none" style={{ stroke: SERIES }} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {geo.dots.map((dot) => (
          <circle key={`dot-${dot.cx}`} cx={dot.cx} cy={dot.cy} r={2.5} style={{ fill: SERIES }} />
        ))}
        {active !== null && a && (
          <g>
            <line x1={geo.x(active)} x2={geo.x(active)} y1={pad.t} y2={H - pad.b} style={{ stroke: "var(--line-strong)" }} />
            {a.value !== null && (
              <circle cx={geo.x(active)} cy={geo.y(a.value)} r={5} style={{ fill: SERIES, stroke: "var(--surface)" }} strokeWidth={2} />
            )}
          </g>
        )}
      </svg>
      {a && (
        <div
          className="pointer-events-none absolute top-2 z-10 -translate-x-1/2 rounded-lg border border-line-strong bg-tooltip text-ink px-3 py-2 text-xs shadow-xl backdrop-blur"
          style={{ left: `clamp(70px, ${tipLeftPct}%, calc(100% - 70px))` }}
          aria-hidden
        >
          <p className="text-muted">{a.label}</p>
          <p className="mt-0.5 font-medium tabular-nums text-ink">{a.value === null ? NO_DATA : valueFormat(a.value)}</p>
        </div>
      )}
      <p className="sr-only" aria-live="polite">
        {a ? `${a.label}: ${a.value === null ? NO_DATA : valueFormat(a.value)}` : ""}
      </p>
      <table className="sr-only">
        <caption>{valueLabel}</caption>
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col">{valueLabel}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.label}>
              <td>{d.label}</td>
              <td>{d.value === null ? NO_DATA : valueFormat(d.value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Horizontal bar list — values in text tokens, bars carry magnitude only. */
export function BarList({ items, valueFormat = formatCompact }: { items: { label: string; sub?: string; value: number }[]; valueFormat?: (n: number) => string }) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <ul className="space-y-3.5">
      {items.map((it) => (
        <li key={it.label} className="group">
          <div className="mb-1.5 flex items-baseline justify-between gap-3 text-[13px]">
            <span className="truncate text-ink">
              {it.label}
              {it.sub && <span className="ml-2 text-muted">{it.sub}</span>}
            </span>
            <span className="tabular-nums text-ink-2">{valueFormat(it.value)}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-hover">
            <div
              className="h-full rounded-full bg-chart-1 transition-[width,opacity] duration-700 ease-out group-hover:opacity-85"
              style={{ width: `${(it.value / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
