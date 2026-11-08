"""Command line: ``anac-ingest sample | full | status``."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from anac.config import IngestionConfig, load_config
from anac.ingestion.pipeline import run_ingestion, run_status
from anac.ingestion.supplements import (
    compare_revisions,
    load_supplement_config,
    publish,
    publish_evaluation,
    supplement_status,
)

DEFAULT_CONFIG = Path("configs/ingestion.toml")
SUPPLEMENT_CONFIG = Path("configs/supplements.toml")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="anac-ingest", description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    commands = parser.add_subparsers(dest="command", required=True)

    sample = commands.add_parser("sample", help="process randomly placed blocks of the CSV")
    sample.add_argument("--blocks", type=int)
    sample.add_argument("--block-mb", type=int)
    sample.add_argument("--seed", type=int)
    sample.add_argument("--output-root", type=Path)

    full = commands.add_parser("full", help="process the whole CSV (requires --confirm-full)")
    full.add_argument("--confirm-full", action="store_true")
    full.add_argument("--chunk-mb", type=float)
    full.add_argument("--limit-chunks", type=int, help="stop early; rerun without it to resume")
    full.add_argument("--output-root", type=Path)

    status = commands.add_parser("status", help="show the progress of a run")
    status.add_argument("--output-root", type=Path)

    supplements = commands.add_parser("supplements", help="official monthly ZIPs")
    supplements.add_argument(
        "action", choices=["status", "publish", "revisions", "publish-evaluation"]
    )
    return parser


def _with_overrides(cfg: IngestionConfig, args: argparse.Namespace) -> IngestionConfig:
    overrides = {
        "sample_blocks": getattr(args, "blocks", None),
        "sample_block_mb": getattr(args, "block_mb", None),
        "sample_seed": getattr(args, "seed", None),
        "chunk_size_mb": getattr(args, "chunk_mb", None),
    }
    changes = {key: value for key, value in overrides.items() if value is not None}
    return dataclasses.replace(cfg, **changes)


def _supplements(action: str) -> int:
    cfg = load_supplement_config(SUPPLEMENT_CONFIG)
    processed, interim = Path("data/processed"), Path("data/interim")
    try:
        result: object
        if action == "status":
            result = supplement_status(cfg)
        elif action == "publish":
            result = publish(cfg, processed, interim)
        elif action == "revisions":
            result = compare_revisions(cfg, processed)
        else:
            result = publish_evaluation(cfg, processed, interim)
    except (RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "supplements":
        return _supplements(args.action)
    cfg = _with_overrides(load_config(args.config), args)
    if args.command == "status":
        root = args.output_root or cfg.full_output_root
        print(json.dumps(run_status(cfg, root), indent=2))
        return 0
    try:
        if args.command == "sample":
            report = run_ingestion(cfg, "sample", output_root=args.output_root)
        else:
            report = run_ingestion(
                cfg,
                "full",
                output_root=args.output_root,
                confirm_full=args.confirm_full,
                limit_chunks=args.limit_chunks,
            )
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report.get("reconciliation", report), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
