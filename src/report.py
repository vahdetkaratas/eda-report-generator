"""
HTML report generation (Jinja2). Optional PDF via WeasyPrint.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.config import PROFILE_CORR_STRONG_ABS


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"


def _report_context(profile_data: dict[str, Any], source_name: str | None) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return {
        **profile_data,
        "generated_at": generated_at,
        "source_name": source_name or "—",
        "corr_strong_abs": PROFILE_CORR_STRONG_ABS,
    }


def _render_html(profile_data: dict[str, Any], source_name: str | None = None) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("report.html")
    return template.render(**_report_context(profile_data, source_name))


def get_report_html(profile_data: dict[str, Any], source_name: str | None = None) -> str:
    """Build report HTML in memory (for download / session use)."""
    return _render_html(profile_data, source_name)


def get_report_pdf_result(
    profile_data: dict[str, Any], source_name: str | None = None
) -> tuple[bytes | None, str | None]:
    """
    Build report PDF in memory.
    On success: (pdf_bytes, None).
    On failure: (None, reason) with reason 'missing_weasyprint' or 'render_failed'.
    """
    try:
        from weasyprint import HTML as WeasyHTML
    except ImportError:
        return None, "missing_weasyprint"
    except OSError:
        # WeasyPrint is installed but native deps (Pango, GLib/gobject, etc.) are missing
        return None, "render_failed"
    try:
        html = _render_html(profile_data, source_name)
        return WeasyHTML(string=html).write_pdf(), None
    except Exception:
        return None, "render_failed"


def get_report_pdf_bytes(profile_data: dict[str, Any], source_name: str | None = None) -> bytes | None:
    """Build report PDF in memory. Returns None if WeasyPrint is missing or rendering fails."""
    pdf, _err = get_report_pdf_result(profile_data, source_name)
    return pdf


def render_report(
    profile_data: dict[str, Any],
    output_path: Path,
    source_name: str | None = None,
) -> Path:
    """
    Write HTML report to a given path (e.g. tests or explicit export).
    Does not use a shared default path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = _render_html(profile_data, source_name)
    output_path.write_text(html, encoding="utf-8")
    return output_path
