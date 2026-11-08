/**
 * Data contracts shared by every data provider.
 *
 * The visual components consume ONLY these types. Swapping the
 * MockDataProvider for the ApiDataProvider must not require touching
 * any component.
 */

export type DataSourceKind = "DEMO" | "API";

/** Provenance attached to every response, so the UI can label it honestly. */
export interface ResponseMeta {
  source: DataSourceKind;
  /** True for any synthetic/demonstration data. The UI must show a DEMO badge. */
  isDemo: boolean;
  generatedAt: string; // ISO timestamp
  /** Human-readable note shown next to the data (e.g. coverage, caveats). */
  note?: string;
}

export interface Envelope<T> {
  data: T;
  meta: ResponseMeta;
}

export interface Kpi {
  id: "flights" | "passengers" | "load_factor" | "active_routes";
  label: string;
  value: number;
  unit?: "count" | "ratio";
  /** Relative change vs. the previous period, e.g. 0.042 = +4.2%. */
  delta?: number | null;
  /** Monthly trend for the sparkline (oldest → newest). `null` marks a month without data. */
  trend: (number | null)[];
}

export interface MonthlyPoint {
  month: string; // YYYY-MM
  passengers: number;
  flights: number;
}

export interface AirportStat {
  icao: string;
  iata: string;
  name: string;
  city: string;
  uf: string;
  lat: number;
  lon: number;
  movements: number;
}

export interface RouteStat {
  origin: string; // IATA
  destination: string; // IATA
  passengers: number;
  loadFactor: number; // 0–1
}

export type ModelStatus = "not_trained" | "training" | "available" | "deprecated";

export interface ModelMetric {
  name: string;
  value: number;
  /** Split / evaluation set the metric was computed on. Required: no orphan metrics. */
  evaluatedOn: string;
  /** How to display the value: percent (WAPE) or percentage points (MAE on a ratio). */
  unit?: "percent" | "points" | null;
}

export interface ModelCard {
  id: string;
  name: string;
  task: string;
  /** Backend script / pipeline that produces the model. */
  pipeline: string;
  status: ModelStatus;
  /** Real evaluation metrics only. `null` until the backend reports them. */
  metrics: ModelMetric[] | null;
  lastTrainedAt: string | null;
  /** Forecasting module this card belongs to (a, b, c, d). */
  module?: string | null;
  /** Method name, e.g. "LightGBM" or "Baseline: same month last year". */
  method?: string | null;
  /** True for the method actually used by the module. */
  selected?: boolean | null;
  note?: string | null;
}

export interface DatasetInfo {
  name: string;
  description: string;
  approxSize: string;
  status: "ingesting" | "ready" | "planned";
}

export interface OverviewData {
  period: { from: string; to: string };
  kpis: Kpi[];
  monthly: MonthlyPoint[];
  topRoutes: RouteStat[];
  topAirports: AirportStat[];
}

export interface ModuleFeature {
  name: string;
  type: string;
  source: string;
  description: string;
}

export interface ModuleDescription {
  module: string;
  title: string;
  unit: string[];
  targets: Record<string, string>;
  primary_metric: string;
  features: ModuleFeature[];
}

/** What the AI Aviation Analyst may read and must state. The agent itself does not exist yet. */
export interface AnalystCatalog {
  version: number;
  dataset: string;
  tools: { name: string; endpoint: string; payload: string }[];
  facts_that_must_accompany_answers: string[];
  must_not_claim: string[];
}

export interface AnalystStatus {
  available: boolean;
  provider: string;
  model: string;
  reason: string | null;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatSource {
  endpoint: string;
  dataset: string;
  period: string;
  unit: string;
  generated_at: string;
}

export interface ChatResponse {
  status: "answered" | "no_data" | "unverified";
  answer: string;
  sources: ChatSource[];
  caveats: string[];
}

export interface HealthStatus {
  ok: boolean;
  version?: string;
  detail?: string;
}

/* ---- Analytical layer: /v2/analytics/* (see docs/analytics.md) ---- */

export interface Period {
  from: string; // YYYY-MM
  to: string; // YYYY-MM
}

/** Every analytics response states the period it actually covers and the months without data. */
export interface PeriodContext {
  period: Period;
  months_with_data: number;
  /** Months with no data at all. Never zeros: they are unknown. */
  absent_months: string[];
}

export interface PageInfo {
  total: number;
  limit: number;
  offset: number;
}

/** Passenger-scope measures shared by route and carrier rows. */
export interface PassengerMeasures {
  all_takeoffs: number;
  passenger_takeoffs: number;
  paid_passengers: number;
  seats: number;
  rpk: number;
  ask: number;
  /** Σ paid passengers / Σ seats. Null when no seats were offered. */
  load_factor_paid: number | null;
}

export interface AnalyticsRoute extends PassengerMeasures {
  origin: string; // ICAO
  destination: string; // ICAO
  origin_iata: string | null;
  destination_iata: string | null;
  is_international: boolean;
  distance_km: number | null;
  months_operated: number;
}

export interface RoutesPage extends PeriodContext, PageInfo {
  routes: AnalyticsRoute[];
}

export interface RoutePoint extends PassengerMeasures {
  month: string;
}

export interface RouteSeries extends PeriodContext {
  points: RoutePoint[];
}

export interface AirportMeasures {
  /** All operated legs, cargo included. */
  departures: number;
  arrivals: number;
  movements: number;
  /** Passenger scope. */
  departing_paid_passengers: number;
  arriving_paid_passengers: number;
}

export interface AnalyticsAirport extends AirportMeasures {
  airport: string; // ICAO
  iata: string | null;
  name: string | null;
  city: string | null;
  uf: string | null;
  country: string | null;
  months_operated: number;
}

export interface AirportsPage extends PeriodContext, PageInfo {
  airports: AnalyticsAirport[];
}

export interface AirportPoint extends AirportMeasures {
  month: string;
}

export interface AirportSeries extends PeriodContext {
  airport_found: boolean;
  points: AirportPoint[];
}

export interface AnalyticsCarrier extends PassengerMeasures {
  carrier: string; // ICAO
  iata: string | null;
  name: string | null;
  country: string | null;
  months_operated: number;
  international_paid_passengers: number;
  /** Share of every carrier's paid passengers in the same period. */
  market_share: number | null;
}

export interface CarriersPage extends PeriodContext, PageInfo {
  market_paid_passengers: number;
  carriers: AnalyticsCarrier[];
}

export interface CarrierPoint extends PassengerMeasures {
  month: string;
  market_paid_passengers: number;
  market_share: number | null;
}

export interface CarrierSeries extends PeriodContext {
  carrier_found: boolean;
  points: CarrierPoint[];
}

export interface Coverage {
  dataset: string;
  first_month: string;
  last_month: string;
  absent_months: string[];
  tables: Record<string, { rows: number; bytes: number }>;
  units: Record<string, string>;
}

/** One airport code, for search. `recent_movements` only orders suggestions. */
export interface AirportEntry {
  airport: string; // ICAO
  iata: string | null;
  name: string | null;
  city: string | null;
  uf: string | null;
  country: string | null;
  first_month: string;
  last_month: string;
  recent_movements: number;
}

export interface AirportCatalog {
  recent_period: Period;
  airports: AirportEntry[];
}

/** One carrier code, with its latest recorded name. Codes are not merged across companies. */
export interface CarrierEntry {
  carrier: string; // ICAO
  iata: string | null;
  name: string | null;
  country: string | null;
  name_variants: number;
  first_month: string;
  last_month: string;
  recent_paid_passengers: number;
}

export interface CarrierCatalog {
  recent_period: Period;
  carriers: CarrierEntry[];
}

/** Local check: is a key configured? It does not contact the model provider. */
export interface AnalystConfig {
  configured: boolean;
  provider: string;
  model: string;
}

export interface PeriodQuery {
  from?: string;
  to?: string;
}

export interface PageQuery {
  limit?: number;
  offset?: number;
}

export interface RouteQuery extends PeriodQuery {
  /** ICAO or IATA. */
  origin?: string;
  destination?: string;
}

export interface AirportQuery extends PeriodQuery {
  airport?: string;
}

export interface CarrierQuery extends PeriodQuery {
  carrier?: string;
}

export interface FlightDataProvider {
  readonly kind: DataSourceKind;
  readonly label: string;
  health(): Promise<Envelope<HealthStatus>>;
  getCoverage(): Promise<Envelope<Coverage>>;
  getAirportCatalog(): Promise<Envelope<AirportCatalog>>;
  getCarrierCatalog(): Promise<Envelope<CarrierCatalog>>;
  /** Without any request to the model provider. */
  getAnalystConfig(): Promise<AnalystConfig>;
  getRouteRanking(query: RouteQuery & PageQuery, signal?: AbortSignal): Promise<Envelope<RoutesPage>>;
  getRouteSeries(query: RouteQuery, signal?: AbortSignal): Promise<Envelope<RouteSeries>>;
  getAirportRanking(query: AirportQuery & PageQuery, signal?: AbortSignal): Promise<Envelope<AirportsPage>>;
  getAirportSeries(query: AirportQuery & { airport: string }, signal?: AbortSignal): Promise<Envelope<AirportSeries>>;
  getCarrierRanking(query: CarrierQuery & PageQuery, signal?: AbortSignal): Promise<Envelope<CarriersPage>>;
  getCarrierSeries(query: CarrierQuery & { carrier: string }, signal?: AbortSignal): Promise<Envelope<CarrierSeries>>;
  getOverview(): Promise<Envelope<OverviewData>>;
  getAirports(): Promise<Envelope<AirportStat[]>>;
  getRoutes(): Promise<Envelope<RouteStat[]>>;
  getModels(): Promise<Envelope<ModelCard[]>>;
  getDatasets(): Promise<Envelope<DatasetInfo[]>>;
  getModules(): Promise<Envelope<ModuleDescription[]>>;
  getAnalystCatalog(): Promise<Envelope<AnalystCatalog>>;
  getAnalystStatus(): Promise<AnalystStatus>;
  askAnalyst(question: string, history: ChatTurn[]): Promise<ChatResponse>;
}

export class DataProviderError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly endpoint?: string,
    /** Machine-readable reason sent by the backend, when there is one. */
    readonly code?: string,
  ) {
    super(message);
    this.name = "DataProviderError";
  }
}
