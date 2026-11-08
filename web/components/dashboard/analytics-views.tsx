"use client";

import { useCallback, useState } from "react";
import { useDataProvider } from "@/components/data-provider";
import { useResource } from "@/hooks/use-resource";
import {
  totals,
  withGaps,
  type AirportPoint,
  type CarrierPoint,
  type Coverage,
  type Period,
  type RoutePoint,
} from "@/lib/data";
import { formatCompact, formatNumber, formatPercent } from "@/lib/utils";
import {
  AIRPORT_CODE,
  CARRIER_CODE,
  CoverageGate,
  FilterBar,
  GapNotice,
  MetricTabs,
  Pager,
  PeriodLine,
  RowButton,
  StatTile,
  SwapButton,
  Term,
  usePeriodParam,
  validCode,
} from "./analytics-controls";
import { AirportCombobox, CarrierCombobox } from "./entity-combobox";
import { PeriodPicker } from "./period-picker";
import { BarList, TrendChart, monthLabel } from "./charts";
import { Header, Loaded } from "./data-views";
import { Card, DataTable } from "./ui";

const PAGE = 25;
const percent = (n: number) => formatPercent(n);
const ratio = (n: number | null) => (n === null ? "—" : formatPercent(n));
const code = (iata: string | null, icao: string) => iata || icao;

interface Metric<P> {
  key: string;
  label: string;
  value: (point: P) => number | null;
  /** Ratios are shown as percentages, counts as numbers. */
  isRatio?: boolean;
}

function SeriesChart<P extends { month: string }>({ points, period, metric }: { points: P[]; period: Period; metric: Metric<P> }) {
  return (
    <TrendChart
      valueLabel={metric.label}
      data={withGaps(points, period, metric.value).map((p) => ({ label: monthLabel(p.month), value: p.value }))}
      valueFormat={metric.isRatio ? percent : formatNumber}
      tickFormat={metric.isRatio ? (n) => formatPercent(n, 0) : formatCompact}
    />
  );
}


/* ------------------------------------------------------------------ Routes */

const ROUTE_METRICS: Metric<RoutePoint>[] = [
  { key: "paid_passengers", label: "Paid passengers", value: (p) => p.paid_passengers },
  { key: "passenger_takeoffs", label: "Passenger flights", value: (p) => p.passenger_takeoffs },
  { key: "seats", label: "Seats offered", value: (p) => p.seats },
  { key: "load_factor_paid", label: "Load factor", value: (p) => p.load_factor_paid, isRatio: true },
];

interface RouteCodes {
  origin: string;
  destination: string;
}

export function RoutesView() {
  return <CoverageGate href="/dashboard/routes">{(coverage) => <RoutesExplorer coverage={coverage} />}</CoverageGate>;
}

function RoutesExplorer({ coverage }: { coverage: Coverage }) {
  const provider = useDataProvider();
  const [period, setPeriod] = usePeriodParam(coverage);
  const [codes, setCodes] = useState<RouteCodes>({ origin: "", destination: "" });
  const [offset, setOffset] = useState(0);
  const ranking = useResource(
    useCallback((signal: AbortSignal) => provider.getRouteRanking({ ...codes, ...period, limit: PAGE, offset }, signal), [provider, codes, period, offset]),
  );

  const apply = (next: RouteCodes) => {
    // Codes come from the catalog or the API, and are checked again before any request.
    if (!validCode(next.origin, AIRPORT_CODE) || !validCode(next.destination, AIRPORT_CODE)) return;
    setCodes(next);
    setOffset(0);
  };
  const selection = `${codes.origin || "Any airport"} → ${codes.destination || "any airport"}`;

  return (
    <>
      <Header href="/dashboard/routes" state={ranking} />
      <FilterBar>
        <PeriodPicker
          coverage={coverage}
          value={period}
          onChange={(next) => {
            setPeriod(next);
            setOffset(0);
          }}
        />
        <AirportCombobox label="Origin" value={codes.origin} onChange={(origin) => apply({ ...codes, origin })} />
        <SwapButton onSwap={() => apply({ origin: codes.destination, destination: codes.origin })} disabled={!codes.origin && !codes.destination} />
        <AirportCombobox label="Destination" value={codes.destination} onChange={(destination) => apply({ ...codes, destination })} />
      </FilterBar>
      {ranking.status === "success" && <GapNotice context={ranking.data} />}
      <div className="grid gap-5">
        <RouteSeriesCard codes={codes} period={period} selection={selection} />
        <Card title="Routes" subtitle="Directed: A → B and B → A are separate rows. Ordered by paid passengers in the period.">
          <Loaded
            state={ranking}
            isEmpty={(data) => data.total === 0}
            emptyMessage="No route matches these filters in this period."
          >
            {(data) => (
              <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.9fr)]">
                <BarList
                  items={data.routes.slice(0, 12).map((r) => ({
                    label: `${code(r.origin_iata, r.origin)} → ${code(r.destination_iata, r.destination)}`,
                    sub: `LF ${ratio(r.load_factor_paid)}`,
                    value: r.paid_passengers,
                  }))}
                />
                <div className="min-w-0">
                  <DataTable
                    caption="Routes by paid passengers"
                    columns={[
                      "Route",
                      "Distance (km)",
                      "Months",
                      <Term key="pax" term="paid_passengers">Paid passengers</Term>,
                      <Term key="flights" term="passenger_flights">Passenger flights</Term>,
                      <Term key="seats" term="seats">Seats</Term>,
                      <Term key="lf" term="load_factor">Load factor</Term>,
                    ]}
                    alignRight={[1, 2, 3, 4, 5, 6]}
                    rows={data.routes.map((r) => {
                      const origin = code(r.origin_iata, r.origin);
                      const destination = code(r.destination_iata, r.destination);
                      return [
                        <RowButton
                          key="route"
                          selected={codes.origin === origin && codes.destination === destination}
                          onClick={() => apply({ origin, destination })}
                        >
                          {origin} → {destination}
                          {r.is_international ? " · intl" : ""}
                        </RowButton>,
                        r.distance_km === null ? "—" : formatNumber(Math.round(r.distance_km)),
                        String(r.months_operated),
                        formatNumber(r.paid_passengers),
                        formatNumber(r.passenger_takeoffs),
                        formatNumber(r.seats),
                        ratio(r.load_factor_paid),
                      ];
                    })}
                  />
                  <Pager page={data} onOffset={setOffset} noun="routes" />
                </div>
              </div>
            )}
          </Loaded>
        </Card>
      </div>
    </>
  );
}

function RouteSeriesCard({ codes, period, selection }: { codes: RouteCodes; period: Period; selection: string }) {
  const provider = useDataProvider();
  const series = useResource(useCallback((signal: AbortSignal) => provider.getRouteSeries({ ...codes, ...period }, signal), [provider, codes, period]));
  const [metric, setMetric] = useState(ROUTE_METRICS[0].key);
  const active = ROUTE_METRICS.find((m) => m.key === metric) ?? ROUTE_METRICS[0];
  return (
    <Card
      title={`Monthly evolution · ${selection}`}
      subtitle="Passenger scope, per flight leg. Load factor is Σ paid passengers / Σ seats."
      action={<MetricTabs options={ROUTE_METRICS} value={metric} onChange={setMetric} />}
    >
      <Loaded
        state={series}
        isEmpty={(data) => data.points.every((p) => p.all_takeoffs === 0)}
        emptyMessage="No flights for this selection in the period."
      >
        {(data) => {
          const sum = totals(data.points);
          return (
            <>
              <div className="mb-6 grid grid-cols-2 gap-4 xl:grid-cols-4">
                <StatTile term="paid_passengers" label="Paid passengers" value={formatCompact(sum.paid_passengers)} sub={formatNumber(sum.paid_passengers)} />
                <StatTile term="passenger_flights" label="Passenger flights" value={formatCompact(sum.passenger_takeoffs)} sub={formatNumber(sum.passenger_takeoffs)} />
                <StatTile term="seats" label="Seats offered" value={formatCompact(sum.seats)} sub={formatNumber(sum.seats)} />
                <StatTile term="load_factor" label="Load factor" value={ratio(sum.load_factor_paid)} sub="Σ paid passengers / Σ seats" />
              </div>
              <SeriesChart points={data.points} period={data.period} metric={active} />
              <div className="mt-2">
                <PeriodLine context={data} />
              </div>
            </>
          );
        }}
      </Loaded>
    </Card>
  );
}

/* ---------------------------------------------------------------- Airports */

const AIRPORT_METRICS: Metric<AirportPoint>[] = [
  { key: "movements", label: "Movements", value: (p) => p.movements },
  { key: "departures", label: "Departures", value: (p) => p.departures },
  { key: "arrivals", label: "Arrivals", value: (p) => p.arrivals },
  { key: "departing_paid_passengers", label: "Departing paid passengers", value: (p) => p.departing_paid_passengers },
  { key: "arriving_paid_passengers", label: "Arriving paid passengers", value: (p) => p.arriving_paid_passengers },
];

const AIRPORT_DEFINITION =
  "Movements are takeoffs plus landings of every operated leg, cargo included. Paid passengers use the passenger scope.";

export function AirportsView() {
  return <CoverageGate href="/dashboard/airports">{(coverage) => <AirportsExplorer coverage={coverage} />}</CoverageGate>;
}

function AirportsExplorer({ coverage }: { coverage: Coverage }) {
  const provider = useDataProvider();
  const [period, setPeriod] = usePeriodParam(coverage);
  const [airport, setAirport] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const ranking = useResource(
    useCallback((signal: AbortSignal) => provider.getAirportRanking({ airport, ...period, limit: PAGE, offset }, signal), [provider, airport, period, offset]),
  );
  const first = ranking.status === "success" ? ranking.data.airports[0] : undefined;
  const chartCode = selected ?? (first ? code(first.iata, first.airport) : null);

  return (
    <>
      <Header href="/dashboard/airports" state={ranking} />
      <FilterBar>
        <PeriodPicker
          coverage={coverage}
          value={period}
          onChange={(next) => {
            setPeriod(next);
            setOffset(0);
          }}
        />
        <AirportCombobox
          label="Airport"
          value={airport}
          onChange={(next) => {
            if (!validCode(next, AIRPORT_CODE)) return;
            setAirport(next);
            setSelected(null);
            setOffset(0);
          }}
        />
      </FilterBar>
      {ranking.status === "success" && <GapNotice context={ranking.data} />}
      <div className="grid gap-5">
        {chartCode && <AirportSeriesCard airport={chartCode} period={period} />}
        <Card title={<Term term="movements">Airports by aircraft movements</Term>} subtitle={AIRPORT_DEFINITION}>
          <Loaded
            state={ranking}
            isEmpty={(data) => data.total === 0}
            emptyMessage="This airport has no flights in this period."
          >
            {(data) => (
              <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.9fr)]">
                <BarList
                  items={data.airports.slice(0, 12).map((a) => ({
                    label: code(a.iata, a.airport),
                    sub: [a.city, a.uf ?? a.country].filter(Boolean).join(" · "),
                    value: a.movements,
                  }))}
                />
                <div className="min-w-0">
                  <DataTable
                    caption="Airports by movements"
                    columns={[
                      "Code",
                      "Airport",
                      "City",
                      "UF / country",
                      <Term key="m" term="movements">Movements</Term>,
                      <Term key="d" term="departures">Departures</Term>,
                      <Term key="a" term="arrivals">Arrivals</Term>,
                      <Term key="dp" term="departing_paid_passengers">Departing paid pax</Term>,
                      <Term key="ap" term="arriving_paid_passengers">Arriving paid pax</Term>,
                    ]}
                    alignRight={[4, 5, 6, 7, 8]}
                    rows={data.airports.map((a) => {
                      const label = code(a.iata, a.airport);
                      return [
                        <RowButton key="code" selected={chartCode === label} onClick={() => setSelected(label)}>
                          {label}
                        </RowButton>,
                        a.name ?? "—",
                        a.city ?? "—",
                        a.uf ?? a.country ?? "—",
                        formatNumber(a.movements),
                        formatNumber(a.departures),
                        formatNumber(a.arrivals),
                        formatNumber(a.departing_paid_passengers),
                        formatNumber(a.arriving_paid_passengers),
                      ];
                    })}
                  />
                  <Pager page={data} onOffset={setOffset} noun="airports" />
                </div>
              </div>
            )}
          </Loaded>
        </Card>
      </div>
    </>
  );
}

function AirportSeriesCard({ airport, period }: { airport: string; period: Period }) {
  const provider = useDataProvider();
  const series = useResource(useCallback((signal: AbortSignal) => provider.getAirportSeries({ airport, ...period }, signal), [provider, airport, period]));
  const [metric, setMetric] = useState(AIRPORT_METRICS[0].key);
  const active = AIRPORT_METRICS.find((m) => m.key === metric) ?? AIRPORT_METRICS[0];
  return (
    <Card title={`Monthly evolution · ${airport}`} subtitle="Pick an airport in the table to change it." action={<MetricTabs options={AIRPORT_METRICS} value={metric} onChange={setMetric} />}>
      <Loaded state={series} isEmpty={(data) => !data.airport_found || data.points.length === 0} emptyMessage="This airport has no data in the period.">
        {(data) => (
          <>
            <SeriesChart points={data.points} period={data.period} metric={active} />
            <div className="mt-2">
              <PeriodLine context={data} />
            </div>
          </>
        )}
      </Loaded>
    </Card>
  );
}

/* ---------------------------------------------------------------- Airlines */

const CARRIER_METRICS: Metric<CarrierPoint>[] = [
  { key: "market_share", label: "Market share", value: (p) => p.market_share, isRatio: true },
  { key: "paid_passengers", label: "Paid passengers", value: (p) => p.paid_passengers },
  { key: "passenger_takeoffs", label: "Passenger flights", value: (p) => p.passenger_takeoffs },
  { key: "seats", label: "Seats offered", value: (p) => p.seats },
  { key: "load_factor_paid", label: "Load factor", value: (p) => p.load_factor_paid, isRatio: true },
];


export function AirlinesView() {
  return <CoverageGate href="/dashboard/airlines">{(coverage) => <AirlinesExplorer coverage={coverage} />}</CoverageGate>;
}

function AirlinesExplorer({ coverage }: { coverage: Coverage }) {
  const provider = useDataProvider();
  const [period, setPeriod] = usePeriodParam(coverage);
  const [carrier, setCarrier] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const ranking = useResource(
    useCallback((signal: AbortSignal) => provider.getCarrierRanking({ carrier, ...period, limit: PAGE, offset }, signal), [provider, carrier, period, offset]),
  );
  const first = ranking.status === "success" ? ranking.data.carriers[0] : undefined;
  const chartCode = selected ?? first?.carrier ?? null;

  return (
    <>
      <Header href="/dashboard/airlines" state={ranking} />
      <FilterBar>
        <PeriodPicker
          coverage={coverage}
          value={period}
          onChange={(next) => {
            setPeriod(next);
            setOffset(0);
          }}
        />
        <CarrierCombobox
          label="Carrier"
          value={carrier}
          onChange={(next) => {
            if (!validCode(next, CARRIER_CODE)) return;
            setCarrier(next);
            setSelected(null);
            setOffset(0);
          }}
        />
      </FilterBar>
      {ranking.status === "success" && <GapNotice context={ranking.data} />}
      <div className="grid gap-5">
        {chartCode && <CarrierSeriesCard carrier={chartCode} period={period} />}
        <Card
          title={<Term term="market_share">Carriers by paid passengers</Term>}
          subtitle="Market share is each carrier's part of all carriers' paid passengers in the same period: passenger scope, per leg, domestic and international."
        >
          <Loaded state={ranking} isEmpty={(data) => data.total === 0} emptyMessage="This carrier has no flights in this period.">
            {(data) => (
              <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.9fr)]">
                <BarList
                  valueFormat={percent}
                  items={data.carriers.slice(0, 10).map((c) => ({ label: code(c.iata, c.carrier), sub: c.name ?? undefined, value: c.market_share ?? 0 }))}
                />
                <div className="min-w-0">
                  <DataTable
                    caption="Carriers by paid passengers"
                    columns={[
                      "Carrier",
                      "Name",
                      "Country",
                      <Term key="p" term="paid_passengers">Paid passengers</Term>,
                      <Term key="ms" term="market_share">Market share</Term>,
                      <Term key="f" term="passenger_flights">Passenger flights</Term>,
                      <Term key="s" term="seats">Seats</Term>,
                      <Term key="lf" term="load_factor">Load factor</Term>,
                      <Term key="i" term="international_paid_passengers">International paid pax</Term>,
                    ]}
                    alignRight={[3, 4, 5, 6, 7, 8]}
                    rows={data.carriers.map((c) => [
                      <RowButton key="code" selected={chartCode === c.carrier} onClick={() => setSelected(c.carrier)}>
                        {c.carrier}
                        {c.iata ? ` · ${c.iata}` : ""}
                      </RowButton>,
                      c.name ?? "—",
                      c.country ?? "—",
                      formatNumber(c.paid_passengers),
                      ratio(c.market_share),
                      formatNumber(c.passenger_takeoffs),
                      formatNumber(c.seats),
                      ratio(c.load_factor_paid),
                      formatNumber(c.international_paid_passengers),
                    ])}
                  />
                  <Pager page={data} onOffset={setOffset} noun="carriers" />
                  <p className="mt-3 text-xs leading-relaxed text-muted">
                    Names are the latest recorded for each code. TAM keeps its code under LATAM. Total of the period:{" "}
                    {formatNumber(data.market_paid_passengers)} paid passengers.
                  </p>
                </div>
              </div>
            )}
          </Loaded>
        </Card>
      </div>
    </>
  );
}

function CarrierSeriesCard({ carrier, period }: { carrier: string; period: Period }) {
  const provider = useDataProvider();
  const series = useResource(useCallback((signal: AbortSignal) => provider.getCarrierSeries({ carrier, ...period }, signal), [provider, carrier, period]));
  const [metric, setMetric] = useState(CARRIER_METRICS[0].key);
  const active = CARRIER_METRICS.find((m) => m.key === metric) ?? CARRIER_METRICS[0];
  return (
    <Card
      title={`Monthly evolution · ${carrier}`}
      subtitle="Share of each month's paid passengers. Pick a carrier in the table to change it."
      action={<MetricTabs options={CARRIER_METRICS} value={metric} onChange={setMetric} />}
    >
      <Loaded state={series} isEmpty={(data) => !data.carrier_found || data.points.length === 0} emptyMessage="This carrier has no data in the period.">
        {(data) => (
          <>
            <SeriesChart points={data.points} period={data.period} metric={active} />
            <div className="mt-2">
              <PeriodLine context={data} />
            </div>
          </>
        )}
      </Loaded>
    </Card>
  );
}
