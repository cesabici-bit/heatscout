# HeatScout — CLAUDE.md

## Stack
- Python 3.10+, CoolProp, Plotly, Streamlit, ReportLab, numpy-financial, pandas
- Build: setuptools (pyproject.toml)
- Test: pytest + pytest-cov

## Commands
```bash
# Run app
streamlit run heatscout/web/app.py

# Test (89 tests currently)
pytest tests/ -v

# Test with coverage
pytest tests/ --cov=heatscout --cov-report=term-missing

# Install dev
pip install -e ".[dev]"
```

## Architecture
```
heatscout/
  core/           # Domain logic
    stream.py           # HeatStream dataclass, power/energy/exergy calculation
    stream_analyzer.py  # Aggregate analysis of multiple streams
    heat_balance.py     # Factory heat balance
    fluid_properties.py # CoolProp wrapper + custom fluids (flue gas, thermal oil)
    technology_selector.py  # Heat recovery technology selection
    economics.py        # CAPEX, payback, NPV, IRR
    examples.py         # 10 preloaded industrial examples
    scenario_comparison.py  # Scenario comparison
  knowledge/      # Database and models
    tech_database.py      # Heat recovery technology DB
    efficiency_models.py  # Simplified efficiency models
    cost_correlations.py  # CAPEX correlations (+/-30% uncertainty)
  plotting/       # Visualizations
    sankey.py             # Sankey diagram (Plotly)
    comparison_chart.py   # Technology comparison charts
  report/         # Output
    executive_summary.py  # Text summary
    pdf_generator.py      # PDF report (ReportLab)
  web/
    app.py              # Streamlit UI (entry point)
tests/            # 89 tests including physics sanity checks
```

## Code conventions
- Dataclasses for data models (HeatStream, etc.)
- SI units internally (W, K, kg/s, J), conversion only in UI
- Fluids: CoolProp for standard fluids, polynomial correlations for custom
- Pure functions where possible, side-effects only in web/ and report/

## Physics constraints (sanity checks)
- cp water ~4186 J/(kg*K), verified against CoolProp
- First and second law of thermodynamics respected
- Exergy <= Energy always
- Technology efficiency: 0 < eta < 1

## Declared uncertainties
- CAPEX: +/-30%
- Estimated savings: +/-15%
- Efficiency models: first-level (not a substitute for engineering study)

## Test architecture (4 levels)
1. **Unit tests** (test_stream, test_economics, etc.) — functional baseline
2. **Physics sanity checks** (test_physics_sanity) — cp, thermodynamics, exergy
3. **Property-based** (test_properties) — Hypothesis, invariants on random input
4. **Golden snapshot** (test_snapshot_examples) — anti-regression on 10 examples
- Golden file: tests/snapshots/golden_examples.json
- To update snapshot: python tests/update_snapshots.py (requires human review)
5. **Real-world validation** (test_validation_real) — comparison with measured data from real plants
- Sources: DOE Better Buildings, ETEKINA H2020, CORDIS, ScienceDirect, L&L Engineering
- Data in: tests/validation_data/real_case_studies.json
- Tolerances: power +/-20%, payback +/-50%, savings +/-50%
- Total: 168 tests
6. **Fail-fast assertions** in production code (fluid_properties, stream_analyzer, economics)
- Show-your-work: calc_thermal_power(stream, detailed=True) returns verifiable intermediates

## Mandatory checkpoints
- After each subtask: list changes + pytest evidence
- Do NOT proceed to next subtask without user approval
- Mandatory pre-mortem before each implementation

## Project status
- Phase 1+2 COMPLETE: core engine, 10 examples, UI, PDF report, 163 tests
- Phase 3-4: full roadmap in ROADMAP.md (17 tasks, from CI/CD to Release v1.0)
- 3A.1 DONE: Public GitHub https://github.com/cesabici-bit/heatscout
- 3A.2 DONE: GitHub Actions CI (163 tests, green)
- 3B.1 DONE: Live deploy https://heatscout.streamlit.app
- 3F.1 DONE: UI error handling (5 user-friendly error scenarios, catch-all with GitHub link)
- 3F.2 DONE: e2e integration tests (5 tests: workflow, foundry, multi-stream, 1kW, 800°C)
- 3C.1 DONE: White Certificates TEE (incentives.py, with/without incentive comparison in UI)
- 3C.2 DONE: Generic CAPEX incentive (international, any tax credit/grant)
- 3D.1 DONE: Excel export (3 sheets: Streams, Technologies, Economics + incentives)
- 3D.2 DONE: Save/Load analysis JSON (round-trip verified)
- 3D.3 DONE: Import CSV/Excel streams (template + alias columns)
- 3E.1 DONE: Energy price sensitivity (±50% sweep, payback/NPV charts)
- 3E.2 DONE: Tornado chart multi-parameter (±20% on 4 params, sorted by NPV impact)
- DONE: All economic params user-editable (discount rate, horizon, OPEX/install multipliers)
- 3A.3 DONE: Pre-commit hooks (ruff lint + format, .pre-commit-config.yaml)
- 4A.1 DONE: In-app help (tooltips, disclaimer, interpretation guide)
- 4A.2 DONE: Methodology page (efficiency models, CAPEX table, bibliography)
- 4B.1 IN PROGRESS: Beta testing issue #1 created, awaiting user feedback
- Total: 249 tests
- Next task: 4B.2 (Release v1.0, after beta feedback)

## Gotchas
- CoolProp can be slow on first call (loading tables)
- kaleido required for Plotly image export (used in PDFs)
- Streamlit: every user interaction re-runs the script, use st.session_state
- Custom fluids (flue gas, thermal oil) do NOT use CoolProp, they have separate correlations
