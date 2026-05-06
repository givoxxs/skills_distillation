"""Base classes for LLM-only evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

PASS_THRESHOLD = 0.8


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float  # 0.0–1.0
    reason: str = ""


@dataclass
class EvalResult:
    test_case_id: str
    skill: str
    model: str
    round_n: int
    output_dir: str

    checks: list[CheckResult] = field(default_factory=list)

    llm_judge_score: float = -1.0  # -1 = not run yet
    llm_judge_reasoning: str = ""

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def summary_line(self) -> str:
        score = self.llm_judge_score if self.llm_judge_score >= 0 else 0.0
        status = "PASS" if score >= PASS_THRESHOLD else "FAIL"
        fails = ", ".join(c.name for c in self.failed_checks) or "none"
        llm_str = f"{self.llm_judge_score:.2f}" if self.llm_judge_score >= 0 else "n/a"
        return (
            f"[{status}] tc={self.test_case_id} "
            f"llm={llm_str} "
            f"failed_checks=[{fails}]"
        )


class BaseEvaluator(Protocol):
    """Interface all skill evaluators must implement."""

    def score(
        self,
        output_dir: str,
        test_case: dict,
        model: str,
        round_n: int,
    ) -> EvalResult:
        """Score one test case run.

        Args:
            output_dir: Path where skill_runner copied output files.
            test_case:  Dict with keys: id, name, prompt, expected_behavior.
            model:      Model ID used for this run.
            round_n:    Distillation round number (0 = baseline).

        Returns:
            EvalResult with all checks populated and llm_judge_score computed.
        """
        ...
