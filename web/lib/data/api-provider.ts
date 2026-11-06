/**
 * ApiDataProvider — talks to the FastAPI backend.
 *
 * Endpoint mapping (v2 contract, to be implemented by the backend):
 *   GET /health                → HealthStatus        (exists today)
 *   GET /v2/overview           → OverviewData
 *   GET /v2/airports           → AirportStat[]
 *   GET /v2/routes             → RouteStat[]
 *   GET /v2/models             → ModelCard[]
 *   GET /v2/datasets           → DatasetInfo[]
 *   GET /v2/modules            → ModuleDescription[]
 *   GET /v2/analyst/catalog    → AnalystCatalog
 *
 * Responses may be a bare payload or an `{ data, meta }` envelope; both are
 * normalised here so components never change.
 */
import {
  DataProviderError,
  type AirportStat,
  type AnalystCatalog,
  type AnalystStatus,
  type ChatResponse,
  type ChatTurn,
  type DatasetInfo,
  type Envelope,
  type FlightDataProvider,
  type HealthStatus,
  type ModelCard,
  type ModuleDescription,
  type OverviewData,
  type ResponseMeta,
  type RouteStat,
} from "./contracts";

export interface ApiOptions {
  baseUrl: string;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
}

const ANALYST_TIMEOUT_MS = 90_000;

export class ApiDataProvider implements FlightDataProvider {
  readonly kind = "API" as const;
  readonly label = "ApiDataProvider";
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetchImpl: typeof fetch;

  constructor(opts: ApiOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/+$/, "");
    this.timeoutMs = opts.timeoutMs ?? 10_000;
    this.fetchImpl = opts.fetchImpl ?? ((...args) => fetch(...args));
  }

  private async get<T>(path: string): Promise<Envelope<T>> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    const url = `${this.baseUrl}${path}`;
    try {
      const res = await this.fetchImpl(url, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!res.ok) throw new DataProviderError(`Request failed (${res.status})`, res.status, path);
      const body: unknown = await res.json();
      return normalise<T>(body);
    } catch (err) {
      if (err instanceof DataProviderError) throw err;
      const aborted = err instanceof DOMException && err.name === "AbortError";
      throw new DataProviderError(aborted ? "Request timed out" : "Backend unreachable", undefined, path);
    } finally {
      clearTimeout(timer);
    }
  }

  health() {
    return this.get<HealthStatus>("/health");
  }
  getOverview() {
    return this.get<OverviewData>("/v2/overview");
  }
  getAirports() {
    return this.get<AirportStat[]>("/v2/airports");
  }
  getRoutes() {
    return this.get<RouteStat[]>("/v2/routes");
  }
  getModels() {
    return this.get<ModelCard[]>("/v2/models");
  }
  getDatasets() {
    return this.get<DatasetInfo[]>("/v2/datasets");
  }
  getModules() {
    return this.get<ModuleDescription[]>("/v2/modules");
  }
  getAnalystCatalog() {
    return this.get<AnalystCatalog>("/v2/analyst/catalog");
  }

  async getAnalystStatus(): Promise<AnalystStatus> {
    return this.requestJson<AnalystStatus>("/v2/analyst/status", { method: "GET" }, this.timeoutMs);
  }

  /** The API key stays on the server: this only sends the question. */
  async askAnalyst(question: string, history: ChatTurn[]): Promise<ChatResponse> {
    return this.requestJson<ChatResponse>(
      "/v2/analyst/chat",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, history }) },
      ANALYST_TIMEOUT_MS,
    );
  }

  private async requestJson<T>(path: string, init: RequestInit, timeoutMs: number): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await this.fetchImpl(`${this.baseUrl}${path}`, {
        ...init,
        headers: { Accept: "application/json", ...init.headers },
        signal: controller.signal,
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as { detail?: { code?: string; message?: string } } | null;
        throw new DataProviderError(body?.detail?.message ?? `Request failed (${res.status})`, res.status, path, body?.detail?.code);
      }
      return (await res.json()) as T;
    } catch (err) {
      if (err instanceof DataProviderError) throw err;
      const aborted = err instanceof DOMException && err.name === "AbortError";
      throw new DataProviderError(aborted ? "Request timed out" : "Backend unreachable", undefined, path);
    } finally {
      clearTimeout(timer);
    }
  }
}

function isEnvelope(x: unknown): x is { data: unknown; meta?: Partial<ResponseMeta> } {
  return typeof x === "object" && x !== null && "data" in x;
}

export function normalise<T>(body: unknown): Envelope<T> {
  const fallbackMeta: ResponseMeta = { source: "API", isDemo: false, generatedAt: new Date().toISOString() };
  if (isEnvelope(body)) {
    const meta = { ...fallbackMeta, ...(body.meta ?? {}) };
    // A backend may still serve sample data; respect its own flag.
    meta.isDemo = Boolean(body.meta?.isDemo);
    return { data: body.data as T, meta };
  }
  return { data: body as T, meta: fallbackMeta };
}
