"""Command line: ``anac-analytics build``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from anac.analytics.build import AnalyticsStale, build_analytics
from anac.analytics.validate import AnalyticsValidationError
from anac.features.config import load_feature_config

DEFAULT_OUTPUT = Path("data/analytics/v1")
DEFAULT_REPORT = Path("reports/analytics/validation.json")
AIRPORTS = Path("data/raw/supplements/reference/AerodromosPublicos.csv")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="anac-analytics", description=__doc__)
    parser.add_argument("action", choices=["build"])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    cfg = load_feature_config(Path("configs/features.toml"))
    try:
        manifest = build_analytics(cfg, args.output, DEFAULT_REPORT, AIRPORTS)
    except (AnalyticsStale, AnalyticsValidationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    summary = {name: item["rows"] for name, item in manifest["tables"].items()}
    print(
        json.dumps(
            {
                "output": str(args.output),
                "rows": summary,
                "absent_months": manifest["absent_months"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
