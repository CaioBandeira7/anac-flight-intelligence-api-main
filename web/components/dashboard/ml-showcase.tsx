"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText } from "lucide-react";
import {
  REPORT_URL,
  formatDifference,
  formatError,
  loadShowcase,
  type Example,
  type Showcase,
  type ShowcaseTask,
  type TaskKey,
} from "@/lib/data/showcase";
import { formatCompact, formatNumber, formatPercent } from "@/lib/utils";
import { MetricTabs, StatTile } from "./analytics-controls";
import { BarList } from "./charts";
import { Histogram, Legend, LinesChart, PairBars, SERIES_COLORS, Scatter, type Series } from "./ml-charts";
import { Card, DataTable, ErrorState, Skeleton } from "./ui";

const TASKS: { key: TaskKey; label: string }[] = [
  { key: "a", label: "A · Airport traffic" },
  { key: "b", label: "B · Seat occupancy" },
  { key: "d_pax", label: "D · Route passengers" },
  { key: "d_seats", label: "D · Route seats" },
];

/** What each experiment forecasts. Definitions only; every number below comes from the payload. */
const PROBLEM: Record<TaskKey, { what: string; unit: string; entity: string }> = {
  a: {
    what: "Daily takeoffs plus landings at each of the 50 busiest airports, forecast 1 and 3 months ahead from data known two months before the origin month.",
    unit: "Airport × day",
    entity: "airport (ICAO)",
  },
  b: {
    what: "Paid seat occupancy (paid passengers / seats) by route and carrier, 1, 3 and 6 months ahead. Only units operating in the target month are scored. This is not RPK / ASK.",
    unit: "Route × carrier × month",
    entity: "carrier",
  },
  d_pax: {
    what: "Monthly paid passengers on each directed route, 1, 3 and 6 months ahead.",
    unit: "Route × month",
    entity: "directed route",
  },
  d_seats: {
    what: "Monthly seats offered on each directed route, 1, 3 and 6 months ahead.",
    unit: "Route × month",
    entity: "directed route",
  },
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const isRatio = (key: TaskKey) => key === "b";

function useShowcase() {
  const [state, setState] = useState<{ data?: Showcase; error?: Error; attempt: number }>({ attempt: 0 });
  useEffect(() => {
    let alive = true;
    loadShowcase().then(
      (data) => alive && setState((s) => ({ ...s, data, error: undefined })),
      (error: Error) => alive && setState((s) => ({ ...s, error })),
    );
    return () => {
      alive = false;
    };
  }, [state.attempt]);
  return { ...state, retry: () => setState((s) => ({ attempt: s.attempt + 1 })) };
}

const ci = (task: ShowcaseTask, interval: [number, number] | null) =>
  interval ? `95% interval ${formatError(task, interval[0])} to ${formatError(task, interval[1])}` : undefined;

/** Plain statements derived from the results, so the page never overstates them. */
function findings(task: ShowcaseTask): string[] {
  const out: string[] = [];
  const diff = task.difference_vs_best_baseline;
  out.push(
    task.beats_best_baseline
      ? `LightGBM beats the best baseline (${task.best_baseline}): the 95% interval of the paired difference excludes zero.`
      : `No conclusive gain over ${task.best_baseline}: the 95% interval of the difference (${formatDifference(task, diff.ci95?.[0] ?? 0)} to ${formatDifference(task, diff.ci95?.[1] ?? 0)}) includes zero. The baseline remains the method of record.`,
  );
  for (const row of task.by_horizon) {
    const best = Math.min(...Object.values(row.baselines));
    if (row.model > best) out.push(`At ${row.horizon} month${row.horizon > 1 ? "s" : ""} ahead, LightGBM is worse than the best baseline (${formatError(task, row.model)} vs ${formatError(task, best)}).`);
  }
  if (task.metric === "WAPE" && Math.abs(task.bias.value) >= 0.05) {
    out.push(`Systematic ${task.bias.value < 0 ? "under" : "over"}-forecast: bias ${formatPercent(task.bias.value)} of the actual total.`);
  }
  return out;
}

export function MlShowcase() {
  const { data, error, retry } = useShowcase();
  const [key, setKey] = useState<TaskKey>("a");
  if (error) return <ErrorState error={error} onRetry={retry} hint="The results file is part of the web build." />;
  if (!data) {
    return (
      <div aria-busy className="mb-5 space-y-3">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  const task = data.tasks[key];
  return (
    <section aria-labelledby="showcase-title" className="mb-10 grid gap-5">
      {/* Inside a glass card, like the filter bars: text straight on the sky is hard to read in DAY. */}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 id="showcase-title" className="text-[17px] font-semibold tracking-[-0.01em] text-ink">
              Experiment results
            </h2>
            <p className="mt-1 text-[13px] text-muted">Out-of-sample predictions on {data.evaluated_on}. Pick an experiment.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a href={REPORT_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-xs text-ink-2 hover:border-line-strong hover:text-ink">
              <FileText className="size-3.5" aria-hidden /> Technical report (PDF)
            </a>
            <Link href="/dashboard/methodology" className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-xs text-ink-2 hover:border-line-strong hover:text-ink">
              Methodology
            </Link>
          </div>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-muted">
          Reproducible from the repository: <code className="font-mono">scripts/audit_ml.py --artifact-root PATH</code> checks saved 2023 predictions without refitting frozen models; <code className="font-mono">analysis.py</code> rebuilds this page&apos;s data.
        </p>
        <details className="mt-4 rounded-lg border border-line p-3 text-xs leading-relaxed text-muted">
          <summary className="cursor-pointer font-medium text-ink">How to read this evaluation</summary>
          <ul className="mt-2 list-disc space-y-1 pl-4">
            <li>Fitting: 2013–2021, with horizon-specific purging. Early stopping: 2022. Validation: 2023.</li>
            <li>The 2024–2025 test was not scored. Annual totals were previously inspected, so it is not fully blind.</li>
            <li>Scores come from selection-stage models. Frozen final boosters were refit on eligible 2023 history and must not be used to rescore this validation.</li>
            <li>WAPE = total absolute error / total observed volume. 10% WAPE does not mean 90% accuracy. Occupancy MAE is weighted by seats and shown in percentage points.</li>
            <li>95% intervals resample 12 target-month clusters, 2,000 draws. They are uncertainty estimates for these validation errors, not future prediction intervals.</li>
            <li>Horizon means months from forecast origin to target; the source-data cutoff is two months before origin. A 1-month horizon therefore uses observations at least 3 reference months before the target.</li>
            <li>Rows pool multiple horizons: repeated targets are separate forecast tasks, not additional independent passengers or flights.</li>
            <li>Module C has no trained model. Module D describes carried demand and operated seats, not prices, unconstrained demand or commercial opportunity.</li>
          </ul>
        </details>
        <div className="mt-4">
          <MetricTabs options={TASKS} value={key} onChange={setKey} />
        </div>
      </Card>
      <TaskView key={key} taskKey={key} task={task} />
    </section>
  );
}

function TaskView({ taskKey, task }: { taskKey: TaskKey; task: ShowcaseTask }) {
  const horizons = task.by_horizon.map((h) => h.horizon);
  const [horizon, setHorizon] = useState(horizons[0]);
  const [example, setExample] = useState<"best" | "worst">("best");
  const fmtValue = isRatio(taskKey) ? (n: number) => formatPercent(n, 1) : (n: number) => formatNumber(Math.round(n));
  const fmtTick = isRatio(taskKey) ? (n: number) => formatPercent(n, 0) : formatCompact;
  const fmtErr = (n: number) => formatError(task, n, 1);
  const problem = PROBLEM[taskKey];
  const weightedBias = isRatio(taskKey) ? task.seat_weighted_bias : undefined;
  const points = (n: number) => `${n > 0 ? "+" : ""}${(n * 100).toFixed(2)} pts`;

  const monthly = task.monthly.filter((m) => m.horizon === horizon);
  const series: Series[] = [
    { name: "Actual", values: monthly.map((m) => m.actual), color: SERIES_COLORS.actual, width: 2.4 },
    { name: "LightGBM", values: monthly.map((m) => m.model), color: SERIES_COLORS.model },
    { name: task.best_baseline, values: monthly.map((m) => m.baseline), color: SERIES_COLORS.baseline, dashed: true },
  ];
  const baselineNames = Object.keys(task.baselines);
  const res = task.residuals;
  const resFormat = res.unit === "percentage points" ? (n: number) => `${n.toFixed(0)}` : (n: number) => `${Math.round(n * 100)}%`;

  return (
    <div className="grid gap-5">
      <Card title={task.title} subtitle={`${problem.unit} · ${formatNumber(task.rows)} validation rows · ${formatNumber(task.rows_fit)} training rows · ${task.best_iteration} trees`}>
        <p className="max-w-3xl text-[13.5px] leading-relaxed text-ink-2">{problem.what}</p>
        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatTile label={`LightGBM, ${task.metric}`} value={formatError(task, task.lightgbm.value)} sub={ci(task, task.lightgbm.ci95)} />
          <StatTile label={`Best baseline, ${task.metric}`} value={formatError(task, task.baselines[task.best_baseline].value)} sub={task.best_baseline} />
          <StatTile
            label="Difference (LightGBM − baseline)"
            value={formatDifference(task, task.difference_vs_best_baseline.value)}
            sub={task.beats_best_baseline ? "Conclusive: interval excludes zero" : "Not conclusive: interval includes zero"}
          />
          <StatTile
            label={weightedBias ? "Bias, seat-weighted" : isRatio(taskKey) ? "Relative bias, unweighted" : "Bias"}
            value={weightedBias ? points(weightedBias.value) : formatPercent(task.bias.value)}
            sub={weightedBias ? "Signed occupancy error in percentage points" : task.bias.value < 0 ? "Under-forecast of the actual total" : "Over-forecast of the actual total"}
          />
        </div>
        <ul className="mt-5 space-y-1.5 text-[13px] leading-relaxed text-ink-2">
          {findings(task).map((f) => (
            <li key={f} className="flex gap-2">
              <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-chart-1" />
              {f}
            </li>
          ))}
        </ul>
      </Card>

      {taskKey.startsWith("d_") && (
        <Card title="Historical v1 training caveat">
          <p className="text-[13px] leading-relaxed text-ink-2">The audit found that four globally missing source months were treated as zero targets in v1 route training. The loader is corrected for future runs; frozen models and the 2023 scores shown here are unchanged. A new model version and fresh evaluation are required before adoption.</p>
        </Card>
      )}
      <Card
        title="Actual vs predicted, by target month"
        subtitle={isRatio(taskKey) ? "Seat-weighted load factor across all scored units" : `Total ${task.unit} across all scored units`}
        action={<MetricTabs options={horizons.map((h) => ({ key: String(h), label: `${h} mo ahead` }))} value={String(horizon)} onChange={(v) => setHorizon(Number(v))} />}
      >
        <LinesChart
          label={`${task.title}: actual vs predicted by target month, ${horizon} months ahead`}
          labels={monthly.map((m) => MONTHS[Number(m.month.slice(5, 7)) - 1])}
          series={series}
          valueFormat={fmtValue}
          tickFormat={fmtTick}
          tickEvery={1}
        />
        <p className="mt-3 text-xs leading-relaxed text-muted">X: target month in 2023. Y: {isRatio(taskKey) ? "seat-weighted occupancy, using observed seats for every series" : task.unit}. This selector changes only this monthly chart. Aggregation can hide offsetting unit-level errors; the baseline here is the best overall baseline, which can differ from the best at one horizon.</p>
        <div className="mt-3">
          <Legend series={series} />
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Error by horizon" subtitle="Lower is better. Every method is scored on the same rows.">
          <DataTable
            caption="Error by horizon"
            columns={["Horizon", "LightGBM", ...baselineNames, isRatio(taskKey) ? "Seat-weighted bias (pts)" : "Bias"]}
            alignRight={Array.from({ length: baselineNames.length + 2 }, (_, i) => i + 1)}
            rows={task.by_horizon.map((h) => [
              `${h.horizon} mo`,
              fmtErr(h.model),
              ...baselineNames.map((n) => fmtErr(h.baselines[n])),
              isRatio(taskKey) && h.seat_weighted_bias_model != null ? points(h.seat_weighted_bias_model) : h.bias_model == null ? "—" : formatPercent(h.bias_model),
            ])}
          />
          <p className="mt-3 text-xs leading-relaxed text-muted">All other summaries pool horizons. A smaller point estimate alone does not establish an improvement; horizon-specific intervals are documented in the experiment results.</p>
        </Card>
        <Card title="Error by traffic volume" subtitle="Deciles of the unit's level known at the cutoff, never the target. 1 = smallest.">
          <LinesChart
            label="Error by decile of traffic volume"
            labels={task.by_volume_decile.map((d) => `D${d.decile}`)}
            series={[
              { name: "LightGBM", values: task.by_volume_decile.map((d) => d.model), color: SERIES_COLORS.model },
              { name: task.best_baseline, values: task.by_volume_decile.map((d) => d.baseline), color: SERIES_COLORS.baseline, dashed: true },
            ]}
            valueFormat={fmtErr}
            tickFormat={(n) => formatError(task, n, 0)}
            height={220}
            zero
            tickEvery={1}
          />
          <p className="mt-3 text-xs leading-relaxed text-muted">X: validation-sample decile of a historical feature. Y: prediction error, lower is better. Decile boundaries are descriptive and estimated on validation; they are not fixed production thresholds.</p>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title={`Largest units, by ${problem.entity}`} subtitle="Pooled-horizon error on the 10 largest by observed 2023 volume; a retrospective ranking">
          <PairBars
            baselineName={task.best_baseline}
            format={fmtErr}
            rows={task.by_entity.slice(0, 10).map((e) => ({ label: e.entity, model: e.model, baseline: e.baseline }))}
          />
          <div className="mt-4">
            <Legend
              series={[
                { name: "LightGBM", color: SERIES_COLORS.model },
                { name: task.best_baseline, color: SERIES_COLORS.baseline },
              ]}
            />
          </div>
        </Card>
        <Card title="Residuals" subtitle={res.unit === "percentage points" ? "Predicted minus actual, in points (clipped at ±30)" : "(Predicted − actual) / actual, clipped at ±100%"}>
          <Histogram
            label="Residual distribution"
            edges={res.edges}
            xFormat={resFormat}
            groups={[
              { name: task.best_baseline, counts: res.baseline, color: SERIES_COLORS.baseline, opacity: 0.45 },
              { name: "LightGBM", counts: res.model, color: SERIES_COLORS.model, opacity: 0.9, narrow: true },
            ]}
          />
          <Legend series={[{name: "LightGBM", color: SERIES_COLORS.model}, {name: task.best_baseline, color: SERIES_COLORS.baseline}]} />
          <p className="mt-3 text-xs leading-relaxed text-muted">
            Y: unweighted validation-row count. Positive errors mean over-prediction. {formatNumber(res.rows)} of {formatNumber(task.rows)} rows are included; zero actual volumes are excluded for relative errors. Clipped tails accumulate in the outer bins, while the quantiles below use unclipped errors. This is not a future uncertainty band.
          </p>
          <p className="mt-3 text-xs leading-relaxed text-muted">
            Median: LightGBM {resFormat(res.model_quantiles.p50)}, baseline {resFormat(res.baseline_quantiles.p50)}. 80% of LightGBM residuals fall between{" "}
            {resFormat(res.model_quantiles.p10)} and {resFormat(res.model_quantiles.p90)}.
          </p>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Actual vs predicted, row level" subtitle={`Random sample of ${task.scatter.length} validation rows, 1 month ahead${isRatio(taskKey) ? "" : ", log scale"}`}>
          <Scatter points={task.scatter} log={!isRatio(taskKey)} format={fmtTick} label={`${task.title}: actual against LightGBM prediction`} />
          <p className="mt-3 text-xs leading-relaxed text-muted">X: observed {task.unit}. Y: LightGBM prediction. Below the diagonal means under-prediction. A fixed-seed sample is descriptive, not the data used to compute the headline score. Non-positive pairs are omitted on logarithmic axes.</p>
        </Card>
        <Card title="What the trees split on" subtitle="LightGBM gain importance of the selection model. Not SHAP, not a causal effect.">
          <BarList
            valueFormat={(n) => formatPercent(n, 1)}
            items={Object.entries(task.top_features_by_gain).map(([name, gain]) => ({ label: name, value: gain }))}
          />
          <p className="mt-3 text-xs leading-relaxed text-muted">Bars show each feature&apos;s share of total training split gain. Only the top 10 are shown, so their shares need not sum to 100%. Correlated features can share or substitute importance; this is not held-out permutation importance or a driver of causal effects.</p>
        </Card>
      </div>

      {task.examples && (
        <Card
          title="Retrospective hits and misses"
          subtitle={`Entities picked by pooled error among the ${taskKey === "a" ? "10 busiest airports" : "20 largest routes"}; lines show horizon 1 only. These are selected extremes, not representative samples.`}
          action={
            <MetricTabs
              options={[
                { key: "best", label: "Best" },
                { key: "worst", label: "Worst" },
              ]}
              value={example}
              onChange={setExample}
            />
          }
        >
          <ExampleChart task={task} example={task.examples[example]} valueFormat={fmtValue} tickFormat={fmtTick} />
        </Card>
      )}
    </div>
  );
}

function ExampleChart({
  task,
  example,
  valueFormat,
  tickFormat,
}: {
  task: ShowcaseTask;
  example: Example;
  valueFormat: (n: number) => string;
  tickFormat: (n: number) => string;
}) {
  const labels = example.points.map((p) => {
    const value = p.date ?? p.month ?? "";
    const month = MONTHS[Number(value.slice(5, 7)) - 1];
    return p.date ? `${month} ${value.slice(8, 10)}` : month;
  });
  const series: Series[] = [
    { name: "Actual", values: example.points.map((p) => p.actual), color: SERIES_COLORS.actual, width: 1.8 },
    { name: "LightGBM", values: example.points.map((p) => p.model), color: SERIES_COLORS.model, width: 1.5 },
    { name: task.best_baseline, values: example.points.map((p) => p.baseline), color: SERIES_COLORS.baseline, dashed: true, width: 1.3 },
  ];
  return (
    <>
      <p className="mb-3 text-[13.5px] text-ink">
        <span className="font-medium">{example.entity}</span>
        <span className="ml-2 text-muted">
          Pooled {task.metric} {formatError(task, example.model, 1)} (baseline {formatError(task, example.baseline, 1)})
        </span>
      </p>
      <LinesChart
        label={`${example.entity}: actual vs predicted`}
        labels={labels}
        series={series}
        valueFormat={valueFormat}
        tickFormat={tickFormat}
        tickEvery={labels.length > 40 ? 30 : 1}
      />
      <div className="mt-3">
        <Legend series={series} />
      </div>
    </>
  );
}
