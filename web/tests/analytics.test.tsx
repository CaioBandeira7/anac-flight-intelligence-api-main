import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { DataProviderRoot } from "@/components/data-provider";
import { AirlinesView, AirportsView, RoutesView } from "@/components/dashboard/analytics-views";
import { AnalystChat, AnalystProvider, FloatingAnalyst } from "@/components/dashboard/analyst";
import { AirportCombobox } from "@/components/dashboard/entity-combobox";
import { Overview } from "@/components/dashboard/overview";
import { PeriodPicker } from "@/components/dashboard/period-picker";
import {
  ApiDataProvider,
  MockDataProvider,
  airportSearchable,
  carrierSearchable,
  comparePeriods,
  defaultPeriod,
  formatPeriod,
  highlight,
  isValidPeriod,
  monthRange,
  periodPresets,
  rank,
  withGaps,
  type AirportCatalog,
  type AirportEntry,
  type CarrierCatalog,
  type CarrierEntry,
  type CarriersPage,
  type Coverage,
  type Envelope,
  type FlightDataProvider,
  type Period,
  type RoutePoint,
  type RouteSeries,
  type RoutesPage,
} from "@/lib/data";
import { toQuery } from "@/lib/data/api-provider";

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard" }));

const meta = { source: "API" as const, isDemo: false, generatedAt: "2026-11-06T00:00:00Z" };
const COVERAGE: Coverage = { dataset: "flights", first_month: "2024-01", last_month: "2025-12", absent_months: ["2024-03"], tables: {}, units: {} };
const ok = <T,>(data: T): Promise<Envelope<T>> => Promise.resolve({ data, meta });

const airport = (airport: string, iata: string | null, name: string, city: string, uf: string | null, recent: number): AirportEntry => ({
  airport, iata, name, city, uf, country: uf ? "BRASIL" : "PORTUGAL", first_month: "2000-01", last_month: "2025-12", recent_movements: recent,
});
const AIRPORTS: AirportEntry[] = [
  airport("SBGR", "GRU", "GUARULHOS - GOVERNADOR ANDRÉ FRANCO MONTORO", "GUARULHOS", "SP", 287291),
  airport("SBSP", "CGH", "CONGONHAS", "SÃO PAULO", "SP", 200000),
  airport("SBRJ", "SDU", "SANTOS DUMONT", "RIO DE JANEIRO", "RJ", 150000),
  airport("SBKP", "VCP", "VIRACOPOS", "CAMPINAS", "SP", 100000),
  airport("LPPT", "LIS", "LISBOA", "LISBOA", null, 5000),
];
const carrier = (carrier: string, iata: string | null, name: string, last = "2025-12"): CarrierEntry => ({
  carrier, iata, name, country: "BRASIL", name_variants: 1, first_month: "2000-01", last_month: last, recent_paid_passengers: 0,
});
const CARRIERS: CarrierEntry[] = [
  carrier("TAM", "JJ", "TAM LINHAS AÉREAS S.A."),
  carrier("GLO", "G3", "GOL LINHAS AÉREAS S.A. (EX- VRG LINHAS AÉREAS S.A.)"),
  carrier("AZU", "AD", "AZUL LINHAS AÉREAS BRASILEIRAS S/A"),
  carrier("LAN", "LA", "LATAM AIRLINES GROUP (EX - LAN AIRLINES S/A)"),
  carrier("ONE", "O6", "OCEANAIR LINHAS AÉREAS S.A. (AVIANCA)", "2019-04"),
];
const airportCatalog: AirportCatalog = { recent_period: { from: "2025-01", to: "2025-12" }, airports: AIRPORTS };
const carrierCatalog: CarrierCatalog = { recent_period: { from: "2025-01", to: "2025-12" }, carriers: CARRIERS };

function point(month: string, paid: number, seats: number, flights = 100): RoutePoint {
  return { month, all_takeoffs: flights, passenger_takeoffs: flights, paid_passengers: paid, seats, rpk: 0, ask: 0, load_factor_paid: seats ? paid / seats : null };
}

/** A series over `period` that leaves out absent months, as the API does. */
function series(period: Period, make: (month: string) => RoutePoint): RouteSeries {
  const months = monthRange(period).filter((m) => !COVERAGE.absent_months.includes(m));
  return { period, months_with_data: months.length, absent_months: COVERAGE.absent_months.filter((m) => m >= period.from && m <= period.to), points: months.map(make) };
}

function routesPage(period: Period, rows: Partial<RoutesPage["routes"][number]>[]): RoutesPage {
  return {
    period,
    months_with_data: 12,
    absent_months: [],
    total: rows.length,
    limit: 25,
    offset: 0,
    routes: rows.map((r) => ({ origin: "SBSP", destination: "SBRJ", origin_iata: "CGH", destination_iata: "SDU", is_international: false, distance_km: 366, months_operated: 12, all_takeoffs: 10, passenger_takeoffs: 10, paid_passengers: 1000, seats: 1200, rpk: 0, ask: 0, load_factor_paid: 0.8333, ...r })),
  };
}

function withProvider(overrides: Partial<FlightDataProvider>, ui: React.ReactNode) {
  const provider = Object.assign(new MockDataProvider({ latencyMs: 0 }), {
    getCoverage: () => ok(COVERAGE),
    getAirportCatalog: () => ok(airportCatalog),
    getCarrierCatalog: () => ok(carrierCatalog),
    ...overrides,
  }) as FlightDataProvider;
  return render(<DataProviderRoot provider={provider}>{ui}</DataProviderRoot>);
}

const codes = (items: { iata: string | null }[]) => items.map((i) => i.iata);

describe("periods", () => {
  it("defaults to the last 12 months of the dataset", () => {
    expect(defaultPeriod(COVERAGE)).toEqual({ from: "2025-01", to: "2025-12" });
  });

  it("formats periods for reading", () => {
    expect(formatPeriod({ from: "2025-01", to: "2025-12" })).toBe("Jan 2025 – Dec 2025");
    expect(formatPeriod({ from: "2025-03", to: "2025-03" })).toBe("Mar 2025");
  });

  it("accepts only ordered periods inside the coverage", () => {
    expect(isValidPeriod({ from: "2024-02", to: "2025-01" }, COVERAGE)).toBe(true);
    expect(isValidPeriod({ from: "2025-05", to: "2025-01" }, COVERAGE)).toBe(false);
    expect(isValidPeriod({ from: "2023-12", to: "2025-01" }, COVERAGE)).toBe(false);
    expect(isValidPeriod({ from: "2025-01", to: "2026-01" }, COVERAGE)).toBe(false);
    expect(isValidPeriod({ from: "2025-1", to: "2025-12" }, COVERAGE)).toBe(false);
    expect(isValidPeriod({ from: "2025-01" }, COVERAGE)).toBe(false);
  });

  it("offers presets that end on covered months", () => {
    const presets = Object.fromEntries(periodPresets(COVERAGE).map((p) => [p.id, p]));
    expect(presets["3m"].period).toEqual({ from: "2025-10", to: "2025-12" });
    expect(presets["6m"].period).toEqual({ from: "2025-07", to: "2025-12" });
    expect(presets["12m"].period).toEqual({ from: "2025-01", to: "2025-12" });
    expect(presets.year).toMatchObject({ label: "2025", period: { from: "2025-01", to: "2025-12" } });
    expect(presets["previous-year"].period).toEqual({ from: "2024-01", to: "2024-12" });
    expect(presets.all.period).toEqual({ from: "2024-01", to: "2025-12" });
    // A partial last year is labelled as such, and nothing is offered before the data starts.
    const partial = periodPresets({ ...COVERAGE, first_month: "2025-05", last_month: "2025-09" });
    expect(partial.find((p) => p.id === "year")).toMatchObject({ label: "2025 to date", period: { from: "2025-05", to: "2025-09" } });
    expect(partial.find((p) => p.id === "previous-year")).toBeUndefined();
    expect(partial.find((p) => p.id === "12m")?.period.from).toBe("2025-05");
  });

  it("turns absent months into gaps, never zeros", () => {
    const values = withGaps([point("2024-02", 5, 10), point("2024-04", 7, 10)], { from: "2024-02", to: "2024-04" }, (p) => p.paid_passengers);
    expect(values.map((v) => v.value)).toEqual([5, null, 7]);
  });

  it("compares only months with data on both sides, and recomputes load factor from sums", () => {
    const period = { from: "2025-01", to: "2025-04" };
    const points = [...["2024-01", "2024-02", "2024-04"].map((m) => point(m, 100, 200)), ...["2025-01", "2025-02", "2025-03", "2025-04"].map((m) => point(m, 150, 200))];
    const result = comparePeriods(points, period);
    expect(result.previousPeriod).toEqual({ from: "2024-01", to: "2024-04" });
    expect(result.unpaired).toEqual(["2025-03"]);
    expect(result.current.paid_passengers).toBe(600);
    expect(result.pairedCurrent?.paid_passengers).toBe(450);
    expect(result.pairedPrevious?.paid_passengers).toBe(300);
    expect(result.current.load_factor_paid).toBe(600 / 800);
  });
});

describe("PeriodPicker", () => {
  function Harness({ onChange }: { onChange: (p: Period) => void }) {
    const [value, setValue] = useState<Period>({ from: "2025-01", to: "2025-12" });
    return (
      <div>
        <div id="dashboard-overlays" />
        <PeriodPicker
          coverage={COVERAGE}
          value={value}
          onChange={(p) => {
            setValue(p);
            onChange(p);
          }}
        />
      </div>
    );
  }

  it("shows the period legibly and applies a preset", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    const trigger = screen.getByRole("button", { name: /Period Jan 2025 – Dec 2025/ });
    fireEvent.click(trigger);
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Last 3 months" }));
    expect(onChange).toHaveBeenCalledWith({ from: "2025-10", to: "2025-12" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Oct 2025 – Dec 2025/ })).toBeInTheDocument();
  });

  it("picks a custom range across years and never inverts it", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: /Period/ }));
    const dialog = screen.getByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Previous year" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Jun 2024" }));
    // Clicking a month before the start restarts the range there instead of inverting it.
    fireEvent.click(within(dialog).getByRole("button", { name: "Feb 2024" }));
    expect(within(dialog).getByRole("button", { name: "Apply" })).toBeDisabled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Next year" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "May 2025" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Apply" }));
    expect(onChange).toHaveBeenCalledWith({ from: "2024-02", to: "2025-05" });
  });

  it("marks months without data and disables months outside the dataset", () => {
    render(<Harness onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Period/ }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByRole("combobox", { name: "Year" }), { target: { value: "2024" } });
    expect(within(dialog).getByRole("button", { name: "Mar 2024, no data" })).toBeEnabled();
    expect(within(dialog).getByRole("button", { name: "Previous year" })).toBeDisabled();
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("search", () => {
  const find = (q: string) => codes(rank(AIRPORTS, q, airportSearchable, 8));

  it("finds airports by IATA, ICAO, name, city and UF, ignoring case and accents", () => {
    expect(find("GRU")[0]).toBe("GRU");
    expect(find("sbgr")[0]).toBe("GRU");
    expect(find("guarulhos")).toEqual(["GRU"]);
    expect(find("são paulo")).toEqual(["CGH"]);
    expect(find("sao paulo")).toEqual(["CGH"]);
    expect(find("santos")).toEqual(["SDU"]);
    expect(find("SP")).toEqual(["GRU", "CGH", "VCP"]);
    expect(find("zzzz")).toEqual([]);
    // Without a query, the busiest first.
    expect(find("")).toEqual(["GRU", "CGH", "SDU", "VCP", "LIS"]);
  });

  it("finds carriers by code and name, without merging codes", () => {
    const find = (q: string) => rank(CARRIERS, q, carrierSearchable, 8).map((c) => c.carrier);
    expect(find("JJ")).toEqual(["TAM"]);
    expect(find("tam")[0]).toBe("TAM");
    expect(find("G3")).toEqual(["GLO"]);
    expect(find("gol")[0]).toBe("GLO");
    expect(find("azul")).toEqual(["AZU"]);
    expect(find("AD")[0]).toBe("AZU");
    // "LATAM" is only in LAN's recorded name: TAM is not silently treated as the same entity.
    expect(find("latam")).toEqual(["LAN"]);
  });

  it("highlights the matching part, keeping the original accents", () => {
    expect(highlight("SÃO PAULO", "sao")).toEqual([
      { text: "SÃO", match: true },
      { text: " PAULO", match: false },
    ]);
  });
});

describe("AirportCombobox", () => {
  function Harness({ onChange }: { onChange: (code: string) => void }) {
    const [value, setValue] = useState("");
    return (
      <>
        <div id="dashboard-overlays" />
        <AirportCombobox
          label="Airport"
          value={value}
          onChange={(code) => {
            setValue(code);
            onChange(code);
          }}
        />
      </>
    );
  }

  const setup = () => {
    const onChange = vi.fn();
    withProvider({}, <Harness onChange={onChange} />);
    return { onChange, input: screen.getByRole("combobox", { name: "Airport" }) };
  };

  it("suggests the busiest airports on focus and selects with the keyboard", async () => {
    const { onChange, input } = setup();
    fireEvent.focus(input);
    const list = await screen.findByRole("listbox");
    expect(input).toHaveAttribute("aria-expanded", "true");
    expect(within(list).getAllByRole("option")).toHaveLength(5);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input.getAttribute("aria-activedescendant")).toBe(within(list).getAllByRole("option")[1].id);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("CGH");
    expect(input).toHaveValue("CGH · SBSP");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("filters by name as you type and highlights the match", async () => {
    const { onChange, input } = setup();
    fireEvent.change(input, { target: { value: "viracopos" } });
    const options = within(await screen.findByRole("listbox")).getAllByRole("option");
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveTextContent("VCP · SBKP");
    expect(options[0].querySelector("mark")).toHaveTextContent("VIRACOPOS");
    fireEvent.click(options[0]);
    expect(onChange).toHaveBeenCalledWith("VCP");
  });

  it("never picks an ambiguous match by itself, but accepts an exact code", async () => {
    const { onChange, input } = setup();
    fireEvent.change(input, { target: { value: "SP" } });
    expect(await screen.findAllByRole("option")).toHaveLength(3);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).not.toHaveBeenCalled();
    expect(await screen.findByText("Choose one of the suggestions.")).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "sbrj" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("SDU");
  });

  it("says so when nothing matches, closes on Escape and clears in one click", async () => {
    const { onChange, input } = setup();
    fireEvent.change(input, { target: { value: "xyzw" } });
    expect(await screen.findByText(/No airport matches “xyzw”/)).toBeInTheDocument();
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    fireEvent.change(input, { target: { value: "GRU" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenLastCalledWith("GRU");
    fireEvent.click(screen.getByRole("button", { name: "Clear airport" }));
    expect(onChange).toHaveBeenLastCalledWith("");
    expect(input).toHaveValue("");
  });
});

describe("ApiDataProvider analytics", () => {
  it("builds encoded queries and leaves out empty filters", () => {
    expect(toQuery({ origin: "CGH", destination: "", from: "2025-01", limit: 25, offset: 0 })).toBe("?origin=CGH&from=2025-01&limit=25&offset=0");
    expect(toQuery({ origin: "a&b=c" })).toBe("?origin=a%26b%3Dc");
    expect(toQuery({})).toBe("");
  });

  it("calls the analytics endpoints and reads coverage and catalogs once", async () => {
    const fetchImpl = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ data: {}, meta }), { status: 200 })));
    const api = new ApiDataProvider({ baseUrl: "http://api.test/", fetchImpl });
    await api.getRouteSeries({ origin: "CGH", destination: "SDU", from: "2025-01", to: "2025-12" });
    await api.getCarrierRanking({ carrier: "JJ", limit: 25, offset: 50 });
    await Promise.all([api.getCoverage(), api.getCoverage(), api.getAirportCatalog(), api.getAirportCatalog(), api.getCarrierCatalog()]);
    await api.getAnalystConfig();
    const urls = fetchImpl.mock.calls.map((call) => (call as unknown[])[0]);
    expect(urls).toEqual([
      "http://api.test/v2/analytics/routes/monthly?origin=CGH&destination=SDU&from=2025-01&to=2025-12",
      "http://api.test/v2/analytics/carriers?carrier=JJ&limit=25&offset=50",
      "http://api.test/v2/analytics/coverage",
      "http://api.test/v2/analytics/airports/catalog",
      "http://api.test/v2/analytics/carriers/catalog",
      "http://api.test/v2/analyst/config",
    ]);
  });

  it("surfaces the backend's reason and supports cancelling", async () => {
    const failing = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ detail: "The analytical tables have not been built" }), { status: 503 })));
    await expect(new ApiDataProvider({ baseUrl: "http://x", fetchImpl: failing }).getAirportRanking({})).rejects.toThrow("not been built");
    const hanging = vi.fn((_url: string, init?: RequestInit) => new Promise<Response>((_, reject) => init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")))));
    const controller = new AbortController();
    const pending = new ApiDataProvider({ baseUrl: "http://x", fetchImpl: hanging as unknown as typeof fetch }).getRouteRanking({}, controller.signal);
    controller.abort();
    await expect(pending).rejects.toMatchObject({ code: "cancelled" });
  });
});

async function pick(label: string, query: string) {
  const input = await screen.findByRole("combobox", { name: label });
  fireEvent.change(input, { target: { value: query } });
  // Suggestions exist only once the catalog has loaded.
  await screen.findAllByRole("option");
  fireEvent.keyDown(input, { key: "ArrowDown" });
  fireEvent.keyDown(input, { key: "Enter" });
}

describe("Routes Explorer", () => {
  const period = { from: "2025-01", to: "2025-12" };

  it("sends origin and destination as a direction, swaps them, and leaves a blank side open", async () => {
    const getRouteRanking = vi.fn((q: { origin?: string; destination?: string }) =>
      ok(routesPage(period, q.origin === "SDU" ? [{ origin_iata: "SDU", destination_iata: "CGH", paid_passengers: 900 }] : [{}])),
    );
    const getRouteSeries = vi.fn(() => ok(series(period, (m) => point(m, 100, 120))));
    withProvider({ getRouteRanking, getRouteSeries }, <RoutesView />);
    await pick("Origin", "congonhas");
    await waitFor(() => expect(getRouteRanking).toHaveBeenLastCalledWith({ origin: "CGH", destination: "", from: "2025-01", to: "2025-12", limit: 25, offset: 0 }, expect.anything()));
    await pick("Destination", "santos dumont");
    await waitFor(() => expect(getRouteRanking).toHaveBeenLastCalledWith(expect.objectContaining({ origin: "CGH", destination: "SDU" }), expect.anything()));
    expect(getRouteSeries).toHaveBeenLastCalledWith({ origin: "CGH", destination: "SDU", from: "2025-01", to: "2025-12" }, expect.anything());
    fireEvent.click(screen.getByRole("button", { name: "Swap direction" }));
    await waitFor(() => expect(getRouteRanking).toHaveBeenLastCalledWith(expect.objectContaining({ origin: "SDU", destination: "CGH" }), expect.anything()));
    expect((await screen.findAllByText("SDU → CGH")).length).toBeGreaterThan(0);
    expect(screen.getByRole("combobox", { name: "Origin" })).toHaveValue("SDU · SBRJ");
    fireEvent.click(screen.getByRole("button", { name: "Clear origin" }));
    await waitFor(() => expect(getRouteRanking).toHaveBeenLastCalledWith(expect.objectContaining({ origin: "", destination: "CGH" }), expect.anything()));
  });

  it("never shows the answer to filters that are no longer selected", async () => {
    let releaseFirst: () => void = () => {};
    const getRouteRanking = vi.fn((q: { origin?: string }) => {
      if (!q.origin) return new Promise<Envelope<RoutesPage>>((resolve) => (releaseFirst = () => resolve({ data: routesPage(period, [{ origin_iata: "OLD", paid_passengers: 5 }]), meta })));
      return ok(routesPage(period, [{ origin_iata: "GRU", destination_iata: "REC", paid_passengers: 7 }]));
    });
    withProvider({ getRouteRanking, getRouteSeries: () => ok(series(period, (m) => point(m, 1, 2))) }, <RoutesView />);
    await pick("Origin", "GRU");
    expect((await screen.findAllByText("GRU → REC")).length).toBeGreaterThan(0);
    await act(async () => releaseFirst());
    expect(screen.queryByText(/OLD/)).not.toBeInTheDocument();
  });

  it("warns about absent months and draws them as gaps", async () => {
    const gapped = { from: "2024-01", to: "2024-06" };
    const getRouteSeries = () => ok(series(gapped, (m) => point(m, 100, 120)));
    const getRouteRanking = () => ok({ ...routesPage(gapped, [{}]), absent_months: ["2024-03"], months_with_data: 5 });
    withProvider({ getRouteSeries, getRouteRanking }, <RoutesView />);
    expect(await screen.findByRole("note")).toHaveTextContent("2024-03");
    expect(screen.getByRole("note")).toHaveTextContent("not a zero");
    const table = (await screen.findAllByRole("table", { hidden: true })).find((t) => within(t).queryByText("Mar 24"));
    expect(within(table as HTMLElement).getByText("Mar 24").nextSibling).toHaveTextContent("No data");
    expect(screen.getByText(/5 months with data/)).toBeInTheDocument();
  });

  it("explains each measure on demand, keeping their scopes apart", async () => {
    withProvider({ getRouteRanking: () => ok(routesPage({ from: "2025-01", to: "2025-12" }, [{}])) }, <RoutesView />);
    const [tip] = await screen.findAllByRole("button", { name: "What is passenger flights?" });
    fireEvent.focus(tip);
    expect(screen.getByRole("tooltip")).toHaveTextContent("passenger scope only");
    fireEvent.blur(tip);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});

describe("Airports Intelligence", () => {
  it("filters by an airport picked by city", async () => {
    const getAirportRanking = vi.fn(() => ok({ period: { from: "2025-01", to: "2025-12" }, months_with_data: 12, absent_months: [], total: 0, limit: 25, offset: 0, airports: [] }));
    withProvider({ getAirportRanking }, <AirportsView />);
    await pick("Airport", "campinas");
    await waitFor(() => expect(getAirportRanking).toHaveBeenLastCalledWith(expect.objectContaining({ airport: "VCP" }), expect.anything()));
  });
});

describe("Market Overview", () => {
  it("shows the four KPIs for the period, with load factor change in points and a gap caveat", async () => {
    const getRouteSeries = vi.fn((q: { from?: string; to?: string }) =>
      ok(series({ from: q.from as string, to: q.to as string }, (m) => (m < "2025-01" ? point(m, 100, 200, 10) : point(m, 150, 200, 12)))),
    );
    const getRouteRanking = (q: { from?: string; to?: string }) => ok(routesPage({ from: q.from as string, to: q.to as string }, [{}]));
    withProvider({ getRouteSeries, getRouteRanking }, <Overview />);
    await waitFor(() => expect(getRouteSeries).toHaveBeenCalledWith({ from: "2024-01", to: "2025-12" }, expect.anything()));
    expect(await screen.findByText("Seats offered")).toBeInTheDocument();
    expect(screen.getByText("1.8K")).toBeInTheDocument();
    expect(screen.getByText("+50.0%")).toBeInTheDocument();
    expect(screen.getByText("+25.0 pts")).toBeInTheDocument();
    expect(screen.getByText(/2025-03 had no counterpart/)).toBeInTheDocument();
    expect(screen.getAllByText(/Jan 2025 – Dec 2025/).length).toBeGreaterThan(0);
  });

  it("applies a preset to every request on the page and mirrors it in the URL", async () => {
    window.history.replaceState(null, "", "/dashboard");
    const getRouteRanking = vi.fn((q: { from?: string; to?: string }) => ok(routesPage({ from: q.from as string, to: q.to as string }, [{}])));
    const getAirportRanking = vi.fn((q: { from?: string; to?: string }) =>
      ok({ period: { from: q.from as string, to: q.to as string }, months_with_data: 6, absent_months: [], total: 0, limit: 8, offset: 0, airports: [] }),
    );
    const getRouteSeries = vi.fn((q: { from?: string; to?: string }) => ok(series({ from: q.from as string, to: q.to as string }, (m) => point(m, 1, 2))));
    render(
      <>
        <div id="dashboard-overlays" />
        <DataProviderRoot provider={Object.assign(new MockDataProvider({ latencyMs: 0 }), { getCoverage: () => ok(COVERAGE), getRouteRanking, getAirportRanking, getRouteSeries }) as FlightDataProvider}>
          <Overview />
        </DataProviderRoot>
      </>,
    );
    fireEvent.click(await screen.findByRole("button", { name: /Period/ }));
    fireEvent.click(screen.getByRole("button", { name: "Last 6 months" }));
    await waitFor(() => expect(getRouteRanking).toHaveBeenLastCalledWith({ from: "2025-07", to: "2025-12", limit: 6 }, expect.anything()));
    expect(getAirportRanking).toHaveBeenLastCalledWith({ from: "2025-07", to: "2025-12", limit: 8 }, expect.anything());
    expect(getRouteSeries).toHaveBeenLastCalledWith({ from: "2024-07", to: "2025-12" }, expect.anything());
    expect(window.location.search).toBe("?from=2025-07&to=2025-12");
    expect(await screen.findAllByText(/Jul 2025 – Dec 2025/)).not.toHaveLength(0);
  });

  it("reads a valid period from the URL and ignores an invalid one", async () => {
    window.history.replaceState(null, "", "/dashboard?from=2024-05&to=2024-08");
    const getRouteRanking = vi.fn((q: { from?: string; to?: string }) => ok(routesPage({ from: q.from as string, to: q.to as string }, [{}])));
    const { unmount } = withProvider({ getRouteRanking }, <Overview />);
    await waitFor(() => expect(getRouteRanking).toHaveBeenCalledWith({ from: "2024-05", to: "2024-08", limit: 6 }, expect.anything()));
    unmount();
    window.history.replaceState(null, "", "/dashboard?from=2025-09&to=2025-02");
    const second = vi.fn((q: { from?: string; to?: string }) => ok(routesPage({ from: q.from as string, to: q.to as string }, [{}])));
    withProvider({ getRouteRanking: second }, <Overview />);
    await waitFor(() => expect(second).toHaveBeenCalledWith({ from: "2025-01", to: "2025-12", limit: 6 }, expect.anything()));
    window.history.replaceState(null, "", "/");
  });
});

describe("Airlines Analytics", () => {
  it("ranks carriers with market share and charts the first one", async () => {
    const page: CarriersPage = {
      period: { from: "2025-01", to: "2025-12" },
      months_with_data: 12,
      absent_months: [],
      market_paid_passengers: 1000,
      total: 1,
      limit: 25,
      offset: 0,
      carriers: [{ carrier: "TAM", iata: "JJ", name: "TAM LINHAS AÉREAS S.A.", country: "BRASIL", months_operated: 12, all_takeoffs: 10, passenger_takeoffs: 10, paid_passengers: 337, seats: 400, rpk: 0, ask: 0, international_paid_passengers: 0, load_factor_paid: 0.8425, market_share: 0.337 }],
    };
    const getCarrierSeries = vi.fn((q: { carrier: string }) => ok({ period: page.period, months_with_data: 12, absent_months: [], carrier_found: q.carrier === "TAM", points: [] }));
    withProvider({ getCarrierRanking: () => ok(page), getCarrierSeries }, <AirlinesView />);
    expect(await screen.findAllByText("33.7%")).not.toHaveLength(0);
    await waitFor(() => expect(getCarrierSeries).toHaveBeenCalledWith({ carrier: "TAM", from: "2025-01", to: "2025-12" }, expect.anything()));
    expect(screen.getByText(/1,000 paid passengers/)).toBeInTheDocument();
  });

  it("filters by a carrier found by its name, and labels historical codes", async () => {
    const getCarrierRanking = vi.fn(() => ok({ period: { from: "2025-01", to: "2025-12" }, months_with_data: 12, absent_months: [], market_paid_passengers: 0, total: 0, limit: 25, offset: 0, carriers: [] }));
    withProvider({ getCarrierRanking }, <AirlinesView />);
    const input = await screen.findByRole("combobox", { name: "Carrier" });
    fireEvent.change(input, { target: { value: "avianca" } });
    expect(await screen.findByText("last flew 2019-04")).toBeInTheDocument();
    await pick("Carrier", "azul");
    await waitFor(() => expect(getCarrierRanking).toHaveBeenLastCalledWith(expect.objectContaining({ carrier: "AZU" }), expect.anything()));
  });

  it("renders demo data with a DEMO badge", async () => {
    render(
      <DataProviderRoot provider={new MockDataProvider({ latencyMs: 0 })}>
        <AirlinesView />
      </DataProviderRoot>,
    );
    expect((await screen.findAllByText("Demo Carrier A")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Demo").length).toBeGreaterThan(0);
  });
});

describe("Floating analyst", () => {
  const answer = {
    status: "answered" as const,
    answer: "CGH to SDU carried 1,968,523 paid passengers.",
    sources: [{ endpoint: "/v2/routes", dataset: "flights", period: "2025-01 to 2025-12", unit: "paid passengers", generated_at: "x" }],
    caveats: [],
  };

  function Pages({ provider }: { provider: FlightDataProvider }) {
    const [page, setPage] = useState("overview");
    return (
      <DataProviderRoot provider={provider}>
        <AnalystProvider>
          <button type="button" onClick={() => setPage(page === "overview" ? "routes" : "overview")}>
            Navigate
          </button>
          {page === "overview" ? <p>Overview page</p> : <p>Routes page</p>}
          <FloatingAnalyst />
        </AnalystProvider>
      </DataProviderRoot>
    );
  }

  const apiLike = (overrides: Partial<FlightDataProvider>) =>
    Object.assign(new MockDataProvider({ latencyMs: 0 }), {
      kind: "API",
      getAnalystConfig: vi.fn(() => Promise.resolve({ configured: true, provider: "groq", model: "m" })),
      getAnalystStatus: vi.fn(() => Promise.reject(new Error("must not be called"))),
      ...overrides,
    }) as unknown as FlightDataProvider & { getAnalystConfig: ReturnType<typeof vi.fn>; getAnalystStatus: ReturnType<typeof vi.fn> };

  it("opens without contacting the model provider and sends nothing by itself", async () => {
    const askAnalyst = vi.fn(() => Promise.resolve(answer));
    const provider = apiLike({ askAnalyst });
    render(<Pages provider={provider} />);
    fireEvent.click(screen.getByRole("button", { name: "Open AI analyst" }));
    const panel = await screen.findByRole("dialog", { name: "AI Aviation Analyst" });
    expect(await within(panel).findByText(/connection not checked/)).toBeInTheDocument();
    expect(within(panel).getByText(/I'm the ANAC Flight Intelligence assistant/)).toBeInTheDocument();
    expect(provider.getAnalystConfig).toHaveBeenCalledTimes(1);
    expect(provider.getAnalystStatus).not.toHaveBeenCalled();
    expect(askAnalyst).not.toHaveBeenCalled();
  });

  it("keeps the conversation across pages and asks a suggested question only when clicked", async () => {
    const askAnalyst = vi.fn(() => Promise.resolve(answer));
    render(<Pages provider={apiLike({ askAnalyst })} />);
    fireEvent.click(screen.getByRole("button", { name: "Open AI analyst" }));
    const suggestion = await screen.findByRole("button", { name: "Which routes were the busiest in 2025?" });
    await waitFor(() => expect(suggestion).toBeEnabled());
    fireEvent.click(suggestion);
    expect(askAnalyst).toHaveBeenCalledWith("Which routes were the busiest in 2025?", []);
    expect(await screen.findByText(/1,968,523/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close analyst" }));
    fireEvent.click(screen.getByRole("button", { name: "Navigate" }));
    expect(screen.getByText("Routes page")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open AI analyst" }));
    expect(await screen.findByText(/1,968,523/)).toBeInTheDocument();
    expect(screen.getByText(/Connected · m/)).toBeInTheDocument();
    expect(askAnalyst).toHaveBeenCalledTimes(1);
  });

  it("explains when the AI is not configured, and invents no answer", async () => {
    const askAnalyst = vi.fn();
    render(<Pages provider={apiLike({ askAnalyst, getAnalystConfig: vi.fn(() => Promise.resolve({ configured: false, provider: "groq", model: "m" })) })} />);
    fireEvent.click(screen.getByRole("button", { name: "Open AI analyst" }));
    expect(await screen.findByText(/not configured on the server/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /question/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Which routes were the busiest in 2025?" })).toBeDisabled();
    expect(askAnalyst).not.toHaveBeenCalled();
  });

  it("checks the connection only when asked, and reports an unavailable provider", async () => {
    const getAnalystStatus = vi.fn(() => Promise.resolve({ available: false, provider: "groq", model: "m", reason: "auth_failed" }));
    render(<Pages provider={apiLike({ getAnalystStatus })} />);
    fireEvent.click(screen.getByRole("button", { name: "Open AI analyst" }));
    fireEvent.click(await screen.findByRole("button", { name: "Check connection" }));
    expect(getAnalystStatus).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/could not authenticate/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /question/i })).toBeDisabled();
  });

  it("stays off on demo data without any request", async () => {
    const demo = new MockDataProvider({ latencyMs: 0 });
    const spy = vi.spyOn(demo, "getAnalystConfig");
    render(
      <DataProviderRoot provider={demo}>
        <AnalystProvider>
          <AnalystChat />
        </AnalystProvider>
      </DataProviderRoot>,
    );
    expect(await screen.findByText(/only works with real data/)).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });
});

// Runs only against a live backend: ANAC_API_URL=http://127.0.0.1:8765 npx vitest run tests/analytics.test.tsx
// Never calls the analyst chat or status, so it makes no request to the model provider.
describe.runIf(process.env.ANAC_API_URL)("live analytics API", () => {
  const api = () => new ApiDataProvider({ baseUrl: process.env.ANAC_API_URL as string, timeoutMs: 20_000 });

  it("answers for the period requested, with the known gaps", async () => {
    const coverage = (await api().getCoverage()).data;
    expect(coverage.absent_months).toEqual(["2015-08", "2016-02", "2018-07", "2020-08"]);
    const market = (await api().getRouteSeries({ from: "2025-01", to: "2025-12" })).data;
    expect(market.period).toEqual({ from: "2025-01", to: "2025-12" });
    expect(market.points.reduce((s, p) => s + p.paid_passengers, 0)).toBe(131_593_763);
    const gapped = (await api().getRouteSeries({ from: "2015-01", to: "2016-12" })).data;
    expect(gapped.absent_months).toEqual(["2015-08", "2016-02"]);
    expect(gapped.points.map((p) => p.month)).not.toContain("2015-08");
  }, 30_000);

  it("keeps directions apart and accepts IATA or ICAO", async () => {
    const forward = (await api().getRouteRanking({ origin: "CGH", destination: "SDU", from: "2025-01", to: "2025-12" })).data.routes[0];
    const icao = (await api().getRouteRanking({ origin: "SBSP", destination: "SBRJ", from: "2025-01", to: "2025-12" })).data.routes[0];
    const backward = (await api().getRouteRanking({ origin: "SDU", destination: "CGH", from: "2025-01", to: "2025-12" })).data.routes[0];
    expect(forward.paid_passengers).toBe(1_968_523);
    expect(icao.paid_passengers).toBe(forward.paid_passengers);
    expect(backward.paid_passengers).toBe(1_966_721);
  }, 30_000);

  it("serves carriers whose shares come from the same market total", async () => {
    const page = (await api().getCarrierRanking({ from: "2025-01", to: "2025-12", limit: 500 })).data;
    expect(page.market_paid_passengers).toBe(131_593_763);
    expect(page.carriers.reduce((s, c) => s + (c.market_share ?? 0), 0)).toBeCloseTo(1, 6);
    const gru = (await api().getAirportRanking({ airport: "GRU", from: "2025-01", to: "2025-12" })).data.airports[0];
    expect(gru.movements).toBe(287_291);
  }, 30_000);

  it("serves full catalogs that the search can use", async () => {
    const airports = (await api().getAirportCatalog()).data;
    expect(airports.airports).toHaveLength(1180);
    expect(airports.airports[0].iata).toBe("GRU");
    expect(rank(airports.airports, "guarulhos", airportSearchable, 8)[0].airport).toBe("SBGR");
    expect(rank(airports.airports, "congonhas", airportSearchable, 8)[0].iata).toBe("CGH");
    const carriers = (await api().getCarrierCatalog()).data;
    expect(carriers.carriers).toHaveLength(317);
    const find = (q: string) => rank(carriers.carriers, q, carrierSearchable, 8).map((c) => c.carrier);
    expect(find("JJ")[0]).toBe("TAM");
    expect(find("G3")[0]).toBe("GLO");
    expect(find("azul")[0]).toBe("AZU");
    expect(find("latam")).toContain("LAN");
  }, 30_000);

  it("renders the Overview from the real API for the default period", async () => {
    window.history.replaceState(null, "", "/dashboard");
    render(
      <DataProviderRoot provider={api()}>
        <Overview />
      </DataProviderRoot>,
    );
    expect(await screen.findByText("131.6M", undefined, { timeout: 20_000 })).toBeInTheDocument();
    expect(screen.getByText("82.1%")).toBeInTheDocument();
    expect(screen.getAllByText(/Jan 2025 – Dec 2025/).length).toBeGreaterThan(0);
  }, 30_000);
});
