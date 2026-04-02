"""Base classes for rule-based evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class CheckResult:
    name: str
    passed: bool        # True/False
    score: float        # 0.0 or 1.0 (binary for rule-based)
    reason: str = ""    # short explanation, shown in summary/key_notes


@dataclass
class EvalResult:
    test_case_id: str
    skill: str
    model: str
    round_n: int
    output_dir: str

    checks: list[CheckResult] = field(default_factory=list)

    # Computed after all checks run
    rule_score: float = 0.0        # weighted average of rule checks (0.0 – 1.0)
    llm_judge_score: float = -1.0  # -1 = not run yet
    llm_judge_reasoning: str = ""
    human_eval_score: float = -1.0 # -1 = not run yet

    # Hybrid weights — override per evaluator:
    #   Tier 1-2 (docx, xlsx, slack-gif, webapp):  rule=0.50, llm=0.50, human=0.00
    #   Tier 3   (frontend-design, algorithmic-art): rule=0.00, llm=0.30, human=0.70
    _rule_weight: float = 0.50
    _llm_weight: float = 0.50
    _human_weight: float = 0.00

    @property
    def hybrid_score(self) -> float:
        """Weighted hybrid score.
        If llm_judge not run (-1), falls back to rule_score for the llm portion.
        If human_eval not run (-1), the human weight is redistributed to rule+llm.
        """
        llm = self.llm_judge_score if self.llm_judge_score >= 0 else self.rule_score
        if self.human_eval_score >= 0:
            return (
                self._rule_weight * self.rule_score
                + self._llm_weight * llm
                + self._human_weight * self.human_eval_score
            )
        else:
            # Redistribute human weight proportionally to rule + llm
            total = self._rule_weight + self._llm_weight
            if total == 0:
                return self.rule_score
            r = self._rule_weight / total
            l = self._llm_weight / total
            return r * self.rule_score + l * llm

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def summary_line(self) -> str:
        status = "PASS" if self.hybrid_score >= 0.6 else "FAIL"
        fails = ", ".join(c.name for c in self.failed_checks) or "none"
        llm_str = f"{self.llm_judge_score:.2f}" if self.llm_judge_score >= 0 else "n/a"
        return (
            f"[{status}] tc={self.test_case_id} "
            f"rule={self.rule_score:.2f} llm={llm_str} hybrid={self.hybrid_score:.2f} "
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
            EvalResult with all checks populated and rule_score computed.
        """
        ...
