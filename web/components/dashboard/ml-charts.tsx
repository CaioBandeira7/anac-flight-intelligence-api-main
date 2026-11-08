"use client";

import { useId, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { cn, formatCompact } from "@/lib/utils";

/* Theme tokens (globals.css), so DAY and NIGHT both work. */
export const SERIES_COLORS = {
  actual: "var(--ink)",
  model: "var(--chart-1)",
  baseline: "var(--muted)",
  accent: "var(--chart-2)",
};
const GRID = "var(--grid)";

export interface Series {
  name: string;
  values: (number | null)[];
  color: string;
  dashed?: boolean;
  width?: number;
}

function niceDomain(values: number[], zero: boolean): [number, number] {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const lo = zero ? Math.min(0, min) : min - (max - min) * 0.08;
  const hi = max + (max - min) * 0.08 || max + 1;
  return [lo, hi];
}

export function Legend({ series }: { series: Pick<Series, "name" | "color" | "dashed">[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted" aria-hidden>
      {series.map((s) => (
        <li key={s.name} className="flex items-center gap-1.5">
          <svg width="18" height="6" aria-hidden>
            <line x1="0" x2="18" y1="3" y2="3" style={{ stroke: s.color }} strokeWidth={2} strokeDasharray={s.dashed ? "4 3" : undefined} />
          </svg>
          {s.name}
        </li>
      ))}
    </ul>
  );
}

/** Several series over shared labels, with a crosshair tooltip and a hidden table. */
export function LinesChart({
  labels,
  series,
  valueFormat,
  tickFormat = formatCompact,
  height = 260,
  zero = false,
  label,
  tickEvery,
}: {
  labels: string[];
  series: Series[];
  valueFormat: (n: number) => string;
  tickFormat?: (n: number) => string;
  height?: number;
  zero?: boolean;
  label: string;
  tickEvery?: number;
}) {
  const W = 760;
  const H = height;
  const pad = { t: 14, r: 12, b: 28, l: 56 };
  const svgRef = useRef<SVGSVGElement>(null);
  const [active, setActive] = useState<number | null>(null);
  const geo = useMemo(() => {
    const all = series.flatMap((s) => s.values.filter((v): v is number => v !== null && Number.isFinite(v)));
    const [lo, hi] = all.length ? niceDomain(all, zero) : [0, 1];
    const x = (i: number) => pad.l + (i / Math.max(1, labels.length - 1)) * (W - pad.l - pad.r);
    const y = (v: number) => pad.t + (1 - (v - lo) / (hi - lo || 1)) * (H - pad.t - pad.b);
    const paths = series.map((s) => {
      let d = "";
      let open = false;
      s.values.forEach((v, i) => {
        if (v === null || !Number.isFinite(v)) {
          open = false;
          return;
        }
        d += `${open ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`;
        open = true;
      });
      return d;
    });
    const ticks = [0, 0.25, 0.5, 0.75, 1].map((k) => lo + (hi - lo) * k);
    const every = tickEvery ?? Math.max(1, Math.ceil(labels.length / 8));
    return { x, y, paths, ticks, every };
  }, [series, labels, H, zero, tickEvery, pad.b, pad.l, pad.r, pad.t]);

  const onMove = (e: PointerEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (labels.length - 1));
    setActive(Math.max(0, Math.min(labels.length - 1, i)));
  };
  const onKey = (e: KeyboardEvent<SVGSVGElement>) => {
    if (e.key === "ArrowRight") setActive((a) => Math.min(labels.length - 1, (a ?? -1) + 1));
    else if (e.key === "ArrowLeft") setActive((a) => Math.max(0, (a ?? labels.length) - 1));
    else if (e.key === "Escape") setActive(null);
    else return;
    e.preventDefault();
  };

  return (
    // On narrow screens the chart keeps a readable width and scrolls sideways, like the tables.
    <div className="scrollbar-thin overflow-x-auto">
    <div className="relative min-w-[560px]">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full touch-pan-y select-none overflow-visible"
        role="img"
        aria-label={`${label}. Use left and right arrow keys to inspect values.`}
        tabIndex={0}
        onPointerMove={onMove}
        onPointerLeave={() => setActive(null)}
        onKeyDown={onKey}
        onBlur={() => setActive(null)}
      >
        {geo.ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={geo.y(t)} y2={geo.y(t)} style={{ stroke: GRID }} />
            <text x={pad.l - 8} y={geo.y(t) + 4} textAnchor="end" className="fill-muted text-[11px]">
              {tickFormat(t)}
            </text>
          </g>
        ))}
        {labels.map((l, i) =>
          i % geo.every === 0 ? (
            <text key={`${l}-${i}`} x={geo.x(i)} y={H - 8} textAnchor="middle" className="fill-muted text-[11px]">
              {l}
            </text>
          ) : null,
        )}
        {series.map((s, i) => (
          <path
            key={s.name}
            d={geo.paths[i]}
            fill="none"
            style={{ stroke: s.color }}
            strokeWidth={s.width ?? 2}
            strokeDasharray={s.dashed ? "5 4" : undefined}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}
        {active !== null && <line x1={geo.x(active)} x2={geo.x(active)} y1={pad.t} y2={H - pad.b} style={{ stroke: "var(--line-strong)" }} />}
      </svg>
      {active !== null && (
        <div
          className="pointer-events-none absolute top-2 z-10 -translate-x-1/2 rounded-lg border border-line-strong bg-tooltip px-3 py-2 text-xs text-ink shadow-xl backdrop-blur"
          style={{ left: `clamp(90px, ${(geo.x(active) / W) * 100}%, calc(100% - 90px))` }}
          aria-hidden
        >
          <p className="text-muted">{labels[active]}</p>
          {series.map((s) => (
            <p key={s.name} className="mt-0.5 flex justify-between gap-4 tabular-nums">
              <span style={{ color: s.color }}>{s.name}</span>
              <span>{s.values[active] == null ? "—" : valueFormat(s.values[active] as number)}</span>
            </p>
          ))}
        </div>
      )}
      <table className="sr-only">
        <caption>{label}</caption>
        <thead>
          <tr>
            <th scope="col">Point</th>
            {series.map((s) => (
              <th key={s.name} scope="col">
                {s.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {labels.map((l, i) => (
            <tr key={`${l}-${i}`}>
              <td>{l}</td>
              {series.map((s) => (
                <td key={s.name}>{s.values[i] == null ? "—" : valueFormat(s.values[i] as number)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    </div>
  );
}

/** Overlaid histograms on shared bins. */
export function Histogram({
  edges,
  groups,
  xFormat,
  label,
}: {
  edges: number[];
  groups: { name: string; counts: number[]; color: string; opacity?: number; narrow?: boolean }[];
  xFormat: (n: number) => string;
  label: string;
}) {
  const W = 760;
  const H = 220;
  const pad = { t: 10, r: 12, b: 28, l: 48 };
  const max = Math.max(1, ...groups.flatMap((g) => g.counts));
  const lo = edges[0];
  const hi = edges[edges.length - 1];
  const x = (v: number) => pad.l + ((v - lo) / (hi - lo)) * (W - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - v / max) * (H - pad.t - pad.b);
  const ticks = [lo, lo / 2, 0, hi / 2, hi];
  return (
    <div className="scrollbar-thin overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full min-w-[560px]" role="img" aria-label={label}>
        {[0, 0.5, 1].map((k) => (
          <g key={k}>
            <line x1={pad.l} x2={W - pad.r} y1={y(max * k)} y2={y(max * k)} style={{ stroke: GRID }} />
            <text x={pad.l - 8} y={y(max * k) + 4} textAnchor="end" className="fill-muted text-[11px]">
              {formatCompact(max * k)}
            </text>
          </g>
        ))}
        {groups.map((g) =>
          g.counts.map((c, i) => {
            const x0 = x(edges[i]);
            const x1 = x(edges[i + 1]);
            const w = (x1 - x0) * (g.narrow ? 0.5 : 0.92);
            return <rect key={`${g.name}-${i}`} x={x0 + (x1 - x0 - w) / 2} y={y(c)} width={w} height={H - pad.b - y(c)} style={{ fill: g.color, opacity: g.opacity ?? 1 }}><title>{`${g.name}: ${xFormat(edges[i])} to ${xFormat(edges[i + 1])}; ${c} rows`}</title></rect>;
          }),
        )}
        <line x1={x(0)} x2={x(0)} y1={pad.t} y2={H - pad.b} style={{ stroke: "var(--ink)" }} strokeWidth={1} />
        {ticks.map((t) => (
          <text key={t} x={x(t)} y={H - 8} textAnchor="middle" className="fill-muted text-[11px]">
            {xFormat(t)}
          </text>
        ))}
      </svg>
      <table className="sr-only">
        <caption>{label}</caption>
        <thead>
          <tr>
            <th scope="col">Bin</th>
            {groups.map((g) => (
              <th key={g.name} scope="col">
                {g.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {edges.slice(0, -1).map((e, i) => (
            <tr key={e}>
              <td>
                {xFormat(e)} to {xFormat(edges[i + 1])}
              </td>
              {groups.map((g) => (
                <td key={g.name}>{g.counts[i]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Actual against predicted, with the diagonal of a perfect forecast. */
export function Scatter({
  points,
  log,
  format,
  label,
}: {
  points: { actual: number; model: number }[];
  log: boolean;
  format: (n: number) => string;
  label: string;
}) {
  const id = useId();
  const W = 420;
  const H = 400;
  const pad = { t: 10, r: 10, b: 34, l: 52 };
  const usable = points.filter((p) => (log ? p.actual > 0 && p.model > 0 : true));
  const t = (v: number) => (log ? Math.log10(v) : v);
  const all = usable.flatMap((p) => [t(p.actual), t(p.model)]);
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const span = hi - lo || 1;
  const sx = (v: number) => pad.l + ((t(v) - lo) / span) * (W - pad.l - pad.r);
  const sy = (v: number) => pad.t + (1 - (t(v) - lo) / span) * (H - pad.t - pad.b);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((k) => (log ? 10 ** (lo + span * k) : lo + span * k));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mx-auto h-auto w-full max-w-[460px]" role="img" aria-label={label} aria-describedby={id}>
      <desc id={id}>
        {usable.length} validation rows. Points on the dotted diagonal are perfect forecasts; points below it are under-forecasts.
      </desc>
      {ticks.map((v) => (
        <g key={v}>
          <line x1={pad.l} x2={W - pad.r} y1={sy(v)} y2={sy(v)} style={{ stroke: GRID }} />
          <text x={pad.l - 6} y={sy(v) + 4} textAnchor="end" className="fill-muted text-[10px]">
            {format(v)}
          </text>
          <text x={sx(v)} y={H - 18} textAnchor="middle" className="fill-muted text-[10px]">
            {format(v)}
          </text>
        </g>
      ))}
      <line x1={sx(ticks[0])} y1={sy(ticks[0])} x2={sx(ticks[4])} y2={sy(ticks[4])} style={{ stroke: "var(--ink)" }} strokeDasharray="3 3" />
      {usable.map((p, i) => (
        <circle key={i} cx={sx(p.actual)} cy={sy(p.model)} r={2.4} style={{ fill: SERIES_COLORS.model, opacity: 0.45 }}><title>{`Actual: ${format(p.actual)}; LightGBM: ${format(p.model)}`}</title></circle>
      ))}
      <text x={(W + pad.l) / 2} y={H - 2} textAnchor="middle" className="fill-muted text-[11px]">
        Actual
      </text>
      <text x={12} y={H / 2} textAnchor="middle" transform={`rotate(-90 12 ${H / 2})`} className="fill-muted text-[11px]">
        LightGBM
      </text>
    </svg>
  );
}

/** Horizontal pairs of bars: model against baseline, per row. */
export function PairBars({
  rows,
  format,
  modelName = "LightGBM",
  baselineName,
}: {
  rows: { label: string; sub?: string; model: number; baseline: number }[];
  format: (n: number) => string;
  modelName?: string;
  baselineName: string;
}) {
  const max = Math.max(...rows.flatMap((r) => [r.model, r.baseline]), 1e-9);
  return (
    <ul className="space-y-3">
      {rows.map((r) => (
        <li key={r.label}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-[13px]">
            <span className="truncate text-ink">
              {r.label}
              {r.sub && <span className="ml-2 text-xs text-muted">{r.sub}</span>}
            </span>
            <span className="shrink-0 tabular-nums text-xs text-ink-2">
              <span className="text-[color:var(--chart-1)]">{format(r.model)}</span> <span className="text-muted">vs {format(r.baseline)}</span>
            </span>
          </div>
          <div className="space-y-1" aria-hidden>
            <div className="h-1.5 overflow-hidden rounded-full bg-hover">
              <div className={cn("h-full rounded-full bg-chart-1")} style={{ width: `${(r.model / max) * 100}%` }} title={modelName} />
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-hover">
              <div className="h-full rounded-full bg-[color:var(--muted)] opacity-60" style={{ width: `${(r.baseline / max) * 100}%` }} title={baselineName} />
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
