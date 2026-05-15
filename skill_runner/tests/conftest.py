"""Make `from runner.* import ...` resolve when pytest is invoked from
either the repo root or `skill_runner/`."""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_RUNNER_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_RUNNER_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_RUNNER_ROOT))
