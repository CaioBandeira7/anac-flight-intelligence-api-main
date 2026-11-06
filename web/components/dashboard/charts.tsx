"use client";

import { useId, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { cn, formatCompact, formatNumber } from "@/lib/utils";

/* Chart tokens — single blue series on the navy surface (validated: ≥3:1 vs surface). */
const SERIES = "#3b82f6";
const GRID = "rgba(148,163,184,0.12)";

export function Sparkline({ values, className, label }: { values: number[]; className?: string; label: string }) {
  const id = useId();
  const { line, area } = useMemo(() => {
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const pts = values.map((v, i) => [(i / (values.length - 1)) * 100, 28 - ((v - min) / span) * 24 - 2]);
    const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)} ${y.toFixed(2)}`).join(" ");
    return { line, area: `${line} L100 30 L0 30 Z` };
  }, [values]);
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" className={cn("h-9 w-full", className)} role="img" aria-label={label}>
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={SERIES} stopOpacity="0.28" />
          <stop offset="1" stopColor={SERIES} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke={SERIES} strokeWidth={1.75} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
}

interface Point {
  label: string;
  value: number;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const monthLabel = (ym: string) => {
  const [y, m] = ym.split("-");
  return `${MONTHS[Number(m) - 1]} ${y.slice(2)}`;
};

/**
 * Area/line chart with crosshair + tooltip on hover, arrow-key navigation,
 * and a visually hidden data table for screen readers.
 */
export function TrendChart({ data, valueLabel, height = 280 }: { data: Point[]; valueLabel: string; height?: number }) {
  const W = 760;
  const H = height;
  const pad = { t: 16, r: 12, b: 28, l: 52 };
  const gradId = useId();
  const svgRef = useRef<SVGSVGElement>(null);
  const [active, setActive] = useState<number | null>(null);

  const geo = useMemo(() => {
    const max = Math.max(...data.map((d) => d.value));
    const niceMax = Math.ceil((max * 1.08) / 1_000_000) * 1_000_000 || 1;
    const x = (i: number) => pad.l + (i / Math.max(1, data.length - 1)) * (W - pad.l - pad.r);
    const y = (v: number) => pad.t + (1 - v / niceMax) * (H - pad.t - pad.b);
    const line = data.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(d.value).toFixed(1)}`).join(" ");
    const area = `${line} L${x(data.length - 1)} ${H - pad.b} L${x(0)} ${H - pad.b} Z`;
    const ticks = [0, 0.25, 0.5, 0.75, 1].map((k) => ({ v: niceMax * k, y: y(niceMax * k) }));
    return { x, y, line, area, ticks };
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
            <stop offset="0" stopColor={SERIES} stopOpacity="0.24" />
            <stop offset="1" stopColor={SERIES} stopOpacity="0" />
          </linearGradient>
        </defs>
        {geo.ticks.map((t) => (
          <g key={t.v}>
            <line x1={pad.l} x2={W - pad.r} y1={t.y} y2={t.y} stroke={GRID} />
            <text x={pad.l - 10} y={t.y + 4} textAnchor="end" className="fill-muted text-[11px]">
              {formatCompact(t.v)}
            </text>
          </g>
        ))}
        {data.map((d, i) =>
          i % 3 === 0 ? (
            <text key={d.label} x={geo.x(i)} y={H - 8} textAnchor="middle" className="fill-muted text-[11px]">
              {d.label}
            </text>
          ) : null,
        )}
        <path d={geo.area} fill={`url(#${gradId})`} />
        <path d={geo.line} fill="none" stroke={SERIES} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {active !== null && a && (
          <g>
            <line x1={geo.x(active)} x2={geo.x(active)} y1={pad.t} y2={H - pad.b} stroke="rgba(248,250,252,0.25)" />
            <circle cx={geo.x(active)} cy={geo.y(a.value)} r={5} fill={SERIES} stroke="#111a2b" strokeWidth={2} />
          </g>
        )}
      </svg>
      {a && (
        <div
          className="pointer-events-none absolute top-2 z-10 -translate-x-1/2 rounded-lg border border-line-strong bg-[#0b1322]/95 px-3 py-2 text-xs shadow-xl backdrop-blur"
          style={{ left: `clamp(70px, ${tipLeftPct}%, calc(100% - 70px))` }}
          aria-hidden
        >
          <p className="text-muted">{a.label}</p>
          <p className="mt-0.5 font-medium tabular-nums text-ink">{formatNumber(a.value)}</p>
        </div>
      )}
      <p className="sr-only" aria-live="polite">
        {a ? `${a.label}: ${formatNumber(a.value)}` : ""}
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
              <td>{formatNumber(d.value)}</td>
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
          <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.05]">
            <div
              className="h-full rounded-full bg-blue transition-[width] duration-700 ease-out group-hover:bg-[#5b9bff]"
              style={{ width: `${(it.value / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
