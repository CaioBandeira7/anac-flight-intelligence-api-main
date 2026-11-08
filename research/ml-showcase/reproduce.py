"""Reproduce the 2023 validation results of modules A, B and D from the saved artifacts.

Read-only with respect to the project: it reads data/features/v1, models/v1 and
reports/models, and writes only under research/ml-showcase/results/. It never reads or
builds the sealed 2024-2025 test period, which does not exist in the feature files.

    .venv\\Scripts\\python research\\ml-showcase\\reproduce.py            # metrics and hashes
    .venv\\Scripts\\python research\\ml-showcase\\reproduce.py --refit    # also refit in memory

--refit retrains the selection models with the frozen configuration, in memory only, and
compares their validation predictions with the saved ones. Nothing is written to models/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from anac.features.config import load_feature_config  # noqa: E402
from anac.features.contracts import CONTRACTS  # noqa: E402
from anac.features.splits import VALIDATION  # noqa: E402
from anac.models.train import (  # noqa: E402
    SPECS,
    compare,
    fit_selection_model,
    load_model_config,
    load_module_frame,
    model_columns,
    predict,
)

OUT = Path(__file__).resolve().parent / "results"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validation_frame(module: str) -> pl.DataFrame:
    """Validation rows with targets, baseline predictions and the saved LightGBM predictions."""
    cfg = load_feature_config(ROOT / "configs" / "features.toml")
    data = load_module_frame(cfg, module)
    keys = [*CONTRACTS[module].forecast_keys, "horizon"]
    saved = pl.read_parquet(
        ROOT
        / "data"
        / "features"
        / "v1"
        / f"module_{module}"
        / "lightgbm_predictions_validation.parquet"
    )
    targets = [spec.target for spec in SPECS if spec.module == module]
    validation = data.filter(pl.col("split") == VALIDATION)
    joined = validation.join(
        saved.rename({name: f"_saved_{name}" for name in targets}),
        on=keys,
        how="inner",
        validate="1:1",
    )
    if joined.height != saved.height:
        raise SystemExit(f"module {module}: {saved.height} saved rows, {joined.height} joined")
    for name in targets:
        actual = joined.get_column(name).fill_null(0.0).to_numpy()
        stored = joined.get_column(f"_saved_{name}").fill_null(0.0).to_numpy()
        if not np.allclose(actual, stored, equal_nan=True):
            raise SystemExit(f"module {module}: saved target {name} differs from the rebuilt one")
    return joined.drop([f"_saved_{name}" for name in targets])


def scalar(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: scalar(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scalar(item) for item in value]
    if isinstance(value, float):
        return round(value, 10)
    return value


def reproduce(refit: bool) -> dict[str, Any]:
    features_cfg = load_feature_config(ROOT / "configs" / "features.toml")
    model_cfg = load_model_config(ROOT / "configs" / "models.toml", root=ROOT)
    result: dict[str, Any] = {
        "environment": {
            "python": platform.python_version(),
            "lightgbm": lgb.__version__,
            "polars": pl.__version__,
            "numpy": np.__version__,
        },
        "modules": {},
    }
    for module in ("a", "b", "d"):
        frame = validation_frame(module)
        report = json.loads(
            (ROOT / "reports" / "models" / f"module_{module}.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (ROOT / "models" / "v1" / f"module_{module}" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        module_result: dict[str, Any] = {
            "rows": frame.height,
            "origin_months": sorted(
                {str(v) for v in frame.get_column("origin_month").unique().to_list()}
            )[:1]
            + sorted({str(v) for v in frame.get_column("origin_month").unique().to_list()})[-1:],
            "manifest": {
                "trained_at": manifest["trained_at"],
                "dataset": manifest["dataset"],
                "dataset_digest": manifest["dataset_digest"],
                "params_fingerprint": manifest["params_fingerprint"],
                "test_period_used": manifest["test_period_used"],
                "git": manifest["git"],
            },
            "frozen_models": {},
            "targets": {},
        }
        for target, info in manifest["models"].items():
            path = ROOT / "models" / "v1" / f"module_{module}" / info["file"]
            actual_hash = sha256(path)
            module_result["frozen_models"][target] = {
                "file": f"models/v1/module_{module}/{info['file']}",
                "sha256": actual_hash,
                "matches_manifest": actual_hash == info["sha256"],
                "rounds": info["rounds"],
                "rows": info["rows"],
                "last_target_month_used": info["last_target_month_used"],
            }
        for spec in (item for item in SPECS if item.module == module):
            name = f"pred_lightgbm_{spec.target}"
            recomputed = compare(frame, spec, name)
            stored = report["targets"][spec.target]
            same = (
                abs(float(recomputed["lightgbm"]["value"]) - float(stored["lightgbm"]["value"]))
                < 1e-12
                and recomputed["best_baseline"] == stored["best_baseline"]
                and abs(
                    float(recomputed["difference_vs_best_baseline"]["value"])
                    - float(stored["difference_vs_best_baseline"]["value"])
                )
                < 1e-12
            )
            entry: dict[str, Any] = {
                "recomputed": scalar(recomputed),
                "matches_report": same,
                "best_iteration_in_report": stored["best_iteration"],
                "top_features_by_gain": stored["top_features_by_gain"],
            }
            if refit:
                numeric, categorical = model_columns(module)
                data = load_module_frame(features_cfg, module)
                booster, vocabulary, sizes = fit_selection_model(data, spec, model_cfg)
                scorable = frame.with_columns(pl.col(spec.weight).fill_null(0.0))
                fresh = predict(booster, scorable, spec, numeric, categorical, vocabulary)
                saved = frame.get_column(name).to_numpy()
                entry["refit"] = {
                    "best_iteration": int(booster.best_iteration),
                    "same_iteration_as_report": int(booster.best_iteration)
                    == stored["best_iteration"],
                    "rows_fit": sizes["fit"],
                    "max_abs_difference": float(np.max(np.abs(fresh - saved))),
                    "identical": bool(np.array_equal(fresh, saved)),
                }
            module_result["targets"][spec.target] = entry
        result["modules"][module] = module_result
        print(
            f"module {module}: {frame.height} rows",
            {t: e["matches_report"] for t, e in module_result["targets"].items()},
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refit", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    result = reproduce(args.refit)
    (OUT / "reproduction.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8"
    )
    print(f"wrote {OUT / 'reproduction.json'}")


if __name__ == "__main__":
    main()
