"use client";

import { useCallback, type ReactNode } from "react";
import { CircleCheck, CircleDashed } from "lucide-react";
import { useDataProvider } from "@/components/data-provider";
import { useResource, type Resource } from "@/hooks/use-resource";
import type { ModelCard, ModelMetric } from "@/lib/data/contracts";
import { formatPercent } from "@/lib/utils";
import { navByHref } from "./nav";
import { Card, DataTable, DemoBadge, EmptyState, ErrorState, PageHeader, Skeleton } from "./ui";

/** One place for the three states every view must show. */
export function Loaded<T>({
  state,
  isEmpty,
  emptyMessage,
  children,
}: {
  state: Resource<T> & { retry: () => void };
  isEmpty?: (data: T) => boolean;
  emptyMessage: string;
  children: (data: T) => ReactNode;
}) {
  if (state.status === "loading") {
    return (
      <div aria-busy className="space-y-3">
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    );
  }
  if (state.status === "error") return <ErrorState error={state.error} onRetry={state.retry} />;
  if (isEmpty?.(state.data)) return <EmptyState message={emptyMessage} />;
  return <>{children(state.data)}</>;
}

const isEmptyList = (data: unknown[]) => data.length === 0;

export function Header({ href, state }: { href: string; state: Resource<unknown> }) {
  const item = navByHref(href);
  return (
    <PageHeader
      title={item?.label ?? ""}
      description={item?.description}
      meta={
        state.status === "success" ? (
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
            {state.meta.isDemo && <DemoBadge />}
            {state.meta.note && <span className="max-w-md">{state.meta.note}</span>}
          </div>
        ) : null
      }
    />
  );
}

export function formatMetric(metric: ModelMetric): string {
  if (metric.unit === "percent") return formatPercent(metric.value, 2);
  if (metric.unit === "points") return `${(metric.value * 100).toFixed(2)} pts`;
  return metric.value.toFixed(3);
}

function MetricList({ card }: { card: ModelCard }) {
  if (!card.metrics?.length) return <p className="mt-3 text-xs text-muted">No metrics reported.</p>;
  return (
    <dl className="mt-3 space-y-2">
      <p className="text-[11px] uppercase tracking-[0.12em] text-muted">Validation, 2023</p>
      {card.metrics.map((metric) => (
        <div key={metric.name} className="flex items-baseline justify-between gap-4 text-[13px]">
          <dt className="text-muted">{metric.name}</dt>
          <dd className="font-medium tabular-nums text-ink">{formatMetric(metric)}</dd>
        </div>
      ))}
      <p className="pt-1 text-[11px] text-muted">Evaluated on {card.metrics[0].evaluatedOn}</p>
    </dl>
  );
}

function ModelPanel({ card }: { card: ModelCard }) {
  // The backend's note on a LightGBM card is its paired comparison with the best baseline.
  const comparison = card.note && /against the baseline/.test(card.note);
  return (
    <div className={`rounded-xl border p-4 ${card.selected ? "border-cyan/40 bg-cyan/[0.04]" : "border-line"}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-[13.5px] font-medium text-ink">{card.method ?? card.name}</p>
        {card.selected ? (
          <span className="inline-flex shrink-0 items-center gap-1 text-[11px] text-cyan" title="Chosen on validation. It does not mean forecasts are being produced.">
            <CircleCheck className="size-3.5" aria-hidden /> Selected method
          </span>
        ) : (
          <span className="shrink-0 text-[11px] text-muted">Not selected</span>
        )}
      </div>
      <MetricList card={card} />
      {card.note && (
        <p className="mt-3 text-xs leading-relaxed text-muted">
          <span className="text-ink-2">{comparison ? "Compared with the baseline: " : "Why: "}</span>
          {card.note}
        </p>
      )}
    </div>
  );
}

const GLOSSARY: { term: string; text: string }[] = [
  { term: "WAPE", text: "Weighted absolute percentage error: total absolute error divided by the total actual value. 10% means the errors add up to a tenth of what happened. Lower is better." },
  { term: "MAE, seat-weighted", text: "Mean absolute error of the load factor, in percentage points, where routes with more seats weigh more. 6 pts means a predicted 80% was off by about 6 points on average." },
  { term: "Percentage points (pts)", text: "The difference between two percentages: from 80% to 86% is 6 points, not 6%." },
  { term: "95% interval", text: "The range the difference between two methods is likely to fall in, from a block bootstrap over the 12 validation months. If it includes zero, the gain is not conclusive." },
  { term: "Baseline", text: "A simple rule, such as the same month last year. A model is only worth using if it beats it." },
];

const MODULE_ORDER = ["a", "b", "d", "c"];

/** Known limitations, as recorded in docs/models.md. Text only: no metric is derived here. */
const LIMITATIONS: Record<string, string[]> = {
  a: ["LightGBM's lower WAPE is not conclusive: the 95% interval of its difference with the baseline includes zero. The baseline is therefore the selected method."],
  b: [],
  d: [
    "Six months ahead, no better than the same month last year (intervals include zero).",
    "Bias of about −12% on passengers and seats in 2023: training ends during the recovery.",
  ],
  c: ["The baggage target is provisional (see decisions 6–9 in docs/decisions.md)."],
};

const COMMON_LIMITATIONS = [
  "The final test on 2024–2025 has not been run.",
  "Training data still lacks four months (2015-08, 2016-02, 2018-07, 2020-08).",
];

function ModuleNotes({ module }: { module: string }) {
  const notes = [...(LIMITATIONS[module] ?? []), ...(module === "c" ? [] : COMMON_LIMITATIONS)];
  return (
    <div className="mt-4 space-y-3 border-t border-line pt-4 text-xs leading-relaxed text-muted">
      <p>
        <span className="text-ink-2">Forecasts:</span> not available. The backend serves validation results only, with no
        prediction endpoint.
      </p>
      {notes.length > 0 && (
        <div>
          <p className="text-ink-2">Limitations</p>
          <ul className="mt-1 list-disc space-y-1 pl-4">
            {notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function MlStudioView() {
  const provider = useDataProvider();
  const state = useResource(useCallback(() => provider.getModels(), [provider]));
  return (
    <>
      <PageHeader title="ML Studio" description="How each forecasting method scored on 2023 data it had not seen." />
      <p className="mb-5 rounded-xl border border-line bg-hover px-4 py-3 text-[13px] leading-relaxed text-ink-2">
        These are <strong className="font-medium text-ink">validation results for 2023</strong>, not current forecasts. No forecasts are
        produced or served: <span className="text-ink">Selected method</span> is the one chosen on validation. The final test on 2024–2025 has not
        been run.
      </p>
      <Loaded state={state} isEmpty={isEmptyList} emptyMessage="No models were reported.">
        {(cards: ModelCard[]) => (
          <div className="grid gap-5 xl:grid-cols-2">
            {MODULE_ORDER.map((module) => {
              const group = cards.filter((card) => card.module === module);
              if (!group.length) return null;
              return (
                <Card key={module} title={`Module ${module.toUpperCase()}: ${group[0].name}`} subtitle={group[0].task}>
                  <div className="grid gap-3">
                    {group.map((card) =>
                      card.status === "not_trained" ? (
                        <p key={card.id} className="flex items-center gap-2 text-[13px] text-muted">
                          <CircleDashed className="size-4" aria-hidden /> Not trained. No metrics to report.
                        </p>
                      ) : (
                        <ModelPanel key={card.id} card={card} />
                      ),
                    )}
                  </div>
                  <ModuleNotes module={module} />
                </Card>
              );
            })}
            {cards
              .filter((card) => !card.module)
              .map((card) => (
                <Card key={card.id} title={card.name} subtitle={card.task} demo={state.status === "success" && state.meta.isDemo}>
                  <p className="flex items-center gap-2 text-[13px] text-muted">
                    <CircleDashed className="size-4" aria-hidden /> Not trained. No metrics to report.
                  </p>
                </Card>
              ))}
            <Card title="How to read these numbers" className="xl:col-span-2">
              <dl className="grid gap-4 text-[13px] leading-relaxed sm:grid-cols-2 xl:grid-cols-3">
                {GLOSSARY.map((item) => (
                  <div key={item.term}>
                    <dt className="font-medium text-ink">{item.term}</dt>
                    <dd className="mt-1 text-xs text-muted">{item.text}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          </div>
        )}
      </Loaded>
    </>
  );
}

export function MethodologyView() {
  const provider = useDataProvider();
  const datasets = useResource(useCallback(() => provider.getDatasets(), [provider]));
  const modules = useResource(useCallback(() => provider.getModules(), [provider]));
  const catalog = useResource(useCallback(() => provider.getAnalystCatalog(), [provider]));
  return (
    <>
      <Header href="/dashboard/methodology" state={datasets} />
      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Datasets">
          <Loaded state={datasets} isEmpty={isEmptyList} emptyMessage="No datasets were reported.">
            {(items) => (
              <ul className="divide-y divide-line">
                {items.map((dataset) => (
                  <li key={dataset.name} className="py-3 first:pt-0">
                    <p className="flex items-center justify-between gap-3 text-[13.5px] font-medium text-ink">
                      <code className="font-mono text-[13px]">{dataset.name}</code>
                      <span className="text-xs font-normal capitalize text-muted">{dataset.status}</span>
                    </p>
                    <p className="mt-1 text-xs text-muted">{dataset.description}</p>
                    <p className="mt-1 text-xs text-muted">{dataset.approxSize}</p>
                  </li>
                ))}
              </ul>
            )}
          </Loaded>
        </Card>
        <Card title="What to keep in mind" className="scroll-mt-24" id="reading-the-data">
          <Loaded
            state={catalog}
            isEmpty={(data) => data.facts_that_must_accompany_answers.length === 0}
            emptyMessage="No caveats were reported."
          >
            {(data) => (
              <ul className="list-disc space-y-2 pl-4 text-[13px] leading-relaxed text-ink-2">
                {data.facts_that_must_accompany_answers.map((fact) => (
                  <li key={fact}>{fact}</li>
                ))}
              </ul>
            )}
          </Loaded>
        </Card>
        <Card title="Modules" className="xl:col-span-2">
          <Loaded state={modules} isEmpty={isEmptyList} emptyMessage="No module contracts were reported.">
            {(items) => (
              <DataTable
                caption="Forecast units and targets"
                columns={["Module", "Unit", "Targets", "Primary metric", "Features"]}
                alignRight={[4]}
                rows={items.map((item) => [
                  `${item.module.toUpperCase()}: ${item.title}`,
                  item.unit.join(" × "),
                  Object.keys(item.targets).join(", "),
                  item.primary_metric,
                  String(item.features.length),
                ])}
              />
            )}
          </Loaded>
        </Card>
      </div>
    </>
  );
}
