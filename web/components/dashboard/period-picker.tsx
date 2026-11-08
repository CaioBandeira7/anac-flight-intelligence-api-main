"use client";

import { useCallback, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { CalendarRange, ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatMonth, formatPeriod, monthName, periodPresets, type Coverage, type Period } from "@/lib/data";
import { cn } from "@/lib/utils";
import { Overlay, POPOVER_SURFACE, useAnchoredStyle, useOutsidePress } from "./overlay";

const month = (year: number, number: number) => `${year}-${String(number).padStart(2, "0")}`;

/**
 * Monthly range picker: presets, a 12-month grid per year and quick year navigation.
 * Only months the dataset covers can be picked; months without data are marked.
 * A second click before the first one starts the range there, so it is never inverted.
 */
export function PeriodPicker({ coverage, value, onChange }: { coverage: Coverage; value: Period; onChange: (period: Period) => void }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<{ from: string; to: string | null }>(value);
  const [year, setYear] = useState(Number(value.to.slice(0, 4)));
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const style = useAnchoredStyle(trigger, open, { width: 520, maxHeight: 460 });
  const presets = useMemo(() => periodPresets(coverage), [coverage]);
  const absent = useMemo(() => new Set(coverage.absent_months), [coverage.absent_months]);
  const firstYear = Number(coverage.first_month.slice(0, 4));
  const lastYear = Number(coverage.last_month.slice(0, 4));

  const show = () => {
    setDraft(value);
    setYear(Number(value.to.slice(0, 4)));
    setOpen(true);
  };
  const close = useCallback(() => {
    setOpen(false);
    trigger.current?.focus();
  }, []);
  useOutsidePress([trigger, panel], open, () => setOpen(false));

  const apply = (period: Period) => {
    onChange(period);
    close();
  };

  const pick = (m: string) => {
    if (draft.to !== null || m < draft.from) setDraft({ from: m, to: null });
    else setDraft({ from: draft.from, to: m });
  };

  const onKey = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      close();
    }
  };

  const activePreset = presets.find((p) => p.period.from === value.from && p.period.to === value.to);
  const end = draft.to ?? draft.from;

  return (
    <div className="flex flex-col gap-1.5 text-xs text-muted">
      <span id={`${titleId}-label`}>Period</span>
      <button
        ref={trigger}
        type="button"
        onClick={() => (open ? setOpen(false) : show())}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-labelledby={`${titleId}-label ${titleId}-value`}
        className="flex items-center gap-2 rounded-lg border border-line bg-hover px-3 py-2 text-sm text-ink transition-colors hover:border-line-strong focus:outline-none focus-visible:border-cyan"
      >
        <CalendarRange className="size-4 text-muted" aria-hidden />
        <span id={`${titleId}-value`} className="tabular-nums">
          {formatPeriod(value)}
        </span>
        {activePreset && <span className="hidden text-xs text-muted sm:inline">· {activePreset.label}</span>}
        <ChevronDown className="size-4 text-muted" aria-hidden />
      </button>

      {open && (
        <Overlay>
          <div
            ref={(node) => {
              panel.current = node;
              // Move focus in once, to the active shortcut or the first control.
              if (node && !node.contains(document.activeElement)) {
                node.querySelector<HTMLElement>("[aria-pressed='true'], button")?.focus();
              }
            }}
            role="dialog"
            aria-modal="false"
            aria-labelledby={titleId}
            onKeyDown={onKey}
            style={style}
            className={cn(POPOVER_SURFACE, "p-4")}
          >
            <h2 id={titleId} className="sr-only">
              Select period
            </h2>
            <div className="grid gap-4 sm:grid-cols-[150px_minmax(0,1fr)]">
              <ul className="flex flex-wrap gap-1.5 sm:flex-col" aria-label="Shortcuts">
                {presets.map((preset) => (
                  <li key={preset.id}>
                    <button
                      type="button"
                      onClick={() => apply(preset.period)}
                      aria-pressed={preset === activePreset}
                      className={cn(
                        "w-full rounded-lg px-2.5 py-1.5 text-left text-xs transition-colors",
                        preset === activePreset ? "bg-cyan/[0.1] text-ink" : "text-ink-2 hover:bg-hover hover:text-ink",
                      )}
                    >
                      {preset.label}
                    </button>
                  </li>
                ))}
              </ul>

              <div>
                <div className="mb-3 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => setYear((y) => Math.max(firstYear, y - 1))}
                    disabled={year <= firstYear}
                    aria-label="Previous year"
                    className="grid size-8 place-items-center rounded-lg text-ink-2 hover:bg-hover disabled:opacity-40"
                  >
                    <ChevronLeft className="size-4" aria-hidden />
                  </button>
                  <select
                    aria-label="Year"
                    value={year}
                    onChange={(e) => setYear(Number(e.target.value))}
                    className="rounded-lg border border-line bg-hover px-2 py-1 text-sm font-medium tabular-nums text-ink focus:outline-none focus-visible:border-cyan"
                  >
                    {Array.from({ length: lastYear - firstYear + 1 }, (_, i) => lastYear - i).map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setYear((y) => Math.min(lastYear, y + 1))}
                    disabled={year >= lastYear}
                    aria-label="Next year"
                    className="grid size-8 place-items-center rounded-lg text-ink-2 hover:bg-hover disabled:opacity-40"
                  >
                    <ChevronRight className="size-4" aria-hidden />
                  </button>
                </div>

                <div className="grid grid-cols-4 gap-1.5" role="group" aria-label={`Months of ${year}`}>
                  {Array.from({ length: 12 }, (_, i) => {
                    const m = month(year, i + 1);
                    const outside = m < coverage.first_month || m > coverage.last_month;
                    const missing = absent.has(m);
                    const edge = m === draft.from || m === end;
                    const inside = m >= draft.from && m <= end;
                    return (
                      <button
                        key={m}
                        type="button"
                        disabled={outside}
                        onClick={() => pick(m)}
                        aria-pressed={inside}
                        aria-label={`${formatMonth(m)}${missing ? ", no data" : ""}${outside ? ", not in the dataset" : ""}`}
                        title={missing ? "No data for this month" : undefined}
                        className={cn(
                          "relative rounded-lg px-2 py-2 text-xs tabular-nums transition-colors disabled:cursor-not-allowed disabled:opacity-30",
                          edge ? "bg-blue text-white" : inside ? "bg-cyan/[0.12] text-ink" : "text-ink-2 hover:bg-hover",
                          missing && "line-through decoration-demo/70",
                        )}
                      >
                        {monthName(i + 1)}
                        {missing && <span className="absolute right-1.5 top-1.5 size-1 rounded-full bg-demo" aria-hidden />}
                      </button>
                    );
                  })}
                </div>

                <p className="mt-3 min-h-4 text-xs text-muted" aria-live="polite">
                  {draft.to === null ? `From ${formatMonth(draft.from)}: pick the last month.` : formatPeriod({ from: draft.from, to: draft.to })}
                </p>
                <p className="mt-1 flex items-center gap-1.5 text-[11px] text-muted">
                  <span className="size-1 rounded-full bg-demo" aria-hidden /> Month without data. Data covers {formatMonth(coverage.first_month)} –{" "}
                  {formatMonth(coverage.last_month)}.
                </p>
                <div className="mt-3 flex justify-end gap-2">
                  <Button type="button" variant="ghost" size="sm" onClick={close}>
                    Cancel
                  </Button>
                  <Button type="button" variant="secondary" size="sm" disabled={draft.to === null} onClick={() => draft.to && apply({ from: draft.from, to: draft.to })}>
                    Apply
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </Overlay>
      )}
    </div>
  );
}
