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
  /** Monthly trend for the sparkline (oldest → newest). Empty when no time series exists. */
  trend: number[];
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

export interface FlightDataProvider {
  readonly kind: DataSourceKind;
  readonly label: string;
  health(): Promise<Envelope<HealthStatus>>;
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
