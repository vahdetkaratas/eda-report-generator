# EDA Report Generator demo shell

This folder renders **static showcase pages** (recruiter vs commercial framing) around the Streamlit-based EDA app. It is not API-first and does not document backend routes.

## Purpose

The shell owns:

- shared layout and typography
- project hero frame and CTAs from `projects/*.json`
- sidebar (technical focus, related links where configured)
- profile-specific identity (see `profiles/*.json`)

The Streamlit app and report logic stay in `src/`; this shell only publishes HTML/CSS/JS for static hosting.

## Domain mapping (final)

| Surface | Domain | Repo output |
|---------|--------|-------------|
| Recruiter static shell (project explanation) | `eda-report.vahdetkaratas.com` | `layout-shell/` |
| Commercial static shell | `eda-report.vahdetlabs.com` | `layout-shell-commercial/` |
| Recruiter Streamlit demo | `eda.vahdetkaratas.com` | `src/` app (deploy separately) |
| Commercial Streamlit demo | `eda.vahdetlabs.com` | same app image / process, second hostname |

Live demo CTAs in JSON: recruiter → `eda.vahdetkaratas.com`; commercial → `eda.vahdetlabs.com`. Sidebar rail `portfolioUrl`: recruiter profile → `https://eda-report.vahdetkaratas.com`; commercial → `https://eda-report.vahdetlabs.com`.

## Files

- `index.html`: template with placeholders
- `shell.css`, `demo-content.css`, `shell.js`: shell UI
- `profile.json`: default recruiter-aligned profile snippet for compatibility
- `profiles/recruiter.json`, `profiles/commercial.json`: named identities
- `projects/eda-report.json`: project + per-profile overrides
- `body/eda-report.html`, `body/eda-report-commercial.html`: recruiter vs commercial body copy (keep separate files)
- `render-shell.mjs`: Node script that fills the template

## Render (this repo)

From the repository root:

Recruiter (e.g. `eda-report.vahdetkaratas.com`):

```bash
node shell/render-shell.mjs \
  --project shell/projects/eda-report.json \
  --body shell/body/eda-report.html \
  --out layout-shell \
  --profile recruiter
```

Commercial (e.g. `eda-report.vahdetlabs.com` — must not embed personal-site domains):

```bash
node shell/render-shell.mjs \
  --project shell/projects/eda-report.json \
  --body shell/body/eda-report-commercial.html \
  --out layout-shell-commercial \
  --profile commercial
```

Outputs per directory:

- `index.html`, `shell.css`, `demo-content.css`, `shell.js`, `profile.json` (and bundled assets referenced by profiles)

Profile-specific fields include home URL, eyebrow copy, sidebar links, footer line. Overrides under `profiles.<name>` in the project JSON control title/summary/CTAs per audience.

## Notes

- Commercial render should use **Labs-only links and assets** (no cross-domain leakage to personal recruiter domains).
- Repo README stays technically neutral where possible; positioning for each domain belongs in rendered shell output and project JSON — not duplicated as sales copy inside `README.md`.
