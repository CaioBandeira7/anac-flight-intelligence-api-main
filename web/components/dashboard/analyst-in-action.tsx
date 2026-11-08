"use client";

import { useEffect, useState } from "react";
import { CircleCheck, CircleX, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import { MetricTabs } from "./analytics-controls";
import { Card, DataTable, ErrorState, Skeleton } from "./ui";

/**
 * Recorded real runs of the analyst (reports/agent, Groq), verified independently against
 * the analytical tables by research/analyst-demo/build_cases.py. Nothing here calls a model.
 */
interface RecordedRun {
  file: string;
  case: number;
  question: string;
  status: "answered" | "no_data" | "unverified";
  answer: string;
  tool_calls: { name: string; arguments: Record<string, unknown> }[];
  sources: { endpoint: string; dataset: string; period: string; unit: string }[];
  rejected_drafts?: { answer: string; problems: string[] }[];
}

interface Verification {
  check: string;
  in_answer: unknown;
  independent: unknown;
  match: boolean;
  note: string;
}

interface DemoCase {
  id: string;
  title: string;
  business_problem: string;
  story?: string;
  runs: RecordedRun[];
  verification: Verification[];
  value: string;
  limits: string;
  checks_passed: number;
  checks_total: number;
}

interface CasesPayload {
  recorded: string;
  provider: string;
  model: string;
  note: string;
  cases: DemoCase[];
}

export const CASES_URL = "/analyst/cases.json";

const show = (value: unknown) =>
  typeof value === "number" ? value.toLocaleString("en-US") : Array.isArray(value) ? (value.length ? value.join(", ") : "none") : String(value);

const STATUS: Record<RecordedRun["status"], string> = {
  answered: "Answered",
  no_data: "No data",
  unverified: "Refused by the verifier",
};

function RunView({ run, final }: { run: RecordedRun; final: boolean }) {
  return (
    <li className={cn("rounded-xl border p-4", final ? "border-cyan/40 bg-cyan/[0.04]" : "border-line")}>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="text-muted">
          Recorded run · <code className="font-mono">{run.file}</code>, case {run.case}
        </span>
        <span className={cn("rounded-md px-1.5 py-0.5 font-medium", run.status === "answered" ? "text-success" : run.status === "unverified" ? "text-danger" : "text-ink-2")}>
          {STATUS[run.status]}
        </span>
      </div>
      <p className="mt-3 ml-auto w-fit max-w-[90%] rounded-xl bg-blue/15 px-3.5 py-2 text-[13.5px] text-ink">{run.question}</p>
      <div className="mt-3 space-y-1.5">
        {run.tool_calls.length === 0 ? (
          <p className="text-xs text-muted">No tool called.</p>
        ) : (
          run.tool_calls.map((call, i) => (
            <p key={i} className="flex items-start gap-2 font-mono text-[11.5px] text-ink-2">
              <Wrench className="mt-0.5 size-3.5 shrink-0 text-muted" aria-hidden />
              {call.name}({JSON.stringify(call.arguments)})
            </p>
          ))
        )}
      </div>
      {run.rejected_drafts?.map((draft, i) => (
        <p key={i} className="mt-3 rounded-lg border border-danger/30 px-3 py-2 text-xs text-ink-2">
          <span className="font-medium text-danger">Rejected draft:</span> {draft.answer} <span className="text-muted">({draft.problems.join("; ")})</span>
        </p>
      ))}
      <p className="mt-3 max-w-[95%] whitespace-pre-wrap rounded-xl border border-line bg-hover px-3.5 py-2.5 text-[13.5px] leading-relaxed text-ink-2">{run.answer}</p>
      {run.sources.length > 0 && (
        <p className="mt-2 text-[11.5px] text-muted">
          Source: {run.sources.map((s) => `${s.endpoint} (${s.period})`).join(" · ")}
        </p>
      )}
    </li>
  );
}

/** "AI Analyst in Action": what the analyst did on real questions, and whether it was right. */
export function AnalystInAction() {
  const [payload, setPayload] = useState<CasesPayload | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [active, setActive] = useState("market");

  useEffect(() => {
    let alive = true;
    fetch(CASES_URL, { headers: { Accept: "application/json" } })
      .then((res) => {
        if (!res.ok) throw new Error(`The recorded cases could not be loaded (${res.status})`);
        return res.json() as Promise<CasesPayload>;
      })
      .then(
        (data) => {
          if (!alive) return;
          setPayload(data);
          setError(null);
        },
        (err: Error) => {
          if (alive) setError(err);
        },
      );
    return () => {
      alive = false;
    };
  }, [attempt]);

  if (error) return <ErrorState error={error} onRetry={() => setAttempt((n) => n + 1)} hint="The file is part of the web build." />;
  if (!payload) return <Skeleton className="h-64 w-full" />;
  const current = payload.cases.find((c) => c.id === active) ?? payload.cases[0];

  return (
    <section id="in-action" aria-labelledby="in-action-title" className="scroll-mt-24">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 id="in-action-title" className="text-[17px] font-semibold tracking-[-0.01em] text-ink">
              AI Analyst in Action
            </h2>
            <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-muted">
              Real runs recorded on {payload.recorded}, with {payload.provider} ({payload.model}). Not live, and not written for this page. Every
              figure is checked against the analytical tables, a path that does not go through the analyst&apos;s tools.
            </p>
          </div>
        </div>
        <div className="mt-4">
          <MetricTabs options={payload.cases.map((c) => ({ key: c.id, label: c.title }))} value={current.id} onChange={setActive} />
        </div>
      </Card>

      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card title={current.title} subtitle={current.business_problem}>
          {current.story && <p className="mb-4 text-[13px] leading-relaxed text-ink-2">{current.story}</p>}
          <ol className="space-y-4">
            {current.runs.map((run, i) => (
              <RunView key={`${run.file}-${run.case}`} run={run} final={i === current.runs.length - 1} />
            ))}
          </ol>
        </Card>
        <div className="grid content-start gap-5">
          <Card title="Independent verification" subtitle={`${current.checks_passed} of ${current.checks_total} checks agree with the data`}>
            <DataTable
              caption="Independent verification"
              columns={["Check", "In the answer", "In the data", ""]}
              rows={current.verification.map((v) => [
                v.check,
                show(v.in_answer),
                show(v.independent),
                v.match ? (
                  <CircleCheck key="ok" className="size-4 text-success" aria-label="Agrees" />
                ) : (
                  <CircleX key="no" className="size-4 text-danger" aria-label="Disagrees" />
                ),
              ])}
            />
            <ul className="mt-3 space-y-1.5 text-[11.5px] leading-relaxed text-muted">
              {current.verification.map((v) => (
                <li key={v.check}>
                  <span className="text-ink-2">{v.check}:</span> {v.note}
                </li>
              ))}
            </ul>
          </Card>
          <Card title="Why it matters">
            <p className="text-[13px] leading-relaxed text-ink-2">{current.value}</p>
            <h3 className="mt-4 text-[13px] font-medium text-ink">Limits</h3>
            <p className="mt-1 text-[13px] leading-relaxed text-ink-2">{current.limits}</p>
          </Card>
        </div>
      </div>
    </section>
  );
}
