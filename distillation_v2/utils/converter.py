"""Convert DOCX output to PNG images for LLM visual judging.

Pipeline: .docx → .pdf (LibreOffice) → .png[] (pdf2image/poppler).
Saves PNGs alongside the source file for debugging inspection.
Returns empty list on any failure — callers fall back to text-only scoring.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

_log = logging.getLogger("distillation.v2.converter")

_SOFFICE = "soffice"
_DEFAULT_MAX_PAGES = 10
_DPI = 150


def docx_to_images(docx_path: Path, max_pages: int = _DEFAULT_MAX_PAGES) -> list[Path]:
    """Convert a .docx file to PNG images (one per page, max `max_pages`).

    Returns list of saved PNG paths. Empty list if conversion fails.
    """
    if not docx_path.is_file():
        _log.warning("converter: file not found: %s", docx_path)
        return []

    pdf_path = _convert_to_pdf(docx_path)
    if pdf_path is None:
        return []

    images = _pdf_to_images(pdf_path, max_pages)
    pdf_path.unlink(missing_ok=True)
    return images


def find_docx(output_dir: Path) -> Path | None:
    """Return the first .docx file found in output_dir (not a fixture copy)."""
    candidates = sorted(output_dir.glob("*.docx"))
    if not candidates:
        return None
    # Prefer files not named like input fixtures (heuristic: exclude 'fixture' in name)
    non_fixture = [p for p in candidates if "fixture" not in p.name.lower()]
    return non_fixture[0] if non_fixture else candidates[0]


# ── Internal ──────────────────────────────────────────────────────────────────


def _convert_to_pdf(docx_path: Path) -> Path | None:
    """Use LibreOffice to convert .docx → .pdf in the same directory."""
    try:
        result = subprocess.run(
            [
                _SOFFICE,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(docx_path.parent),
                str(docx_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            _log.warning(
                "soffice failed (rc=%d): %s", result.returncode, result.stderr[:300]
            )
            return None
        pdf_path = docx_path.parent / (docx_path.stem + ".pdf")
        if not pdf_path.is_file():
            _log.warning("soffice ran but PDF not found: %s", pdf_path)
            return None
        return pdf_path
    except FileNotFoundError:
        _log.warning(
            "LibreOffice (soffice) not found — install to enable visual judging"
        )
        return None
    except subprocess.TimeoutExpired:
        _log.warning("soffice timed out converting %s", docx_path)
        return None
    except Exception as e:  # noqa: BLE001
        _log.warning("soffice error: %s", e)
        return None


def _pdf_to_images(pdf_path: Path, max_pages: int) -> list[Path]:
    """Convert PDF pages to PNG files saved next to the PDF."""
    try:
        from pdf2image import convert_from_path

        pages = convert_from_path(
            str(pdf_path),
            dpi=_DPI,
            first_page=1,
            last_page=max_pages,
        )
        saved: list[Path] = []
        for i, page in enumerate(pages, 1):
            out = pdf_path.parent / f"page_{i:02d}.png"
            page.save(str(out), "PNG")
            saved.append(out)
        _log.debug("converter: %d page(s) → %s", len(saved), pdf_path.parent)
        return saved
    except Exception as e:  # noqa: BLE001
        _log.warning("pdf2image failed: %s", e)
        return []
