/**
 * Search over the airport and carrier catalogs served by the API.
 * Case and accents are ignored, so "sao paulo" finds "SÃO PAULO".
 */
import type { AirportEntry, CarrierEntry } from "./contracts";

/** Folds one character at a time, so positions in the folded text match the original. */
export function fold(text: string): string {
  let out = "";
  for (const char of text) out += char.normalize("NFD").replace(/\p{Diacritic}/gu, "").toUpperCase().charAt(0) || char;
  return out;
}

export interface Searchable {
  /** Codes match exactly or by prefix, and rank first. */
  codes: (string | null)[];
  /** Names match by word prefix, then anywhere. */
  names: (string | null)[];
}

/** Lower is better; null means no match. Every word of the query must appear somewhere. */
export function score(entry: Searchable, query: string): number | null {
  const q = fold(query.trim());
  if (!q) return 0;
  const codes = entry.codes.filter((c): c is string => Boolean(c)).map(fold);
  if (codes.includes(q)) return 0;
  if (codes.some((c) => c.startsWith(q))) return 1;
  const words = q.split(/\s+/);
  const text = [...codes, ...entry.names.filter((n): n is string => Boolean(n)).map(fold)].join(" ");
  if (!words.every((w) => text.includes(w))) return null;
  const starts = text.split(/[\s,/()\-.]+/);
  return words.every((w) => starts.some((s) => s.startsWith(w))) ? 2 : 3;
}

/** Best matches first; ties keep the catalog's order (busiest first). */
export function rank<T>(items: T[], query: string, toSearchable: (item: T) => Searchable, limit: number): T[] {
  if (!query.trim()) return items.slice(0, limit);
  return items
    .map((item, index) => ({ item, index, s: score(toSearchable(item), query) }))
    .filter((r): r is { item: T; index: number; s: number } => r.s !== null)
    .sort((a, b) => a.s - b.s || a.index - b.index)
    .slice(0, limit)
    .map((r) => r.item);
}

/** Splits `text` into parts that match a word of the query and parts that do not. */
export function highlight(text: string, query: string): { text: string; match: boolean }[] {
  const words = fold(query.trim()).split(/\s+/).filter(Boolean);
  if (!words.length || !text) return [{ text, match: false }];
  const folded = fold(text);
  const marks = new Array<boolean>(text.length).fill(false);
  for (const word of words) {
    let at = folded.indexOf(word);
    while (at !== -1) {
      for (let i = at; i < at + word.length; i++) marks[i] = true;
      at = folded.indexOf(word, at + word.length);
    }
  }
  const parts: { text: string; match: boolean }[] = [];
  for (let i = 0; i < text.length; i++) {
    const last = parts[parts.length - 1];
    if (last && last.match === marks[i]) last.text += text[i];
    else parts.push({ text: text[i], match: marks[i] });
  }
  return parts;
}

export const airportSearchable = (a: AirportEntry): Searchable => ({ codes: [a.iata, a.airport], names: [a.name, a.city, a.uf, a.country] });

export const carrierSearchable = (c: CarrierEntry): Searchable => ({ codes: [c.iata, c.carrier], names: [c.name] });

/** The code a filter sends: IATA when there is one, ICAO otherwise. The API accepts both. */
export const airportCode = (a: AirportEntry) => a.iata || a.airport;

export const airportPlace = (a: AirportEntry) => [a.city, a.uf ?? a.country].filter(Boolean).join(a.uf ? "/" : " · ");
