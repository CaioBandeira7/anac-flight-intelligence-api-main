"use client";

import { useCallback } from "react";
import { ArrowDownRight, ArrowUpRight, CircleDashed } from "lucide-react";
import { useDataProvider } from "@/components/data-provider";
import { useResource } from "@/hooks/use-resource";
import { formatCompact, formatPercent } from "@/lib/utils";
import { formatMetric } from "./data-views";
import {
  comparePeriods,
  comparisonShift,
  formatPeriod,
  relativeChange,
  shiftMonth,
  withGaps,
  type Comparison,
  type DefinitionKey,
  type Coverage,
  type Kpi,
  type ModelCard,
  type Period,
  type ResponseMeta,
  type RoutePoint,
} from "@/lib/data";
import Link from "next/link";
import { CoverageGate, FilterBar, GapNotice, METHODOLOGY_HREF, Term, usePeriodParam } from "./analytics-controls";
import { PeriodPicker } from "./period-picker";
import { BarList, Sparkline, TrendChart, monthLabel } from "./charts";
import { Card, DemoBadge, EmptyState, ErrorState, PageHeader, Skeleton } from "./ui";

export function Overview() {
  return <CoverageGate href="/dashboard">{(coverage) => <MarketOverview coverage={coverage} />}</CoverageGate>;
}

/** KPIs over the selected period, compared with the same calendar months a whole number of years earlier. */
function buildKpis(points: RoutePoint[], period: Period): { kpis: KpiView[]; comparison: Comparison } {
  const comparison = comparePeriods(points, period);
  const { current, pairedCurrent: now, pairedPrevious: before } = comparison;
  const trend = (value: (p: RoutePoint) => number | null) => withGaps(points, period, value).map((m) => m.value);
  const change = (key: "paid_passengers" | "all_takeoffs" | "seats") => (now && before ? relativeChange(now[key], before[key]) : null);
  const lfChange =
    now?.load_factor_paid != null && before?.load_factor_paid != null ? now.load_factor_paid - before.load_factor_paid : null;
  return {
    comparison,
    kpis: [
      { id: "passengers", term: "paid_passengers", label: "Paid passengers", value: current.paid_passengers, unit: "count", delta: change("paid_passengers"), trend: trend((p) => p.paid_passengers) },
      { id: "flights", term: "flights", label: "Flights", value: current.all_takeoffs, unit: "count", delta: change("all_takeoffs"), trend: trend((p) => p.all_takeoffs) },
      { id: "seats", term: "seats", label: "Seats offered", value: current.seats, unit: "count", delta: change("seats"), trend: trend((p) => p.seats) },
      { id: "load_factor", term: "load_factor", label: "Load factor", value: current.load_factor_paid ?? 0, unit: "ratio", delta: lfChange, deltaInPoints: true, trend: trend((p) => p.load_factor_paid) },
    ],
  };
}

function MarketOverview({ coverage }: { coverage: Coverage }) {
  const provider = useDataProvider();
  const [period, setPeriod] = usePeriodParam(coverage);
  // One request covers the selection and its comparison window.
  const seriesFrom = shiftMonth(period.from, -comparisonShift(period));
  const series = useResource(
    useCallback(
      (signal: AbortSignal) =>
        provider.getRouteSeries({ from: seriesFrom < coverage.first_month ? coverage.first_month : seriesFrom, to: period.to }, signal),
      [provider, seriesFrom, period.to, coverage.first_month],
    ),
  );
  const routes = useResource(useCallback((signal: AbortSignal) => provider.getRouteRanking({ ...period, limit: 6 }, signal), [provider, period]));
  const airports = useResource(useCallback((signal: AbortSignal) => provider.getAirportRanking({ ...period, limit: 8 }, signal), [provider, period]));
  const models = useResource(useCallback(() => provider.getModels(), [provider]));

  const built = series.status === "success" ? buildKpis(series.data.points, period) : null;
  const demo = series.status === "success" && series.meta.isDemo;
  const monthly = series.status === "success" ? series.data.points.filter((p) => p.month >= period.from && p.month <= period.to) : [];
  const unpaired = built?.comparison.unpaired ?? [];
  const previous = built?.comparison.previousPeriod;
  const comparisonNote = !built
    ? undefined
    : !previous
      ? "There are no earlier months with data to compare with, so no change is shown."
      : unpaired.length > 0
        ? `Changes compare only months with data on both sides: ${unpaired.join(", ")} had no counterpart and ${unpaired.length === 1 ? "is" : "are"} left out of the change.`
        : undefined;

  return (
    <>
      <PageHeader
        title="Overview"
        description="Air transport in Brazil at a glance — traffic, routes, airports and the state of the models."
        meta={routes.status === "success" ? <MetaLine meta={routes.meta} period={routes.data.period} /> : null}
      />
      <FilterBar>
        <PeriodPicker coverage={coverage} value={period} onChange={setPeriod} />
        <p className="mb-2 text-xs text-muted">
          {previous && <>Changes vs. {formatPeriod(previous)}. </>}
          <Link href={METHODOLOGY_HREF} className="text-cyan hover:underline">
            How these are measured
          </Link>
        </p>
      </FilterBar>
      {series.status === "success" && (
        <GapNotice context={{ ...series.data, period }} extra={comparisonNote} />
      )}

      {series.status === "error" ? (
        <ErrorState error={series.error} onRetry={series.retry} />
      ) : (
        <div className="grid min-w-0 grid-cols-1 gap-5" aria-busy={series.status === "loading"}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {!built
              ? Array.from({ length: 4 }, (_, i) => <KpiSkeleton key={i} />)
              : built.kpis.map((k) => <KpiCard key={k.id} kpi={k} demo={demo} />)}
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.75fr)_minmax(0,1fr)]">
            <Card title="Monthly passengers" subtitle="Paid passengers per leg, all carriers, domestic and international" demo={demo}>
              {series.status === "loading" ? (
                <Skeleton className="h-[280px] w-full" />
              ) : monthly.length === 0 ? (
                <EmptyState message="No month in this period has data." />
              ) : (
                <TrendChart
                  valueLabel="Monthly paid passengers"
                  data={withGaps(monthly, period, (p) => p.paid_passengers).map((m) => ({ label: monthLabel(m.month), value: m.value }))}
                />
              )}
            </Card>

            <Card title="Top routes" subtitle="Paid passengers in the period, by direction" demo={routes.status === "success" && routes.meta.isDemo}>
              {routes.status === "loading" ? (
                <ListSkeleton />
              ) : routes.status === "error" ? (
                <ErrorState error={routes.error} onRetry={routes.retry} />
              ) : routes.data.routes.length === 0 ? (
                <EmptyState message="No route data was returned." />
              ) : (
                <BarList
                  items={routes.data.routes.map((r) => ({
                    label: `${r.origin_iata || r.origin} → ${r.destination_iata || r.destination}`,
                    sub: r.load_factor_paid === null ? undefined : `LF ${formatPercent(r.load_factor_paid, 0)}`,
                    value: r.paid_passengers,
                  }))}
                />
              )}
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
            <Card
              title={<Term term="movements">Busiest airports</Term>}
              subtitle="Aircraft movements in the period, all operated legs"
              demo={airports.status === "success" && airports.meta.isDemo}
            >
              {airports.status === "loading" ? (
                <ListSkeleton />
              ) : airports.status === "error" ? (
                <ErrorState error={airports.error} onRetry={airports.retry} />
              ) : airports.data.airports.length === 0 ? (
                <EmptyState message="No airport data was returned." />
              ) : (
                <BarList
                  items={airports.data.airports.map((a) => ({
                    label: a.iata || a.airport,
                    sub: [a.name, a.uf ?? a.country].filter(Boolean).join(" · "),
                    value: a.movements,
                  }))}
                />
              )}
            </Card>

            <ModelsCard state={models} />
          </div>
        </div>
      )}
    </>
  );
}

function MetaLine({ meta, period }: { meta: ResponseMeta; period: { from: string; to: string } }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
      {meta.isDemo && <DemoBadge />}
      <span>
        {formatPeriod(period)}
      </span>
      {meta.note && <span className="hidden text-muted/70 md:inline">· {meta.note}</span>}
    </div>
  );
}

/** A KPI as shown here: the load factor's change is in percentage points, the others are relative. */
type KpiView = Omit<Kpi, "id"> & { id: string; deltaInPoints?: boolean; term: DefinitionKey };

function KpiCard({ kpi, demo }: { kpi: KpiView; demo: boolean }) {
  const value = kpi.unit === "ratio" ? formatPercent(kpi.value) : formatCompact(kpi.value);
  const up = (kpi.delta ?? 0) >= 0;
  const delta = kpi.delta == null ? "" : kpi.deltaInPoints ? `${(kpi.delta * 100).toFixed(1)} pts` : formatPercent(kpi.delta);
  return (
    <div className="group rounded-2xl border border-line bg-glass backdrop-blur-xl p-5 transition-colors hover:border-line-strong">
      <div className="flex items-center justify-between">
        <p className="text-[13px] text-muted">
          <Term term={kpi.term}>{kpi.label}</Term>
        </p>
        {demo && <DemoBadge />}
      </div>
      <p className="mt-3 text-[28px] font-semibold tabular-nums tracking-[-0.02em] text-ink">{value}</p>
      <div className="mt-1 h-5 text-xs">
        {kpi.delta != null && (
          <span className="inline-flex items-center gap-1 text-ink-2">
            {up ? <ArrowUpRight className="size-3.5" aria-hidden /> : <ArrowDownRight className="size-3.5" aria-hidden />}
            <span className="tabular-nums">
              {up ? "+" : ""}
              {delta}
            </span>
            <span className="text-muted">vs. earlier period</span>
          </span>
        )}
      </div>
      {kpi.trend.length > 1 ? (
        <Sparkline values={kpi.trend} className="mt-3" label={`${kpi.label} trend`} />
      ) : (
        <div className="mt-3 h-9" aria-hidden />
      )}
    </div>
  );
}

function KpiSkeleton() {
  return (
    <div className="rounded-2xl border border-line bg-glass backdrop-blur-xl p-5">
      <Skeleton className="h-3.5 w-28" />
      <Skeleton className="mt-4 h-7 w-24" />
      <Skeleton className="mt-3 h-3 w-36" />
      <Skeleton className="mt-4 h-9 w-full" />
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i}>
          <Skeleton className="h-3 w-2/3" />
          <Skeleton className="mt-2 h-1.5 w-full" />
        </div>
      ))}
    </div>
  );
}

const STATUS_COPY: Record<ModelCard["status"], string> = {
  not_trained: "Awaiting training",
  training: "Training",
  available: "Validated on 2023",
  deprecated: "Deprecated",
};

function ModelsCard({ state }: { state: ReturnType<typeof useResource<ModelCard[]>> }) {
  return (
    <Card
      title="Models"
      subtitle="Method in use per module"
      action={state.status === "success" && state.meta.isDemo ? <DemoBadge /> : undefined}
    >
      {state.status === "loading" && <ListSkeleton />}
      {state.status === "error" && <ErrorState error={state.error} onRetry={state.retry} />}
      {state.status === "success" && (
        <>
          <ul className="divide-y divide-line">
            {state.data.filter((m) => m.selected !== false).map((m) => (
              <li key={m.id} className="flex items-center gap-4 py-3 first:pt-0">
                <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-hover text-muted">
                  <CircleDashed className="size-4" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[13.5px] font-medium text-ink">{m.name}</p>
                  <p className="truncate text-xs text-muted">{m.method ?? m.task}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-ink-2">{STATUS_COPY[m.status]}</p>
                  <p className="text-[11px] tabular-nums text-muted">
                    {m.metrics?.length ? formatMetric(m.metrics[0]) : "No metrics yet"}
                  </p>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-4 rounded-lg bg-hover px-3 py-2.5 text-xs leading-relaxed text-muted">
            Metrics are validation results for 2023, not current forecasts.{" "}
            <Link href="/dashboard/ml-studio" className="text-cyan hover:underline">
              Details in ML Studio
            </Link>
          </p>
        </>
      )}
    </Card>
  );
}
