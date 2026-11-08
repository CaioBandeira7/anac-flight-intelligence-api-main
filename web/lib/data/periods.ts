/**
 * Month arithmetic and period comparison for the analytics views.
 *
 * Absent months are unknown, not zero: they become `null` gaps in charts and
 * are left out of comparisons on both sides.
 */
import type { Coverage, Period, PassengerMeasures } from "./contracts";

const index = (month: string) => {
  const [year, number] = month.split("-").map(Number);
  return year * 12 + number - 1;
};

const label = (value: number) => `${Math.floor(value / 12)}-${String((value % 12) + 1).padStart(2, "0")}`;

export const shiftMonth = (month: string, by: number) => label(index(month) + by);

export const monthCount = (period: Period) => index(period.to) - index(period.from) + 1;

/** Every month from `from` to `to`, inclusive. */
export function monthRange(period: Period): string[] {
  const out: string[] = [];
  for (let i = index(period.from); i <= index(period.to); i++) out.push(label(i));
  return out;
}

const later = (a: string, b: string) => (a > b ? a : b);

/** The last 12 months with data in the dataset. */
export function defaultPeriod(coverage: Coverage): Period {
  return { from: later(shiftMonth(coverage.last_month, -11), coverage.first_month), to: coverage.last_month };
}

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export const monthName = (number: number) => MONTH_NAMES[number - 1];

/** "2025-01" → "Jan 2025". */
export const formatMonth = (month: string) => `${MONTH_NAMES[Number(month.slice(5, 7)) - 1]} ${month.slice(0, 4)}`;

/** "Jan 2025 – Dec 2025", or a single month. */
export const formatPeriod = (period: Period) =>
  period.from === period.to ? formatMonth(period.from) : `${formatMonth(period.from)} – ${formatMonth(period.to)}`;

const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;

/** A period inside the coverage, in order. Anything else is rejected rather than corrected silently. */
export function isValidPeriod(period: Partial<Period>, coverage: Coverage): period is Period {
  const { from, to } = period;
  return Boolean(
    from && to && MONTH.test(from) && MONTH.test(to) && from <= to && from >= coverage.first_month && to <= coverage.last_month,
  );
}

export interface PeriodPreset {
  id: string;
  label: string;
  period: Period;
}

/** Shortcuts, all ending on months the dataset covers. "Latest year" is the last year with data. */
export function periodPresets(coverage: Coverage): PeriodPreset[] {
  const last = coverage.last_month;
  const clamp = (from: string) => later(from, coverage.first_month);
  const year = Number(last.slice(0, 4));
  const presets: PeriodPreset[] = [
    { id: "3m", label: "Last 3 months", period: { from: clamp(shiftMonth(last, -2)), to: last } },
    { id: "6m", label: "Last 6 months", period: { from: clamp(shiftMonth(last, -5)), to: last } },
    { id: "12m", label: "Last 12 months", period: { from: clamp(shiftMonth(last, -11)), to: last } },
    { id: "year", label: last.endsWith("-12") ? `${year}` : `${year} to date`, period: { from: clamp(`${year}-01`), to: last } },
  ];
  if (`${year - 1}-12` >= coverage.first_month) {
    presets.push({ id: "previous-year", label: `${year - 1}`, period: { from: clamp(`${year - 1}-01`), to: `${year - 1}-12` } });
  }
  presets.push({ id: "all", label: "All history", period: { from: coverage.first_month, to: last } });
  return presets;
}

/** One value per month of the period. Months without a point (absent) are `null`, never 0. */
export function withGaps<P extends { month: string }>(
  points: P[],
  period: Period,
  value: (point: P) => number | null,
): { month: string; value: number | null }[] {
  const byMonth = new Map(points.map((point) => [point.month, point]));
  return monthRange(period).map((month) => {
    const point = byMonth.get(month);
    return { month, value: point ? value(point) : null };
  });
}

/** Absent months that fall inside the period. */
export const absentIn = (absent: string[], period: Period) => absent.filter((m) => m >= period.from && m <= period.to);

/** Shift of the comparison window: whole years, so the same calendar months are compared. */
export const comparisonShift = (period: Period) => Math.ceil(monthCount(period) / 12) * 12;

export interface Totals {
  paid_passengers: number;
  all_takeoffs: number;
  passenger_takeoffs: number;
  seats: number;
  /** Σ paid passengers / Σ seats, never an average of ratios. */
  load_factor_paid: number | null;
  months: number;
}

export function totals(points: PassengerMeasures[]): Totals {
  const sum = (key: "paid_passengers" | "all_takeoffs" | "passenger_takeoffs" | "seats") =>
    points.reduce((acc, point) => acc + point[key], 0);
  const seats = sum("seats");
  const paid = sum("paid_passengers");
  return {
    paid_passengers: paid,
    all_takeoffs: sum("all_takeoffs"),
    passenger_takeoffs: sum("passenger_takeoffs"),
    seats,
    load_factor_paid: seats > 0 ? paid / seats : null,
    months: points.length,
  };
}

export interface Comparison {
  /** Totals over every known month of the selected period. */
  current: Totals;
  /** The same calendar months shifted back, or null when no month can be paired. */
  previousPeriod: Period | null;
  /** Totals over paired months only, on each side. */
  pairedCurrent: Totals | null;
  pairedPrevious: Totals | null;
  /** Known months of the selection left out of the comparison because their pair has no data. */
  unpaired: string[];
}

/**
 * Compares the selected period with the same months `comparisonShift` earlier.
 * A month counts only when both it and its pair have data, so a gap never looks like a fall.
 */
export function comparePeriods<P extends PassengerMeasures & { month: string }>(points: P[], period: Period): Comparison {
  const shift = comparisonShift(period);
  const byMonth = new Map(points.map((point) => [point.month, point]));
  const current = points.filter((p) => p.month >= period.from && p.month <= period.to);
  const pairedNow: P[] = [];
  const pairedBefore: P[] = [];
  const unpaired: string[] = [];
  for (const point of current) {
    const before = byMonth.get(shiftMonth(point.month, -shift));
    if (before) {
      pairedNow.push(point);
      pairedBefore.push(before);
    } else unpaired.push(point.month);
  }
  const paired = pairedNow.length > 0;
  return {
    current: totals(current),
    previousPeriod: paired ? { from: shiftMonth(period.from, -shift), to: shiftMonth(period.to, -shift) } : null,
    pairedCurrent: paired ? totals(pairedNow) : null,
    pairedPrevious: paired ? totals(pairedBefore) : null,
    unpaired,
  };
}

export const relativeChange = (now: number, before: number) => (before > 0 ? now / before - 1 : null);
