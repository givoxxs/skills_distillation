"""Runtime configuration — paths + which skills we expose."""

from __future__ import annotations

import os
from pathlib import Path

# Root of the upstream pipeline repo. Override with $DISTILL_REPO_ROOT.
DISTILL_REPO_ROOT = Path(
    os.getenv("DISTILL_REPO_ROOT", "/Users/soc_036/study_dir/skill_distillation")
)

STABLE_DIR = DISTILL_REPO_ROOT / "distillation_v2" / "results" / "stable"
TEST_CASES_DIR = DISTILL_REPO_ROOT / "distillation_v2" / "test_cases"

# Skills we ship in the demo. Filesystem state is the source of truth, but we
# keep this allowlist to (a) reject random folder names and (b) preserve the
# canonical display order on /.
KNOWN_SKILLS = ["docx", "internal-comms", "slack-gif-creator"]
