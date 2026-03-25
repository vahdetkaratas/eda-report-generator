# EDA Report Generator — Project Tracking

This file is the single place to track **what is done, where to look, and what to do next**.

---

## 1. Project summary

| | |
|---|---|
| **Purpose** | Upload CSV / Excel (`.xlsx`) → automatic profile report (HTML, optional PDF). Sheet choice, configurable limits, sampling, histograms, structured warnings, executive/data-quality summaries, column intelligence, datetime profiling, outlier notes. Data is not modified, only summarized. |
| **Service** | Automated Dataset Profiling & Reporting |
| **Target audience** | Data/ML teams, businesses that need a data quality audit |

---

## 2. Status (what is done)

- **MVP complete.** Report includes: Executive summary, Data quality snapshot, Structured warnings, Column intelligence, Datetime profiling (when applicable), then Overview, Sample rows (first 5), Schema, Duplicate, Missing, Distributions, Correlations, Quick notes, optional Target summary.
- **Report metadata:** Generated timestamp (UTC), source filename in header.
- **Guards:** Empty/single-column rejected; max file size (config/env/sidebar); datasets over limit sampled with note; **sampling strategy:** first N or random N.
- **Input:** CSV + **`.xlsx`** (read-only; **Excel sheet selector** for multi-sheet workbooks). **Output:** HTML/PDF **in memory** for download in the app; optional **`render_report(..., output_path=…)`** only for tests or manual export — no fixed shared report path at runtime.
- **Report extras:** Per-column **histogram** (SVG) for numeric distributions; **warnings** via `build_warnings` → **`quick_notes`** + structured **`warnings`** in payload; **outlier** notes (IQR) among warning types.
- **Config:** Limits from env (`EDA_MAX_FILE_MB`, `EDA_MAX_ROWS`, `EDA_SAMPLE_SIZE`) and **sidebar overrides** (max file MB, max rows, sample size).
- **Demo:** `scripts/generate_demo_data.py` generates customer + sales CSV.
- **Tests:** `pytest` / `python -m pytest` — **19** tests: load (incl. Excel sheets), profile, report (metadata, sample rows, sampling note).
- **Enhancements delivered:** Excel sheet choice, first/random sampling, histogram SVGs, IQR outlier notes, env + sidebar limits, PDF troubleshooting in README.

### MVP Final (delivery decision)

- **Decision:** MVP is complete and portfolio-ready.
- **Quality gate:** Core scope implemented, tests passing, docs aligned, and known risks mitigated to acceptable MVP level.
- **Release recommendation:** Safe to present as completed MVP; optional items below can be picked up anytime.

---

## 3. Code map (where to look when changing something)

| What to change | File / location |
|----------------|------------------|
| Data loading (CSV/Excel, sheet choice) | `src/load.py` → `load_data()`, `get_excel_sheet_names()`, `get_supported_extensions()` |
| Limits (file size, rows, sample size) | `src/config.py` (env: `EDA_MAX_FILE_MB`, `EDA_MAX_ROWS`, `EDA_SAMPLE_SIZE`) |
| Profiling (schema, duplicate, stats, distributions, correlations, warnings, quick_notes, outliers, hist bins) | `src/profile.py` → `run_full_profile()`, `profile_*`, `build_warnings()`, `warnings_to_quick_notes()` |
| HTML/PDF in memory + file render for tests | `src/report.py` → `get_report_html()`, `get_report_pdf_result()`, `get_report_pdf_bytes()`, `render_report(output_path=…)` |
| Report content / section order | `templates/report.html` |
| UI (upload, Excel sheet, sidebar limits, sampling choice, target column, downloads) | `src/app.py` |
| Demo data generation | `scripts/generate_demo_data.py` |
| New warning / note rule | `src/profile.py` → `build_warnings()` (feeds `warnings` + `quick_notes` in `run_full_profile`) |
| VPS deploy (Nginx, TLS, systemd) | **docs/DEPLOY_VPS.md** |

---

## 4. Optional next steps

Core deliverables (metadata, guards, limits, sampling, sample rows, PDF) are implemented.

### Backlog (prioritized)

| Priority | Item | Status |
|---|---|---|
| P1 | Excel sheet selector | Done |
| P1 | Smarter sampling (first N / random N) | Done |
| P1 | PDF export troubleshooting guide | Done (README) |
| P2 | Outlier quick notes (IQR) | Done |
| P2 | Optional histogram visuals in report | Done (SVG per numeric column) |
| P2 | Config from env + sidebar overrides | Done |
| P3 | Parquet input support | Optional |
| P3 | CI workflow (tests + lint) | Optional |

---

## 5. Common commands

| Action | Command |
|--------|---------|
| Run app | `streamlit run src/app.py` |
| Run tests | `pytest` or `python -m pytest` |
| Generate demo CSV | `python scripts/generate_demo_data.py` |

---

## 6. Relation to README

- **README.md** = Public/GitHub face: what the project is, how to install and run.
- **docs/PROJECT.md** = Internal tracking: status, code map, next steps. Update here when needed.

From now on, "what to do and how to track it" is answered by **docs/PROJECT.md** and **README.md**.
