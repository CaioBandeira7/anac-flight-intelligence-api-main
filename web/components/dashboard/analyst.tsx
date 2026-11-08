"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Bot, MessageCircle, RefreshCw, Send, X } from "lucide-react";
import { useDataProvider } from "@/components/data-provider";
import { useResource } from "@/hooks/use-resource";
import { DataProviderError, type ChatResponse, type ChatTurn } from "@/lib/data/contracts";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { AnalystInAction } from "./analyst-in-action";
import { Header, Loaded } from "./data-views";
import { Card, ErrorState, Skeleton } from "./ui";

/* ------------------------------------------------------------------ State */

/**
 * What the UI knows about the analyst, without guessing:
 * - `configured`: the server has a key. Not proof that the provider answers.
 * - `connected`: the provider answered, to "Check connection" or to a question.
 * Opening the chat reads only the local configuration and never contacts the provider.
 */
export type Availability =
  | { state: "checking" }
  | { state: "demo" }
  | { state: "unreachable" }
  | { state: "not_configured"; model?: string }
  | { state: "configured"; model: string }
  | { state: "connected"; model: string }
  | { state: "unavailable"; reason: string; model?: string };

const UNAVAILABLE_COPY: Record<string, string> = {
  not_configured: "The analyst is not configured on the server: GROQ_API_KEY is missing.",
  auth_failed: "The server could not authenticate with the model provider.",
  rate_limited: "The free usage limit was reached. Please try again shortly.",
  model_not_available: "The configured model is not available for this account.",
  demo_mode: "The analyst only works with real data, and this build runs on demonstration data.",
  timeout: "The model provider is taking too long to respond.",
  unavailable: "The model provider is unavailable right now.",
};

/** Reasons that will not clear by asking again. */
const BLOCKING = new Set(["not_configured", "auth_failed", "model_not_available"]);

export const canAsk = (a: Availability) =>
  a.state === "configured" || a.state === "connected" || (a.state === "unavailable" && !BLOCKING.has(a.reason));

export interface ChatEntry {
  question: string;
  response?: ChatResponse;
  error?: DataProviderError | Error;
}

interface AnalystState {
  entries: ChatEntry[];
  availability: Availability;
  busy: boolean;
  /** Reads the local configuration once. Safe to call on every open. */
  prepare: () => void;
  /** Explicit user action: asks the server to contact the model provider. */
  checkConnection: () => void;
  checking: boolean;
  ask: (question: string) => void;
}

const AnalystContext = createContext<AnalystState | null>(null);

/** Holds the conversation for the whole dashboard session, so it survives page changes. */
export function AnalystProvider({ children }: { children: ReactNode }) {
  const parent = useContext(AnalystContext);
  if (parent) return <>{children}</>;
  return <AnalystRoot>{children}</AnalystRoot>;
}

function AnalystRoot({ children }: { children: ReactNode }) {
  const provider = useDataProvider();
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [availability, setAvailability] = useState<Availability>({ state: "checking" });
  const [checking, setChecking] = useState(false);
  const started = useRef(false);
  const entriesRef = useRef(entries);
  useEffect(() => {
    entriesRef.current = entries;
  }, [entries]);

  const prepare = useCallback(() => {
    if (started.current) return;
    started.current = true;
    if (provider.kind === "DEMO") {
      setAvailability({ state: "demo" });
      return;
    }
    provider.getAnalystConfig().then(
      (config) => setAvailability(config.configured ? { state: "configured", model: config.model } : { state: "not_configured", model: config.model }),
      () => {
        started.current = false;
        setAvailability({ state: "unreachable" });
      },
    );
  }, [provider]);

  const checkConnection = useCallback(() => {
    if (provider.kind === "DEMO") return;
    setChecking(true);
    provider
      .getAnalystStatus()
      .then(
        (status) =>
          setAvailability(
            status.available
              ? { state: "connected", model: status.model }
              : status.reason === "not_configured"
                ? { state: "not_configured", model: status.model }
                : { state: "unavailable", reason: status.reason ?? "unavailable", model: status.model },
          ),
        () => setAvailability({ state: "unreachable" }),
      )
      .finally(() => setChecking(false));
  }, [provider]);

  const ask = useCallback(
    (question: string) => {
      // The request runs once, here. State updaters can run twice in development.
      const kept = entriesRef.current.filter((entry) => entry.question !== question || !entry.error);
      const history: ChatTurn[] = kept
        .filter((entry) => entry.response?.status === "answered")
        .slice(-3)
        .flatMap((entry) => [
          { role: "user" as const, content: entry.question.slice(0, 2000) },
          { role: "assistant" as const, content: (entry.response as ChatResponse).answer.slice(0, 2000) },
        ]);
      setEntries([...kept, { question }]);
      const settle = (result: Partial<ChatEntry>) =>
        setEntries((list) => list.map((entry) => (entry.question === question && !entry.response && !entry.error ? { question, ...result } : entry)));
      provider.askAnalyst(question, history).then(
        (response) => {
          settle({ response });
          setAvailability((a) => (a.state === "configured" || a.state === "unavailable" ? { state: "connected", model: a.model ?? "" } : a));
        },
        (error: Error) => {
          settle({ error });
          const code = error instanceof DataProviderError ? error.code : undefined;
          if (code === "not_configured") setAvailability({ state: "not_configured" });
          else if (code && BLOCKING.has(code)) setAvailability({ state: "unavailable", reason: code });
        },
      );
    },
    [provider],
  );

  const busy = entries.some((entry) => !entry.response && !entry.error);
  const value = useMemo(
    () => ({ entries, availability, busy, prepare, checkConnection, checking, ask }),
    [entries, availability, busy, prepare, checkConnection, checking, ask],
  );
  return <AnalystContext.Provider value={value}>{children}</AnalystContext.Provider>;
}

export function useAnalyst(): AnalystState {
  const ctx = useContext(AnalystContext);
  if (!ctx) throw new Error("useAnalyst must be used inside <AnalystProvider>");
  return ctx;
}

/* --------------------------------------------------------------------- UI */

export const SUGGESTIONS = [
  "Which routes were the busiest in 2025?",
  "What is the difference between flights and movements?",
  "How should I read the load factor?",
  "What are the limitations of the forecasting models?",
];

function describe(a: Availability): { label: string; tone: "ok" | "wait" | "off" } {
  switch (a.state) {
    case "checking":
      return { label: "Checking…", tone: "wait" };
    case "configured":
      return { label: "Ready · connection not checked", tone: "wait" };
    case "connected":
      return { label: a.model ? `Connected · ${a.model}` : "Connected", tone: "ok" };
    case "demo":
      return { label: "Demo mode", tone: "off" };
    case "not_configured":
      return { label: "Not configured", tone: "off" };
    case "unreachable":
      return { label: "Backend unreachable", tone: "off" };
    case "unavailable":
      return { label: "Unavailable", tone: "off" };
  }
}

function unavailableMessage(a: Availability): string | null {
  if (a.state === "demo") return UNAVAILABLE_COPY.demo_mode;
  if (a.state === "not_configured") return UNAVAILABLE_COPY.not_configured;
  if (a.state === "unreachable") return "The backend is not reachable. Check that the API is running.";
  if (a.state === "unavailable") return UNAVAILABLE_COPY[a.reason] ?? UNAVAILABLE_COPY.unavailable;
  return null;
}

export function AvailabilityBadge({ availability }: { availability: Availability }) {
  const { label, tone } = describe(availability);
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted">
      <span className={cn("size-1.5 rounded-full", tone === "ok" ? "bg-success" : tone === "wait" ? "bg-demo" : "bg-danger")} aria-hidden />
      {label}
    </span>
  );
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
  const code = entry.error instanceof DataProviderError ? entry.error.code : undefined;
  return (
    <div className="space-y-3">
      <p className="ml-auto w-fit max-w-[85%] whitespace-pre-wrap rounded-xl bg-blue/15 px-3.5 py-2.5 text-[13.5px] text-ink">{entry.question}</p>
      {entry.response ? (
        <div className="max-w-[92%] rounded-xl border border-line bg-hover px-3.5 py-3">
          <p className="whitespace-pre-wrap text-[13.5px] leading-relaxed text-ink-2">{entry.response.answer}</p>
          <SourceList response={entry.response} />
        </div>
      ) : entry.error ? (
        <ErrorState
          error={code && UNAVAILABLE_COPY[code] ? new Error(UNAVAILABLE_COPY[code]) : entry.error}
          onRetry={onRetry}
          hint="Please try again."
        />
      ) : (
        <div role="status" aria-label="The analyst is working" className="max-w-[70%] space-y-2 rounded-xl border border-line px-3.5 py-3">
          <Skeleton className="h-3 w-5/6" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      )}
    </div>
  );
}

function Welcome({ disabled, onPick }: { disabled: boolean; onPick: (q: string) => void }) {
  return (
    <div className="rounded-xl border border-line bg-hover px-4 py-4 text-[13px] leading-relaxed text-ink-2">
      <p className="flex items-center gap-2 font-medium text-ink">
        <Bot className="size-4 text-cyan" aria-hidden /> Hi! I&apos;m the ANAC Flight Intelligence assistant.
      </p>
      <p className="mt-2">
        I can help you read the indicators, understand airport traffic, analyse routes and airlines, and clarify questions about the data and the
        methodology.
      </p>
      <p className="mt-3 text-xs text-muted">Try asking:</p>
      <ul className="mt-2 space-y-1.5">
        {SUGGESTIONS.map((question) => (
          <li key={question}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onPick(question)}
              className="w-full rounded-lg border border-line px-3 py-2 text-left text-[12.5px] text-ink transition-colors hover:border-cyan/40 hover:bg-cyan/[0.06] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {question}
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[11.5px] text-muted">
        Answers come only from this project&apos;s data, with period, unit and source. It does not forecast: no prediction endpoint exists.
      </p>
    </div>
  );
}

/** The conversation itself: used by the floating panel and by the analyst page. */
export function AnalystChat({ className, autoFocus }: { className?: string; autoFocus?: boolean }) {
  const { entries, availability, busy, prepare, checkConnection, checking, ask } = useAnalyst();
  const [draft, setDraft] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => prepare(), [prepare]);
  useEffect(() => {
    end.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [entries]);
  useEffect(() => {
    if (autoFocus) input.current?.focus();
  }, [autoFocus]);

  const available = canAsk(availability);
  const message = unavailableMessage(availability);

  const send = (question: string) => {
    const text = question.trim();
    if (!text || !available || busy) return;
    ask(text);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!draft.trim() || !available || busy) return;
    send(draft);
    setDraft("");
  };

  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div aria-live="polite" className="scrollbar-thin min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
        {message && (
          <div role="alert" className="flex items-start justify-between gap-3 rounded-xl border border-demo/30 bg-demo/10 px-3.5 py-3 text-[13px] text-ink-2">
            <span>{message}</span>
            {availability.state !== "demo" && (
              <button type="button" onClick={checkConnection} disabled={checking} className="shrink-0 text-xs text-cyan hover:underline disabled:opacity-50">
                Check again
              </button>
            )}
          </div>
        )}
        {entries.length === 0 && <Welcome disabled={!available || busy} onPick={send} />}
        {entries.map((entry, index) => (
          <ChatMessage key={`${index}-${entry.question}`} entry={entry} onRetry={() => send(entry.question)} />
        ))}
        <div ref={end} />
      </div>
      <form className="mt-4 flex gap-2" onSubmit={submit}>
        <input
          ref={input}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={!available}
          maxLength={500}
          aria-label="Question for the analyst"
          placeholder={available ? "Ask about routes, airports or carriers" : "Unavailable"}
          className="min-w-0 flex-1 rounded-lg border border-line bg-hover px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus-visible:border-cyan disabled:cursor-not-allowed"
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
    </div>
  );
}

function ConnectionControl() {
  const { availability, checkConnection, checking } = useAnalyst();
  const checkable = availability.state === "configured" || availability.state === "unavailable" || availability.state === "unreachable";
  return (
    <div className="flex items-center gap-2">
      <AvailabilityBadge availability={availability} />
      {checkable && (
        <button
          type="button"
          onClick={checkConnection}
          disabled={checking}
          title="Asks the server to contact the model provider"
          aria-label="Check connection"
          className="grid size-7 place-items-center rounded-md text-muted hover:bg-hover hover:text-ink disabled:opacity-50"
        >
          <RefreshCw className={cn("size-3.5", checking && "animate-spin")} aria-hidden />
        </button>
      )}
    </div>
  );
}

const PANEL_ID = "analyst-panel";

/** Floating entry point, on every dashboard page except the analyst's own page. */
export function FloatingAnalyst() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  if (pathname === "/dashboard/analyst") return null;

  const close = () => {
    setOpen(false);
    button.current?.focus();
  };

  return (
    <>
      {open && (
        <section
          id={PANEL_ID}
          role="dialog"
          aria-modal="false"
          aria-label="AI Aviation Analyst"
          onKeyDown={(e) => e.key === "Escape" && close()}
          className="fixed bottom-24 right-5 z-40 flex h-[min(620px,calc(100dvh-8rem))] w-[min(400px,calc(100vw-2.5rem))] flex-col rounded-2xl border border-line-strong bg-glass-strong p-4 shadow-2xl shadow-black/30 backdrop-blur-2xl max-sm:inset-x-2 max-sm:bottom-2 max-sm:top-16 max-sm:h-auto max-sm:w-auto"
        >
          <header className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-ink">AI Aviation Analyst</h2>
              <ConnectionControl />
              <Link href="/dashboard/analyst#in-action" onClick={close} className="mt-1 inline-block text-xs text-cyan hover:underline">
                See recorded, verified examples
              </Link>
            </div>
            <button type="button" onClick={close} aria-label="Close analyst" className="grid size-8 place-items-center rounded-lg text-ink-2 hover:bg-hover">
              <X className="size-4" aria-hidden />
            </button>
          </header>
          <AnalystChat className="flex-1" autoFocus />
        </section>
      )}
      <button
        ref={button}
        type="button"
        onClick={() => (open ? close() : setOpen(true))}
        aria-expanded={open}
        aria-controls={PANEL_ID}
        aria-label={open ? "Close AI analyst" : "Open AI analyst"}
        className={cn(
          "fixed bottom-5 right-5 z-40 grid size-14 place-items-center rounded-full border border-line-strong bg-glass-strong text-cyan shadow-xl shadow-black/30 backdrop-blur-2xl transition-[transform,border-color] hover:scale-[1.04] hover:border-cyan/50",
          open && "max-sm:hidden",
        )}
      >
        {open ? <X className="size-5" aria-hidden /> : <MessageCircle className="size-6" aria-hidden />}
      </button>
    </>
  );
}

/** The analyst page: the same conversation, with what it can and cannot do. */
export function AnalystView() {
  return (
    <AnalystProvider>
      <AnalystPage />
    </AnalystProvider>
  );
}

function AnalystPage() {
  const provider = useDataProvider();
  const catalog = useResource(useCallback(() => provider.getAnalystCatalog(), [provider]));
  return (
    <>
      <Header href="/dashboard/analyst" state={catalog} />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Card title="Ask the analyst" action={<ConnectionControl />}>
          <AnalystChat className="h-[560px]" />
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
      <div className="mt-8">
        <AnalystInAction />
      </div>
    </>
  );
}
