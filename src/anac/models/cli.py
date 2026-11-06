"""Command line: ``anac-models train``. There is no option to score the test period here."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from anac.features.config import load_feature_config
from anac.models.train import FrozenModelExists, load_model_config, train_module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="anac-models", description=__doc__)
    parser.add_argument("action", choices=["train"])
    parser.add_argument("--module", choices=["a", "b", "d", "all"], default="all")
    parser.add_argument("--features-config", type=Path, default=Path("configs/features.toml"))
    parser.add_argument("--config", type=Path, default=Path("configs/models.toml"))
    args = parser.parse_args(argv)
    features_cfg = load_feature_config(args.features_config)
    cfg = load_model_config(args.config)
    try:
        for module in ["a", "b", "d"] if args.module == "all" else [args.module]:
            report = train_module(module, features_cfg, cfg)
            summary = {
                name: {
                    "best_iteration": item["best_iteration"],
                    "beats": item["beats_best_baseline"],
                }
                for name, item in report["targets"].items()
            }
            print(json.dumps({"module": module, "targets": summary}))
    except FrozenModelExists as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
