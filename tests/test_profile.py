"""
Tests for profiling module.
"""
import pandas as pd
import pytest

from src.profile import (
    profile_schema,
    profile_duplicates,
    profile_stats,
    profile_distributions,
    profile_correlations,
    profile_target_summary,
    run_full_profile,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 3],
        "value": [10.0, 20.0, 30.0, 30.0],
        "cat": ["A", "B", "A", "A"],
    })


def test_profile_schema(sample_df):
    schema = profile_schema(sample_df)
    assert len(schema) == 3
    assert schema[0]["column"] == "id"
    assert schema[0]["unique_count"] == 3
    assert "dtype" in schema[0]


def test_profile_duplicates(sample_df):
    dup = profile_duplicates(sample_df)
    assert dup["total_rows"] == 4
    assert dup["unique_rows"] == 3
    assert dup["duplicate_count"] == 1


def test_profile_stats(sample_df):
    stats = profile_stats(sample_df)
    assert "missing_count" in stats
    assert "missing_pct" in stats
    assert stats["missing_count"]["id"] == 0


def test_profile_correlations(sample_df):
    corr = profile_correlations(sample_df)
    assert corr is not None
    assert "id" in corr
    assert "value" in corr


def test_profile_distributions_numeric_no_raw_values(sample_df):
    dist = profile_distributions(sample_df)
    meta = dist["numeric"]["value"]
    assert "values" not in meta
    assert set(meta.keys()) == {"hist_edges", "hist_counts", "hist_max"}


def test_profile_target_summary(sample_df):
    summary = profile_target_summary(sample_df, "cat")
    assert summary is not None
    assert summary["column"] == "cat"
    assert summary["n_classes"] == 2
    assert "distribution" in summary


def test_run_full_profile(sample_df):
    out = run_full_profile(sample_df)
    assert "overview" in out
    assert "schema" in out
    assert "duplicate_summary" in out
    assert "quick_notes" in out
    assert "target_summary" in out
    assert out["overview"]["row_count"] == 4
    assert out["duplicate_summary"]["duplicate_count"] == 1
    assert out["target_summary"] is None


def test_run_full_profile_with_target(sample_df):
    out = run_full_profile(sample_df, target_column="cat")
    assert out["target_summary"] is not None
    assert out["target_summary"]["column"] == "cat"
    assert "distribution" in out["target_summary"]
    assert out["target_summary"]["n_classes"] == 2
