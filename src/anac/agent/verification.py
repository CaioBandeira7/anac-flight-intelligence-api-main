"""Check each number in an answer against the record it claims to describe.

A number that merely exists somewhere in the tool results is not enough. Tool results become facts
(value, metric, scopes such as the airport or route, period). For each number, the sentence decides
which entity, metric and year it is about, and a fact must agree on all of them.

Numbers written in the question are never evidence: a user cannot supply the figures.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

SMALL_INTEGER_LIMIT = 12
_SENTENCE = re.compile(r"(?<=[.!?;:\n])\s+")
_NUMBER = re.compile(r"\d[\d.,]*\d|\d")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
# Models write dates with non-breaking hyphens, as in 2025\u201112. A dataset's name is not a metric.
_HYPHENS = str.maketrans(dict.fromkeys("\u2010\u2011\u2012\u2013\u2014\u2212", "-"))
_NOISE = re.compile(
    r"/v\d+/[\w/-]*|\b(?:19|20)\d{2}-\d{2}(?:-\d{2})?\b|\bgpt-[\w.-]+"
    r"|\b(?:dataset|conjunto de dados)\W{0,3}[\w.-]+|\b[\w.-]+ dataset\b"
)
# "The 200 busiest routes": a coverage note, accepted only for a number that is in a note.
_RANKING = re.compile(r"\s*(?:rotas|routes|maiores|principais|busiest|largest|top)\b")
_DECIMAL_IN_TEXT = re.compile(r"\d+(?:\.\d+)?")

METRIC_WORDS = {
    "passengers": ("passengers", "passageiros", "pax"),
    "movements": (
        "movements",
        "movimentos",
        "movimentacoes",
        "pousos",
        "decolagens",
        "takeoffs",
        "landings",
    ),
    "flights": ("flights", "voos"),
    "active_routes": ("active routes", "rotas ativas"),
    "load_factor": ("load factor", "ocupacao", "fator de ocupacao", "lf"),
    "seats": ("seats", "assentos"),
    "wape": ("wape",),
    "mae": ("mae",),
}
_CHANGE = re.compile(
    r"(?<!\w)(?:change|increase[ds]?|decrease[ds]?|growth|up|down|rose|fell|variacao|aumento|queda|alta|"
    r"crescimento|reducao|subiu|caiu|cresceu)(?!\w)"
)
# "12 months" and "the last 24 meses" describe a window, not a measurement.
_TIME_SPAN = re.compile(r"\s*(?:months?|meses|mes|years?|anos?)\b")
METHOD_WORDS = {"baseline": ("baseline",), "lightgbm": ("lightgbm",)}


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


@dataclass(frozen=True)
class Fact:
    value: float
    kind: str  # count, ratio or raw
    metric: str | None = None
    scopes: tuple[tuple[str, str], ...] = ()
    years: frozenset[str] = frozenset()
    change: bool = False

    def readings(self) -> list[float]:
        magnitude = abs(self.value)
        if self.kind == "count":
            return [magnitude, magnitude / 1e3, magnitude / 1e6, magnitude / 1e9]
        if self.kind == "ratio":
            return [magnitude, magnitude * 100]
        return [magnitude]


@dataclass
class Alias:
    pattern: re.Pattern[str]
    group: str
    key: str


@dataclass
class Evidence:
    facts: list[Fact] = field(default_factory=list)
    aliases: list[Alias] = field(default_factory=list)


def _word(text: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(fold(text))}(?!\w)")


def _years(period: str) -> frozenset[str]:
    return frozenset(_YEAR.findall(period))


def _context_numbers(text: str | None, years: frozenset[str]) -> list[Fact]:
    """Numbers in explanatory notes, such as "the 200 busiest routes". They support no metric."""
    return [
        Fact(float(item), "raw", years=years)
        for item in _DECIMAL_IN_TEXT.findall(_YEAR.sub(" ", text or ""))
    ]


def build_evidence(results: list[dict[str, Any]]) -> Evidence:
    evidence = Evidence()
    for result in results:
        provenance = result.get("provenance") or {}
        years = _years(str(provenance.get("period", "")))
        evidence.facts.extend(_context_numbers(provenance.get("note"), frozenset()))
        evidence.facts.extend(_context_numbers(result.get("message"), frozenset()))
        if isinstance(result.get("matches"), int):
            evidence.facts.append(Fact(float(result["matches"]), "raw"))
        for kpi in result.get("kpis", []):
            metric = kpi["id"]
            kind = "ratio" if kpi.get("unit") == "ratio" else "count"
            evidence.facts.append(Fact(float(kpi["value"]), kind, metric, years=years))
            delta = kpi.get("change_vs_previous_12_months")
            if delta is not None:
                earlier = frozenset(str(int(year) - 1) for year in years)
                evidence.facts.append(
                    Fact(float(delta), "ratio", metric, years=years | earlier, change=True)
                )
        for point in result.get("monthly", []):
            month_years = _years(point["month"])
            scopes = (("month", point["month"]),)
            evidence.aliases.append(
                Alias(re.compile(re.escape(point["month"])), "month", point["month"])
            )
            evidence.facts.append(
                Fact(float(point["passengers"]), "count", "passengers", scopes, month_years)
            )
            evidence.facts.append(
                Fact(float(point["flights"]), "count", "flights", scopes, month_years)
            )
        for airport in result.get("airports", []):
            key = airport["icao"]
            names = {
                airport["icao"],
                airport["iata"],
                airport["name"],
                airport["city"],
                str(airport["name"]).split(" - ")[0],
            }
            evidence.aliases.extend(Alias(_word(name), "airport", key) for name in names if name)
            evidence.facts.append(
                Fact(float(airport["movements"]), "count", "movements", (("airport", key),), years)
            )
        for route in result.get("routes", []):
            origin, destination = fold(route["origin"]), fold(route["destination"])
            key = f"{origin}-{destination}"
            between = r"\b[^.;\n]{0,40}?\b"
            evidence.aliases.append(
                Alias(re.compile(rf"\b{origin}{between}{destination}\b"), "route", key)
            )
            # The opposite direction is a different route, so it must not borrow these figures.
            evidence.aliases.append(
                Alias(
                    re.compile(rf"\b{destination}{between}{origin}\b"),
                    "route",
                    f"{destination}-{origin}",
                )
            )
            scopes = (("route", key),)
            evidence.facts.append(
                Fact(float(route["passengers"]), "count", "passengers", scopes, years)
            )
            evidence.facts.append(
                Fact(float(route["loadFactor"]), "ratio", "load_factor", scopes, years)
            )
        for model in result.get("models", []):
            module = model.get("module")
            if not module:
                continue
            method = "lightgbm" if "lightgbm" in fold(str(model.get("method"))) else "baseline"
            model_scopes = (("module", str(module)), ("method", method))
            for pattern in (rf"\bmodul[eo] {module}\b", rf"\bmodulo {module}\b"):
                evidence.aliases.append(Alias(re.compile(pattern), "module", module))
            for metric in model.get("metrics", []):
                name = fold(metric["name"])
                evidence.facts.append(
                    Fact(
                        float(metric["value"]),
                        "ratio",
                        "mae" if "mae" in name else "wape",
                        model_scopes,
                        years,
                    )
                )
            evidence.facts.extend(
                Fact(item.value, "raw", scopes=model_scopes, years=years)
                for item in _context_numbers(model.get("comparison"), frozenset())
            )
    for method, words in METHOD_WORDS.items():
        evidence.aliases.extend(Alias(_word(word), "method", method) for word in words)
    return evidence


def _readings(token: str) -> list[tuple[float, int]]:
    """A number may use either style: 1.234,5 or 1,234.5."""
    text = token.rstrip(".,")
    found: list[tuple[float, int]] = []
    for thousands, decimal in ((".", ","), (",", ".")):
        parts = text.split(decimal)
        if len(parts) > 2:
            continue
        whole = parts[0].replace(thousands, "")
        fraction = parts[1] if len(parts) == 2 else ""
        if whole.isdigit() and (not fraction or fraction.isdigit()):
            found.append((float(f"{whole}.{fraction or 0}"), len(fraction)))
    return found


def _matches(fact: Fact, value: float, decimals: int) -> bool:
    tolerance = 0.5 * 10 ** (-decimals) * 1.001
    return any(abs(value - reading) <= tolerance for reading in fact.readings())


def _nearest_metric(sentence: str, start: int, end: int) -> str | None:
    best: tuple[int, str] | None = None
    for metric, words in METRIC_WORDS.items():
        for word in words:
            for match in _word(word).finditer(sentence):
                distance = start - match.end() if match.end() <= start else match.start() - end
                if best is None or distance < best[0]:
                    best = (max(distance, 0), metric)
    return best[1] if best else None


def _metric_follows(sentence: str, end: int) -> bool:
    """A small integer right before a metric, as in "5 passengers", is a measured claim."""
    next_words = sentence[end : end + 24]
    return any(_word(word).search(next_words) for words in METRIC_WORDS.values() for word in words)


def _bind_scopes(sentence: str, position: int, aliases: list[Alias]) -> dict[str, str]:
    """For each kind of entity, the mention closest before the number, else the first after it."""
    before: dict[str, tuple[int, str]] = {}
    after: dict[str, tuple[int, str]] = {}
    for alias in aliases:
        for match in alias.pattern.finditer(sentence):
            if match.end() <= position:
                if alias.group not in before or match.end() > before[alias.group][0]:
                    before[alias.group] = (match.end(), alias.key)
            elif alias.group not in after or match.start() < after[alias.group][0]:
                after[alias.group] = (match.start(), alias.key)
    return {group: item[1] for group, item in {**after, **before}.items()}


def verify_answer(answer: str, results: list[dict[str, Any]]) -> list[str]:
    """Problems found in an answer, in plain words the model can act on. Empty means verified."""
    evidence = build_evidence(results)
    problems: list[str] = []
    inherited: dict[str, str] = {}
    previous_metric: str | None = None
    for raw_sentence in _SENTENCE.split(fold(answer).translate(_HYPHENS)):
        years = set(_YEAR.findall(raw_sentence))
        sentence = _NOISE.sub(lambda match: " " * len(match.group()), raw_sentence)
        sentence = _YEAR.sub(lambda match: " " * len(match.group()), sentence)
        for match in _NUMBER.finditer(sentence):
            token = match.group()
            readings = _readings(token)
            metric = _nearest_metric(sentence, match.start(), match.end())
            following = sentence[match.end() : match.end() + 3]
            if _TIME_SPAN.match(sentence, match.end()):
                continue
            small = (
                len(readings) > 0
                and readings[0][1] == 0
                and readings[0][0] <= SMALL_INTEGER_LIMIT
                and not _metric_follows(sentence, match.end())
            )
            candidates = [
                fact
                for fact in evidence.facts
                if any(_matches(fact, value, decimals) for value, decimals in readings)
            ]
            if "%" in following:
                candidates = [fact for fact in candidates if fact.kind in ("ratio", "raw")]
            if not candidates:
                if small:
                    continue
                problems.append(f"{token} is not in the tool results")
                continue
            local = _bind_scopes(sentence, match.start(), evidence.aliases)
            bound = {**inherited, **local}
            # The change word may be anywhere earlier in this clause, or right after the number.
            clause = sentence[sentence.rfind(",", 0, match.start()) + 1 : match.start()]
            window = clause + sentence[match.end() : match.end() + 14]
            is_change = bool(_CHANGE.search(window)) and "%" in following
            # "It rose 9.7%" refers to the metric of the sentence before.
            subject = metric or previous_metric
            ranking = bool(_RANKING.match(sentence, match.end()))
            kept = []
            for fact in candidates:
                if fact.metric is None:
                    # A note's number, such as "200 busiest", supports no measured claim.
                    if metric is None or fact.scopes or ranking:
                        kept.append(fact)
                    continue
                if is_change:
                    # A change belongs to one metric, and is never a level.
                    if not fact.change and fact.metric != "load_factor":
                        continue
                    if fact.change and subject is not None and fact.metric != subject:
                        continue
                else:
                    if fact.change:
                        continue
                    if metric is not None and fact.metric != metric:
                        continue
                scopes = dict(fact.scopes)
                if any(bound.get(group, key) != key for group, key in scopes.items()):
                    continue
                # A market total cannot describe an airport or route named in this sentence.
                if not scopes and any(group in local for group in ("airport", "route", "module")):
                    continue
                kept.append(fact)
            if not kept:
                if small:
                    continue
                problems.append(
                    f"{token} does not belong to the entity or metric it is attached to"
                )
                continue
            if years:
                dated = [fact for fact in kept if not fact.years or fact.years & years]
                if not dated:
                    problems.append(
                        f"{token} is not from the year stated ({', '.join(sorted(years))})"
                    )
        for group, key in _bind_scopes(sentence, len(sentence), evidence.aliases).items():
            inherited[group] = key
        previous_metric = _nearest_metric(sentence, len(sentence), len(sentence)) or previous_metric
    return problems
