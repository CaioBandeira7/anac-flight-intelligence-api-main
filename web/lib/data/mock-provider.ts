/**
 * MockDataProvider — deterministic DEMONSTRATION data.
 *
 * Every number produced here is synthetic. Every response is flagged
 * `source: "DEMO"` / `isDemo: true`, and the UI renders a DEMO badge.
 * No ML performance metrics are generated: models are reported as
 * `not_trained` with `metrics: null` until the real backend provides them.
 */
import { AIRPORTS } from "./airports";
import type {
  AnalystCatalog,
  AnalystStatus,
  ChatResponse,
  ModuleDescription,
  AirportStat,
  DatasetInfo,
  Envelope,
  FlightDataProvider,
  HealthStatus,
  Kpi,
  ModelCard,
  MonthlyPoint,
  OverviewData,
  RouteStat,
} from "./contracts";

const DEMO_NOTE = "Synthetic demonstration data — not derived from ANAC records.";

/** Small deterministic PRNG (mulberry32) so DEMO values are stable across renders. */
export function seeded(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface MockOptions {
  /** Artificial latency, to exercise loading states. */
  latencyMs?: number;
  seed?: number;
  /** Fixed clock for reproducible `generatedAt` (tests). */
  now?: () => Date;
}

export class MockDataProvider implements FlightDataProvider {
  readonly kind = "DEMO" as const;
  readonly label = "MockDataProvider";
  private readonly latency: number;
  private readonly seed: number;
  private readonly now: () => Date;

  constructor(opts: MockOptions = {}) {
    this.latency = opts.latencyMs ?? 450;
    this.seed = opts.seed ?? 2026;
    this.now = opts.now ?? (() => new Date());
  }

  private async wrap<T>(data: T): Promise<Envelope<T>> {
    if (this.latency > 0) await new Promise((r) => setTimeout(r, this.latency));
    return {
      data,
      meta: { source: "DEMO", isDemo: true, generatedAt: this.now().toISOString(), note: DEMO_NOTE },
    };
  }

  private monthly(): MonthlyPoint[] {
    const rand = seeded(this.seed);
    const points: MonthlyPoint[] = [];
    const start = new Date(Date.UTC(2024, 9, 1)); // Oct 2024 → 24 months
    for (let i = 0; i < 24; i++) {
      const d = new Date(start);
      d.setUTCMonth(start.getUTCMonth() + i);
      const month = d.getUTCMonth();
      // Seasonality: peaks in Jan and Jul (Brazilian holidays), trough in May/Nov.
      const season = 1 + 0.11 * Math.cos(((month - 0) / 12) * 2 * Math.PI) + 0.06 * Math.cos(((month - 6) / 6) * 2 * Math.PI);
      const growth = 1 + i * 0.004;
      const noise = 1 + (rand() - 0.5) * 0.04;
      const passengers = Math.round(8_200_000 * season * growth * noise);
      points.push({
        month: `${d.getUTCFullYear()}-${String(month + 1).padStart(2, "0")}`,
        passengers,
        flights: Math.round(passengers / (128 + rand() * 6)),
      });
    }
    return points;
  }

  private airports(): AirportStat[] {
    const rand = seeded(this.seed + 1);
    const weights: Record<string, number> = { GRU: 1, CGH: 0.78, BSB: 0.64, GIG: 0.52, VCP: 0.44, CNF: 0.42, SDU: 0.36, REC: 0.35, SSA: 0.31, POA: 0.3, FOR: 0.27, CWB: 0.25 };
    return AIRPORTS.map((a) => ({
      ...a,
      movements: Math.round(290_000 * (weights[a.iata] ?? 0.08 + rand() * 0.12) * (0.95 + rand() * 0.1)),
    })).sort((x, y) => y.movements - x.movements);
  }

  private routes(): RouteStat[] {
    const rand = seeded(this.seed + 2);
    const pairs: [string, string][] = [
      ["CGH", "SDU"], ["GRU", "REC"], ["GRU", "SSA"], ["BSB", "GRU"], ["GRU", "POA"],
      ["CGH", "BSB"], ["GRU", "FOR"], ["CNF", "GRU"], ["GIG", "GRU"], ["CWB", "CGH"],
    ];
    return pairs
      .map(([origin, destination], i) => ({
        origin,
        destination,
        passengers: Math.round(2_400_000 * Math.pow(0.86, i) * (0.94 + rand() * 0.12)),
        loadFactor: 0.74 + rand() * 0.14,
      }))
      .sort((a, b) => b.passengers - a.passengers);
  }

  private kpis(monthly: MonthlyPoint[], routes: RouteStat[]): Kpi[] {
    const last12 = monthly.slice(-12);
    const prev12 = monthly.slice(-24, -12);
    const sum = (xs: MonthlyPoint[], k: "passengers" | "flights") => xs.reduce((s, p) => s + p[k], 0);
    const pax = sum(last12, "passengers");
    const paxPrev = sum(prev12, "passengers");
    const flights = sum(last12, "flights");
    const flightsPrev = sum(prev12, "flights");
    const lf = routes.reduce((s, r) => s + r.loadFactor, 0) / routes.length;
    return [
      { id: "passengers", label: "Passengers (12 mo)", value: pax, unit: "count", delta: pax / paxPrev - 1, trend: last12.map((p) => p.passengers) },
      { id: "flights", label: "Flights (12 mo)", value: flights, unit: "count", delta: flights / flightsPrev - 1, trend: last12.map((p) => p.flights) },
      { id: "load_factor", label: "Avg. load factor", value: lf, unit: "ratio", delta: null, trend: [] },
      { id: "active_routes", label: "Active domestic routes", value: 1186, unit: "count", delta: null, trend: [] },
    ];
  }

  health(): Promise<Envelope<HealthStatus>> {
    return this.wrap({ ok: true, version: "demo", detail: "Mock provider — no backend connected." });
  }

  getOverview(): Promise<Envelope<OverviewData>> {
    const monthly = this.monthly();
    const routes = this.routes();
    return this.wrap({
      period: { from: monthly[0].month, to: monthly[monthly.length - 1].month },
      kpis: this.kpis(monthly, routes),
      monthly,
      topRoutes: routes.slice(0, 6),
      topAirports: this.airports().slice(0, 8),
    });
  }

  getAirports() {
    return this.wrap(this.airports());
  }

  getRoutes() {
    return this.wrap(this.routes());
  }

  getModels(): Promise<Envelope<ModelCard[]>> {
    // Mirrors the backend pipelines. Status only — no invented metrics.
    const models: ModelCard[] = [
      { id: "airport-demand", name: "Airport demand", task: "Forecast passenger movements per airport", pipeline: "03_modelo_aeroporto.py", status: "not_trained", metrics: null, lastTrainedAt: null },
      { id: "seat-occupancy", name: "Seat occupancy", task: "Predict load factor per route", pipeline: "04_modelo_assentos.py", status: "not_trained", metrics: null, lastTrainedAt: null },
      { id: "fare-baggage", name: "Fare & baggage", task: "Estimate fares and baggage fees", pipeline: "05_modelos_preco_bagagem.py", status: "not_trained", metrics: null, lastTrainedAt: null },
      { id: "drift-monitor", name: "Drift monitor", task: "Detect distribution drift in incoming data", pipeline: "07_monitorar_drift.py", status: "not_trained", metrics: null, lastTrainedAt: null },
    ];
    return this.wrap(models);
  }

  getDatasets(): Promise<Envelope<DatasetInfo[]>> {
    return this.wrap([
      { name: "ANAC historical flight records", description: "Statistical air transport data being re-ingested by the new backend.", approxSize: "~20 GB", status: "ingesting" },
      { name: "Feature store", description: "Engineered features for the ML pipelines.", approxSize: "—", status: "planned" },
    ]);
  }

  getModules(): Promise<Envelope<ModuleDescription[]>> {
    return this.wrap([]);
  }

  /** Demo mode never talks to a model and never produces an answer. */
  getAnalystStatus(): Promise<AnalystStatus> {
    return Promise.resolve({ available: false, provider: "none", model: "none", reason: "demo_mode" });
  }

  askAnalyst(): Promise<ChatResponse> {
    return Promise.reject(new Error("The analyst is not available on demonstration data"));
  }

  getAnalystCatalog(): Promise<Envelope<AnalystCatalog>> {
    return this.wrap({ version: 1, dataset: "demo", tools: [], facts_that_must_accompany_answers: [], must_not_claim: [] });
  }
}
