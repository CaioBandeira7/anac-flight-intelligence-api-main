import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DataProviderRoot } from "@/components/data-provider";
import { AirportsView, AnalystView, MlStudioView, formatMetric } from "@/components/dashboard/data-views";
import { ApiDataProvider, DataProviderError, MockDataProvider, type FlightDataProvider, type ModelCard } from "@/lib/data";

const meta = { source: "API" as const, isDemo: false, generatedAt: "2026-11-06T00:00:00Z" };
const ON = "validation (2023-01 to 2023-12)";

const CARDS: ModelCard[] = [
  { id: "baseline-a", module: "a", name: "Flight movements", task: "movements", pipeline: "p", status: "available", lastTrainedAt: null, selected: true, method: "Baseline: same weekday, recent 8 weeks", note: "LightGBM did not beat this baseline on validation, so this rule is used.", metrics: [{ name: "WAPE, movements", value: 0.103, evaluatedOn: ON, unit: "percent" }] },
  { id: "lightgbm-a", module: "a", name: "Flight movements", task: "movements", pipeline: "p", status: "available", lastTrainedAt: null, selected: false, method: "LightGBM", metrics: [{ name: "WAPE, movements", value: 0.101, evaluatedOn: ON, unit: "percent" }] },
  { id: "lightgbm-b", module: "b", name: "Occupancy", task: "load factor", pipeline: "p", status: "available", lastTrainedAt: null, selected: true, method: "LightGBM", metrics: [{ name: "MAE, load factor", value: 0.0606, evaluatedOn: ON, unit: "points" }] },
  { id: "module-c", module: "c", name: "Baggage", task: "t", pipeline: "p", status: "not_trained", lastTrainedAt: null, metrics: null },
];

function withProvider(overrides: Partial<FlightDataProvider>, ui: React.ReactNode) {
  const provider = Object.assign(new MockDataProvider({ latencyMs: 0 }), overrides) as FlightDataProvider;
  return render(<DataProviderRoot provider={provider}>{ui}</DataProviderRoot>);
}

describe("ML Studio", () => {
  it("marks the method in use per module and labels results as 2023 validation", async () => {
    withProvider({ getModels: () => Promise.resolve({ data: CARDS, meta }) }, <MlStudioView />);
    const moduleA = (await screen.findByText(/Module A/)).closest("section") as HTMLElement;
    expect(within(moduleA).getByText("Baseline: same weekday, recent 8 weeks").parentElement).toHaveTextContent("In use");
    expect(within(moduleA).getByText("LightGBM").parentElement).not.toHaveTextContent("In use");
    const moduleB = screen.getByText(/Module B/).closest("section") as HTMLElement;
    expect(within(moduleB).getByText("LightGBM").parentElement).toHaveTextContent("In use");
    expect(screen.getByText(/validation results for 2023/)).toBeInTheDocument();
    expect(screen.getByText(/not current forecasts/)).toBeInTheDocument();
    expect(screen.getByText(/Not trained/)).toBeInTheDocument();
  });

  it("formats metrics without changing their value", () => {
    expect(formatMetric({ name: "w", value: 0.103, evaluatedOn: ON, unit: "percent" })).toBe("10.30%");
    expect(formatMetric({ name: "m", value: 0.0606, evaluatedOn: ON, unit: "points" })).toBe("6.06 pts");
  });

  it("never shows a metric on demo data", async () => {
    withProvider({}, <MlStudioView />);
    expect((await screen.findAllByText(/No metrics to report/)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/%$/)).not.toBeInTheDocument();
  });
});

describe("data states", () => {
  it("shows an error with retry when the API fails", async () => {
    withProvider({ getAirports: () => Promise.reject(new Error("Backend unreachable")) }, <AirportsView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unreachable");
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("shows an empty state instead of an empty table", async () => {
    withProvider({ getAirports: () => Promise.resolve({ data: [], meta }) }, <AirportsView />);
    expect(await screen.findByText("No airport data was returned.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

describe("AI Aviation Analyst", () => {
  const status = { available: true, provider: "groq", model: "m", reason: null };

  it("stays disabled on demo data and generates no answers", async () => {
    withProvider({}, <AnalystView />);
    expect(await screen.findByText(/only works with real data/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /question/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("shows the answer with its period, unit and source", async () => {
    const askAnalyst = vi.fn(() =>
      Promise.resolve({
        status: "answered" as const,
        answer: "CGH to SDU carried 1,968,523 paid passengers.",
        sources: [{ endpoint: "/v2/routes", dataset: "flights", period: "2025-01 to 2025-12", unit: "paid passengers", generated_at: "x" }],
        caveats: ["Only the 200 busiest routes are available."],
      }),
    );
    withProvider({ getAnalystStatus: () => Promise.resolve(status), askAnalyst }, <AnalystView />);
    const input = await screen.findByRole("textbox", { name: /question/i });
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { value: "Busiest route?" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByText(/1,968,523/)).toBeInTheDocument();
    expect(screen.getByText(/Period: 2025-01 to 2025-12/)).toBeInTheDocument();
    expect(screen.getByText("/v2/routes")).toBeInTheDocument();
    expect(askAnalyst).toHaveBeenCalledWith("Busiest route?", []);
  });

  it("shows a usage limit message with retry", async () => {
    const askAnalyst = vi.fn(() => Promise.reject(new DataProviderError("The free usage limit was reached", 429, "/v2/analyst/chat", "rate_limited")));
    withProvider({ getAnalystStatus: () => Promise.resolve(status), askAnalyst }, <AnalystView />);
    const input = await screen.findByRole("textbox", { name: /question/i });
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { value: "Q" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("free usage limit");
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("explains when the server has no key", async () => {
    withProvider(
      { getAnalystStatus: () => Promise.resolve({ ...status, available: false, reason: "not_configured" }) },
      <AnalystView />,
    );
    expect(await screen.findByText(/not configured on the server/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /question/i })).toBeDisabled();
  });
});

describe("ApiDataProvider", () => {
  it("reads the module and analyst endpoints", async () => {
    const fetchImpl = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ data: [], meta }), { status: 200 })));
    const api = new ApiDataProvider({ baseUrl: "http://api.test", fetchImpl });
    await api.getModules();
    await api.getAnalystCatalog();
    expect(fetchImpl).toHaveBeenCalledWith("http://api.test/v2/modules", expect.anything());
    expect(fetchImpl).toHaveBeenCalledWith("http://api.test/v2/analyst/catalog", expect.anything());
  });
});

// Runs only against a live backend: ANAC_API_URL=http://127.0.0.1:8000 npm test
describe.runIf(process.env.ANAC_API_URL)("live API", () => {
  it("serves real payloads the components can read", async () => {
    const api = new ApiDataProvider({ baseUrl: process.env.ANAC_API_URL as string, timeoutMs: 20_000 });
    const overview = await api.getOverview();
    expect(overview.meta.isDemo).toBe(false);
    expect(overview.data.kpis.map((k) => k.id).sort()).toEqual(["active_routes", "flights", "load_factor", "passengers"]);
    const models = (await api.getModels()).data;
    const inUse = Object.fromEntries(models.filter((m) => m.selected).map((m) => [m.module, m.method]));
    expect(inUse.a).toMatch(/^Baseline/);
    expect(inUse.b).toBe("LightGBM");
    expect(inUse.d).toBe("LightGBM");
    for (const model of models.filter((m) => m.metrics)) {
      for (const metric of model.metrics ?? []) expect(metric.evaluatedOn).toMatch(/2023/);
    }
    expect((await api.getAirports()).data.length).toBeGreaterThan(0);
    expect((await api.getRoutes()).data.length).toBeGreaterThan(0);
    expect((await api.getModules()).data).toHaveLength(3);
    expect((await api.getAnalystCatalog()).data.must_not_claim.length).toBeGreaterThan(0);
  }, 30_000);

  it("renders ML Studio from the real API", async () => {
    const api = new ApiDataProvider({ baseUrl: process.env.ANAC_API_URL as string, timeoutMs: 20_000 });
    render(<DataProviderRoot provider={api}><MlStudioView /></DataProviderRoot>);
    const moduleA = (await screen.findByText(/Module A/, undefined, { timeout: 20_000 })).closest("section") as HTMLElement;
    expect(within(moduleA).getByText("10.30%")).toBeInTheDocument();
    expect(within(moduleA).getByText(/^Baseline:/).parentElement).toHaveTextContent("In use");
    const moduleB = screen.getByText(/Module B/).closest("section") as HTMLElement;
    expect(within(moduleB).getByText("LightGBM").parentElement).toHaveTextContent("In use");
    expect(within(moduleB).getByText("6.06 pts")).toBeInTheDocument();
  }, 30_000);
});
