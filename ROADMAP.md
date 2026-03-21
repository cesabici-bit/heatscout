# HeatScout — Full Roadmap (Phase 3-4)

**Current status:** Phase 1+2 COMPLETE + 3A/3B/3F/3C.1 DONE. 186 tests, stable core engine, working UI, PDF report, TEE incentives.
**Model:** Open source, free. Goal: visibility and credibility.
**Created:** 2026-03-09

---

## Legend

Each task has:
- **Input:** what must exist before starting
- **Output:** what exists after completion
- **Pass/Fail:** objective, verifiable criterion
- **Pre-mortem:** how it can fail and how to mitigate

---

## PHASE 3A — Public GitHub & CI

> The repo is the business card. It must make a good impression from the first second.

### Task 3A.1: Public GitHub repository

- **Input:** Local project with 163 passing tests, pyproject.toml
- **Output:**
  - Public GitHub repo with LICENSE (MIT or Apache 2.0)
  - README.md rewritten for GitHub: hero description, screenshot/GIF of UI, quick start, CI badge, live demo link
  - Complete `.gitignore` (no __pycache__, .egg-info, .env, IDE files)
  - Basic CONTRIBUTING.md (how to contribute, how to open issues)
- **Pass/Fail:**
  - A visitor understands what HeatScout does in 10 seconds from the README
  - UI screenshot visible above the fold
  - Open source license present
  - No unnecessary files in repo (no cache, no build artifacts)
- **Pre-mortem:**
  - README too long/technical → max 100 lines, visual, not a wall of text
  - Outdated screenshot → generate from current app with "foundry" example
  - Credentials/local paths in code → grep for "cesab", "C:\Users", absolute paths before push

### Task 3A.2: GitHub Actions CI

- **Input:** Public GitHub repo (Task 3A.1)
- **Output:** `.github/workflows/ci.yml` running `pytest tests/ -v` on every push/PR
- **Pass/Fail:** Green CI badge in README. A broken test blocks merge.
- **Pre-mortem:**
  - CoolProp wheel not available for GitHub runner → test `pip install CoolProp` on ubuntu-latest, fallback to conda if it fails
  - kaleido on headless Linux → skip PDF tests with `pytest.mark` if needed
  - Slow CI (CoolProp is heavy) → cache pip dependencies

### Task 3A.3: Pre-commit hooks (linting) ✅

- **Input:** Green CI (Task 3A.2)
- **Output:** `.pre-commit-config.yaml` with ruff (lint + format)
- **Pass/Fail:** `pre-commit run --all-files` passes without errors
- **Pre-mortem:**
  - Ruff flags too many warnings → configure `ruff.toml` with progressive rules, fix the bulk before enabling
  - Slows down the commit loop → minimal rules, no docstring enforcement

---

## PHASE 3B — Public Deploy

> The app must be testable by anyone with one click, without installing anything.

### Task 3B.1: Deploy on Streamlit Community Cloud

- **Input:** Public GitHub repo with working app
- **Output:**
  - Live app on public URL (e.g. heatscout.streamlit.app)
  - Demo link in README
  - `requirements.txt` verified for Streamlit Cloud (dependency compatibility)
- **Pass/Fail:**
  - URL accessible from browser without login
  - "Foundry" example works end-to-end (analysis + PDF download)
  - Initial load time < 30 seconds
- **Pre-mortem:**
  - CoolProp doesn't install on Streamlit Cloud → verify compatibility, possibly `packages.txt` with system dependencies
  - Limited memory (1GB on free tier) → verify that 10 streams don't exceed it
  - App goes to sleep after inactivity → acceptable for free tier, document in README
  - kaleido for PDF images → might fail, have text fallback

---

## PHASE 3C — Italian Incentives (differentiating feature)

> No free tool calculates the impact of Italian incentives on heat recovery. This is the differentiator.

### Task 3C.1: White Certificates (TEE) module

- **Input:** economics.py with working NPV/payback, data from TEE decree 2025-2030
- **Output:**
  - New module `knowledge/incentives.py` with TEE calculation: energy saved (TEP) × TEE value (€/TEE) × incentive duration
  - Integration in economics.py: NPV and payback recalculated WITH and WITHOUT incentive
  - UI shows both scenarios (table: "without incentives" vs "with White Certificates")
- **Pass/Fail:**
  - TEP calculated consistently with ARERA conversion factors
  - NPV with incentive > NPV without incentive (always)
  - Payback with incentive < payback without incentive (always)
  - Test: `test_incentives.py` with 3+ manually verified examples
  - Regulatory sources cited in code and UI
- **Pre-mortem:**
  - TEE decree 2025-2030 is complex, with variable categories and useful life → simplify to the "heat recovery" specific case, don't generalize
  - TEE market value varies over time (GME market) → use recent average value with note "indicative value"
  - Regulations change → declare last update date in UI

### Task 3C.2: Transizione 5.0

- **Input:** Task 3C.1 completed (incentives.py structure already exists)
- **Output:**
  - Tax credit calculation Transizione 5.0: % tax credit on CAPEX (tiers by investment size)
  - Added to comparison table: third column "with Transizione 5.0"
- **Pass/Fail:**
  - Correct rates per tier (verify vs MIMIT)
  - Effective CAPEX reduced by tax credit
  - Test: verify that net CAPEX < gross CAPEX
- **Pre-mortem:**
  - Transizione 5.0 has complex eligibility requirements (consumption reduction ≥3%) → simplify: show benefit IF eligible, with note on requirements
  - Funds exhausted / expiry → show validity date and note "check availability"

---

## PHASE 3D — Export & Persistence

> Users must be able to export results and save their work.

### Task 3D.1: Excel export of results

- **Input:** Completed analysis in UI
- **Output:** "Download Excel" button → .xlsx with 3 sheets: Streams, Technologies, Economics (including with/without incentive comparison)
- **Pass/Fail:**
  - .xlsx file opens in Excel/LibreOffice without errors
  - Contains all data visible in UI tables (same numbers, same units)
  - Test: `test_export.py` generates xlsx from "foundry" example, verifies columns and values
- **Pre-mortem:**
  - openpyxl as new dependency → add to pyproject.toml and requirements.txt
  - Number formatting → use international format (decimal point), user can convert in Excel

### Task 3D.2: Save/Load analysis (JSON)

- **Input:** Working UI with stream input
- **Output:**
  - "Save analysis" button → downloads .json with all inputs
  - "Load analysis" button → uploads .json restoring inputs
- **Pass/Fail:**
  - Round-trip: save → load → re-run → same results (±0.01%)
  - .json file is readable (indented, clear field names)
  - Schema version included (`"version": "1.0"`)
  - Test: `test_persistence.py` round-trip on 3 examples
- **Pre-mortem:**
  - Undocumented JSON schema → include version field for future compatibility
  - Custom fluids not serializable → verify all ThermalStream fields are JSON-safe

### Task 3D.3: Import streams from CSV/Excel

- **Input:** Task 3D.1 completed (Excel format defined)
- **Output:** File upload in sidebar → populates streams in UI
- **Pass/Fail:**
  - Uploading an exported file recreates the same streams
  - Malformed file → clear error, no crash
  - Downloadable template available
- **Pre-mortem:**
  - CSV encoding from Italian Excel (Latin-1) → force UTF-8 with BOM
  - Huge file → limit to 50 streams with clear message

---

## PHASE 3E — Sensitivity Analysis

> Feature that makes the tool serious: "what happens if parameters change?"

### Task 3E.1: Energy price sensitivity ✅

- **Input:** Working economic analysis, UI with results
- **Output:** New UI section "Sensitivity Analysis" with energy price slider (±50%) and payback vs price chart
- **Pass/Fail:**
  - Monotonically decreasing curve (payback drops when price rises)
  - Price 0 → infinite payback; price 2x → payback ~halved
  - Test: `test_sensitivity.py` verifies monotonicity and edge cases
- **Pre-mortem:**
  - Slow recalculation → precompute 10-20 points, not real-time
  - IRR = None for some prices → handle gracefully in chart

### Task 3E.2: Multi-parameter tornado chart ✅

- **Input:** Task 3E.1 completed
- **Output:** Tornado chart: NPV variation with ±20% change in energy price, CAPEX, operating hours, efficiency
- **Pass/Fail:**
  - Bars sorted by impact (most influential parameter on top)
  - Test: output has 4+ bars with non-zero values
- **Pre-mortem:**
  - Too many parameters → limit to 4 most relevant
  - Interactions ignored → declare "one-at-a-time" assumption in UI

---

## PHASE 3F — Robustness

> The app must never crash in front of a user.

### Task 3F.1: UI error handling

- **Input:** Current app.py with generic try/except
- **Output:** User-friendly error messages:
  - No streams → "Add at least one stream before analyzing"
  - All COLD_DEMAND → "At least one HOT_WASTE stream is required"
  - CoolProp fails → "Error calculating fluid properties: [detail]"
  - PDF fails → "Error generating PDF. Try Excel."
  - Catch-all → "Unexpected error. Report it on GitHub."
- **Pass/Fail:**
  - No Python traceback ever visible to the user
  - Every error shows `st.error()` with clear, understandable message
  - Manual test: trigger each of the 5 errors, verify message
- **Pre-mortem:**
  - Unforeseen errors → final catch-all with link to GitHub issues

### Task 3F.2: End-to-end integration test

- **Input:** All core modules working
- **Output:** `test_integration.py` with 5 tests:
  1. Complete workflow from stream to summary
  2. "Foundry" example end-to-end
  3. Multi-stream (5 streams)
  4. Edge case: 1 kW stream
  5. Edge case: T = 800°C
- **Pass/Fail:** All pass. No unhandled exceptions.
- **Pre-mortem:**
  - Slow tests (CoolProp) → acceptable, there are only 5
  - data/ path → use package-relative paths

---

## PHASE 4A — Documentation & Methodology

> Credibility = transparency. Sources, limits, assumptions all visible.

### Task 4A.1: In-app help (tooltips) ✅

- **Input:** Current UI without contextual help
- **Output:**
  - Tooltips: T_in/T_out, HOT_WASTE vs COLD_DEMAND, NPV, payback
  - Disclaimer visible BEFORE economic results: "First-level analysis, CAPEX ±30%, savings ±15%"
  - Collapsible expanders "How to interpret these results"
- **Pass/Fail:**
  - Every UI section has at least one tooltip or info box
  - Disclaimer visible without scrolling
- **Pre-mortem:**
  - Cluttered UI → collapsible expanders, max 2 sentences per tooltip

### Task 4A.2: Methodology page ✅

- **Input:** Sources already documented in cost_correlations.py, efficiency_models.py
- **Output:** Streamlit "Methodology" page with:
  - Table: technology → CAPEX correlation → source → year
  - Efficiency models: formula + source
  - Validity range for each technology
  - Validation case studies (summary)
- **Pass/Fail:**
  - Every correlation has a cited source (author/organization, year)
  - Explicit validity ranges
- **Pre-mortem:**
  - Too academic → balance rigor and readability
  - Dated sources → flag the year

---

## PHASE 4B — Beta & Release

> Validation with real users, then tag v1.0.

### Task 4B.1: Beta testing (3-5 users) 🔄 IN PROGRESS

- **GitHub Issue:** https://github.com/cesabici-bit/heatscout/issues/1
- **Input:** Live app on Streamlit Cloud, in-app documentation
- **Output:**
  - 3-5 users (engineers/energy managers) test with real data
  - Structured feedback (works / confusing / missing)
  - Prioritized bug list
- **Pass/Fail:**
  - At least 3 users complete end-to-end analysis without assistance
  - No crashes during testing
  - Feedback collected and categorized
- **Pre-mortem:**
  - Users not available → start with 1-2 contacts
  - Data out of range → limits documented in UI
  - Enterprise expectations → clarify it's a screening tool

### Task 4B.2: Release v1.0

- **Input:** Bug list from beta test
- **Output:**
  - Critical bugs fixed
  - Git tag `v1.0.0`
  - CHANGELOG.md
  - Announcement (LinkedIn, energy community, FIRE)
- **Pass/Fail:**
  - Zero open critical bugs
  - 163+ tests pass
  - CHANGELOG lists all changes
- **Pre-mortem:**
  - Scope creep from feedback → only crash fixes and UX confusion, feature requests go to backlog
  - Regressions → CI must catch everything

---

## Summary and Dependencies

```
PHASE 3A: GitHub + CI         <-- FIRST (everything else depends on this)
  ├── 3A.1 Public repo + README
  ├── 3A.2 GitHub Actions CI
  └── 3A.3 Pre-commit

PHASE 3B: Public deploy       <-- right after 3A (app must be testable)
  └── 3B.1 Streamlit Cloud

PHASE 3C: Italian incentives  <-- differentiating feature
  ├── 3C.1 White Certificates
  └── 3C.2 Transizione 5.0 (depends on 3C.1)

PHASE 3D: Export/Persistence  <-- independent
  ├── 3D.1 Excel export
  ├── 3D.2 Save/Load JSON
  └── 3D.3 Import CSV/Excel (depends on 3D.1)

PHASE 3E: Sensitivity         <-- independent
  ├── 3E.1 Price sensitivity
  └── 3E.2 Tornado chart (depends on 3E.1)

PHASE 3F: Robustness          <-- independent
  ├── 3F.1 UI error handling
  └── 3F.2 Integration test

PHASE 4A: Documentation       <-- after 3C-3F (stable UI)
  ├── 4A.1 In-app help
  └── 4A.2 Methodology page

PHASE 4B: Beta & Release      <-- after everything
  ├── 4B.1 Beta test
  └── 4B.2 Release v1.0
```

## Recommended execution order

| # | Task | Dependencies |
|---|------|------------|
| 1 | 3A.1 GitHub repo + README | none |
| 2 | 3A.2 GitHub Actions CI | 3A.1 |
| 3 | 3A.3 Pre-commit | 3A.2 |
| 4 | 3B.1 Streamlit Cloud deploy | 3A.1 |
| 5 | ~~3F.1 UI error handling~~ ✅ | none |
| 6 | ~~3F.2 Integration test~~ ✅ | none |
| 7 | ~~3C.1 White Certificates~~ ✅ | none |
| 8 | ~~3C.2 Generic CAPEX incentive~~ ✅ | 3C.1 |
| 9 | ~~3D.1 Excel export~~ ✅ | none |
| 10 | ~~3D.2 Save/Load JSON~~ ✅ | none |
| 11 | ~~3D.3 Import CSV/Excel~~ ✅ | 3D.1 |
| 12 | 3E.1 Price sensitivity | none |
| 13 | 3E.2 Tornado chart | 3E.1 |
| 14 | 4A.1 In-app help | 3C-3F |
| 15 | 4A.2 Methodology page | none |
| 16 | 4B.1 Beta test | all |
| 17 | 4B.2 Release v1.0 | 4B.1 |

## Features excluded from v1.0 (backlog v2.0)

- **User authentication** — open source, not needed
- **Persistent database** — local JSON is sufficient
- **Multi-language** (EN/ES/FR) — English for now
- **REST API** — no immediate use case
- **Benchmark database** — requires data we don't have
- **Docker** — Streamlit Cloud is enough for v1.0, Docker in v2.0 if self-hosting is needed
- **Side-by-side scenario comparison** — deferred, save/load covers the basic need

---

*Last updated: 2026-03-09*
