"""
CSV and Excel (read-only) loading.
"""
from pathlib import Path
from typing import Any, Union

import pandas as pd


def read_csv_with_encoding_fallback(
    source: str | Path | Any,
    **read_csv_kwargs: Any,
) -> tuple[pd.DataFrame, str]:
    """
    Read CSV with UTF-8 first; on UnicodeDecodeError retry with latin-1.
    Returns (dataframe, encoding_used).
    File-like sources are rewound between attempts.
    """
    encodings = ("utf-8", "latin-1")
    last_err: BaseException | None = None
    for enc in encodings:
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            df = pd.read_csv(source, encoding=enc, **read_csv_kwargs)
            return df, enc
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise ValueError(
        "Could not read CSV as UTF-8 or latin-1."
    ) from last_err


def get_excel_sheet_names(source: Union[str, Path, bytes, Any]) -> list[str]:
    """
    Return sheet names for an Excel file.
    source: file path (str/Path) or file-like object (e.g. Streamlit UploadedFile).
    """
    if isinstance(source, pd.ExcelFile):
        return source.sheet_names
    with pd.ExcelFile(source, engine="openpyxl") as xl:
        return xl.sheet_names


def load_data(path: str | Path, sheet_name: str | int | None = None) -> pd.DataFrame:
    """
    Load a CSV or .xlsx (openpyxl) file.

    - Excel: use sheet_name to pick a sheet (default: first sheet). Read-only; data is not modified.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df, _ = read_csv_with_encoding_fallback(path)
        return df
    if suffix == ".xlsx":
        return pd.read_excel(
            path,
            sheet_name=sheet_name if sheet_name is not None else 0,
            engine="openpyxl",
        )
    raise ValueError(f"Unsupported format: {suffix}. Use .csv or .xlsx.")


def get_supported_extensions() -> tuple[str, ...]:
    """Accepted extensions for upload (.xlsx via openpyxl)."""
    return (".csv", ".xlsx")
