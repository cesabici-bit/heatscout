# Contributing to HeatScout

Thanks for your interest in contributing!

## Getting Started

```bash
# Clone the repo
git clone https://github.com/cesabici-bit/heatscout.git
cd heatscout

# Install in dev mode
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run the app
streamlit run heatscout/web/app.py

# Run tests
pytest tests/ -v
```

## Development Workflow

1. Create a branch from `master`
2. Make your changes
3. `pre-commit run --all-files` — ruff lint + format must pass
4. `pytest tests/ -v` — all 249 tests must pass
5. Open a pull request

## Code Conventions

- Python 3.10+, type hints where useful
- Dataclasses for data models (not dicts)
- SI units internally (W, K, kg/s, J) — conversion only in UI
- Pure functions where possible, side effects only in `web/` and `report/`
- Fail-fast assertions in production code with descriptive messages
- Ruff for linting (F/E/W/I rules) and formatting

## Test Architecture (5 levels)

1. **Unit tests** — each function does what it should
2. **Physics sanity** — cp vs tabulated values, thermodynamics laws
3. **Property-based** (Hypothesis) — invariants on random inputs
4. **Snapshot golden** — anti-regression on 10 examples
5. **Real validation** — comparison with measured data from real plants

To update golden snapshots: `python tests/update_snapshots.py` (requires human review).

## What to Contribute

- Bug reports → [GitHub Issues](https://github.com/cesabici-bit/heatscout/issues)
- New industrial examples (add to `heatscout/core/examples.py`)
- Improved cost correlations (with published source citation)
- UI/UX improvements
- Documentation improvements

## What NOT to Change Without Discussion

- CAPEX correlation coefficients (need published source)
- Efficiency model formulas (need academic reference)
- Golden snapshot files (require `update_snapshots.py` + review)

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
