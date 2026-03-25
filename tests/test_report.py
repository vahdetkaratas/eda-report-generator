"""
Report module tests: render_report produces HTML with required sections.
"""
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.profile import run_full_profile
from src.report import render_report


@pytest.fixture
def sample_profile_data():
    """Profile data without target_summary."""
    df = pd.DataFrame({
        "a": [1, 2, 3],
        "b": [4.0, 5.0, 6.0],
        "c": ["x", "y", "z"],
    })
    return run_full_profile(df)


@pytest.fixture
def profile_data_with_target():
    """Profile data with target_summary."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "label": ["A", "B", "A"],
    })
    return run_full_profile(df, target_column="label")


def test_render_report_creates_html(sample_profile_data):
    """render_report creates an HTML file and returns its path."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        result = render_report(sample_profile_data, output_path=out)
        assert result == out
        assert result.exists()
        html = result.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html or "<html" in html


def test_render_report_contains_sections(sample_profile_data):
    """Generated HTML contains Overview, Schema, Missing, Quick notes sections."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        render_report(sample_profile_data, output_path=out)
        html = out.read_text(encoding="utf-8")
        assert "Overview" in html
        assert "Schema" in html or "Column types" in html
        assert "Missing" in html
        assert "Quick Notes" in html or "Quick notes" in html
        assert str(sample_profile_data["overview"]["row_count"]) in html


def test_render_report_with_target_summary(profile_data_with_target):
    """When target_summary is set, report includes Target Summary section."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        render_report(profile_data_with_target, output_path=out)
        html = out.read_text(encoding="utf-8")
        assert "Target Summary" in html
        assert profile_data_with_target["target_summary"] is not None
        assert profile_data_with_target["target_summary"]["column"] == "label"


def test_render_report_without_target_summary(sample_profile_data):
    """When target_summary is None, render runs without error."""
    assert sample_profile_data.get("target_summary") is None
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        render_report(sample_profile_data, output_path=out)
        html = out.read_text(encoding="utf-8")
        assert "Correlations" in html


def test_render_report_includes_metadata_and_sample_rows(sample_profile_data):
    """Report includes source_name, generated_at, and Sample rows section."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        render_report(sample_profile_data, output_path=out, source_name="test.csv")
        html = out.read_text(encoding="utf-8")
        assert "Source:" in html and "test.csv" in html
        assert "Generated:" in html
        assert "Sample rows" in html
        assert "sample_rows" in sample_profile_data


def test_render_report_includes_sampling_note_when_sampled(sample_profile_data):
    """When sampled_from/sampled_n are set, report shows sampling warning."""
    sample_profile_data["sampled_from"] = 600_000
    sample_profile_data["sampled_n"] = 50_000
    sample_profile_data["sampled_strategy"] = "first"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        render_report(sample_profile_data, output_path=out)
        html = out.read_text(encoding="utf-8")
        assert "sample from" in html and "total" in html
        assert "600000" in html or "600,000" in html
        assert "50000" in html or "50,000" in html
