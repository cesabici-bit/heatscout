# HeatScout v1.0 — Release Notes

**Free screening tool for industrial waste heat recovery.**

Live demo: https://heatscout.streamlit.app

## Highlights

- **8 recovery technologies** analyzed automatically based on your stream data
- **10 preloaded industrial examples** (foundry, dairy, ceramics, glass, paper, brewery, chemical, textile, data center, multi-stream)
- **Full economic analysis**: CAPEX (±30%), payback, NPV, IRR
- **Sensitivity analysis**: energy price sweep + tornado chart on 4 parameters
- **Incentive support**: generic CAPEX reduction (any country) + Italian White Certificates (TEE)
- **Export everywhere**: PDF report, Excel (3 sheets), JSON save/load, CSV/Excel import
- **249 automated tests** including validation against real plant data

## Core Engine

- Thermal power, annual energy, and exergy calculation for any fluid
- CoolProp for standard fluids + custom correlations for flue gas and thermal oil
- Interactive Sankey diagram of the energy balance
- Temperature classification (high >250°C, medium 80-250°C, low <80°C)

## Economics

- CAPEX from published correlations (Thekdi/ACEEE, IEA, Quoilin et al.)
- All parameters user-editable: energy price, discount rate (0-25%), analysis horizon (3-30yr)
- Advanced settings: OPEX multiplier, installation cost multiplier
- Cumulative discounted cashflow chart

## Sensitivity Analysis

- Energy price sweep ±50% with payback and NPV charts
- Tornado chart: ±20% one-at-a-time on energy price, CAPEX, operating hours, efficiency
- Parameters sorted by NPV impact

## Import / Export

- PDF report with executive summary, Sankey, and recommendations
- Excel export (3 sheets: Streams, Technologies, Economics + incentives)
- JSON save/load (full round-trip of all parameters)
- CSV/Excel stream import with flexible column aliases (EN/IT)

## Quality & Documentation

- 249 tests: unit, physics sanity, property-based (Hypothesis), snapshot golden, real validation
- Pre-commit hooks: ruff lint + format
- GitHub Actions CI (lint + tests)
- In-app methodology section with all formulas, sources, and bibliography
- Tooltips on every input field
- Screening-level disclaimer visible before economic results

## Known Limitations

- CAPEX: ±30% uncertainty (screening level)
- Savings: ±15% uncertainty
- Efficiency models: first-order simplified correlations
- Not a substitute for detailed engineering feasibility study

## Tech Stack

Python 3.10+ · Streamlit · CoolProp · Plotly · ReportLab · numpy-financial · pandas · openpyxl
