# EDA Report Generator

**Automated dataset profiling and quality report.**  
Profiles structure, quality, and distributions of your data; data is not modified.

**Target audience:** Data and ML teams, businesses that need a quick data quality audit.

## Architecture (High-Level)

```text
CSV / Excel upload (Excel: sheet selector)
        |
        v
Optional limits (env + sidebar) / row sampling (first or random)
        |
        v
Schema detection (types + unique count)
        |
        v
Profiling engine (missing, duplicates, distributions, correlations, outliers)
        |
        v
Interpretation (structured warnings, quick_notes, executive / data-quality summaries)
        |
        v
HTML report rendering (histograms as SVG)
        |
        v
Export (downloadable HTML, optional PDF)
```

---

## What You Receive

Deliverables:

1. **Single-page HTML report** — downloadable, opens in any browser. Optional **PDF** (requires `weasyprint`).
2. **Report contents:** Source filename and generation timestamp; **Executive summary**, **data quality snapshot**, **structured warnings**, **column intelligence**, **datetime profiling** (when applicable); Overview (with sampling note when applicable); Sample rows (first 5); Schema, Duplicate summary, Missing values; **numeric histograms (SVG)** per column; categorical distributions, Correlation matrix; **outlier notes (IQR)**; Quick notes. Optional: target column summary when a target is selected.
3. **Guards:** Empty or single-column files are rejected. Max file size and row/sample limits are configurable via **env** (`EDA_MAX_FILE_MB`, `EDA_MAX_ROWS`, `EDA_SAMPLE_SIZE`) and **sidebar "Limits (override)"**. For large datasets you can choose **first N rows** or **random sample of N**.

---

## Report Sections

- **Executive summary** — Short bullets from profiling
- **Data quality snapshot** — Headline and quality counts
- **Structured warnings** — Grouped by level (critical / warning / info)
- **Column intelligence** — Constant, near-constant, high-cardinality, ID-like flags
- **Datetime profiling** — Min/max/nulls when datetime-like columns are detected
- **Overview** — Row count, column count, memory (and sampling note if applicable)
- **Sample rows (first 5)** — Preview table
- **Schema / Column types** — Column name, type, unique value count
- **Duplicate summary** — Total / unique / duplicate rows
- **Missing values** — Per-column missing count and %
- **Numeric distributions** — inline histogram (SVG) per column
- **Categorical distributions**
- **Correlations** — Numeric columns only
- **Target summary** (optional) — When a target column is selected: distribution, class balance
- **Quick notes** — Auto-generated notes (high missing, duplicates, correlation, skew, **outliers (IQR)**)

## Requirements

- Python 3.10+
- **Production (runtime):** `requirements-prod.txt` — pandas, jinja2, streamlit, openpyxl, weasyprint.
- **Development:** `requirements-dev.txt` — production deps **plus** pytest (or use `requirements.txt`, which includes dev deps via `-r requirements-dev.txt`).

## Installation

**Local development (app + tests):**

```bash
pip install -r requirements.txt
```

**Production (runtime only):**

```bash
pip install -r requirements-prod.txt
```

To generate or refresh demo datasets (customer, sales):

```bash
python scripts/generate_demo_data.py
```

- `data/demo_customer/customer.csv` — ~1200 rows (id, age, gender, income, segment, signup_date, purchase_count)
- `data/demo_sales/sales.csv` — ~2500 rows (date, product_id, amount, quantity, region, category)

## Run

```bash
streamlit run src/app.py
```

Upload a CSV or Excel file in the browser. For Excel you can **choose the sheet**. The report is generated automatically; Quick notes (including outliers) are shown in an expander; **HTML/PDF are built for download in memory** (no fixed shared report path). Use **Privacy & data handling** (top of app) for how uploads are used. Use the **sidebar "Limits (override)"** to change max file size, max rows, and sample size (0 = use config/env defaults).

### PDF export (WeasyPrint)

- Install: `pip install weasyprint`
- If PDF download is missing or fails:
  - **Windows:** Install [GTK3 Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) or use a conda env: `conda install -c conda-forge weasyprint`.
  - **macOS:** `brew install pango gdk-pixbuf libffi` then `pip install weasyprint`.
  - **Linux (Debian/Ubuntu):** `sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev` then `pip install weasyprint`.
- If WeasyPrint is missing or PDF generation fails on the host, the app still runs; **HTML download stays available** and the UI shows a short in-app note that **PDF is not available in that environment** (not a step-by-step install prompt in the app).

### Config (env and UI)

- **Environment:** `EDA_MAX_FILE_MB`, `EDA_MAX_ROWS`, `EDA_SAMPLE_SIZE` override defaults (e.g. `EDA_MAX_FILE_MB=100`).
- **Sidebar:** In the app, open **Limits (override)** to set max file size (MB), max rows, and sample size; use 0 to keep config/env defaults.

## Test

```bash
pytest
```

On Windows, if `pytest` is not on PATH: `python -m pytest`.

Tests: `tests/test_load.py` (CSV, Excel sheet names), `tests/test_profile.py`, `tests/test_report.py` (HTML, metadata, sampling note, target summary). **19** tests total.

## Input

- **CSV** (`.csv`)
- **Excel** (`.xlsx` only, via openpyxl) — read-only; **sheet selector** when the workbook has multiple sheets

## Project Structure

```
├── src/
│   ├── config.py    # limits; env EDA_MAX_FILE_MB, EDA_MAX_ROWS, EDA_SAMPLE_SIZE
│   ├── load.py      # CSV + Excel; get_excel_sheet_names, load_data(sheet_name=...)
│   ├── profile.py   # profiling, histogram bins, outlier (IQR) notes, sample_rows
│   ├── report.py    # get_report_html, get_report_pdf_result / get_report_pdf_bytes; render_report(path) for tests
│   └── app.py       # Streamlit UI (sheet selector, limits sidebar, sampling choice)
├── templates/
│   └── report.html
├── data/demo_customer/, data/demo_sales/
└── tests/
```

The Streamlit app **does not** write reports to a fixed folder; HTML/PDF are built **in memory** for download. **`render_report(..., output_path=…)`** in `src/report.py` is only for **tests** or an **explicit** export path you choose — not default runtime behavior.

---

**Project status, code map, and next steps:** [docs/PROJECT.md](docs/PROJECT.md)

*Automated Dataset Profiling & Reporting.*
