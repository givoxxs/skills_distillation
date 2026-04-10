"""Logging utilities for the distillation pipeline.

Provides:
  - setup_logging(): configure Python logging from config dict
  - JsonlWriter: context manager for appending JSON lines to .jsonl files
  - module-level logger used by all distillation submodules
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any


# Module-level logger — imported by all distillation submodules
logger = logging.getLogger("distillation")
# Proxy logger names so submodules can `logger = logging.getLogger("distillation.xxx")`
_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Return a named child of the distillation logger."""
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
    """Configure the distillation logger from config values.

    Args:
        level:       Logging level — debug | info | warning
        eval_detail:  Enable eval_detail.jsonl writer
        api_calls:    Enable api_calls.jsonl writer
        results_dir:  Root results directory (default: cwd).
                      If skill is also provided, log files go to {results_dir}/{skill}/.
        skill:       Skill name — if set, log files land inside results_dir/skill/.
        stream:       Also print to stderr (default True)
    """
    lvl = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = []

    if stream:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(lvl)
        ch.setFormatter(
            logging.Formatter("%(asctime)s  %(name)-22s  %(levelname)-8s  %(message)s")
        )
        handlers.append(ch)

    if results_dir:
        base = Path(results_dir)
        if skill:
            base = base / skill
        base.mkdir(parents=True, exist_ok=True)

        if eval_detail:
            _eval_detail_path = base / "eval_detail.jsonl"
            _eval_detail_path.touch(exist_ok=True)
        else:
            _eval_detail_path = None

        if api_calls:
            _api_calls_path = base / "api_calls.jsonl"
            _api_calls_path.touch(exist_ok=True)
        else:
            _api_calls_path = None
    else:
        _eval_detail_path = None
        _api_calls_path = None

    logging.basicConfig(level=lvl, handlers=handlers, force=True)
    logger.setLevel(lvl)

    # Propagate to child loggers already created
    for lgr in _loggers.values():
        lgr.setLevel(lvl)


def get_eval_detail_path() -> Path | None:
    return getattr(sys.modules[__name__], "_eval_detail_path", None)


def get_api_calls_path() -> Path | None:
    return getattr(sys.modules[__name__], "_api_calls_path", None)


def write_eval_detail(record: dict[str, Any]) -> None:
    """Append one EvalResult dict as a JSON line to eval_detail.jsonl."""
    path = get_eval_detail_path()
    if path is None:
        return
    try:
        with path.open("a", buffering=1) as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        pass


def write_api_call(record: dict[str, Any]) -> None:
    """Append one API call record as a JSON line to api_calls.jsonl."""
    path = get_api_calls_path()
    if path is None:
        return
    try:
        with path.open("a", buffering=1) as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        pass
