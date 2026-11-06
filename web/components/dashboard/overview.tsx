"use client";

import { useCallback } from "react";
import { ArrowDownRight, ArrowUpRight, CircleDashed } from "lucide-react";
import { useDataProvider } from "@/components/data-provider";
import { useResource } from "@/hooks/use-resource";
import { formatCompact, formatPercent } from "@/lib/utils";
import { formatMetric } from "./data-views";
import type { Kpi, ModelCard, ResponseMeta } from "@/lib/data/contracts";
import { BarList, Sparkline, TrendChart, monthLabel } from "./charts";
import { Card, DemoBadge, EmptyState, ErrorState, PageHeader, Skeleton } from "./ui";

export function Overview() {
  const provider = useDataProvider();
  const loadOverview = useCallback(() => provider.getOverview(), [provider]);
  const loadModels = useCallback(() => provider.getModels(), [provider]);
  const overview = useResource(loadOverview);
  const models = useResource(loadModels);

  return (
    <>
      <PageHeader
        title="Overview"
        description="Air transport in Brazil at a glance — traffic, routes, airports and the state of the models."
        meta={overview.status === "success" ? <MetaLine meta={overview.meta} period={overview.data.period} /> : null}
      />

      {overview.status === "error" ? (
        <ErrorState error={overview.error} onRetry={overview.retry} />
      ) : (
        <div className="grid min-w-0 grid-cols-1 gap-5" aria-busy={overview.status === "loading"}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {overview.status === "loading"
              ? Array.from({ length: 4 }, (_, i) => <KpiSkeleton key={i} />)
              : overview.data.kpis.map((k) => <KpiCard key={k.id} kpi={k} demo={overview.meta.isDemo} />)}
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.75fr)_minmax(0,1fr)]">
            <Card
              title="Monthly passengers"
              subtitle="All carriers, domestic and international legs"
              demo={overview.status === "success" && overview.meta.isDemo}
            >
              {overview.status === "loading" ? (
                <Skeleton className="h-[280px] w-full" />
              ) : overview.data.monthly.length === 0 ? (
                <EmptyState message="No monthly data was returned." />
              ) : (
                <TrendChart
                  valueLabel="Monthly passengers"
                  data={overview.data.monthly.map((m) => ({ label: monthLabel(m.month), value: m.passengers }))}
                />
              )}
            </Card>

            <Card title="Top routes" subtitle="Passengers, last 12 months" demo={overview.status === "success" && overview.meta.isDemo}>
              {overview.status === "loading" ? (
                <ListSkeleton />
              ) : overview.data.topRoutes.length === 0 ? (
                <EmptyState message="No route data was returned." />
              ) : (
                <BarList
                  items={overview.data.topRoutes.map((r) => ({
                    label: `${r.origin} → ${r.destination}`,
                    sub: `LF ${formatPercent(r.loadFactor, 0)}`,
                    value: r.passengers,
                  }))}
                />
              )}
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
            <Card title="Busiest airports" subtitle="Aircraft movements, last 12 months" demo={overview.status === "success" && overview.meta.isDemo}>
              {overview.status === "loading" ? (
                <ListSkeleton />
              ) : overview.data.topAirports.length === 0 ? (
                <EmptyState message="No airport data was returned." />
              ) : (
                <BarList
                  items={overview.data.topAirports.map((a) => ({ label: a.iata, sub: `${a.name} · ${a.uf}`, value: a.movements }))}
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
        {monthLabel(period.from)} – {monthLabel(period.to)}
      </span>
      {meta.note && <span className="hidden text-muted/70 md:inline">· {meta.note}</span>}
    </div>
  );
}

function KpiCard({ kpi, demo }: { kpi: Kpi; demo: boolean }) {
  const value = kpi.unit === "ratio" ? formatPercent(kpi.value) : formatCompact(kpi.value);
  const up = (kpi.delta ?? 0) >= 0;
  return (
    <div className="group rounded-2xl border border-line bg-glass backdrop-blur-xl p-5 transition-colors hover:border-line-strong">
      <div className="flex items-center justify-between">
        <p className="text-[13px] text-muted">{kpi.label}</p>
        {demo && <DemoBadge />}
      </div>
      <p className="mt-3 text-[28px] font-semibold tabular-nums tracking-[-0.02em] text-ink">{value}</p>
      <div className="mt-1 h-5 text-xs">
        {kpi.delta != null && (
          <span className="inline-flex items-center gap-1 text-ink-2">
            {up ? <ArrowUpRight className="size-3.5" aria-hidden /> : <ArrowDownRight className="size-3.5" aria-hidden />}
            <span className="tabular-nums">
              {up ? "+" : ""}
              {formatPercent(kpi.delta)}
            </span>
            <span className="text-muted">vs. previous 12 mo</span>
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
  available: "Available",
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
            Metrics are validation results for 2023, not current forecasts. Details are in ML Studio.
          </p>
        </>
      )}
    </Card>
  );
}
