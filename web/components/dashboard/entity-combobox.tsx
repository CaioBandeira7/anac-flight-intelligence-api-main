"use client";

import { useCallback, useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Search, X } from "lucide-react";
import { useDataProvider } from "@/components/data-provider";
import { useResource } from "@/hooks/use-resource";
import {
  airportCode,
  airportPlace,
  airportSearchable,
  carrierSearchable,
  fold,
  highlight,
  rank,
  type AirportEntry,
  type CarrierEntry,
  type Searchable,
} from "@/lib/data";
import { cn } from "@/lib/utils";
import { Overlay, POPOVER_SURFACE, useAnchoredStyle, useOutsidePress } from "./overlay";

const LIMIT = 8;

function Marked({ text, query }: { text: string; query: string }) {
  return (
    <>
      {highlight(text, query).map((part, i) =>
        part.match ? (
          <mark key={i} className="rounded-[3px] bg-cyan/20 text-ink">
            {part.text}
          </mark>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </>
  );
}

interface ComboboxProps<T> {
  label: string;
  placeholder: string;
  /** null while the catalog loads. */
  items: T[] | null;
  loadError?: string | null;
  searchable: (item: T) => Searchable;
  /** The code sent to the API when this item is chosen. */
  codeOf: (item: T) => string;
  /** Short text shown in the field once chosen. */
  labelOf: (item: T) => string;
  renderOption: (item: T, query: string) => ReactNode;
  /** The applied code, or "" for no filter. */
  value: string;
  onChange: (code: string) => void;
  noun: string;
}

/**
 * Accessible combobox (WAI-ARIA 1.2 list autocomplete). Suggestions show on focus,
 * filter as you type, and are picked with the mouse or with arrows and Enter.
 * It never picks an ambiguous match by itself: Enter without a highlighted option
 * only accepts a query that is exactly one item's code.
 */
export function Combobox<T>({ label, placeholder, items, loadError, searchable, codeOf, labelOf, renderOption, value, onChange, noun }: ComboboxProps<T>) {
  const id = useId();
  const listId = `${id}-list`;
  const input = useRef<HTMLInputElement>(null);
  const wrapper = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState<string | null>(null);
  const [active, setActive] = useState(-1);
  const [hint, setHint] = useState<string | null>(null);
  const style = useAnchoredStyle(wrapper, open, { maxHeight: 340 });

  const selected = useMemo(() => {
    if (!value || !items) return null;
    const wanted = fold(value);
    return items.find((item) => searchable(item).codes.some((c) => c && fold(c) === wanted)) ?? null;
  }, [items, value, searchable]);

  const shown = query ?? (selected ? labelOf(selected) : value);
  const typed = query ?? "";
  const options = useMemo(() => (items ? rank(items, typed, searchable, LIMIT) : []), [items, typed, searchable]);

  const closeList = useCallback(() => {
    setOpen(false);
    setActive(-1);
    setQuery(null);
    setHint(null);
  }, []);
  useOutsidePress([wrapper, list], open, closeList);

  const choose = (item: T) => {
    onChange(codeOf(item));
    closeList();
  };

  const clear = () => {
    onChange("");
    setQuery(null);
    setHint(null);
    input.current?.focus();
  };

  const onKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) setOpen(true);
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((i) => (options.length ? (i + step + options.length) % options.length : -1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (open && active >= 0 && options[active]) return choose(options[active]);
      if (!typed.trim()) return;
      const exact = (items ?? []).filter((item) => searchable(item).codes.some((c) => c && fold(c) === fold(typed.trim())));
      if (exact.length === 1) return choose(exact[0]);
      setOpen(true);
      setHint(options.length ? "Choose one of the suggestions." : null);
    } else if (event.key === "Escape") {
      if (open) {
        event.preventDefault();
        closeList();
      }
    } else if (event.key === "Tab") {
      closeList();
    }
  };

  const activeId = open && active >= 0 && options[active] ? `${id}-opt-${active}` : undefined;
  const showClear = Boolean(value || query);

  return (
    <div className="flex flex-col gap-1.5 text-xs text-muted">
      <label htmlFor={`${id}-input`}>{label}</label>
      <div ref={wrapper} className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted" aria-hidden />
        <input
          ref={input}
          id={`${id}-input`}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeId}
          autoComplete="off"
          spellCheck={false}
          value={shown}
          placeholder={placeholder}
          onFocus={(e) => {
            e.target.select();
            setOpen(true);
          }}
          onClick={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(-1);
            setHint(null);
            setOpen(true);
          }}
          onKeyDown={onKey}
          className="w-full min-w-0 rounded-lg border border-line bg-hover py-2 pl-8 pr-8 text-sm text-ink placeholder:text-muted focus:outline-none focus-visible:border-cyan sm:w-56"
        />
        {showClear && (
          <button
            type="button"
            onClick={clear}
            aria-label={`Clear ${label.toLowerCase()}`}
            className="absolute right-1.5 top-1/2 grid size-6 -translate-y-1/2 place-items-center rounded-md text-muted hover:bg-hover hover:text-ink"
          >
            <X className="size-3.5" aria-hidden />
          </button>
        )}
      </div>
      {open && (
        <Overlay>
          <ul ref={list} id={listId} role="listbox" aria-label={`${label} suggestions`} style={style} className={cn(POPOVER_SURFACE, "p-1.5")}>
            {hint && <li className="px-3 py-2 text-xs text-demo">{hint}</li>}
            {items === null ? (
              <li className="px-3 py-2 text-xs text-muted">{loadError ?? `Loading ${noun}s…`}</li>
            ) : options.length === 0 ? (
              <li className="px-3 py-2 text-xs text-muted">
                No {noun} matches “{typed.trim()}”. Try a code, a name or a city.
              </li>
            ) : (
              <>
                {!typed.trim() && <li className="px-3 pb-1 pt-1.5 text-[11px] text-muted">Busiest in the last 12 months</li>}
                {options.map((item, index) => (
                  <li
                    key={codeOf(item) + index}
                    id={`${id}-opt-${index}`}
                    role="option"
                    aria-selected={index === active}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => choose(item)}
                    onMouseMove={() => setActive(index)}
                    className={cn("cursor-pointer rounded-lg px-3 py-2 text-[13px]", index === active ? "bg-cyan/[0.1]" : "hover:bg-hover")}
                  >
                    {renderOption(item, typed)}
                  </li>
                ))}
              </>
            )}
          </ul>
        </Overlay>
      )}
    </div>
  );
}

/** Airport filter over the API catalog: IATA, ICAO, name, city, UF and country. */
export function AirportCombobox({ label, value, onChange, placeholder = "Code, name or city" }: { label: string; value: string; onChange: (code: string) => void; placeholder?: string }) {
  const provider = useDataProvider();
  const catalog = useResource(useCallback(() => provider.getAirportCatalog(), [provider]));
  return (
    <Combobox<AirportEntry>
      label={label}
      placeholder={placeholder}
      noun="airport"
      items={catalog.status === "success" ? catalog.data.airports : null}
      loadError={catalog.status === "error" ? "Suggestions are unavailable: the airport list could not be loaded." : null}
      searchable={airportSearchable}
      codeOf={airportCode}
      labelOf={(a) => [a.iata, a.airport].filter(Boolean).join(" · ")}
      value={value}
      onChange={onChange}
      renderOption={(a, q) => (
        <div className="min-w-0">
          <p className="font-mono text-[12.5px] text-ink">
            {a.iata && (
              <>
                <Marked text={a.iata} query={q} /> ·{" "}
              </>
            )}
            <Marked text={a.airport} query={q} />
          </p>
          <p className="truncate text-xs text-muted">
            {a.name && <Marked text={a.name} query={q} />}
            {airportPlace(a) && (
              <>
                {" · "}
                <Marked text={airportPlace(a)} query={q} />
              </>
            )}
          </p>
        </div>
      )}
    />
  );
}

/** Carrier filter over the API catalog: IATA, ICAO and the latest recorded name. Codes are never merged. */
export function CarrierCombobox({ label, value, onChange }: { label: string; value: string; onChange: (code: string) => void }) {
  const provider = useDataProvider();
  const catalog = useResource(useCallback(() => provider.getCarrierCatalog(), [provider]));
  // Codes with no flight in the last 12 months are labelled, so historical codes stand apart.
  const recentFrom = catalog.status === "success" ? catalog.data.recent_period.from : null;
  return (
    <Combobox<CarrierEntry>
      label={label}
      placeholder="Code or name"
      noun="carrier"
      items={catalog.status === "success" ? catalog.data.carriers : null}
      loadError={catalog.status === "error" ? "Suggestions are unavailable: the carrier list could not be loaded." : null}
      searchable={carrierSearchable}
      codeOf={(c) => c.carrier}
      labelOf={(c) => [c.carrier, c.iata].filter(Boolean).join(" · ")}
      value={value}
      onChange={onChange}
      renderOption={(c, q) => (
        <div className="min-w-0">
          <p className="font-mono text-[12.5px] text-ink">
            <Marked text={c.carrier} query={q} />
            {c.iata && (
              <>
                {" · "}
                <Marked text={c.iata} query={q} />
              </>
            )}
            {recentFrom && c.last_month < recentFrom && <span className="ml-2 font-sans text-[11px] text-muted">last flew {c.last_month}</span>}
          </p>
          {c.name && (
            <p className="truncate text-xs text-muted">
              <Marked text={c.name} query={q} />
            </p>
          )}
        </div>
      )}
    />
  );
}
