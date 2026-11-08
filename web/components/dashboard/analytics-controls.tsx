"use client";

import { useCallback, useId, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeftRight, ChevronLeft, ChevronRight, Info } from "lucide-react";
import { useDataProvider } from "@/components/data-provider";
import { Button } from "@/components/ui/button";
import { useResource } from "@/hooks/use-resource";
import {
  DEFINITIONS,
  absentIn,
  defaultPeriod,
  formatPeriod,
  isValidPeriod,
  type Coverage,
  type DefinitionKey,
  type PageInfo,
  type Period,
  type PeriodContext,
} from "@/lib/data";
import { cn, formatNumber } from "@/lib/utils";
import { navByHref } from "./nav";
import { Overlay, POPOVER_SURFACE, useAnchoredStyle } from "./overlay";
import { Card, ErrorState, PageHeader, Skeleton } from "./ui";

/** Coverage (period and absent months) is shared by every view; the provider requests it once. */
export function useCoverage() {
  const provider = useDataProvider();
  return useResource(useCallback(() => provider.getCoverage(), [provider]));
}

/** Renders the page only once coverage is known, so every filter starts from real bounds. */
export function CoverageGate({ href, children }: { href: string; children: (coverage: Coverage) => ReactNode }) {
  const coverage = useCoverage();
  const item = navByHref(href);
  if (coverage.status === "success") return <>{children(coverage.data)}</>;
  return (
    <>
      <PageHeader title={item?.label ?? ""} description={item?.description} />
      {coverage.status === "error" ? (
        <ErrorState error={coverage.error} onRetry={coverage.retry} />
      ) : (
        <div aria-busy className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
    </>
  );
}

export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <Card className="mb-5">
      <div className="flex flex-wrap items-end gap-4">{children}</div>
    </Card>
  );
}

/** Codes the analytics endpoints accept. Checked again here, before any request. */
export const AIRPORT_CODE = /^[A-Za-z0-9]{3,4}$/;
export const CARRIER_CODE = /^[A-Za-z0-9]{2,3}$/;
export const validCode = (code: string, pattern: RegExp) => !code || pattern.test(code);

function readPeriod(coverage: Coverage): Period | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const period = { from: params.get("from") ?? undefined, to: params.get("to") ?? undefined };
  return isValidPeriod(period, coverage) ? period : null;
}

/**
 * Period state, mirrored in the URL (`?from=YYYY-MM&to=YYYY-MM`) so a view can be shared.
 * A missing or invalid period in the URL falls back to the last 12 months with data.
 */
export function usePeriodParam(coverage: Coverage): [Period, (period: Period) => void] {
  const [period, setPeriod] = useState<Period>(() => readPeriod(coverage) ?? defaultPeriod(coverage));
  const update = useCallback((next: Period) => {
    setPeriod(next);
    const url = new URL(window.location.href);
    url.searchParams.set("from", next.from);
    url.searchParams.set("to", next.to);
    window.history.replaceState(window.history.state, "", url);
  }, []);
  return [period, update];
}

/** Swaps origin and destination: the other direction is another route. */
export function SwapButton({ onSwap, disabled }: { onSwap: () => void; disabled?: boolean }) {
  return (
    <Button type="button" variant="ghost" size="sm" className="mb-1" onClick={onSwap} disabled={disabled} aria-label="Swap direction">
      <ArrowLeftRight aria-hidden /> Swap
    </Button>
  );
}

/** A discreet definition, opened by hover or keyboard focus. */
export function InfoTip({ term, label }: { term: DefinitionKey; label: string }) {
  const [open, setOpen] = useState(false);
  const anchor = useRef<HTMLButtonElement>(null);
  const id = useId();
  const style = useAnchoredStyle(anchor, open, { width: 260, maxHeight: 200 });
  return (
    <>
      <button
        ref={anchor}
        type="button"
        aria-label={`What is ${label.toLowerCase()}?`}
        aria-describedby={open ? id : undefined}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        className="inline-grid size-4 shrink-0 place-items-center rounded-full text-muted/80 transition-colors hover:text-ink focus-visible:text-ink"
      >
        <Info className="size-3.5" aria-hidden />
      </button>
      {open && (
        <Overlay>
          <div id={id} role="tooltip" style={style} className={cn(POPOVER_SURFACE, "pointer-events-none px-3 py-2 text-xs leading-relaxed text-ink-2")}>
            {DEFINITIONS[term]}
          </div>
        </Overlay>
      )}
    </>
  );
}

/** A measure's label with its definition next to it. */
export function Term({ term, children }: { term: DefinitionKey; children: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      {children}
      <InfoTip term={term} label={children} />
    </span>
  );
}

export const METHODOLOGY_HREF = "/dashboard/methodology#reading-the-data";

/** States the period the API actually answered for, and how many months in it have data. */
export function PeriodLine({ context }: { context: PeriodContext }) {
  return (
    <span className="text-xs text-muted">
      {formatPeriod(context.period)} · {context.months_with_data} months with data
    </span>
  );
}

/** Shown whenever the selected period contains months without data. */
export function GapNotice({ context, extra }: { context: PeriodContext; extra?: string }) {
  const absent = absentIn(context.absent_months, context.period);
  if (!absent.length && !extra) return null;
  return (
    <div role="note" className="mb-5 flex items-start gap-3 rounded-xl border border-demo/30 bg-demo/10 px-4 py-3 text-[13px] leading-relaxed text-ink-2">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-demo" aria-hidden />
      <p>
        {absent.length > 0 && (
          <>
            {absent.length === 1 ? "Month" : "Months"} without data in this period: <strong className="font-medium text-ink">{absent.join(", ")}</strong>.
            Totals leave {absent.length === 1 ? "it" : "them"} out and charts show a gap, not a zero.{" "}
          </>
        )}
        {extra}{" "}
        <Link href={METHODOLOGY_HREF} className="whitespace-nowrap text-cyan hover:underline">
          About the data
        </Link>
      </p>
    </div>
  );
}

export function Pager({ page, onOffset, noun }: { page: PageInfo; onOffset: (offset: number) => void; noun: string }) {
  if (page.total <= page.limit && page.offset === 0) {
    return <p className="mt-3 text-xs text-muted">{formatNumber(page.total)} {noun}</p>;
  }
  const first = page.total ? page.offset + 1 : 0;
  const last = Math.min(page.offset + page.limit, page.total);
  return (
    <div className="mt-3 flex items-center justify-between gap-3 text-xs text-muted">
      <span>
        {formatNumber(first)}–{formatNumber(last)} of {formatNumber(page.total)} {noun}
      </span>
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" disabled={page.offset === 0} onClick={() => onOffset(Math.max(0, page.offset - page.limit))} aria-label="Previous page">
          <ChevronLeft aria-hidden />
        </Button>
        <Button variant="secondary" size="sm" disabled={last >= page.total} onClick={() => onOffset(page.offset + page.limit)} aria-label="Next page">
          <ChevronRight aria-hidden />
        </Button>
      </div>
    </div>
  );
}

export function MetricTabs<K extends string>({
  options,
  value,
  onChange,
}: {
  options: { key: K; label: string }[];
  value: K;
  onChange: (key: K) => void;
}) {
  return (
    <div role="tablist" aria-label="Metric" className="flex flex-wrap gap-1.5">
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          role="tab"
          aria-selected={option.key === value}
          onClick={() => onChange(option.key)}
          className={cn(
            "rounded-lg border px-2.5 py-1 text-xs transition-colors",
            option.key === value ? "border-cyan/40 bg-cyan/[0.08] text-ink" : "border-line text-muted hover:border-line-strong hover:text-ink",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function StatTile({ label, value, sub, term }: { label: string; value: string; sub?: string; term?: DefinitionKey }) {
  return (
    <div className="rounded-2xl border border-line bg-glass p-5 backdrop-blur-xl">
      <p className="text-[13px] text-muted">{term ? <Term term={term}>{label}</Term> : label}</p>
      <p className="mt-3 text-[24px] font-semibold tabular-nums tracking-[-0.02em] text-ink">{value}</p>
      {sub && <p className="mt-1 text-xs text-muted">{sub}</p>}
    </div>
  );
}

/** Row action that selects an entity for the monthly chart. */
export function RowButton({ children, onClick, selected }: { children: ReactNode; onClick: () => void; selected?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn("font-mono text-[12.5px] hover:text-cyan hover:underline", selected ? "text-cyan" : "text-ink")}
    >
      {children}
    </button>
  );
}
