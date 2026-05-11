"""Logging utilities for distillation_v2."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("distillation")
_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    if name not in _loggers:
        _loggers[name] = logger.getChild(name)
    return _loggers[name]


def setup_logging(
    level: str = "info",
    eval_detail: bool = True,
    api_calls: bool = True,
    results_dir: str | Path | None = None,
    skill: str | None = None,
    stream: bool = True,
) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = []

    if stream:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(lvl)
        ch.setFormatter(
            logging.Formatter("%(asctime)s  %(name)-22s  %(levelname)-8s  %(message)s")
        )
        handlers.append(ch)

    _mod = sys.modules[__name__]
    if results_dir:
        base = Path(results_dir)
        if skill:
            base = base / skill
        base.mkdir(parents=True, exist_ok=True)
        _mod._eval_detail_path = (base / "eval_detail.jsonl") if eval_detail else None
        _mod._api_calls_path = (base / "api_calls.jsonl") if api_calls else None
        if _mod._eval_detail_path:
            _mod._eval_detail_path.touch(exist_ok=True)
        if _mod._api_calls_path:
            _mod._api_calls_path.touch(exist_ok=True)
    else:
        _mod._eval_detail_path = None
        _mod._api_calls_path = None

    logging.basicConfig(level=lvl, handlers=handlers, force=True)
    logger.setLevel(lvl)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    for lgr in _loggers.values():
        lgr.setLevel(lvl)


def get_eval_detail_path() -> Path | None:
    return getattr(sys.modules[__name__], "_eval_detail_path", None)


def get_api_calls_path() -> Path | None:
    return getattr(sys.modules[__name__], "_api_calls_path", None)


def _append_jsonl(path: Path, record: dict[str, Any], kind: str) -> None:
    try:
        with path.open("a", buffering=1) as f:
            f.write(json.dumps(record, default=str) + "\n")
    except (OSError, TypeError, ValueError) as e:
        logger.warning("%s write failed (%s): %s", kind, path, e)


def write_eval_detail(record: dict[str, Any]) -> None:
    path = get_eval_detail_path()
    if path is None:
        return
    _append_jsonl(path, record, "eval_detail")


def write_api_call(record: dict[str, Any]) -> None:
    path = get_api_calls_path()
    if path is None:
        return
    _append_jsonl(path, record, "api_call")
