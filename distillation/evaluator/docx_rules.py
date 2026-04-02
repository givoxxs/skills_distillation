"""Rule-based evaluator for the docx skill.

Philosophy: rule-based checks ONLY cover format correctness. Content adequacy
is entirely the LLM Judge's job.

Scoring:
  Group 1 — File validity   (weight 0.50): file_exists, file_parseable, file_not_empty
  Group 2 — Format sanity   (weight 0.50): no_placeholders + structural_checks +
                                            auto_eval checks (XML inspection)

structural_checks fields (all optional, default false/null):
  heading_levels   : list[int]   — heading levels that must be present, e.g. [1, 2]
  has_table        : bool        — at least one table
  has_toc          : bool        — Table of Contents present
  has_header_footer: bool        — at least one section with non-empty header or footer
  has_list         : bool        — at least one bulleted or numbered list
  min_pages        : int | null  — minimum estimated page count
  max_pages        : int | null  — maximum estimated page count
  expected_filename: str | null  — output file must match this name

auto_eval fields (all optional):
  xml_must_contain     : list[str]  — substrings that must appear in document.xml
  xml_must_not_contain : list[str]  — substrings that must NOT appear in document.xml
  footer_xml_must_contain: list[str] — substrings that must appear in any footer*.xml
  file_exists          : list[str]  — paths that must exist inside the .docx zip
  keywords_in_text     : list[str]  — words that must appear in extracted plain text
  validate_passes      : bool       — run scripts/office/validate.py, exit code 0
  (tool_used, workflow_steps, numbering_references_count — not auto-checkable, skipped)

Hybrid: rule 50% + llm_judge 50% (Tier 1-2)
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from evaluator.base import CheckResult, EvalResult
from evaluator.llm_judge import LLMJudge

# Path to validate.py — resolved relative to this file's skill scripts location
_VALIDATE_PY = (
    Path(__file__).parent.parent.parent
    / "skill_runner"
    / "skills"
    / "docx"
    / "scripts"
    / "office"
    / "validate.py"
)


class DocxEvaluator:
    """Hybrid evaluator for .docx output (rule-based format + LLM Judge content)."""

    skill = "docx"

    def __init__(
        self, judge_model: str = "claude-haiku-4-5", use_llm_judge: bool = True
    ) -> None:
        self.use_llm_judge = use_llm_judge
        self._judge = LLMJudge(model=judge_model) if use_llm_judge else None

    def score(
        self,
        output_dir: str,
        test_case: dict,
        model: str,
        round_n: int,
    ) -> EvalResult:
        result = EvalResult(
            test_case_id=test_case["id"],
            skill=self.skill,
            model=model,
            round_n=round_n,
            output_dir=output_dir,
        )

        out = Path(output_dir)
        sc = test_case.get("structural_checks") or {}
        ae = test_case.get("auto_eval") or {}

        # Locate output file
        expected_filename = sc.get("expected_filename") or ae.get("expected_filename")
        if expected_filename:
            docx_path = out / expected_filename
            if not docx_path.exists():
                docx_path = next(iter(out.rglob("*.docx")), None)
        else:
            docx_files = list(out.rglob("*.docx"))
            docx_path = docx_files[0] if docx_files else None

        doc = _try_load(docx_path)

        # ── Group 1: File validity (weight 0.50) ─────────────────────────────
        g1 = [
            self._check_file_exists(docx_path, expected_filename),
            self._check_file_parseable(docx_path, doc),
            self._check_file_not_empty(docx_path),
        ]

        # ── Group 2: Format sanity (weight 0.50) ─────────────────────────────
        g2 = [self._check_no_placeholders(doc)]

        # structural_checks
        for level in sc.get("heading_levels") or []:
            g2.append(self._check_has_heading_level(doc, level))
        if sc.get("has_table"):
            g2.append(self._check_has_table(doc))
        if sc.get("has_toc"):
            g2.append(self._check_has_toc(doc))
        if sc.get("has_header_footer"):
            g2.append(self._check_has_header_footer(doc))
        if sc.get("has_list"):
            g2.append(self._check_has_list(doc))
        if sc.get("min_pages") or sc.get("max_pages"):
            g2.append(
                self._check_page_count(doc, sc.get("min_pages"), sc.get("max_pages"))
            )

        # auto_eval checks
        if ae:
            g2 += self._run_auto_eval(docx_path, ae)

        result.checks = g1 + g2
        result.rule_score = 0.50 * _avg(g1) + 0.50 * _avg(g2)

        # Tier 1-2 weights: rule 40% + llm 60% (thesis spec)
        result._rule_weight = 0.40
        result._llm_weight = 0.60

        # ── LLM Judge (60% of hybrid score) ──────────────────────────────────
        if self._judge and result.rule_score > 0:
            llm_score, reasoning = self._judge.score(output_dir, test_case, self.skill)
            result.llm_judge_score = llm_score
            result.llm_judge_reasoning = reasoning

        return result

    # ── Group 1 ───────────────────────────────────────────────────────────────

    def _check_file_exists(
        self, path: Path | None, expected_filename: str | None
    ) -> CheckResult:
        ok = path is not None and path.exists()
        msg = ""
        if not ok:
            msg = (
                f"Expected '{expected_filename}' not found"
                if expected_filename
                else "No .docx file found in output_dir"
            )
        return CheckResult("file_exists", ok, 1.0 if ok else 0.0, msg)

    def _check_file_parseable(self, path: Path | None, doc) -> CheckResult:
        if path is None or not path.exists():
            return CheckResult("file_parseable", False, 0.0, "No file to parse")
        ok = doc is not None
        return CheckResult(
            "file_parseable",
            ok,
            1.0 if ok else 0.0,
            "" if ok else "python-docx raised an error — file may be corrupt",
        )

    def _check_file_not_empty(self, path: Path | None) -> CheckResult:
        if path is None or not path.exists():
            return CheckResult("file_not_empty", False, 0.0, "No file")
        size = path.stat().st_size
        ok = size > 1024
        return CheckResult(
            "file_not_empty",
            ok,
            1.0 if ok else 0.0,
            "" if ok else f"File only {size} bytes — likely empty or invalid",
        )

    # ── Group 2: structural checks ────────────────────────────────────────────

    def _check_no_placeholders(self, doc) -> CheckResult:
        if doc is None:
            return CheckResult("no_placeholders", False, 0.0, "Could not load document")
        text = " ".join(p.text for p in doc.paragraphs)
        pattern = re.compile(
            r"\[INSERT|\[YOUR |\[NAME\]|\[DATE\]|\{\{|TBD\b|TODO\b", re.I
        )
        match = pattern.search(text)
        ok = match is None
        return CheckResult(
            "no_placeholders",
            ok,
            1.0 if ok else 0.0,
            "" if ok else f"Unfilled placeholder: '{match.group()}'",
        )

    def _check_has_heading_level(self, doc, level: int) -> CheckResult:
        name = f"has_h{level}"
        if doc is None:
            return CheckResult(name, False, 0.0, "Could not load document")
        ok = any(
            p.style is not None and p.style.name == f"Heading {level}"
            for p in doc.paragraphs
        )
        return CheckResult(
            name,
            ok,
            1.0 if ok else 0.0,
            "" if ok else f"No 'Heading {level}' paragraph found",
        )

    def _check_has_table(self, doc) -> CheckResult:
        if doc is None:
            return CheckResult("has_table", False, 0.0, "Could not load document")
        ok = len(doc.tables) > 0
        return CheckResult(
            "has_table", ok, 1.0 if ok else 0.0, "" if ok else "No tables found"
        )

    def _check_has_toc(self, doc) -> CheckResult:
        if doc is None:
            return CheckResult("has_toc", False, 0.0, "Could not load document")
        body_xml = doc.element.body.xml
        ok = "TOC" in body_xml or any(
            p.style is not None and p.style.name.startswith("TOC")
            for p in doc.paragraphs
        )
        return CheckResult(
            "has_toc",
            ok,
            1.0 if ok else 0.0,
            "" if ok else "No table of contents found",
        )

    def _check_has_header_footer(self, doc) -> CheckResult:
        if doc is None:
            return CheckResult(
                "has_header_footer", False, 0.0, "Could not load document"
            )
        has = any(
            (section.header and any(p.text.strip() for p in section.header.paragraphs))
            or (
                section.footer
                and any(p.text.strip() for p in section.footer.paragraphs)
            )
            for section in doc.sections
        )
        return CheckResult(
            "has_header_footer",
            has,
            1.0 if has else 0.0,
            "" if has else "No header or footer with content found",
        )

    def _check_has_list(self, doc) -> CheckResult:
        if doc is None:
            return CheckResult("has_list", False, 0.0, "Could not load document")
        ok = any(
            (p.style is not None and p.style.name.startswith("List"))
            or (p._element.pPr is not None and p._element.pPr.numPr is not None)
            for p in doc.paragraphs
        )
        return CheckResult(
            "has_list", ok, 1.0 if ok else 0.0, "" if ok else "No list items found"
        )

    def _check_page_count(
        self, doc, min_pages: int | None, max_pages: int | None
    ) -> CheckResult:
        if doc is None:
            return CheckResult("page_count", False, 0.0, "Could not load document")
        count = doc.element.body.xml.count('w:type="page"') + 1
        ok = True
        msg = f"Estimated {count} page(s)"
        if min_pages and count < min_pages:
            ok = False
            msg = f"Estimated {count} page(s), expected >= {min_pages}"
        elif max_pages and count > max_pages:
            ok = False
            msg = f"Estimated {count} page(s), expected <= {max_pages}"
        return CheckResult("page_count", ok, 1.0 if ok else 0.0, "" if ok else msg)

    # ── Group 2: auto_eval checks ─────────────────────────────────────────────

    def _run_auto_eval(self, docx_path: Path | None, ae: dict) -> list[CheckResult]:
        checks: list[CheckResult] = []
        if docx_path is None or not docx_path.exists():
            return checks

        # Unzip once into temp dir for all XML checks
        tmp_dir = None
        need_xml = (
            ae.get("xml_must_contain")
            or ae.get("xml_must_not_contain")
            or ae.get("footer_xml_must_contain")
            or ae.get("file_exists")
        )
        if need_xml:
            tmp_dir = Path(tempfile.mkdtemp(prefix="docx_eval_"))
            try:
                with zipfile.ZipFile(docx_path, "r") as zf:
                    zf.extractall(tmp_dir)
            except Exception as e:
                checks.append(CheckResult("unzip", False, 0.0, f"Failed to unzip: {e}"))
                return checks

        try:
            # xml_must_contain — checked against xml_file (default: document.xml)
            if ae.get("xml_must_contain"):
                xml_filename = ae.get("xml_file", "word/document.xml")
                doc_xml = _read_file(tmp_dir / xml_filename)
                for needle in ae["xml_must_contain"]:
                    ok = needle in doc_xml
                    checks.append(
                        CheckResult(
                            f"xml_has:{needle[:40]}",
                            ok,
                            1.0 if ok else 0.0,
                            ""
                            if ok
                            else f"XML missing in {xml_filename}: {needle[:60]}",
                        )
                    )

            # xml_must_not_contain — checked against xml_file (default: document.xml)
            if ae.get("xml_must_not_contain"):
                xml_filename = ae.get("xml_file", "word/document.xml")
                doc_xml = _read_file(tmp_dir / xml_filename)
                for needle in ae["xml_must_not_contain"]:
                    ok = needle not in doc_xml
                    checks.append(
                        CheckResult(
                            f"xml_absent:{needle[:40]}",
                            ok,
                            1.0 if ok else 0.0,
                            ""
                            if ok
                            else f"XML must not contain in {xml_filename}: {needle[:60]}",
                        )
                    )

            # footer_xml_must_contain — checked against any word/footer*.xml
            if ae.get("footer_xml_must_contain") and tmp_dir:
                footer_xml = ""
                for fpath in tmp_dir.glob("word/footer*.xml"):
                    footer_xml += _read_file(fpath)
                for needle in ae["footer_xml_must_contain"]:
                    ok = needle in footer_xml
                    checks.append(
                        CheckResult(
                            f"footer_has:{needle[:40]}",
                            ok,
                            1.0 if ok else 0.0,
                            "" if ok else f"Footer XML missing: {needle[:60]}",
                        )
                    )

            # file_exists — paths inside the zip (e.g. "word/footnotes.xml")
            if ae.get("file_exists") and tmp_dir:
                for rel_path in ae["file_exists"]:
                    target = tmp_dir / rel_path.rstrip("/")
                    # allow directory prefix match (e.g. "word/media/")
                    if rel_path.endswith("/"):
                        dir_path = tmp_dir / rel_path.rstrip("/")
                        ok = dir_path.is_dir() and any(dir_path.iterdir())
                    else:
                        ok = target.exists()
                    checks.append(
                        CheckResult(
                            f"zip_has:{rel_path}",
                            ok,
                            1.0 if ok else 0.0,
                            "" if ok else f"Missing in docx zip: {rel_path}",
                        )
                    )

            # keywords_in_text — extracted from doc paragraphs
            if ae.get("keywords_in_text") or ae.get("keywords_in_output"):
                keywords = (
                    ae.get("keywords_in_text") or ae.get("keywords_in_output") or []
                )
                doc = _try_load(docx_path)
                text = ""
                if doc:
                    text = " ".join(p.text for p in doc.paragraphs).lower()
                for kw in keywords:
                    ok = kw.lower() in text
                    checks.append(
                        CheckResult(
                            f"kw:{kw[:30]}",
                            ok,
                            1.0 if ok else 0.0,
                            "" if ok else f"Keyword not found in document text: '{kw}'",
                        )
                    )

            # validate_passes — run scripts/office/validate.py
            if ae.get("validate_passes") and _VALIDATE_PY.exists():
                checks.append(self._check_validate(docx_path))

        finally:
            if tmp_dir:
                import shutil

                shutil.rmtree(tmp_dir, ignore_errors=True)

        return checks

    def _check_validate(self, docx_path: Path) -> CheckResult:
        try:
            proc = subprocess.run(
                [sys.executable, str(_VALIDATE_PY), str(docx_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(_VALIDATE_PY.parent),
            )
            ok = proc.returncode == 0
            msg = "" if ok else (proc.stdout + proc.stderr).strip()[:200]
            return CheckResult("validate_passes", ok, 1.0 if ok else 0.0, msg)
        except subprocess.TimeoutExpired:
            return CheckResult("validate_passes", False, 0.0, "validate.py timed out")
        except Exception as e:
            return CheckResult("validate_passes", False, 0.0, f"validate.py error: {e}")


# ── helpers ───────────────────────────────────────────────────────────────────


def _try_load(path: Path | None):
    if path is None or not path.exists():
        return None
    try:
        from docx import Document

        return Document(str(path))
    except Exception:
        return None


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _avg(checks: list[CheckResult]) -> float:
    if not checks:
        return 1.0
    return sum(c.score for c in checks) / len(checks)
