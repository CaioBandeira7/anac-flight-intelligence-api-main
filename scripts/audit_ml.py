"""Read-only reconciliation of frozen 2023 validation artifacts (never refits or opens the test)."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from anac.evaluation.metrics import average_precision, ratio_with_interval
from anac.features.config import SealedTestError, load_feature_config, parse_month
from anac.features.contracts import CONTRACTS, validate_features
from anac.features.splits import TRAIN, VALIDATION, assign_split
from anac.models.train import SPECS, compare, load_module_frame, model_columns

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def audit(artifact_root: Path) -> dict[str, Any]:
    cfg = load_feature_config(ROOT / "configs/features.toml", root=ROOT)
    cfg = replace(
        cfg, output=artifact_root / "data/features/v1", reports=artifact_root / "reports/baselines"
    )
    sources = [
        p
        for directory in [artifact_root / "models/v1", cfg.output]
        for p in directory.rglob("*")
        if p.is_file()
    ]
    before = {p.relative_to(artifact_root).as_posix(): digest(p) for p in sorted(sources)}
    checks: list[dict[str, Any]] = []

    def check(name: str, actual: Any, expected: Any, tolerance: float = 1e-10) -> None:
        def equivalent(left: Any, right: Any) -> bool:
            if left == right:
                return True
            if type(left) is int and type(right) is int:
                return False
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return math.isclose(left, right, rel_tol=tolerance, abs_tol=tolerance)
            if isinstance(left, list) and isinstance(right, list):
                return len(left) == len(right) and all(
                    equivalent(a, b) for a, b in zip(left, right, strict=True)
                )
            if isinstance(left, dict) and isinstance(right, dict):
                return left.keys() == right.keys() and all(
                    equivalent(left[k], right[k]) for k in left
                )
            return False

        passed = equivalent(actual, expected)
        checks.append({"name": name, "actual": actual, "expected": expected, "passed": passed})

    tasks: dict[str, Any] = {}
    modules: dict[str, Any] = {}
    payload = json.loads((ROOT / "web/public/ml/showcase.json").read_text(encoding="utf-8"))
    for module in ("a", "b", "d"):
        directory = cfg.output / f"module_{module}"
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        frozen = json.loads(
            (artifact_root / f"models/v1/module_{module}/manifest.json").read_text()
        )
        if (
            manifest.get("test_targets_written")
            or parse_month(manifest["identity"]["last_target"]) >= cfg.time.test_start
        ):
            raise SealedTestError("Audit accepts only pre-test artifacts; refusing to open targets")
        features = pl.read_parquet(directory / "features.parquet")
        targets = pl.read_parquet(directory / "targets.parquet")
        validate_features(features.drop("split"), CONTRACTS[module])
        check(module + ".feature_test_rows", features.filter(pl.col("split") == "test").height, 0)
        check(
            module + ".target_month_max_before_test",
            features["target_month"].max() < cfg.time.test_start,
            True,
        )
        check(
            module + ".split_assignment",
            features["split"].to_list(),
            assign_split(features.drop("split"), cfg.time)["split"].to_list(),
        )
        # Avoid embedding hundreds of thousands of split labels in the report.
        checks[-1]["actual"] = "validated every feature row"
        checks[-1]["expected"] = "chronological split_expr with per-row purging"
        check(module + ".frozen_test_used", frozen["test_period_used"], False)
        check(module + ".feature_test_written", manifest["test_targets_written"], False)
        missing = [parse_month(month) for month in manifest["unknown_months"]]
        unknown = features.filter(pl.col("target_month").is_in(missing))
        check(
            module + ".target_stamps",
            features.filter(
                pl.col(CONTRACTS[module].stamp) > pl.col(CONTRACTS[module].limit)
            ).height,
            0,
        )
        data = load_module_frame(cfg, module)
        saved = pl.read_parquet(directory / "lightgbm_predictions_validation.parquet")
        keys = [*CONTRACTS[module].forecast_keys, "horizon"]
        target_names = [spec.target for spec in SPECS if spec.module == module]
        validation = data.filter(pl.col("split") == VALIDATION)
        joined = validation.join(
            saved.rename({n: "_saved_" + n for n in target_names}),
            on=keys,
            how="inner",
            validate="1:1",
        )
        check(module + ".prediction_join_rows", joined.height, saved.height)
        for name in target_names:
            check(
                module + "." + name + ".saved_targets",
                joined[name].to_list(),
                joined["_saved_" + name].to_list(),
            )
            checks[-1]["actual"] = "checked every saved target"
            checks[-1]["expected"] = "exact match to separate target file"
        first = cfg.time.first_target
        modules[module] = {
            "feature_rows": features.height,
            "target_rows": targets.height,
            "splits": features.group_by("split").len().sort("split").to_dicts(),
            "unknown_months": manifest["unknown_months"],
            "unknown_target_feature_rows": unknown.height,
            "corrected_loader_rows": data.height,
            "features": [
                {
                    "name": name,
                    "description": next(
                        s.description for s in CONTRACTS[module].features if s.name == name
                    ),
                }
                for group in model_columns(module)
                for name in group
            ],
            "frozen_manifest": frozen,
            "source_identity": manifest["identity"],
            "fit_target_first": first,
        }
        report = json.loads((ROOT / f"reports/models/module_{module}.json").read_text())
        for spec in [s for s in SPECS if s.module == module]:
            key = module if module != "d" else "d_" + spec.target
            model = "pred_lightgbm_" + spec.target
            frozen_model = frozen["models"][spec.target]
            check(
                key + ".model_hash",
                digest(artifact_root / f"models/v1/module_{module}" / frozen_model["file"]),
                frozen_model["sha256"],
            )
            check(
                key + ".feature_order",
                [*model_columns(module)[0], *model_columns(module)[1]],
                [*frozen_model["numeric"], *frozen_model["categorical"]],
            )
            eligible = joined.filter(
                pl.all_horizontal(pl.col(n).is_not_null() for n in spec.baselines)
            )
            expected = report["targets"][spec.target]
            computed = compare(joined, spec, model)
            a = eligible[spec.target].to_numpy().astype(float)
            predictions = eligible[model].to_numpy().astype(float)
            weights = (
                eligible["seats"].to_numpy().astype(float) if module == "b" else np.ones(len(a))
            )
            denominator = weights.sum() if module == "b" else np.abs(a).sum()
            oracle = float((np.abs(predictions - a) * weights).sum() / denominator)
            check(key + ".independent_primary", oracle, expected["lightgbm"]["value"])
            check(key + ".rows", eligible.height, expected["rows"])
            for section in ["lightgbm", "difference_vs_best_baseline", "bias"]:
                check(
                    key + "." + section + ".value",
                    computed[section]["value"],
                    expected[section]["value"],
                )
                for i, bound in enumerate(["lower", "upper"]):
                    check(
                        key + "." + section + ".ci_" + bound,
                        computed[section]["ci95"][i],
                        expected[section]["ci95"][i],
                    )
            check(key + ".baseline_identity", computed["best_baseline"], expected["best_baseline"])
            for name, result in computed["baselines"].items():
                check(key + "." + name, result["value"], expected["baselines"][name]["value"])
            for h, result in computed["by_horizon"].items():
                for name in ["lightgbm", "best_baseline_value", "difference"]:
                    check(
                        key + ".h" + h + "." + name, result[name], expected["by_horizon"][h][name]
                    )
                for i in [0, 1]:
                    check(
                        key + ".h" + h + ".ci" + str(i),
                        result["ci95"][i],
                        expected["by_horizon"][h]["ci95"][i],
                    )
            display = payload["tasks"][key]
            check(key + ".ui_primary", display["lightgbm"]["value"], oracle)
            check(
                key + ".ui_adoption",
                display["beats_best_baseline"],
                expected["beats_best_baseline"],
            )
            check(key + ".ui_scatter_max", len(display["scatter"]) <= 400, True)
            check(
                key + ".ui_months",
                all(r["month"].startswith("2023-") for r in display["monthly"]),
                True,
            )
            for h in sorted(eligible["horizon"].unique().to_list()):
                part = eligible.filter(pl.col("horizon") == h)
                for month in sorted(part["target_month"].unique().to_list()):
                    p = part.filter(pl.col("target_month") == month)
                    label = f"{month // 12:04d}-{month % 12 + 1:02d}"
                    row = next(
                        r for r in display["monthly"] if r["horizon"] == h and r["month"] == label
                    )
                    for column, field in [
                        (spec.target, "actual"),
                        (model, "model"),
                        (expected["best_baseline"], "baseline"),
                    ]:
                        value = (
                            float((p[column] * p["seats"]).sum() / p["seats"].sum())
                            if module == "b"
                            else float(p[column].sum())
                        )
                        check(
                            key + f".monthly.{h}.{label}.{field}",
                            row[field],
                            round(value, 4),
                            1e-10,
                        )
            check(
                key + ".ui_gain_source",
                display["top_features_by_gain"],
                expected["top_features_by_gain"],
            )
            reference = eligible[expected["best_baseline"]].to_numpy().astype(float)
            residual_mask = np.ones(len(a), dtype=bool) if module == "b" else a > 0
            edges = np.linspace(-30, 30, 31) if module == "b" else np.linspace(-1, 1, 41)
            for series, values in [("model", predictions), ("baseline", reference)]:
                residual = (
                    (values - a) * 100
                    if module == "b"
                    else (values[residual_mask] - a[residual_mask]) / a[residual_mask]
                )
                histogram = np.histogram(np.clip(residual, edges[0], edges[-1]), bins=edges)[
                    0
                ].tolist()
                check(key + ".histogram." + series, display["residuals"][series], histogram)
                for q, label in [(0.1, "p10"), (0.5, "p50"), (0.9, "p90")]:
                    check(
                        key + ".residual." + series + "." + label,
                        display["residuals"][series + "_quantiles"][label],
                        round(float(np.quantile(residual, q)), 4),
                    )
            if module == "b":
                weighted = ratio_with_interval(
                    eligible,
                    (pl.col(model) - pl.col(spec.target)) * pl.col("seats"),
                    pl.col("seats"),
                )
                for field in ["value", "ci95", "months"]:
                    check(
                        key + ".ui_weighted_bias." + field,
                        display["seat_weighted_bias"][field],
                        weighted[field],
                    )
                for h in display["by_horizon"]:
                    part = eligible.filter(pl.col("horizon") == h["horizon"])
                    value = float(
                        ((part[model] - part[spec.target]) * part["seats"]).sum()
                        / part["seats"].sum()
                    )
                    check(
                        key + ".ui_weighted_bias.h" + str(h["horizon"]),
                        h["seat_weighted_bias_model"],
                        value,
                    )
            legacy_unknown_usable = unknown.filter(pl.col("split") == TRAIN)
            if spec.scale:
                legacy_unknown_usable = legacy_unknown_usable.filter(pl.col(spec.scale) > 0)
            tasks[key] = {
                "module": module,
                "target": spec.target,
                "rows": eligible.height,
                "metrics": computed,
                "selection_fit_rows_recorded": expected["rows_fit"],
                "stopping_rows_recorded": expected["rows_early_stopping"],
                "rounds": expected["best_iteration"],
                "legacy_unknown_train_rows": legacy_unknown_usable.height if module == "d" else 0,
                "legacy_unknown_fit_rows": legacy_unknown_usable.filter(
                    pl.col("target_month") <= parse_month("2022-01") - pl.col("distance")
                ).height
                if module == "d"
                else 0,
                "residual_histogram_rows": display["residuals"]["rows"],
                "zero_target_rows": int((a == 0).sum()),
                "seat_weighted_signed_error": float(
                    ((predictions - a) * weights).sum() / weights.sum()
                )
                if module == "b"
                else None,
                "seat_weighted_bias": ratio_with_interval(
                    eligible,
                    (pl.col(model) - pl.col(spec.target)) * pl.col("seats"),
                    pl.col("seats"),
                )
                if module == "b"
                else None,
                "seat_weighted_bias_by_horizon": {
                    str(h): float(
                        ((part[model] - part[spec.target]) * part["seats"]).sum()
                        / part["seats"].sum()
                    )
                    for h in sorted(eligible["horizon"].unique().to_list())
                    for part in [eligible.filter(pl.col("horizon") == h)]
                }
                if module == "b"
                else None,
            }
    pressure_report = json.loads((ROOT / "reports/models/module_d.json").read_text())[
        "high_pressure_event"
    ]
    threshold = pressure_report["lightgbm"]["threshold_from_train"]
    operating = joined.filter(pl.col("seats") > 0)
    secondary = {
        "threshold_reported": threshold,
        "brier_independently_recomputed": False,
        "brier_limitation": "Calibration rates and selection-stage training predictions are not saved; no refit was performed.",
    }
    for method, prediction in [
        ("lightgbm", "_model_pressure"),
        ("baseline", "pred_pressure_seasonal_trend"),
    ]:
        if method == "lightgbm":
            part = operating.filter(pl.col("pred_lightgbm_seats") > 0).with_columns(
                (pl.col("pred_lightgbm_pax") / pl.col("pred_lightgbm_seats")).alias(prediction)
            )
        else:
            part = operating.filter(pl.col(prediction).is_not_null())
        labels = (part["pax"] / part["seats"] >= threshold).to_list()
        scores = part[prediction].to_list()
        secondary[method] = {
            "average_precision_tie_corrected": average_precision(labels, scores),
            "reported_legacy_pr_auc": pressure_report[method]["pr_auc"],
            "reported_brier": pressure_report[method]["brier"],
            "rows": part.height,
        }
    after = {p.relative_to(artifact_root).as_posix(): digest(p) for p in sorted(sources)}
    check("source_artifacts_unchanged", before, after)
    checks[-1]["actual"] = "SHA-256 rechecked for every input file"
    checks[-1]["expected"] = "same hashes before and after read-only audit"
    return {
        "status": "passed" if all(c["passed"] for c in checks) else "failed",
        "base_commit": "22a120a5aa94c95810580618531864f9d85f99b9",
        "scope": "saved 2023 selection-model predictions only; frozen final boosters are not used to score 2023",
        "test_period_read": False,
        "production_models_refit": False,
        "corrected_training_requires_new_version": True,
        "source_sha256": before,
        "modules": modules,
        "tasks": tasks,
        "secondary_pressure": secondary,
        "checks": checks,
        "check_count": len(checks),
        "failures": [c for c in checks if not c["passed"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "research/ml-showcase/results/audit.json"
    )
    args = parser.parse_args()
    allowed_output = (ROOT / "research/ml-showcase/results").resolve()
    if not args.output.resolve().is_relative_to(allowed_output):
        raise ValueError("Audit output must stay under research/ml-showcase/results")
    result = audit(args.artifact_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "checks": result["check_count"],
                "failures": result["failures"],
            }
        )
    )
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
