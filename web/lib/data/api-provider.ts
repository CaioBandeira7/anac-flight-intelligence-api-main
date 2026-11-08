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
 *   GET /v2/analytics/*        → filtered rankings and monthly series (docs/analytics.md)
 *
 * Responses may be a bare payload or an `{ data, meta }` envelope; both are
 * normalised here so components never change.
 */
import {
  DataProviderError,
  type AirportCatalog,
  type AnalystConfig,
  type CarrierCatalog,
  type AirportQuery,
  type AirportSeries,
  type AirportsPage,
  type CarrierQuery,
  type CarrierSeries,
  type CarriersPage,
  type Coverage,
  type PageQuery,
  type RouteQuery,
  type RouteSeries,
  type RoutesPage,
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

  /** `signal` lets a view cancel a request whose filters are no longer current. */
  private async get<T>(path: string, signal?: AbortSignal): Promise<Envelope<T>> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    const cancel = () => controller.abort();
    signal?.addEventListener("abort", cancel);
    const url = `${this.baseUrl}${path}`;
    try {
      const res = await this.fetchImpl(url, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
        const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${res.status})`;
        throw new DataProviderError(detail, res.status, path);
      }
      const body: unknown = await res.json();
      return normalise<T>(body);
    } catch (err) {
      if (err instanceof DataProviderError) throw err;
      if (signal?.aborted) throw new DataProviderError("Request cancelled", undefined, path, "cancelled");
      const aborted = err instanceof DOMException && err.name === "AbortError";
      throw new DataProviderError(aborted ? "Request timed out" : "Backend unreachable", undefined, path);
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", cancel);
    }
  }

  health() {
    return this.get<HealthStatus>("/health");
  }

  /** Coverage does not change while the app runs, so every view shares one request. */
  getCoverage() {
    return this.once<Coverage>("/v2/analytics/coverage");
  }
  private cached = new Map<string, Promise<Envelope<unknown>>>();

  /** One request per app session for data that does not change while it runs. */
  private once<T>(path: string): Promise<Envelope<T>> {
    let pending = this.cached.get(path) as Promise<Envelope<T>> | undefined;
    if (!pending) {
      pending = this.get<T>(path).catch((err: unknown) => {
        this.cached.delete(path);
        throw err;
      });
      this.cached.set(path, pending);
    }
    return pending;
  }

  getAirportCatalog() {
    return this.once<AirportCatalog>("/v2/analytics/airports/catalog");
  }
  getCarrierCatalog() {
    return this.once<CarrierCatalog>("/v2/analytics/carriers/catalog");
  }
  getAnalystConfig(): Promise<AnalystConfig> {
    return this.requestJson<AnalystConfig>("/v2/analyst/config", { method: "GET" }, this.timeoutMs);
  }

  getRouteRanking(query: RouteQuery & PageQuery, signal?: AbortSignal) {
    return this.get<RoutesPage>(`/v2/analytics/routes${toQuery(query)}`, signal);
  }
  getRouteSeries(query: RouteQuery, signal?: AbortSignal) {
    return this.get<RouteSeries>(`/v2/analytics/routes/monthly${toQuery(query)}`, signal);
  }
  getAirportRanking(query: AirportQuery & PageQuery, signal?: AbortSignal) {
    return this.get<AirportsPage>(`/v2/analytics/airports${toQuery(query)}`, signal);
  }
  getAirportSeries(query: AirportQuery & { airport: string }, signal?: AbortSignal) {
    return this.get<AirportSeries>(`/v2/analytics/airports/monthly${toQuery(query)}`, signal);
  }
  getCarrierRanking(query: CarrierQuery & PageQuery, signal?: AbortSignal) {
    return this.get<CarriersPage>(`/v2/analytics/carriers${toQuery(query)}`, signal);
  }
  getCarrierSeries(query: CarrierQuery & { carrier: string }, signal?: AbortSignal) {
    return this.get<CarrierSeries>(`/v2/analytics/carriers/monthly${toQuery(query)}`, signal);
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

/** Builds a query string, leaving out empty values. Values are encoded, never concatenated raw. */
export function toQuery(params: object): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
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
