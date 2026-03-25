"""
Profiling engine: schema, stats, missing, duplicates, distributions, correlations.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from src.config import (
    PROFILE_CORR_STRONG_ABS,
    PROFILE_HIGH_CARD_UNIQUE_RATIO,
    PROFILE_MISSING_WARNING_PCT,
    PROFILE_NEAR_CONSTANT_PCT,
    PROFILE_OUTLIER_MIN_ABS,
    PROFILE_OUTLIER_MIN_FRAC,
    PROFILE_SKEW_STDDEV_MULT,
)


# --- Heuristic thresholds (not yet env-backed) ---

_ID_LIKE_UNIQUE_RATIO = 0.90
_DT_PROBE_SAMPLE = 5000
_DT_PARSE_OK_RATIO = 0.85
_DT_MAX_ROWS_FULL_PARSE = 100_000
_MISSING_CRITICAL_PCT = 50.0


# --- Schema & unique count ---

def profile_schema(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Column types and per-column unique value count.
    Report: Schema / Column types table.
    """
    return [
        {
            "column": col,
            "dtype": str(df[col].dtype),
            "unique_count": int(df[col].nunique()),
        }
        for col in df.columns
    ]


# --- Duplicates (reporting only) ---

def profile_duplicates(df: pd.DataFrame) -> dict[str, int]:
    """
    Duplicate row summary. Data is not modified.
    Returns: total_rows, unique_rows, duplicate_count
    """
    total = len(df)
    unique_rows = df.drop_duplicates()
    unique_count = len(unique_rows)
    duplicate_count = total - unique_count
    return {
        "total_rows": total,
        "unique_rows": unique_count,
        "duplicate_count": duplicate_count,
    }


# --- Stats & missing ---

def profile_stats(df: pd.DataFrame) -> dict[str, Any]:
    """
    Per-column missing count and percentage.
    """
    stats: dict[str, Any] = {}
    missing = df.isna().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    stats["missing_count"] = missing.to_dict()
    stats["missing_pct"] = missing_pct.to_dict()
    return stats


# --- Distributions ---

def _histogram_bins(series: "pd.Series", n_bins: int = 12) -> tuple[list[float], list[int]]:
    """Return (bin_edges, counts) for a numeric series. bin_edges has length n_bins+1."""
    s = series.dropna()
    if len(s) < 2:
        return [], []
    lo, hi = float(s.min()), float(s.max())
    if lo == hi:
        return [lo, hi], [len(s)]
    edges = [lo + (hi - lo) * i / n_bins for i in range(n_bins + 1)]
    counts = [0] * n_bins
    for v in s:
        idx = min(int((v - lo) / (hi - lo) * n_bins) if v < hi else n_bins - 1, n_bins - 1)
        counts[max(0, idx)] += 1
    return edges, counts


_CAT_TOP_K = 20


def profile_distributions(df: pd.DataFrame) -> dict[str, Any]:
    """
    Numeric: values + histogram bins for SVG; Categorical: top-k counts + coverage.
    """
    result: dict[str, Any] = {"numeric": {}, "categorical": {}}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            edges, counts = _histogram_bins(df[col], n_bins=12)
            result["numeric"][col] = {
                "hist_edges": edges,
                "hist_counts": counts,
                "hist_max": max(counts) if counts else 1,
            }
        else:
            s = df[col]
            vc = s.value_counts(dropna=True)
            top = vc.head(_CAT_TOP_K)
            counts = top.to_dict()
            sum_top = int(top.sum()) if len(top) else 0
            n_nonnull = int(s.notna().sum())
            n_rows = len(df)
            tail = max(0, n_nonnull - sum_top)
            if n_rows > 0:
                top_k_coverage_pct = round(100.0 * sum_top / n_rows, 1)
                other_pct = round(100.0 * tail / n_rows, 1)
            else:
                top_k_coverage_pct = 0.0
                other_pct = 0.0
            result["categorical"][col] = {
                "counts": counts,
                "top_k_coverage_pct": top_k_coverage_pct,
                "other_pct": other_pct,
                "k": _CAT_TOP_K,
            }
    return result


# --- Correlations ---

def profile_correlations(df: pd.DataFrame) -> dict[str, Any] | None:
    """
    Correlation matrix for numeric columns only.
    """
    numeric = df.select_dtypes(include=["number"])
    if numeric.empty or len(numeric.columns) < 2:
        return None
    corr = numeric.corr()
    return corr.round(4).to_dict()


# --- Column intelligence ---

def _column_name_id_like(name: str) -> bool:
    n = name.lower().strip()
    if n == "id":
        return True
    if re.search(r"_id$", n):
        return True
    if re.match(r"^id_", n):
        return True
    return False


def _column_name_suggests_datetime(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in ("date", "time", "day", "month", "year", "timestamp"))


def profile_column_intelligence(df: pd.DataFrame) -> dict[str, Any]:
    """
    Conservative flags: constant, near-constant, high-cardinality, id-like.
    """
    nrows = len(df)
    constant: list[str] = []
    near_constant: list[dict[str, Any]] = []
    high_cardinality: list[dict[str, Any]] = []
    id_like: list[str] = []

    for col in df.columns:
        s = df[col]
        nu = int(s.nunique(dropna=True))
        if nu <= 1:
            constant.append(col)
            continue

        non_null = s.notna().sum()
        if non_null > 0:
            vc = s.value_counts(dropna=True)
            top_share = float(vc.iloc[0] / non_null * 100) if len(vc) else 0.0
            if top_share >= PROFILE_NEAR_CONSTANT_PCT:
                near_constant.append({"column": col, "top_value_share_pct": round(top_share, 1)})

        ratio_vs_rows = nu / nrows if nrows else 0.0
        if ratio_vs_rows >= PROFILE_HIGH_CARD_UNIQUE_RATIO and col not in constant:
            high_cardinality.append(
                {"column": col, "unique_ratio": round(ratio_vs_rows, 4), "unique_count": nu}
            )

        if _column_name_id_like(col) and (nu / nrows if nrows else 0) >= _ID_LIKE_UNIQUE_RATIO:
            id_like.append(col)

    return {
        "constant": constant,
        "near_constant": near_constant,
        "high_cardinality": high_cardinality,
        "id_like": id_like,
    }


# --- Datetime profile ---

def profile_datetime_profile(df: pd.DataFrame) -> dict[str, Any]:
    """
    Datetime-like columns only. Conservative: skip object parsing when len(df) > _DT_MAX_ROWS_FULL_PARSE.
    """
    out: dict[str, Any] = {}
    n = len(df)

    for col in df.columns:
        s = df[col]

        if pd.api.types.is_datetime64_any_dtype(s):
            ts = pd.to_datetime(s, errors="coerce")
            valid = ts.notna()
            if not valid.any():
                continue
            out[col] = {
                "parseable": True,
                "min": ts[valid].min().isoformat()[:10],
                "max": ts[valid].max().isoformat()[:10],
                "null_pct": round(float((~valid).mean() * 100), 2),
                "row_count": n,
            }
            continue

        if n > _DT_MAX_ROWS_FULL_PARSE:
            continue

        if pd.api.types.is_numeric_dtype(s):
            if not _column_name_suggests_datetime(col):
                continue

        if not (
            s.dtype == object
            or pd.api.types.is_string_dtype(s)
            or isinstance(s.dtype, pd.CategoricalDtype)
        ):
            if not pd.api.types.is_numeric_dtype(s):
                continue

        non_null = s.dropna()
        if len(non_null) == 0:
            continue

        if (
            s.dtype == object or isinstance(s.dtype, pd.CategoricalDtype)
        ) and not _column_name_suggests_datetime(col):
            continue

        sample = non_null.sample(min(_DT_PROBE_SAMPLE, len(non_null)), random_state=42)
        if pd.api.types.is_numeric_dtype(s):
            parsed_probe = pd.to_datetime(sample, errors="coerce")
        else:
            parsed_probe = pd.to_datetime(sample.astype(str), errors="coerce")

        if parsed_probe.notna().mean() < _DT_PARSE_OK_RATIO:
            continue

        full_parsed = pd.to_datetime(df[col], errors="coerce")
        valid = full_parsed.notna()
        if not valid.any():
            continue
        out[col] = {
            "parseable": True,
            "min": full_parsed[valid].min().isoformat()[:10],
            "max": full_parsed[valid].max().isoformat()[:10],
            "null_pct": round(float((~valid).mean() * 100), 2),
            "row_count": n,
        }

    return out


# --- Structured warnings ---

def _sort_warnings(warns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank = {"critical": 0, "warning": 1, "info": 2}
    return sorted(
        warns,
        key=lambda w: (rank.get(w.get("level", "info"), 9), w.get("column") or "", w["message"]),
    )


def build_warnings(
    df: pd.DataFrame,
    dup: dict[str, int],
    stats: dict[str, Any],
    corr: dict[str, Any],
    column_intelligence: dict[str, Any],
    datetime_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    warns: list[dict[str, Any]] = []

    if dup["duplicate_count"] > 0:
        warns.append(
            {
                "level": "warning",
                "message": f"{dup['duplicate_count']} fully duplicate row(s) detected.",
                "column": None,
                "code": "DUPLICATE_ROWS",
            }
        )

    missing_pct = stats.get("missing_pct", {})
    for col, pct in missing_pct.items():
        if pct > _MISSING_CRITICAL_PCT:
            warns.append(
                {
                    "level": "critical",
                    "message": f"Column '{col}' has {pct:.1f}% missing.",
                    "column": col,
                    "code": "MISSING_CRITICAL",
                }
            )
        elif pct > PROFILE_MISSING_WARNING_PCT:
            warns.append(
                {
                    "level": "warning",
                    "message": f"Column '{col}' has {pct:.1f}% missing — note.",
                    "column": col,
                    "code": "MISSING_HIGH",
                }
            )

    if not corr and len(df.select_dtypes(include=["number"]).columns) < 2:
        warns.append(
            {
                "level": "info",
                "message": "No correlation matrix (need at least 2 numeric columns).",
                "column": None,
                "code": "NO_CORR_MATRIX",
            }
        )

    if corr:
        for col_a, row in corr.items():
            for col_b, r in row.items():
                if col_a >= col_b:
                    continue
                if abs(r) > PROFILE_CORR_STRONG_ABS:
                    warns.append(
                        {
                            "level": "warning",
                            "message": (
                                f"Strong correlation between '{col_a}' and '{col_b}' "
                                f"(r≈{r:.2f}) — multicollinearity risk."
                            ),
                            "column": None,
                            "code": "CORR_STRONG",
                        }
                    )

    numeric = df.select_dtypes(include=["number"])
    for col in numeric.columns:
        s = df[col].dropna()
        if len(s) < 4:
            continue
        mean, median = s.mean(), s.median()
        std = s.std()
        if std and abs(mean - median) > PROFILE_SKEW_STDDEV_MULT * std:
            warns.append(
                {
                    "level": "info",
                    "message": f"Column '{col}' has skewed distribution (mean ≠ median).",
                    "column": col,
                    "code": "SKEW",
                }
            )
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((s < lower) | (s > upper)).sum())
        if n_out > 0 and (
            n_out >= max(PROFILE_OUTLIER_MIN_ABS, len(s) * PROFILE_OUTLIER_MIN_FRAC)
        ):
            warns.append(
                {
                    "level": "warning",
                    "message": f"Column '{col}' has {n_out} potential outlier(s) (IQR method).",
                    "column": col,
                    "code": "OUTLIERS_IQR",
                }
            )

    const_cols = column_intelligence.get("constant") or []
    if const_cols:
        shown = const_cols[:5]
        extra = len(const_cols) - len(shown)
        tail = f" (+{extra} more)" if extra > 0 else ""
        warns.append(
            {
                "level": "info",
                "message": f"Constant columns (≤1 distinct non-null value): {', '.join(shown)}{tail}.",
                "column": None,
                "code": "CONSTANT_COLUMNS",
            }
        )

    near = column_intelligence.get("near_constant") or []
    if near:
        names = ", ".join(x["column"] for x in near[:5])
        extra = len(near) - min(5, len(near))
        tail = f" (+{extra} more)" if extra > 0 else ""
        warns.append(
            {
                "level": "warning",
                "message": f"Near-constant columns (≥{PROFILE_NEAR_CONSTANT_PCT:.0f}% one value): {names}{tail}.",
                "column": None,
                "code": "NEAR_CONSTANT",
            }
        )

    hc = column_intelligence.get("high_cardinality") or []
    if hc:
        names = ", ".join(x["column"] for x in hc[:5])
        extra = len(hc) - min(5, len(hc))
        tail = f" (+{extra} more)" if extra > 0 else ""
        warns.append(
            {
                "level": "info",
                "message": (
                    f"High-cardinality columns (≥{PROFILE_HIGH_CARD_UNIQUE_RATIO:.0%} unique/ratio): "
                    f"{names}{tail}."
                ),
                "column": None,
                "code": "HIGH_CARDINALITY",
            }
        )

    idl = column_intelligence.get("id_like") or []
    if idl:
        warns.append(
            {
                "level": "info",
                "message": f"ID-like columns (name + ≥{_ID_LIKE_UNIQUE_RATIO:.0%} unique): {', '.join(idl)}.",
                "column": None,
                "code": "ID_LIKE",
            }
        )

    if datetime_profile:
        names = ", ".join(list(datetime_profile.keys())[:8])
        extra = len(datetime_profile) - min(8, len(datetime_profile))
        tail = f" (+{extra} more)" if extra > 0 else ""
        warns.append(
            {
                "level": "info",
                "message": f"Datetime-like columns detected: {names}{tail}.",
                "column": None,
                "code": "DATETIME_DETECTED",
            }
        )

    return warns


def warnings_to_quick_notes(warnings: list[dict[str, Any]]) -> list[str]:
    """Flat messages in stable order: critical → warning → info."""
    return [w["message"] for w in _sort_warnings(warnings)]


def build_data_quality(
    df: pd.DataFrame,
    dup: dict[str, int],
    stats: dict[str, Any],
    column_intelligence: dict[str, Any],
    datetime_profile: dict[str, Any],
) -> dict[str, Any]:
    missing_pct = stats.get("missing_pct", {})
    high_missing = sum(1 for p in missing_pct.values() if p > PROFILE_MISSING_WARNING_PCT)
    return {
        "headline": (
            f"{dup['duplicate_count']} duplicate row(s); "
            f"{high_missing} column(s) with >{PROFILE_MISSING_WARNING_PCT:.0f}% missing."
        ),
        "high_missing_column_count": high_missing,
        "duplicate_row_count": dup["duplicate_count"],
        "constant_column_count": len(column_intelligence.get("constant") or []),
        "near_constant_column_count": len(column_intelligence.get("near_constant") or []),
        "high_cardinality_column_count": len(column_intelligence.get("high_cardinality") or []),
        "id_like_column_count": len(column_intelligence.get("id_like") or []),
        "datetime_column_count": len(datetime_profile),
    }


def build_executive_summary(
    overview: dict[str, Any],
    data_quality: dict[str, Any],
    warnings: list[dict[str, Any]],
    dup: dict[str, int],
) -> list[str]:
    bullets: list[str] = []
    bullets.append(
        f"Dataset: {overview['row_count']:,} rows × {overview['column_count']} columns "
        f"(~{overview['memory_mb']} MB in memory)."
    )
    bullets.append(data_quality["headline"])

    if dup["duplicate_count"] > 0:
        bullets.append(f"{dup['duplicate_count']} fully duplicate row(s) — review before modeling.")

    crit = [w for w in warnings if w.get("level") == "critical"]
    if crit:
        bullets.append(crit[0]["message"])
    elif any(w.get("level") == "warning" for w in warnings):
        wn = next(w for w in _sort_warnings(warnings) if w.get("level") == "warning")
        bullets.append(wn["message"])

    if data_quality["datetime_column_count"] > 0:
        bullets.append(
            f"{data_quality['datetime_column_count']} datetime-like column(s) identified for time-based checks."
        )

    return bullets[:5]


# --- Target summary (optional; for ML) ---

def profile_target_summary(df: pd.DataFrame, target_column: str) -> dict[str, Any] | None:
    """
    When target column is set: distribution, missing %, class balance if categorical.
    """
    if target_column not in df.columns:
        return None
    col = df[target_column]
    missing = col.isna().sum()
    missing_pct = round(missing / len(df) * 100, 2)
    dist = col.value_counts()
    summary: dict[str, Any] = {
        "column": target_column,
        "dtype": str(col.dtype),
        "missing_count": int(missing),
        "missing_pct": missing_pct,
        "distribution": dist.head(30).to_dict(),
    }
    if not pd.api.types.is_numeric_dtype(col):
        n_classes = dist.shape[0]
        max_pct = (dist.iloc[0] / len(df) * 100) if len(dist) else 0
        summary["n_classes"] = n_classes
        summary["max_class_pct"] = round(max_pct, 1)
        summary["balanced"] = max_pct < 70
    return summary


# --- Full profile in one call ---

def run_full_profile(df: pd.DataFrame, target_column: str | None = None) -> dict[str, Any]:
    """
    Run all profiling steps; returns report payload.
    target_column: optional; adds target summary for ML use.
    """
    schema = profile_schema(df)
    dup = profile_duplicates(df)
    stats = profile_stats(df)
    dist = profile_distributions(df)
    corr = profile_correlations(df)
    corr_dict = corr if corr is not None else {}

    column_intelligence = profile_column_intelligence(df)
    datetime_profile = profile_datetime_profile(df)
    warnings = build_warnings(df, dup, stats, corr_dict, column_intelligence, datetime_profile)
    quick_notes = warnings_to_quick_notes(warnings)

    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    overview = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "memory_mb": round(float(memory_mb), 2),
    }

    data_quality = build_data_quality(df, dup, stats, column_intelligence, datetime_profile)
    executive_summary = build_executive_summary(overview, data_quality, warnings, dup)

    raw_sample = df.head(5).to_dict(orient="records")
    sample_rows = [
        {k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in row.items()}
        for row in raw_sample
    ]

    result: dict[str, Any] = {
        "overview": overview,
        "schema": schema,
        "duplicate_summary": dup,
        "stats": stats,
        "distributions": dist,
        "correlations": corr_dict,
        "quick_notes": quick_notes,
        "warnings": _sort_warnings(warnings),
        "column_intelligence": column_intelligence,
        "datetime_profile": datetime_profile,
        "data_quality": data_quality,
        "executive_summary": executive_summary,
        "sample_rows": sample_rows,
    }
    if target_column and target_column in df.columns:
        result["target_summary"] = profile_target_summary(df, target_column)
    else:
        result["target_summary"] = None
    return result
