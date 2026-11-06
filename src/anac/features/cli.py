"""Command line: ``anac-features build | baselines``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from anac.evaluation.baselines import evaluate_module
from anac.features.build import StaleBuild, build_module
from anac.features.config import load_feature_config
from anac.features.contracts import CONTRACTS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="anac-features", description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/features.toml"))
    parser.add_argument("action", choices=["build", "baselines"])
    parser.add_argument("--module", choices=[*CONTRACTS, "all"], default="all")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
    )
    cfg = load_feature_config(args.config)
    modules = list(CONTRACTS) if args.module == "all" else [args.module]
    try:
        for module in modules:
            if args.action == "build":
                result = build_module(cfg, module)
                print(json.dumps({"module": module, "rows": result["rows"]}, default=str))
            else:
                report = evaluate_module(cfg, module)
                print(json.dumps({"module": module, "rows": report["rows"]}, default=str))
    except (StaleBuild, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
