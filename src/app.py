"""
Streamlit app: CSV/Excel upload → Profiling → HTML report download.
"""
from pathlib import Path
import streamlit as st

from src.config import MAX_FILE_SIZE_BYTES, MAX_ROWS, SAMPLE_SIZE
from src.load import (
    get_excel_sheet_names,
    load_data,
    get_supported_extensions,
    read_csv_with_encoding_fallback,
)
from src.profile import run_full_profile
from src.report import get_report_html, get_report_pdf_result


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_CUSTOMER = PROJECT_ROOT / "data" / "demo_customer" / "customer.csv"
DEMO_SALES = PROJECT_ROOT / "data" / "demo_sales" / "sales.csv"


st.set_page_config(page_title="EDA Report Generator", layout="wide")
st.title("EDA Report Generator")
st.caption("Dataset profiling & quality report — upload CSV or Excel.")

with st.expander("Privacy & data handling", expanded=False):
    st.markdown(
        """
        **How your data is used**

        - Uploaded files are processed **in this browser session** on the server to build the profile and downloads.
        - This app **does not write uploads or reports to a fixed shared path** for later retrieval; HTML/PDF for download are **generated on demand** (in memory for the report content).
        - PDF generation (WeasyPrint) or the server environment **may use short-lived temporary files**; we do not keep your dataset or reports for reuse after the session.
        - **Do not upload confidential data** to shared or untrusted hosts. For sensitive data, run the app on infrastructure you control.
        """
    )

with st.sidebar:
    with st.expander("Limits (override)", expanded=False):
        st.caption("Leave 0 to use defaults from config/env.")
        override_max_mb = st.number_input("Max file size (MB)", min_value=0, value=0, step=1)
        override_max_rows = st.number_input("Max rows (above = sample)", min_value=0, value=0, step=10000)
        override_sample_size = st.number_input("Sample size (when sampling)", min_value=0, value=0, step=5000)

effective_max_file_bytes = (int(override_max_mb * 1024 * 1024) if override_max_mb else MAX_FILE_SIZE_BYTES)
effective_max_rows = override_max_rows or MAX_ROWS
effective_sample_size = override_sample_size or SAMPLE_SIZE

uploaded = st.file_uploader(
    "Upload file",
    type=[e.lstrip(".") for e in get_supported_extensions()],
)

demo_path = None
if not uploaded:
    demo = st.radio("Or use demo", ["None", "Demo Customer", "Demo Sales"], horizontal=True)
    if demo == "Demo Customer" and DEMO_CUSTOMER.exists():
        demo_path = DEMO_CUSTOMER
    elif demo == "Demo Sales" and DEMO_SALES.exists():
        demo_path = DEMO_SALES

import pandas as pd

df = None
if uploaded:
    if getattr(uploaded, "size", 0) > effective_max_file_bytes:
        st.error(f"File too large. Maximum size: {effective_max_file_bytes // (1024*1024)} MB.")
    else:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df, csv_enc = read_csv_with_encoding_fallback(uploaded)
                if csv_enc != "utf-8":
                    st.caption("CSV read using Latin-1 after UTF-8 decoding failed.")
            else:
                sheet_names = get_excel_sheet_names(uploaded)
                if not sheet_names:
                    st.error("No sheets in workbook.")
                    df = None
                else:
                    sheet = st.selectbox("Excel sheet", sheet_names, key="excel_sheet")
                    uploaded.seek(0)
                    df = pd.read_excel(uploaded, sheet_name=sheet, engine="openpyxl")
        except Exception:
            st.error("Could not read the uploaded file.")
            st.caption("Please check the file format and try again.")
            df = None
elif demo_path:
    try:
        df = load_data(demo_path)
    except Exception:
        st.error("Could not load the demo dataset.")
        df = None
else:
    df = None

if df is not None and (df.empty or len(df.columns) < 1):
    st.error("Upload a valid file with at least one column and one row.")
    df = None

target_column = None
if df is not None:
    target_options = ["None"] + list(df.columns)
    target_column = st.selectbox("Target column (optional — for ML)", target_options)
    if target_column == "None":
        target_column = None

if df is not None:
    original_rows = len(df)
    sample_strategy = "first"
    if original_rows > effective_max_rows:
        sample_strategy = st.radio(
            "Large dataset: how to sample?",
            ["First N rows", "Random sample of N rows"],
            horizontal=True,
            key="sample_strategy",
        )
        n_sample = min(effective_sample_size, len(df))
        if "Random" in sample_strategy:
            df = df.sample(n=n_sample, random_state=42)
            sample_strategy = "random"
        else:
            df = df.head(n_sample)
            sample_strategy = "first"
        st.warning(f"Dataset has {original_rows:,} rows; report uses {len(df):,} rows ({'random' if sample_strategy == 'random' else 'first'} sample).")
    with st.spinner("Profiling…"):
        profile_data = run_full_profile(df, target_column=target_column)
    if original_rows > effective_max_rows:
        profile_data["sampled_from"] = original_rows
        profile_data["sampled_n"] = len(df)
        profile_data["sampled_strategy"] = sample_strategy

    st.success(f"Report ready: {len(df)} rows, {len(df.columns)} columns.")

    ov = profile_data["overview"]
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Rows", ov["row_count"])
    with c2:
        st.metric("Columns", ov["column_count"])
    with c3:
        st.metric("Memory (MB)", ov["memory_mb"])
    dup = profile_data["duplicate_summary"]
    if dup["duplicate_count"] > 0:
        st.warning(f"Duplicate rows: {dup['duplicate_count']}")

    st.subheader("Executive summary")
    exec_lines = profile_data.get("executive_summary") or []
    if exec_lines:
        for line in exec_lines:
            st.markdown(f"- {line}")
    else:
        st.caption("No executive summary available for this profile.")

    st.subheader("Data quality snapshot")
    dq = profile_data.get("data_quality") or {}
    st.markdown(dq.get("headline") or "—")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.metric("High-missing columns", int(dq.get("high_missing_column_count", 0)))
        st.metric("Duplicate rows", int(dq.get("duplicate_row_count", 0)))
    with d2:
        st.metric("Constant columns", int(dq.get("constant_column_count", 0)))
        st.metric("Near-constant columns", int(dq.get("near_constant_column_count", 0)))
    with d3:
        st.metric("High-cardinality columns", int(dq.get("high_cardinality_column_count", 0)))
        st.metric("ID-like columns", int(dq.get("id_like_column_count", 0)))
    with d4:
        st.metric("Datetime-like columns", int(dq.get("datetime_column_count", 0)))

    st.subheader("Structured warnings")
    warn_list = profile_data.get("warnings") or []
    _levels = ("critical", "warning", "info")
    _labels = {"critical": "Critical", "warning": "Warning", "info": "Info"}
    if not warn_list:
        st.caption("No structured warnings for this dataset.")
    else:
        for lvl in _levels:
            bucket = [w for w in warn_list if str(w.get("level", "")).lower() == lvl]
            if not bucket:
                continue
            st.markdown(f"**{_labels[lvl]}**")
            for w in bucket:
                msg = w.get("message") or ""
                col = w.get("column")
                extra = f" *({col})*" if col else ""
                st.markdown(f"- {msg}{extra}")

    st.subheader("Column intelligence")
    ci = profile_data.get("column_intelligence") or {}
    with st.expander("Constant columns", expanded=False):
        const_cols = ci.get("constant") or []
        if const_cols:
            st.markdown("\n".join(f"- {c}" for c in const_cols))
        else:
            st.caption("None detected.")
    with st.expander("Near-constant columns", expanded=False):
        near = ci.get("near_constant") or []
        if near:
            st.dataframe(pd.DataFrame(near), hide_index=True, use_container_width=True)
        else:
            st.caption("None detected.")
    with st.expander("High-cardinality columns", expanded=False):
        hc = ci.get("high_cardinality") or []
        if hc:
            st.dataframe(pd.DataFrame(hc), hide_index=True, use_container_width=True)
        else:
            st.caption("None detected.")
    with st.expander("ID-like columns", expanded=False):
        id_like = ci.get("id_like") or []
        if id_like:
            st.markdown("\n".join(f"- {c}" for c in id_like))
        else:
            st.caption("None detected.")

    dtp = profile_data.get("datetime_profile") or {}
    if dtp:
        st.subheader("Datetime profiling")
        dt_rows = [
            {
                "column": name,
                "min": meta.get("min"),
                "max": meta.get("max"),
                "null_pct": meta.get("null_pct"),
                "row_count": meta.get("row_count"),
            }
            for name, meta in dtp.items()
        ]
        st.dataframe(pd.DataFrame(dt_rows), hide_index=True, use_container_width=True)

    notes = profile_data.get("quick_notes") or []
    if notes:
        with st.expander("Quick notes", expanded=True):
            for note in notes:
                st.markdown(f"- {note}")

    source_name = uploaded.name if uploaded else (demo_path.name if demo_path else None)
    html_report = get_report_html(profile_data, source_name=source_name)
    pdf_bytes, pdf_fail_reason = get_report_pdf_result(profile_data, source_name=source_name)
    st.success("Report ready to download.")
    st.download_button(
        "Download report (HTML)",
        html_report,
        file_name="eda_profile_report.html",
        mime="text/html",
    )
    if pdf_bytes is not None:
        st.download_button(
            "Download report (PDF)",
            pdf_bytes,
            file_name="eda_profile_report.pdf",
            mime="application/pdf",
        )
    else:
        if pdf_fail_reason == "missing_weasyprint":
            pdf_note = (
                "This usually means the optional PDF component is not installed on the server."
            )
        else:
            pdf_note = (
                "This usually means PDF system dependencies are not installed or configured on the server."
            )
        st.info(
            "PDF export is not available in this environment. "
            + pdf_note
            + " HTML export is still available."
        )
else:
    st.info("Upload a CSV or Excel file, or select a demo dataset.")
