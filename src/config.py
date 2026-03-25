"""
App limits: file size, row cap, sampling.
Profiling thresholds (see PROFILE_* constants).
Read from environment when set: EDA_MAX_FILE_MB, EDA_MAX_ROWS, EDA_SAMPLE_SIZE, EDA_* profiling keys.
"""
import os


def _env_int(name: str, default: int) -> int:
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _env_int_bounded(name: str, default: int, *, low: int | None = None, high: int | None = None) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        v = int(float(raw))
    except ValueError:
        return default
    if low is not None and v < low:
        return default
    if high is not None and v > high:
        return default
    return v


def _env_float_bounded(
    name: str,
    default: float,
    *,
    low: float | None = None,
    high: float | None = None,
    low_inclusive: bool = True,
    high_inclusive: bool = True,
) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        v = float(raw)
    except ValueError:
        return default
    if low is not None:
        if low_inclusive and v < low:
            return default
        if not low_inclusive and v <= low:
            return default
    if high is not None:
        if high_inclusive and v > high:
            return default
        if not high_inclusive and v >= high:
            return default
    return v


# Max upload size (MB); env EDA_MAX_FILE_MB
_MAX_FILE_MB = _env_float("EDA_MAX_FILE_MB", 50.0)
MAX_FILE_SIZE_BYTES = int(_MAX_FILE_MB * 1024 * 1024)

# Above this row count we sample; env EDA_MAX_ROWS
MAX_ROWS = _env_int("EDA_MAX_ROWS", 500_000)

# Rows to keep when sampling; env EDA_SAMPLE_SIZE
SAMPLE_SIZE = _env_int("EDA_SAMPLE_SIZE", 50_000)

# --- Profiling thresholds (env-backed; invalid/out-of-range → defaults) ---

# Missing % above which a column gets a warning (not critical); env EDA_MISSING_PCT_NOTE
PROFILE_MISSING_WARNING_PCT = _env_float_bounded(
    "EDA_MISSING_PCT_NOTE", 20.0, low=0.0, high=100.0
)

# |r| above which pairwise correlation is flagged; env EDA_CORR_STRONG_ABS
PROFILE_CORR_STRONG_ABS = _env_float_bounded(
    "EDA_CORR_STRONG_ABS", 0.8, low=0.0, high=1.0
)

# Skew note when |mean − median| > this × std; env EDA_SKEW_STDDEV_MULT
PROFILE_SKEW_STDDEV_MULT = _env_float_bounded(
    "EDA_SKEW_STDDEV_MULT", 2.0, low=0.0, high=100.0, low_inclusive=False
)

# IQR outliers: minimum count to flag; env EDA_OUTLIER_MIN_ABS
PROFILE_OUTLIER_MIN_ABS = _env_int_bounded("EDA_OUTLIER_MIN_ABS", 3, low=0, high=10_000_000)

# IQR outliers: minimum fraction of non-null count; env EDA_OUTLIER_MIN_FRAC
PROFILE_OUTLIER_MIN_FRAC = _env_float_bounded(
    "EDA_OUTLIER_MIN_FRAC", 0.01, low=0.0, high=1.0
)

# Top-value share % for near-constant columns; env EDA_NEAR_CONSTANT_PCT
PROFILE_NEAR_CONSTANT_PCT = _env_float_bounded(
    "EDA_NEAR_CONSTANT_PCT", 95.0, low=0.0, high=100.0
)

# Unique/ratio vs rows for high-cardinality; env EDA_HIGH_CARD_UNIQUE_RATIO
PROFILE_HIGH_CARD_UNIQUE_RATIO = _env_float_bounded(
    "EDA_HIGH_CARD_UNIQUE_RATIO", 0.95, low=0.0, high=1.0
)
