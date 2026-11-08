"""Atomic filesystem helpers: a reader never observes a partially written result."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

import polars as pl

_REPLACE_RETRIES = 6


def _replace_with_retry(source: Path, target: Path) -> None:
    """``os.replace``, tolerating short file locks from Windows antivirus or indexers."""
    delay = 0.1
    for attempt in range(_REPLACE_RETRIES):
        try:
            source.replace(target)
            return
        except PermissionError:
            if attempt == _REPLACE_RETRIES - 1:
                raise
            time.sleep(delay)
            delay *= 2


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, default=str)
        handle.flush()
        os.fsync(handle.fileno())
    _replace_with_retry(temporary, path)


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    _replace_with_retry(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    return loaded


def write_parquet_atomic(frame: pl.DataFrame, path: Path, *, zstd_level: int) -> int:
    """Write, read back the row count, then publish. Returns the file size in bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    frame.write_parquet(
        temporary, compression="zstd", compression_level=zstd_level, statistics=True
    )
    written = pl.scan_parquet(temporary).select(pl.len()).collect().item()
    if written != frame.height:
        temporary.unlink(missing_ok=True)
        raise OSError(f"{path}: wrote {frame.height} rows but read back {written}")
    size = temporary.stat().st_size
    _replace_with_retry(temporary, path)
    return size


def publish_directory(temporary: Path, final: Path) -> None:
    final.parent.mkdir(parents=True, exist_ok=True)
    _replace_with_retry(temporary, final)


def remove_stale_temporaries(root: Path) -> int:
    """Delete leftovers of interrupted runs. Only names containing ``.tmp-`` match."""
    if not root.exists():
        return 0
    removed = 0
    for path in sorted(root.rglob("*.tmp-*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
        removed += 1
    return removed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()
