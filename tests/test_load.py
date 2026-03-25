"""
Tests for load_data module.
"""
from pathlib import Path
import tempfile
import pandas as pd
import pytest

from src.load import (
    get_excel_sheet_names,
    load_data,
    get_supported_extensions,
    read_csv_with_encoding_fallback,
)


def test_load_csv():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        f.write(b"a,b\n1,2\n3,4\n")
        f.flush()
        path = f.name
    df = load_data(path)
    assert len(df) == 2
    assert list(df.columns) == ["a", "b"]
    Path(path).unlink(missing_ok=True)


def test_load_csv_latin1_fallback():
    """Byte 0xE9 is invalid as UTF-8 alone; latin-1 decodes it."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as f:
        f.write(b"h\n\xe9\n")
        path = f.name
    try:
        df, enc = read_csv_with_encoding_fallback(path)
        assert enc == "latin-1"
        assert len(df) == 1
        assert list(df.columns) == ["h"]
        df2 = load_data(path)
        assert len(df2) == 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_supported_extensions():
    exts = get_supported_extensions()
    assert exts == (".csv", ".xlsx")
    assert ".xls" not in exts


def test_load_nonexistent():
    with pytest.raises(FileNotFoundError):
        load_data(Path("/nonexistent/file.csv"))


def test_get_excel_sheet_names_and_load_sheet():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        with pd.ExcelWriter(path, engine="openpyxl") as w:
            pd.DataFrame({"x": [1, 2]}).to_excel(w, sheet_name="First", index=False)
            pd.DataFrame({"y": [3, 4, 5]}).to_excel(w, sheet_name="Second", index=False)
        names = get_excel_sheet_names(path)
        assert "First" in names and "Second" in names
        df1 = load_data(path, sheet_name="First")
        df2 = load_data(path, sheet_name="Second")
        assert list(df1.columns) == ["x"] and len(df1) == 2
        assert list(df2.columns) == ["y"] and len(df2) == 3
    finally:
        Path(path).unlink(missing_ok=True)
