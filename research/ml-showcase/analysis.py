"""Error analysis, figures and the ML Studio payload, from the 2023 validation predictions.

    .venv\\Scripts\\python research\\ml-showcase\\analysis.py

Inputs (read-only): data/features/v1, data/analytics/v1, reports/models, models/v1.
Outputs: research/ml-showcase/results/*.json, research/ml-showcase/figures/*.{png,svg},
and web/public/ml/showcase.json (aggregates plus bounded validation samples).

Segments use values known at the forecast cutoff (for example the unit's recent level),
never the target itself, so grouping cannot leak the answer. Run reproduce.py first.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.ticker import FuncFormatter, PercentFormatter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from reproduce import validation_frame  # noqa: E402

from anac.evaluation.metrics import ratio_with_interval  # noqa: E402
from anac.models.train import SPECS, model_columns  # noqa: E402

FIG = HERE / "figures"
RESULTS = HERE / "results"
WEB = ROOT / "web" / "public" / "ml" / "showcase.json"

INK = "#0b1d38"
MODEL = "#1d5fd1"
BASE = "#8a97ab"
ACCENT = "#0b7f9e"
GRID = "#d9e1ec"
BAD = "#b42318"

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "font.size": 10,
        "font.family": "DejaVu Sans",
        "axes.edgecolor": "#9aa8bc",
        "axes.labelcolor": INK,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": "#46546a",
        "ytick.color": "#46546a",
        "legend.frameon": False,
    }
)

BASELINE_NAMES = {
    "pred_seasonal_naive": "Same weekday a year ago",
    "pred_seasonal_trend": "Same weekday a year ago, with trend",
    "pred_recent_weekday": "Recent same weekday (8 weeks)",
    "pred_same_month_last_year": "Same month last year",
    "pred_mean_12": "Mean of the last 12 known months",
    "pred_mean_3": "Mean of the last 3 known months",
    "pred_pax_seasonal_naive": "Same month last year",
    "pred_pax_seasonal_trend": "Same month last year, with trend",
    "pred_seats_seasonal_naive": "Same month last year",
    "pred_seats_seasonal_trend": "Same month last year, with trend",
}


def month_label(index: int) -> str:
    return f"{index // 12}-{index % 12 + 1:02d}"


def save(fig: plt.Figure, name: str) -> str:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    return f"figures/{name}.png"


def compact(value: float, _pos: Any = None) -> str:
    for size, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= size:
            return f"{value / size:.1f}{suffix}".replace(".0", "")
    return f"{value:.0f}"


# ----------------------------------------------------------------- metrics


def wape(actual: np.ndarray, predicted: np.ndarray) -> float:
    total = float(np.abs(actual).sum())
    return float(np.abs(predicted - actual).sum() / total) if total else float("nan")


def bias(actual: np.ndarray, predicted: np.ndarray) -> float:
    total = float(np.abs(actual).sum())
    return float((predicted - actual).sum() / total) if total else float("nan")


def wmae(actual: np.ndarray, predicted: np.ndarray, weight: np.ndarray) -> float:
    total = float(weight.sum())
    return float((np.abs(predicted - actual) * weight).sum() / total) if total else float("nan")


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((predicted - actual) ** 2)))


def error(frame: pl.DataFrame, task: dict[str, Any], column: str) -> float:
    a = frame.get_column(task["target"]).to_numpy().astype(float)
    p = frame.get_column(column).to_numpy().astype(float)
    if task["metric"] == "wmae":
        return wmae(a, p, frame.get_column("seats").to_numpy().astype(float))
    return wape(a, p)


def r(value: float, digits: int = 6) -> float | None:
    return None if value is None or not np.isfinite(value) else round(float(value), digits)


# ------------------------------------------------------------------- tasks


def tasks() -> list[dict[str, Any]]:
    """One entry per target, with the rows used in the official comparison."""
    out = []
    frames = {module: validation_frame(module) for module in ("a", "b", "d")}
    reports = {
        module: json.loads(
            (ROOT / "reports" / "models" / f"module_{module}.json").read_text(encoding="utf-8")
        )
        for module in ("a", "b", "d")
    }
    for spec in SPECS:
        frame = frames[spec.module].filter(
            pl.all_horizontal(pl.col(n).is_not_null() for n in spec.baselines)
        )
        report = reports[spec.module]["targets"][spec.target]
        key = spec.module if spec.module != "d" else f"d_{spec.target}"
        out.append(
            {
                "key": key,
                "module": spec.module,
                "target": spec.target,
                "frame": frame,
                "report": report,
                "baselines": list(spec.baselines),
                "best": report["best_baseline"],
                "model": f"pred_lightgbm_{spec.target}",
                "metric": "wmae" if spec.module == "b" else "wape",
            }
        )
    return out


TITLES = {
    "a": "Model A: daily aircraft movements, 50 busiest airports",
    "b": "Model B: paid seat occupancy by route and carrier",
    "d_pax": "Model D: monthly paid passengers by route",
    "d_seats": "Model D: monthly seats offered by route",
}
UNITS = {"a": "movements", "b": "seat occupancy", "d_pax": "paid passengers", "d_seats": "seats"}


# ------------------------------------------------------------ aggregations


def monthly(task: dict[str, Any]) -> pl.DataFrame:
    """Totals per target month and horizon. For B, seat-weighted load factor."""
    f = task["frame"]
    t, m, b = task["target"], task["model"], task["best"]
    if task["metric"] == "wmae":
        agg = f.group_by("horizon", "target_month").agg(
            ((pl.col(t) * pl.col("seats")).sum() / pl.col("seats").sum()).alias("actual"),
            ((pl.col(m) * pl.col("seats")).sum() / pl.col("seats").sum()).alias("model"),
            ((pl.col(b) * pl.col("seats")).sum() / pl.col("seats").sum()).alias("baseline"),
            (
                (pl.col(m) - pl.col(t)).abs().mul(pl.col("seats")).sum() / pl.col("seats").sum()
            ).alias("model_error"),
            (
                (pl.col(b) - pl.col(t)).abs().mul(pl.col("seats")).sum() / pl.col("seats").sum()
            ).alias("baseline_error"),
        )
    else:
        agg = f.group_by("horizon", "target_month").agg(
            pl.col(t).sum().alias("actual"),
            pl.col(m).sum().alias("model"),
            pl.col(b).sum().alias("baseline"),
            ((pl.col(m) - pl.col(t)).abs().sum() / pl.col(t).abs().sum()).alias("model_error"),
            ((pl.col(b) - pl.col(t)).abs().sum() / pl.col(t).abs().sum()).alias("baseline_error"),
        )
    return agg.sort("horizon", "target_month")


def by_horizon(task: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for h in sorted(task["frame"].get_column("horizon").unique().to_list()):
        part = task["frame"].filter(pl.col("horizon") == h)
        a = part.get_column(task["target"]).to_numpy().astype(float)
        entry: dict[str, Any] = {
            "horizon": int(h),
            "rows": part.height,
            "model": r(error(part, task, task["model"])),
        }
        entry["baselines"] = {n: r(error(part, task, n)) for n in task["baselines"]}
        entry["bias_model"] = r(bias(a, part.get_column(task["model"]).to_numpy().astype(float)))
        entry["bias_best_baseline"] = r(
            bias(a, part.get_column(task["best"]).to_numpy().astype(float))
        )
        if task["metric"] == "wape":
            entry["rmse_model"] = r(
                rmse(a, part.get_column(task["model"]).to_numpy().astype(float)), 3
            )
            entry["rmse_best_baseline"] = r(
                rmse(a, part.get_column(task["best"]).to_numpy().astype(float)), 3
            )
            entry["mae_model"] = r(
                float(np.mean(np.abs(part.get_column(task["model"]).to_numpy() - a))), 3
            )
        if task["metric"] == "wmae":
            entry["seat_weighted_bias_model"] = float(
                ((part.get_column(task["model"]) - part.get_column(task["target"]))
                 * part.get_column("seats")).sum() / part.get_column("seats").sum()
            )
        rows.append(entry)
    return rows


SIZE = {
    "a": "hist_level_56",
    "b": "hist_seats_mean_12",
    "d_pax": "hist_pax_mean_12",
    "d_seats": "hist_seats_mean_12",
}


def by_size(task: dict[str, Any]) -> list[dict[str, Any]]:
    """Error by decile of the unit's level known at the cutoff (not the target)."""
    f = task["frame"].filter(pl.col(SIZE[task["key"]]).is_not_null())
    f = f.with_columns(
        pl.col(SIZE[task["key"]]).qcut(10, labels=[str(i) for i in range(1, 11)]).alias("decile")
    )
    out = []
    for decile in [str(i) for i in range(1, 11)]:
        part = f.filter(pl.col("decile") == decile)
        if part.height == 0:
            continue
        level = part.get_column(SIZE[task["key"]])
        out.append(
            {
                "decile": int(decile),
                "rows": part.height,
                "level_min": r(float(level.min()), 2),
                "level_max": r(float(level.max()), 2),
                "model": r(error(part, task, task["model"])),
                "baseline": r(error(part, task, task["best"])),
            }
        )
    return out


def entity_column(task: dict[str, Any]) -> pl.Expr:
    if task["module"] == "a":
        return pl.col("airport")
    if task["module"] == "b":
        return pl.col("carrier")
    return pl.concat_str(pl.col("origin"), pl.lit("→"), pl.col("destination"))


def by_entity(task: dict[str, Any], top: int) -> list[dict[str, Any]]:
    f = task["frame"].with_columns(entity_column(task).alias("entity"))
    weight = "seats" if task["metric"] == "wmae" else task["target"]
    sizes = (
        f.group_by("entity")
        .agg(pl.col(weight).sum().alias("volume"))
        .sort("volume", descending=True)
        .head(top)
    )
    out = []
    for entity, volume in sizes.iter_rows():
        part = f.filter(pl.col("entity") == entity)
        a = part.get_column(task["target"]).to_numpy().astype(float)
        out.append(
            {
                "entity": entity,
                "volume": r(float(volume), 1),
                "rows": part.height,
                "model": r(error(part, task, task["model"])),
                "baseline": r(error(part, task, task["best"])),
                "bias_model": r(bias(a, part.get_column(task["model"]).to_numpy().astype(float)))
                if task["metric"] == "wape"
                else r(
                    float((part.get_column(task["model"]) - part.get_column(task["target"])).mean())
                ),
            }
        )
    return out


def by_market(task: dict[str, Any]) -> list[dict[str, Any]]:
    if "id_is_international" not in task["frame"].columns:
        return []
    out = []
    for flag, label in ((False, "Domestic"), (True, "International")):
        part = task["frame"].filter(pl.col("id_is_international") == flag)
        if part.height:
            out.append(
                {
                    "market": label,
                    "rows": part.height,
                    "model": r(error(part, task, task["model"])),
                    "baseline": r(error(part, task, task["best"])),
                }
            )
    return out


def by_weekday(task: dict[str, Any]) -> list[dict[str, Any]]:
    f = task["frame"].with_columns(pl.col("target_date").dt.weekday().alias("weekday"))
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return [
        {
            "weekday": names[d - 1],
            "model": r(error(f.filter(pl.col("weekday") == d), task, task["model"])),
            "baseline": r(error(f.filter(pl.col("weekday") == d), task, task["best"])),
        }
        for d in range(1, 8)
    ]


def residuals(task: dict[str, Any]) -> dict[str, Any]:
    """Relative error for volumes (rows with a positive actual), points for load factor."""
    f = task["frame"]
    a = f.get_column(task["target"]).to_numpy().astype(float)
    p = f.get_column(task["model"]).to_numpy().astype(float)
    b = f.get_column(task["best"]).to_numpy().astype(float)
    if task["metric"] == "wmae":
        rm, rb, unit = (p - a) * 100, (b - a) * 100, "percentage points"
        edges = np.linspace(-30, 30, 31)
    else:
        keep = a > 0
        rm, rb, unit = (
            (p[keep] - a[keep]) / a[keep],
            (b[keep] - a[keep]) / a[keep],
            "relative error",
        )
        edges = np.linspace(-1, 1, 41)
    hm, _ = np.histogram(np.clip(rm, edges[0], edges[-1]), bins=edges)
    hb, _ = np.histogram(np.clip(rb, edges[0], edges[-1]), bins=edges)
    q = lambda x, s: r(float(np.quantile(x, s)), 4)  # noqa: E731
    return {
        "unit": unit,
        "edges": [r(float(e), 4) for e in edges],
        "model": hm.tolist(),
        "baseline": hb.tolist(),
        "rows": len(rm),
        "model_quantiles": {"p10": q(rm, 0.1), "p50": q(rm, 0.5), "p90": q(rm, 0.9)},
        "baseline_quantiles": {"p10": q(rb, 0.1), "p50": q(rb, 0.5), "p90": q(rb, 0.9)},
        "_raw_model": rm,
        "_raw_baseline": rb,
    }


def scatter_sample(task: dict[str, Any], n: int, seed: int = 7) -> pl.DataFrame:
    f = task["frame"].filter(pl.col("horizon") == 1)
    return f.sample(n=min(n, f.height), seed=seed, shuffle=True)


# ----------------------------------------------------------------- figures


def fig_monthly(task: dict[str, Any], mon: pl.DataFrame) -> str:
    horizons = sorted(mon.get_column("horizon").unique().to_list())
    fig, axes = plt.subplots(1, len(horizons), figsize=(4.2 * len(horizons), 3.4), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, h in zip(axes, horizons, strict=True):
        part = mon.filter(pl.col("horizon") == h)
        x = [month_label(v)[5:] for v in part.get_column("target_month")]
        ax.plot(x, part.get_column("actual"), color=INK, lw=2.2, marker="o", ms=3.5, label="Actual")
        ax.plot(
            x, part.get_column("model"), color=MODEL, lw=1.8, marker="o", ms=3, label="LightGBM"
        )
        ax.plot(
            x,
            part.get_column("baseline"),
            color=BASE,
            lw=1.6,
            ls="--",
            label=BASELINE_NAMES[task["best"]],
        )
        ax.set_title(f"{h} month{'s' if h > 1 else ''} ahead")
        ax.set_xlabel("Target month, 2023")
        if task["metric"] == "wmae":
            ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
        else:
            ax.yaxis.set_major_formatter(FuncFormatter(compact))
    axes[0].set_ylabel(
        "Seat-weighted load factor" if task["metric"] == "wmae" else f"Total {UNITS[task['key']]}"
    )
    axes[0].legend(loc="lower left", fontsize=8.5)
    fig.suptitle(
        f"{TITLES[task['key']]} — actual vs predicted, validation 2023",
        fontsize=12,
        fontweight="bold",
        color=INK,
        y=1.03,
    )
    return save(fig, f"{task['key']}_actual_vs_predicted_monthly")


def fig_scatter(task: dict[str, Any]) -> str:
    s = scatter_sample(task, 4000)
    a = s.get_column(task["target"]).to_numpy().astype(float)
    p = s.get_column(task["model"]).to_numpy().astype(float)
    fig, ax = plt.subplots(figsize=(4.8, 4.6))
    if task["metric"] == "wmae":
        ax.scatter(a, p, s=5, alpha=0.25, color=MODEL, edgecolors="none")
        lim = [0, max(1.05, float(np.nanmax(a)), float(np.nanmax(p)))]
        ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
        ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    else:
        keep = (a > 0) & (p > 0)
        ax.scatter(a[keep], p[keep], s=5, alpha=0.25, color=MODEL, edgecolors="none")
        ax.set_xscale("log")
        ax.set_yscale("log")
        lo, hi = float(min(a[keep].min(), p[keep].min())), float(max(a[keep].max(), p[keep].max()))
        lim = [lo * 0.8, hi * 1.25]
        ax.xaxis.set_major_formatter(FuncFormatter(compact))
        ax.yaxis.set_major_formatter(FuncFormatter(compact))
    ax.plot(lim, lim, color=INK, lw=1, ls=":")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel(f"Actual {UNITS[task['key']]}")
    ax.set_ylabel("LightGBM prediction")
    ax.set_title(
        f"{task['key'].upper().replace('_', ' ')}: actual vs predicted, 1 month ahead\n(random sample of {len(a):,} validation rows)",
        fontsize=10,
    )
    return save(fig, f"{task['key']}_scatter")


def fig_residuals(task: dict[str, Any], res: dict[str, Any]) -> str:
    edges = np.array(res["edges"])
    centers = (edges[:-1] + edges[1:]) / 2
    width = edges[1] - edges[0]
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.bar(
        centers,
        res["baseline"],
        width=width * 0.95,
        color=BASE,
        alpha=0.55,
        label=BASELINE_NAMES[task["best"]],
    )
    ax.bar(centers, res["model"], width=width * 0.55, color=MODEL, alpha=0.9, label="LightGBM")
    ax.axvline(0, color=INK, lw=1)
    if task["metric"] == "wmae":
        ax.set_xlabel("Predicted minus actual, percentage points (clipped at ±30)")
    else:
        ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
        ax.set_xlabel("(Predicted − actual) / actual (clipped at ±100%)")
    ax.set_ylabel("Validation rows")
    ax.legend(fontsize=8.5)
    ax.set_title(f"{TITLES[task['key']]}\nresidual distribution, validation 2023", fontsize=10.5)
    return save(fig, f"{task['key']}_residuals")


def fig_horizon(task: dict[str, Any], hz: list[dict[str, Any]]) -> str:
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    names = ["LightGBM", *[BASELINE_NAMES[n] for n in task["baselines"]]]
    width = 0.8 / len(names)
    for i, name in enumerate(names):
        values = [
            row["model"] if i == 0 else row["baselines"][task["baselines"][i - 1]] for row in hz
        ]
        xs = np.arange(len(hz)) + (i - (len(names) - 1) / 2) * width
        color = MODEL if i == 0 else [BASE, "#b8c2d1", "#d3dae5"][i - 1]
        bars = ax.bar(xs, values, width=width * 0.92, color=color, label=name)
        for bar, value in zip(bars, values, strict=True):
            label = f"{value * 100:.1f}" + ("" if task["metric"] == "wmae" else "%")
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                label,
                ha="center",
                va="bottom",
                fontsize=7,
                color=INK,
            )
    ax.set_xticks(range(len(hz)), [f"{row['horizon']} mo ahead" for row in hz])
    ax.set_ylabel("Seat-weighted MAE (pts)" if task["metric"] == "wmae" else "WAPE")
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v * 100:.0f}" + ("" if task["metric"] == "wmae" else "%"))
    )
    ax.legend(fontsize=7.5, loc="upper left", ncols=1)
    ax.set_title(
        f"{TITLES[task['key']]}\nerror by horizon: LightGBM vs baselines (lower is better)",
        fontsize=10.5,
    )
    return save(fig, f"{task['key']}_by_horizon")


def fig_size(task: dict[str, Any], deciles: list[dict[str, Any]]) -> str:
    fig, ax = plt.subplots(figsize=(5.8, 3.3))
    x = [d["decile"] for d in deciles]
    ax.plot(x, [d["model"] for d in deciles], color=MODEL, marker="o", lw=2, label="LightGBM")
    ax.plot(
        x,
        [d["baseline"] for d in deciles],
        color=BASE,
        marker="o",
        ls="--",
        lw=1.6,
        label=BASELINE_NAMES[task["best"]],
    )
    ax.set_xticks(x)
    ax.set_xlabel("Decile of the unit's recent level, known at the cutoff (1 = smallest)")
    ax.set_ylabel("Seat-weighted MAE (pts)" if task["metric"] == "wmae" else "WAPE")
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v * 100:.0f}" + ("" if task["metric"] == "wmae" else "%"))
    )
    ax.legend(fontsize=8.5)
    ax.set_title(f"{TITLES[task['key']]}\nerror by traffic volume", fontsize=10.5)
    return save(fig, f"{task['key']}_by_volume")


def fig_entities(task: dict[str, Any], ents: list[dict[str, Any]], label: str) -> str:
    ents = ents[:20][::-1]
    fig, ax = plt.subplots(figsize=(6.2, 0.28 * len(ents) + 1.3))
    y = np.arange(len(ents))
    ax.barh(
        y + 0.2,
        [e["baseline"] for e in ents],
        height=0.38,
        color=BASE,
        label=BASELINE_NAMES[task["best"]],
    )
    ax.barh(y - 0.2, [e["model"] for e in ents], height=0.38, color=MODEL, label="LightGBM")
    ax.set_yticks(y, [e["entity"] for e in ents], fontsize=8)
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v * 100:.0f}" + ("" if task["metric"] == "wmae" else "%"))
    )
    ax.set_xlabel("Seat-weighted MAE (pts)" if task["metric"] == "wmae" else "WAPE")
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title(f"{TITLES[task['key']]}\nerror by {label} (largest by volume)", fontsize=10.5)
    return save(fig, f"{task['key']}_by_entity")


def fig_monthly_error(task: dict[str, Any], mon: pl.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    for h, style in zip(
        sorted(mon.get_column("horizon").unique().to_list()), ["-", "--", ":"], strict=False
    ):
        part = mon.filter(pl.col("horizon") == h)
        x = [month_label(v)[5:] for v in part.get_column("target_month")]
        ax.plot(
            x,
            part.get_column("model_error"),
            color=MODEL,
            ls=style,
            marker="o",
            ms=3,
            label=f"LightGBM, {h} mo",
        )
        ax.plot(
            x,
            part.get_column("baseline_error"),
            color=BASE,
            ls=style,
            marker=".",
            ms=3,
            label=f"Baseline, {h} mo",
        )
    ax.set_xlabel("Target month, 2023")
    ax.set_ylabel("Seat-weighted MAE (pts)" if task["metric"] == "wmae" else "WAPE")
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v * 100:.0f}" + ("" if task["metric"] == "wmae" else "%"))
    )
    ax.legend(fontsize=7.5, ncols=2)
    ax.set_title(f"{TITLES[task['key']]}\nerror by target month", fontsize=10.5)
    return save(fig, f"{task['key']}_error_by_month")


def fig_importance(task: dict[str, Any]) -> str:
    items = list(task["report"]["top_features_by_gain"].items())[::-1]
    fig, ax = plt.subplots(figsize=(5.6, 0.3 * len(items) + 1.2))
    ax.barh([k for k, _ in items], [v for _, v in items], color=ACCENT)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Share of total split gain (top 10 features)")
    ax.set_title(
        f"{TITLES[task['key']]}\nLightGBM gain importance (selection model)", fontsize=10.5
    )
    return save(fig, f"{task['key']}_feature_gain")


def fig_examples_a(task: dict[str, Any], ents: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """Daily series 1 month ahead for the best- and worst-predicted of the 10 busiest airports."""
    top10 = sorted(ents[:10], key=lambda e: e["model"])
    picks = [top10[0], top10[-1]]
    f = task["frame"].filter(pl.col("horizon") == 1)
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True)
    payload = {}
    for ax, pick, word in zip(axes, picks, ["Best", "Worst"], strict=True):
        part = f.filter(pl.col("airport") == pick["entity"]).sort("target_date")
        x = part.get_column("target_date").to_list()
        ax.plot(x, part.get_column("movements"), color=INK, lw=1.2, label="Actual")
        ax.plot(x, part.get_column(task["model"]), color=MODEL, lw=1.1, label="LightGBM")
        ax.plot(
            x, part.get_column(task["best"]), color=BASE, lw=1, ls="--", label="Recent same weekday"
        )
        ax.set_title(
            f"{word} of the 10 busiest: {pick['entity']} — WAPE {pick['model'] * 100:.1f}% (baseline {pick['baseline'] * 100:.1f}%)",
            fontsize=10,
        )
        ax.set_ylabel("Daily movements")
        payload[word.lower()] = {
            "entity": pick["entity"],
            "model": pick["model"],
            "baseline": pick["baseline"],
            "points": [
                {
                    "date": d.isoformat(),
                    "actual": float(av),
                    "model": round(float(mv), 1),
                    "baseline": round(float(bv), 1),
                }
                for d, av, mv, bv in zip(
                    x,
                    part.get_column("movements"),
                    part.get_column(task["model"]),
                    part.get_column(task["best"]),
                    strict=True,
                )
            ],
        }
    axes[0].legend(fontsize=8, ncols=3, loc="lower left")
    fig.suptitle(
        "Model A — daily movements, 1 month ahead, validation 2023",
        fontsize=11.5,
        fontweight="bold",
        color=INK,
    )
    fig.tight_layout()
    return save(fig, "a_examples_daily"), payload


def fig_examples_routes(
    task: dict[str, Any], ents: list[dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    """Monthly series 1 month ahead for the best- and worst-predicted of the 20 largest routes."""
    top = sorted(ents[:20], key=lambda e: e["model"])
    picks = [top[0], top[-1]]
    f = (
        task["frame"]
        .filter(pl.col("horizon") == 1)
        .with_columns(entity_column(task).alias("entity"))
    )
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.3))
    payload = {}
    for ax, pick, word in zip(axes, picks, ["Best", "Worst"], strict=True):
        part = f.filter(pl.col("entity") == pick["entity"]).sort("target_month")
        x = [month_label(v)[5:] for v in part.get_column("target_month")]
        ax.plot(
            x, part.get_column(task["target"]), color=INK, marker="o", ms=3, lw=1.8, label="Actual"
        )
        ax.plot(
            x,
            part.get_column(task["model"]),
            color=MODEL,
            marker="o",
            ms=3,
            lw=1.5,
            label="LightGBM",
        )
        ax.plot(
            x,
            part.get_column(task["best"]),
            color=BASE,
            ls="--",
            lw=1.3,
            label="Same month last year",
        )
        ax.yaxis.set_major_formatter(FuncFormatter(compact))
        ax.set_title(
            f"{word} of the 20 largest: {pick['entity']}\nWAPE {pick['model'] * 100:.1f}% (baseline {pick['baseline'] * 100:.1f}%)",
            fontsize=9.5,
        )
        payload[word.lower()] = {
            "entity": pick["entity"],
            "model": pick["model"],
            "baseline": pick["baseline"],
            "points": [
                {
                    "month": month_label(v),
                    "actual": float(av),
                    "model": round(float(mv), 1),
                    "baseline": round(float(bv), 1),
                }
                for v, av, mv, bv in zip(
                    part.get_column("target_month"),
                    part.get_column(task["target"]),
                    part.get_column(task["model"]),
                    part.get_column(task["best"]),
                    strict=True,
                )
            ],
        }
    axes[0].legend(fontsize=8)
    fig.suptitle(
        f"{TITLES[task['key']]} — 1 month ahead, validation 2023",
        fontsize=11,
        fontweight="bold",
        color=INK,
        y=1.04,
    )
    return save(fig, f"{task['key']}_examples"), payload


def fig_overview(tasks_: list[dict[str, Any]]) -> str:
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.2))
    for ax, task in zip(axes, tasks_, strict=True):
        rep = task["report"]
        model = float(rep["lightgbm"]["value"])
        base = float(rep["baselines"][rep["best_baseline"]]["value"])
        mci = rep["lightgbm"]["ci95"]
        bci = rep["baselines"][rep["best_baseline"]]["ci95"]
        ax.bar(
            [0],
            [base],
            color=BASE,
            yerr=[[base - bci[0]], [bci[1] - base]],
            capsize=4,
            ecolor="#5b677a",
        )
        ax.bar(
            [1],
            [model],
            color=MODEL,
            yerr=[[model - mci[0]], [mci[1] - model]],
            capsize=4,
            ecolor="#21324f",
        )
        ax.set_xticks([0, 1], ["Best baseline", "LightGBM"])
        fmt = (
            (lambda v: f"{v * 100:.2f} pts")
            if task["metric"] == "wmae"
            else (lambda v: f"{v * 100:.2f}%")
        )
        for x, v in ((0, base), (1, model)):
            ax.text(
                x,
                v / 2,
                fmt(v),
                ha="center",
                va="center",
                color="white",
                fontsize=8.5,
                fontweight="bold",
            )
        verdict = "beats baseline" if rep["beats_best_baseline"] else "no conclusive gain"
        ax.set_title(
            f"{task['key'].upper().replace('_', ' · ')}\n{verdict}",
            fontsize=10,
            color=MODEL if rep["beats_best_baseline"] else BAD,
        )
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}"))
        ax.set_ylabel("Seat-weighted MAE (pts)" if task["metric"] == "wmae" else "WAPE (%)")
    fig.suptitle(
        "Validation 2023: LightGBM vs the best baseline (95% block-bootstrap intervals over 12 months)",
        fontsize=11.5,
        fontweight="bold",
        color=INK,
        y=1.06,
    )
    fig.tight_layout()
    return save(fig, "overview_model_vs_baseline")


# --------------------------------------------------------------------- EDA


def eda() -> dict[str, Any]:
    analytics = ROOT / "data" / "analytics" / "v1"
    months = (
        pl.read_parquet(analytics / "dim_month.parquet").select("month", "has_data").sort("month")
    )
    routes = pl.read_parquet(analytics / "fact_route_month.parquet")
    monthly_tot = routes.group_by("month").agg(
        pl.col("paid_passengers", "seats", "all_takeoffs").sum()
    )
    series = months.join(monthly_tot, on="month", how="left").sort("month")
    fig, ax = plt.subplots(figsize=(11, 3.6))
    known = series.with_columns(
        pl.when(pl.col("has_data")).then(pl.col("paid_passengers")).alias("pax"),
        pl.when(pl.col("has_data")).then(pl.col("seats")).alias("seat"),
    )
    x = known.get_column("month").to_list()
    ax.plot(
        x,
        known.get_column("seat").to_numpy().astype(float),
        color=BASE,
        lw=1.2,
        label="Seats offered",
    )
    ax.plot(
        x,
        known.get_column("pax").to_numpy().astype(float),
        color=MODEL,
        lw=1.5,
        label="Paid passengers",
    )
    for month in known.filter(~pl.col("has_data")).get_column("month").to_list():
        ax.axvline(month, color=BAD, lw=0.8, ls=":")
    ax.axvspan(
        date(2023, 1, 1), date(2023, 12, 1), color=ACCENT, alpha=0.12, label="Validation (2023)"
    )
    ax.axvspan(
        date(2024, 1, 1),
        date(2025, 12, 1),
        color="#9aa8bc",
        alpha=0.18,
        label="Sealed test (2024–2025)",
    )
    ax.yaxis.set_major_formatter(FuncFormatter(compact))
    ax.set_ylabel("Per month, passenger scope")
    ax.legend(fontsize=8, ncols=4, loc="upper left")
    ax.set_title(
        "Brazilian air transport, 2000–2025: monthly paid passengers and seats (dotted red lines: months without data)",
        fontsize=10.5,
    )
    eda_series = save(fig, "eda_monthly_market")

    airports = pl.read_parquet(analytics / "fact_airport_month.parquet").filter(
        pl.col("month").is_between(date(2022, 1, 1), date(2022, 12, 1))
    )
    by_airport = (
        airports.group_by("airport")
        .agg(pl.col("movements").sum())
        .sort("movements", descending=True)
    )
    share = by_airport.get_column("movements").cum_sum() / by_airport.get_column("movements").sum()
    route_pax = (
        routes.filter(pl.col("month").is_between(date(2022, 1, 1), date(2022, 12, 1)))
        .group_by("origin", "destination")
        .agg(pl.col("paid_passengers").sum())
        .filter(pl.col("paid_passengers") > 0)
        .sort("paid_passengers", descending=True)
    )
    route_share = (
        route_pax.get_column("paid_passengers").cum_sum()
        / route_pax.get_column("paid_passengers").sum()
    )
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.plot(
        np.arange(1, len(share) + 1),
        share.to_numpy(),
        color=MODEL,
        lw=2,
        label=f"Airports by movements ({len(share)})",
    )
    ax.plot(
        np.arange(1, len(route_share) + 1),
        route_share.to_numpy(),
        color=ACCENT,
        lw=2,
        label=f"Directed routes by paid passengers ({len(route_share)})",
    )
    ax.axvline(50, color=BASE, ls="--", lw=1)
    ax.set_xscale("log")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Top N (log scale)")
    ax.set_ylabel("Cumulative share, 2022")
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title("Traffic is concentrated: cumulative share by rank, 2022", fontsize=10.5)
    eda_conc = save(fig, "eda_concentration")

    splits = {}
    for module in ("a", "b", "d"):
        feats = pl.read_parquet(
            ROOT / "data" / "features" / "v1" / f"module_{module}" / "features.parquet",
            columns=["split", "target_month"],
        )
        counts = (
            feats.group_by("split")
            .agg(
                pl.len().alias("rows"),
                pl.col("target_month").min().alias("first"),
                pl.col("target_month").max().alias("last"),
            )
            .sort("split")
        )
        numeric, categorical = model_columns(module)
        splits[module] = {
            "splits": [
                {
                    "split": s,
                    "rows": n,
                    "first_target": month_label(a),
                    "last_target": month_label(b),
                }
                for s, n, a, b in counts.iter_rows()
            ],
            "numeric_features": len(numeric),
            "categorical_features": len(categorical),
            "categorical": categorical,
            "feature_groups": {
                g: sum(1 for c in [*numeric, *categorical] if c.startswith(g))
                for g in ("cal_", "hist_", "id_", "lag_")
            },
        }
    pax_2022 = int(route_pax.get_column("paid_passengers").sum())
    return {
        "figures": {"market": eda_series, "concentration": eda_conc},
        "absent_months": [
            m.isoformat()[:7]
            for m in known.filter(~pl.col("has_data")).get_column("month").to_list()
        ],
        "top50_airport_movement_share_2022": r(float(share[49]), 4),
        "airports_2022": len(share),
        "routes_with_pax_2022": len(route_share),
        "paid_passengers_2022": pax_2022,
        "routes_for_80pct_pax_2022": int((route_share.to_numpy() < 0.8).sum()) + 1,
        "modules": splits,
    }


# -------------------------------------------------------------------- main


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    all_tasks = tasks()
    out: dict[str, Any] = {
        "generated_from": "validation 2023 (origins 2022-11 to 2023-11), saved LightGBM predictions",
        "tasks": {},
    }
    web: dict[str, Any] = {
        "version": 1,
        "evaluated_on": "validation, target months 2023-01 to 2023-12",
        "tasks": {},
    }
    entity_label = {"a": "airport", "b": "carrier", "d_pax": "route", "d_seats": "route"}
    for task in all_tasks:
        key = task["key"]
        mon = monthly(task)
        hz = by_horizon(task)
        deciles = by_size(task)
        ents = by_entity(task, 25)
        res = residuals(task)
        figures = {
            "monthly": fig_monthly(task, mon),
            "scatter": fig_scatter(task),
            "residuals": fig_residuals(task, res),
            "by_horizon": fig_horizon(task, hz),
            "by_volume": fig_size(task, deciles),
            "by_entity": fig_entities(task, ents, entity_label[key]),
            "error_by_month": fig_monthly_error(task, mon),
        }
        if key in ("a", "b", "d_pax", "d_seats"):
            figures["feature_gain"] = fig_importance(task)
        examples = None
        if key == "a":
            figures["examples"], examples = fig_examples_a(task, ents)
        elif key in ("d_pax",):
            figures["examples"], examples = fig_examples_routes(task, ents)
        rep = task["report"]
        summary = {
            "title": TITLES[key],
            "unit": UNITS[key],
            "rows": task["frame"].height,
            "metric": rep["metric"],
            "lightgbm": rep["lightgbm"],
            "baselines": {BASELINE_NAMES[n]: v for n, v in rep["baselines"].items()},
            "best_baseline": BASELINE_NAMES[rep["best_baseline"]],
            "difference_vs_best_baseline": rep["difference_vs_best_baseline"],
            "beats_best_baseline": rep["beats_best_baseline"],
            "bias": rep["bias"],
            "best_iteration": rep["best_iteration"],
            "rows_fit": rep["rows_fit"],
            "top_features_by_gain": rep["top_features_by_gain"],
        }
        if task["metric"] == "wmae":
            summary["seat_weighted_bias"] = ratio_with_interval(
                task["frame"],
                (pl.col(task["model"]) - pl.col(task["target"])) * pl.col("seats"),
                pl.col("seats"),
            )
        clean_res = {k: v for k, v in res.items() if not k.startswith("_")}
        readable_hz = [
            {**row, "baselines": {BASELINE_NAMES[n]: v for n, v in row["baselines"].items()}}
            for row in hz
        ]
        task_out = {
            **summary,
            "by_horizon": readable_hz,
            "by_volume_decile": deciles,
            "by_entity": ents,
            "by_market": by_market(task),
            "residuals": clean_res,
            "monthly": [
                {
                    "horizon": int(h),
                    "month": month_label(mth),
                    "actual": r(a, 4),
                    "model": r(mo, 4),
                    "baseline": r(b, 4),
                    "model_error": r(me),
                    "baseline_error": r(be),
                }
                for h, mth, a, mo, b, me, be in mon.iter_rows()
            ],
            "figures": figures,
        }
        if key == "a":
            task_out["by_weekday"] = by_weekday(task)
        if examples:
            task_out["examples"] = examples
        out["tasks"][key] = task_out
        sample = scatter_sample(task, 400, seed=11)
        web["tasks"][key] = {
            **{k: v for k, v in task_out.items() if k not in ("figures", "by_entity", "examples")},
            "by_entity": ents[:15],
            "examples": examples,
            "scatter": [
                {"actual": r(float(a), 4), "model": r(float(p), 4)}
                for a, p in zip(
                    sample.get_column(task["target"]), sample.get_column(task["model"]), strict=True
                )
            ],
        }
        print(key, "done")
    out["overview_figure"] = fig_overview(all_tasks)
    out["eda"] = eda()
    web["eda"] = {k: v for k, v in out["eda"].items() if k != "figures"}
    (RESULTS / "analysis.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    WEB.parent.mkdir(parents=True, exist_ok=True)
    WEB.write_text(json.dumps(web, separators=(",", ":"), default=str), encoding="utf-8")
    print("wrote", RESULTS / "analysis.json", "and", WEB, f"({WEB.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
