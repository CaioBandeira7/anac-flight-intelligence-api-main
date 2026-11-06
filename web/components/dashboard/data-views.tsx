"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Bot, CircleCheck, CircleDashed, Send } from "lucide-react";
import { useDataProvider } from "@/components/data-provider";
import { useResource, type Resource } from "@/hooks/use-resource";
import type { AirportStat, AnalystStatus, ChatResponse, ChatTurn, DataProviderError, ModelCard, ModelMetric, RouteStat } from "@/lib/data/contracts";
import { formatNumber, formatPercent } from "@/lib/utils";
import { navByHref } from "./nav";
import { BarList } from "./charts";
import { Card, DataTable, DemoBadge, EmptyState, ErrorState, PageHeader, Skeleton } from "./ui";

/** One place for the three states every view must show. */
function Loaded<T>({
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

function Header({ href, state }: { href: string; state: Resource<unknown> }) {
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

export function AirportsView() {
  const provider = useDataProvider();
  const state = useResource(useCallback(() => provider.getAirports(), [provider]));
  return (
    <>
      <Header href="/dashboard/airports" state={state} />
      <Card title="Airports by aircraft movements" subtitle="Takeoffs and landings, last 12 months in the dataset">
        <Loaded state={state} isEmpty={isEmptyList} emptyMessage="No airport data was returned.">
          {(airports: AirportStat[]) => (
            <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
              <BarList items={airports.slice(0, 12).map((a) => ({ label: a.iata, sub: `${a.city} · ${a.uf}`, value: a.movements }))} />
              <DataTable
                caption="All airports with published coordinates"
                columns={["Code", "Airport", "City", "UF", "Movements"]}
                alignRight={[4]}
                rows={airports.map((a) => [a.iata, a.name, a.city, a.uf, formatNumber(a.movements)])}
              />
            </div>
          )}
        </Loaded>
      </Card>
    </>
  );
}

export function RoutesView() {
  const provider = useDataProvider();
  const state = useResource(useCallback(() => provider.getRoutes(), [provider]));
  return (
    <>
      <Header href="/dashboard/routes" state={state} />
      <Card title="Busiest routes" subtitle="Paid passengers and load factor, last 12 months in the dataset">
        <Loaded state={state} isEmpty={isEmptyList} emptyMessage="No route data was returned.">
          {(routes: RouteStat[]) => (
            <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
              <BarList
                items={routes.slice(0, 12).map((r) => ({
                  label: `${r.origin} → ${r.destination}`,
                  sub: `LF ${formatPercent(r.loadFactor, 0)}`,
                  value: r.passengers,
                }))}
              />
              <DataTable
                caption="Routes by paid passengers"
                columns={["Origin", "Destination", "Paid passengers", "Load factor"]}
                alignRight={[2, 3]}
                rows={routes.map((r) => [r.origin, r.destination, formatNumber(r.passengers), formatPercent(r.loadFactor)])}
              />
            </div>
          )}
        </Loaded>
      </Card>
    </>
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
  return (
    <div className={`rounded-xl border p-4 ${card.selected ? "border-cyan/40 bg-cyan/[0.04]" : "border-line"}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-[13.5px] font-medium text-ink">{card.method ?? card.name}</p>
        {card.selected && (
          <span className="inline-flex shrink-0 items-center gap-1 text-[11px] text-cyan">
            <CircleCheck className="size-3.5" aria-hidden /> In use
          </span>
        )}
      </div>
      <MetricList card={card} />
      {card.note && <p className="mt-3 text-xs leading-relaxed text-muted">{card.note}</p>}
    </div>
  );
}

const MODULE_ORDER = ["a", "b", "d", "c"];

export function MlStudioView() {
  const provider = useDataProvider();
  const state = useResource(useCallback(() => provider.getModels(), [provider]));
  return (
    <>
      <PageHeader title="ML Studio" description="Which method each module uses, and how it scored on held-out data." />
      <p className="mb-5 rounded-xl border border-line bg-white/[0.03] px-4 py-3 text-[13px] leading-relaxed text-ink-2">
        These are <strong className="font-medium text-ink">validation results for 2023</strong>, not current forecasts. No live
        predictions are shown, and the final test on 2024–2025 has not been run.
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
        <Card title="What to keep in mind">
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

const UNAVAILABLE_COPY: Record<string, string> = {
  not_configured: "The analyst is not configured on the server: GROQ_API_KEY is missing.",
  auth_failed: "The server could not authenticate with the model provider.",
  rate_limited: "The free usage limit was reached. Please try again shortly.",
  model_not_available: "The configured model is not available for this account.",
  demo_mode: "The analyst only works with real data, and this build runs on demonstration data.",
  timeout: "The model provider is taking too long to respond.",
};

interface ChatEntry {
  question: string;
  response?: ChatResponse;
  error?: DataProviderError | Error;
}

function SourceList({ response }: { response: ChatResponse }) {
  if (!response.sources.length && !response.caveats.length) return null;
  return (
    <div className="mt-3 space-y-1.5 border-t border-line pt-3 text-[11.5px] leading-relaxed text-muted">
      {response.sources.map((source) => (
        <p key={source.endpoint}>
          <span className="text-ink-2">Source:</span> <code className="font-mono">{source.endpoint}</code>, dataset{" "}
          <code className="font-mono">{source.dataset}</code>. Period: {source.period}. Unit: {source.unit}.
        </p>
      ))}
      {response.caveats.map((caveat) => (
        <p key={caveat}>{caveat}</p>
      ))}
    </div>
  );
}

function ChatMessage({ entry, onRetry }: { entry: ChatEntry; onRetry: () => void }) {
  return (
    <div className="space-y-3">
      <p className="ml-auto w-fit max-w-[85%] whitespace-pre-wrap rounded-xl bg-blue/15 px-3.5 py-2.5 text-[13.5px] text-ink">{entry.question}</p>
      {entry.response ? (
        <div className="max-w-[92%] rounded-xl border border-line bg-white/[0.03] px-3.5 py-3">
          <p className="whitespace-pre-wrap text-[13.5px] leading-relaxed text-ink-2">{entry.response.answer}</p>
          <SourceList response={entry.response} />
        </div>
      ) : entry.error ? (
        <ErrorState error={entry.error} onRetry={onRetry} hint="Please try again." />
      ) : (
        <div role="status" aria-label="The analyst is working" className="max-w-[70%] space-y-2 rounded-xl border border-line px-3.5 py-3">
          <Skeleton className="h-3 w-5/6" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      )}
    </div>
  );
}

/** Chat over fixed read-only tools. The key lives on the server, and answers are plain text. */
export function AnalystView() {
  const provider = useDataProvider();
  const catalog = useResource(useCallback(() => provider.getAnalystCatalog(), [provider]));
  const [status, setStatus] = useState<AnalystStatus | "checking" | "error">("checking");
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [draft, setDraft] = useState("");
  const [checks, setChecks] = useState(0);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    provider.getAnalystStatus().then(
      (value) => alive && setStatus(value),
      () => alive && setStatus("error"),
    );
    return () => {
      alive = false;
    };
  }, [provider, checks]);

  useEffect(() => {
    end.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [entries]);

  const available = status !== "checking" && status !== "error" && status.available;
  const busy = entries.some((entry) => !entry.response && !entry.error);

  const ask = (question: string) => {
    // The request runs once, here. State updaters can run twice in development.
    const kept = entries.filter((entry) => entry.question !== question || !entry.error);
    const history: ChatTurn[] = kept
      .filter((entry) => entry.response?.status === "answered")
      .slice(-3)
      .flatMap((entry) => [
        { role: "user" as const, content: entry.question.slice(0, 2000) },
        { role: "assistant" as const, content: (entry.response as ChatResponse).answer.slice(0, 2000) },
      ]);
    setEntries([...kept, { question }]);
    const settle = (result: Partial<ChatEntry>) =>
      setEntries((list) => list.map((entry) => (entry.question === question && !entry.response ? { question, ...result } : entry)));
    provider.askAnalyst(question, history).then(
      (response) => settle({ response }),
      (error: Error) => settle({ error }),
    );
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const question = draft.trim();
    if (!question || !available || busy) return;
    setDraft("");
    ask(question);
  };

  const unavailableMessage =
    status === "error"
      ? "The backend is not reachable. Check that the API is running."
      : status !== "checking" && !status.available
        ? (UNAVAILABLE_COPY[status.reason ?? ""] ?? "The model provider is unavailable right now.")
        : null;

  return (
    <>
      <Header href="/dashboard/analyst" state={catalog} />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Card
          title="Ask the analyst"
          action={
            <span className="text-xs text-muted">
              {status === "checking" ? "Checking…" : available ? `${(status as AnalystStatus).model}` : "Unavailable"}
            </span>
          }
        >
          <div aria-live="polite" className="scrollbar-thin max-h-[480px] min-h-48 space-y-5 overflow-y-auto">
            {unavailableMessage && (
              <div role="alert" className="flex items-start justify-between gap-3 rounded-xl border border-demo/30 bg-demo/10 px-3.5 py-3 text-[13px] text-ink-2">
                <span>{unavailableMessage}</span>
                <button type="button" onClick={() => setChecks((n) => n + 1)} className="shrink-0 text-xs text-cyan hover:underline">
                  Check again
                </button>
              </div>
            )}
            {entries.length === 0 && !unavailableMessage && (
              <div className="grid min-h-44 place-items-center rounded-xl border border-dashed border-line px-6 py-8 text-center">
                <div>
                  <Bot className="mx-auto size-7 text-muted" strokeWidth={1.5} aria-hidden />
                  <p className="mt-3 text-sm text-ink-2">Ask about airports, routes, market totals or model results.</p>
                  <p className="mt-1 text-xs text-muted">Answers come only from this project&apos;s data, with period, unit and source.</p>
                </div>
              </div>
            )}
            {entries.map((entry, index) => (
              <ChatMessage key={`${index}-${entry.question}`} entry={entry} onRetry={() => ask(entry.question)} />
            ))}
            <div ref={end} />
          </div>
          <form className="mt-4 flex gap-2" onSubmit={submit}>
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              disabled={!available}
              maxLength={500}
              aria-label="Question for the analyst"
              placeholder={available ? "Which route carried the most passengers?" : "Unavailable"}
              className="min-w-0 flex-1 rounded-lg border border-line bg-white/[0.03] px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus-visible:border-cyan disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!available || busy || !draft.trim()}
              aria-label="Send question"
              className="grid size-9 shrink-0 place-items-center rounded-lg border border-line text-ink-2 transition-colors hover:border-line-strong disabled:cursor-not-allowed disabled:text-muted"
            >
              <Send className="size-4" aria-hidden />
            </button>
          </form>
        </Card>
        <Card title="What it can and cannot do">
          <Loaded
            state={catalog}
            isEmpty={(data) => data.must_not_claim.length === 0 && data.tools.length === 0}
            emptyMessage="The rules are served by the backend."
          >
            {(data) => (
              <div className="space-y-5 text-[13px] leading-relaxed">
                <div>
                  <h3 className="mb-2 font-medium text-ink">It reads only</h3>
                  <ul className="space-y-1 font-mono text-xs text-muted">
                    {data.tools.map((tool) => (
                      <li key={tool.endpoint}>{tool.endpoint}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="mb-2 font-medium text-ink">It must never claim</h3>
                  <ul className="list-disc space-y-1.5 pl-4 text-ink-2">
                    {data.must_not_claim.map((rule) => (
                      <li key={rule}>{rule}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </Loaded>
        </Card>
      </div>
    </>
  );
}
