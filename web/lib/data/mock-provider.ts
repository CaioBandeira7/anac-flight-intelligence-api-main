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
  AirportCatalog,
  AnalystConfig,
  CarrierCatalog,
  AirportQuery,
  AirportSeries,
  AirportsPage,
  AnalyticsAirport,
  CarrierQuery,
  CarrierSeries,
  CarriersPage,
  Coverage,
  PageQuery,
  PeriodContext,
  PeriodQuery,
  RouteQuery,
  RoutePoint,
  RouteSeries,
  RoutesPage,
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

  /* ---- Analytics: synthetic, shaped like /v2/analytics/*, flagged DEMO ---- */

  private demoSeries(scale: number): RoutePoint[] {
    return this.monthly().map((m) => {
      const paid = Math.round(m.passengers * scale);
      const seats = Math.round(paid / 0.82);
      const flights = Math.round(m.flights * scale);
      return { month: m.month, all_takeoffs: flights, passenger_takeoffs: flights, paid_passengers: paid, seats, rpk: paid * 800, ask: seats * 800, load_factor_paid: seats ? paid / seats : null };
    });
  }

  private context(query: PeriodQuery): PeriodContext & { months: string[] } {
    const all = this.monthly().map((m) => m.month);
    const from = query.from && query.from > all[0] ? query.from : all[0];
    const to = query.to && query.to < all[all.length - 1] ? query.to : all[all.length - 1];
    const months = all.filter((m) => m >= from && m <= to);
    return { period: { from, to }, months_with_data: months.length, absent_months: [], months };
  }

  private page<T>(rows: T[], query: PageQuery) {
    const limit = query.limit ?? 50;
    const offset = query.offset ?? 0;
    return { total: rows.length, limit, offset, rows: rows.slice(offset, offset + limit) };
  }

  private routeShares() {
    const routes = this.routes();
    const market = this.monthly().slice(-12).reduce((s, m) => s + m.passengers, 0);
    return routes.map((r) => ({ ...r, share: r.passengers / market }));
  }

  private matchRoute(query: RouteQuery) {
    const code = (v?: string) => v?.trim().toUpperCase();
    return this.routeShares().filter(
      (r) => (!query.origin || r.origin === code(query.origin)) && (!query.destination || r.destination === code(query.destination)),
    );
  }

  getCoverage(): Promise<Envelope<Coverage>> {
    const months = this.monthly();
    return this.wrap({ dataset: "demo", first_month: months[0].month, last_month: months[months.length - 1].month, absent_months: [], tables: {}, units: {} });
  }

  getAirportCatalog(): Promise<Envelope<AirportCatalog>> {
    const months = this.monthly();
    const span = { from: months[months.length - 12].month, to: months[months.length - 1].month };
    return this.wrap({
      recent_period: span,
      airports: this.demoAirports(12).map((a) => ({ airport: a.airport, iata: a.iata, name: a.name, city: a.city, uf: a.uf, country: a.country, first_month: months[0].month, last_month: span.to, recent_movements: a.movements })),
    });
  }

  getCarrierCatalog(): Promise<Envelope<CarrierCatalog>> {
    const months = this.monthly();
    const span = { from: months[months.length - 12].month, to: months[months.length - 1].month };
    const market = months.slice(-12).reduce((s, m) => s + m.passengers, 0);
    return this.wrap({
      recent_period: span,
      carriers: MockDataProvider.CARRIERS.map((c) => ({ carrier: c.carrier, iata: c.iata, name: c.name, country: "BRASIL", name_variants: 1, first_month: months[0].month, last_month: span.to, recent_paid_passengers: Math.round(market * c.share) })),
    });
  }

  /** Demo mode has no model provider. */
  getAnalystConfig(): Promise<AnalystConfig> {
    return Promise.resolve({ configured: false, provider: "none", model: "none" });
  }

  getRouteRanking(query: RouteQuery & PageQuery): Promise<Envelope<RoutesPage>> {
    const { months, ...context } = this.context(query);
    const market = this.demoSeries(1).filter((p) => months.includes(p.month));
    const rows = this.matchRoute(query).map((r) => {
      const points = market.map((p) => ({ paid: Math.round(p.paid_passengers * r.share), flights: Math.round(p.passenger_takeoffs * r.share) }));
      const paid = points.reduce((s, p) => s + p.paid, 0);
      const flights = points.reduce((s, p) => s + p.flights, 0);
      const seats = Math.round(paid / r.loadFactor);
      return { origin: r.origin, destination: r.destination, origin_iata: r.origin, destination_iata: r.destination, is_international: false, distance_km: null, months_operated: months.length, all_takeoffs: flights, passenger_takeoffs: flights, paid_passengers: paid, seats, rpk: paid * 800, ask: seats * 800, load_factor_paid: seats ? paid / seats : null };
    });
    const { rows: routes, ...page } = this.page(rows, query);
    return this.wrap({ ...context, ...page, routes });
  }

  getRouteSeries(query: RouteQuery): Promise<Envelope<RouteSeries>> {
    const { months, ...context } = this.context(query);
    const filtered = query.origin || query.destination;
    const scale = filtered ? this.matchRoute(query).reduce((s, r) => s + r.share, 0) : 1;
    return this.wrap({ ...context, points: this.demoSeries(scale).filter((p) => months.includes(p.month)) });
  }

  private demoAirports(months: number): AnalyticsAirport[] {
    return this.airports().map((a) => {
      const movements = Math.round((a.movements * months) / 12);
      const departures = Math.round(movements / 2);
      const paid = Math.round(departures * 125);
      return { airport: a.icao, iata: a.iata, name: a.name, city: a.city, uf: a.uf, country: "BRASIL", months_operated: months, departures, arrivals: movements - departures, movements, departing_paid_passengers: paid, arriving_paid_passengers: paid };
    });
  }

  getAirportRanking(query: AirportQuery & PageQuery): Promise<Envelope<AirportsPage>> {
    const { months, ...context } = this.context(query);
    const code = query.airport?.trim().toUpperCase();
    const rows = this.demoAirports(months.length).filter((a) => !code || a.airport === code || a.iata === code);
    const { rows: airports, ...page } = this.page(rows, query);
    return this.wrap({ ...context, ...page, airports });
  }

  getAirportSeries(query: AirportQuery & { airport: string }): Promise<Envelope<AirportSeries>> {
    const { months, ...context } = this.context(query);
    const code = query.airport.trim().toUpperCase();
    const airport = this.demoAirports(12).find((a) => a.airport === code || a.iata === code);
    const market = this.demoSeries(1).filter((p) => months.includes(p.month));
    const total = market.reduce((s, p) => s + p.all_takeoffs, 0) || 1;
    const points = airport
      ? market.map((p) => {
          // A 12-month total spread over the months in proportion to market takeoffs.
          const departures = Math.round((airport.departures * p.all_takeoffs * months.length) / total / 12);
          const paid = Math.round(departures * 125);
          return { month: p.month, departures, arrivals: departures, movements: departures * 2, departing_paid_passengers: paid, arriving_paid_passengers: paid };
        })
      : [];
    return this.wrap({ ...context, airport_found: Boolean(airport), points });
  }

  private static readonly CARRIERS = [
    { carrier: "DMA", iata: "D1", name: "Demo Carrier A", share: 0.38 },
    { carrier: "DMB", iata: "D2", name: "Demo Carrier B", share: 0.33 },
    { carrier: "DMC", iata: "D3", name: "Demo Carrier C", share: 0.29 },
  ];

  private matchCarrier(code?: string) {
    const wanted = code?.trim().toUpperCase();
    return MockDataProvider.CARRIERS.filter((c) => !wanted || c.carrier === wanted || c.iata === wanted);
  }

  getCarrierRanking(query: CarrierQuery & PageQuery): Promise<Envelope<CarriersPage>> {
    const { months, ...context } = this.context(query);
    const market = this.demoSeries(1).filter((p) => months.includes(p.month));
    const marketPaid = market.reduce((s, p) => s + p.paid_passengers, 0);
    const rows = this.matchCarrier(query.carrier).map((c) => {
      const t = market.reduce(
        (acc, p) => ({ paid: acc.paid + Math.round(p.paid_passengers * c.share), flights: acc.flights + Math.round(p.passenger_takeoffs * c.share), seats: acc.seats + Math.round(p.seats * c.share) }),
        { paid: 0, flights: 0, seats: 0 },
      );
      return { carrier: c.carrier, iata: c.iata, name: c.name, country: "BRASIL", months_operated: months.length, all_takeoffs: t.flights, passenger_takeoffs: t.flights, paid_passengers: t.paid, seats: t.seats, rpk: t.paid * 800, ask: t.seats * 800, international_paid_passengers: 0, load_factor_paid: t.seats ? t.paid / t.seats : null, market_share: marketPaid ? t.paid / marketPaid : null };
    });
    const { rows: carriers, ...page } = this.page(rows, query);
    return this.wrap({ ...context, market_paid_passengers: marketPaid, ...page, carriers });
  }

  getCarrierSeries(query: CarrierQuery & { carrier: string }): Promise<Envelope<CarrierSeries>> {
    const { months, ...context } = this.context(query);
    const carrier = this.matchCarrier(query.carrier)[0];
    const points = carrier
      ? this.demoSeries(1)
          .filter((p) => months.includes(p.month))
          .map((p) => {
            const paid = Math.round(p.paid_passengers * carrier.share);
            const seats = Math.round(p.seats * carrier.share);
            const flights = Math.round(p.passenger_takeoffs * carrier.share);
            return { month: p.month, all_takeoffs: flights, passenger_takeoffs: flights, paid_passengers: paid, seats, rpk: paid * 800, ask: seats * 800, load_factor_paid: seats ? paid / seats : null, market_paid_passengers: p.paid_passengers, market_share: paid / p.paid_passengers };
          })
      : [];
    return this.wrap({ ...context, carrier_found: Boolean(carrier), points });
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
