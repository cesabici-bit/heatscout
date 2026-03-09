# HeatScout — CLAUDE.md

## Stack
- Python 3.10+, CoolProp, Plotly, Streamlit, ReportLab, numpy-financial, pandas
- Build: setuptools (pyproject.toml)
- Test: pytest + pytest-cov

## Comandi
```bash
# Run app
streamlit run heatscout/web/app.py

# Test (89 test attuali)
pytest tests/ -v

# Test con coverage
pytest tests/ --cov=heatscout --cov-report=term-missing

# Install dev
pip install -e ".[dev]"
```

## Architettura
```
heatscout/
  core/           # Logica di dominio
    stream.py           # HeatStream dataclass, calcolo potenza/energia/exergia
    stream_analyzer.py  # Analisi aggregata di stream multipli
    heat_balance.py     # Bilancio termico impianto
    fluid_properties.py # Wrapper CoolProp + fluidi custom (fumi, olio diatermico)
    technology_selector.py  # Selezione tecnologie di recupero
    economics.py        # CAPEX, payback, NPV, IRR
    examples.py         # 10 esempi industriali precaricati
    scenario_comparison.py  # Confronto scenari
  knowledge/      # Database e modelli
    tech_database.py      # DB tecnologie recupero calore
    efficiency_models.py  # Modelli efficienza semplificati
    cost_correlations.py  # Correlazioni CAPEX (+/-30% incertezza)
  plotting/       # Visualizzazioni
    sankey.py             # Diagramma Sankey (Plotly)
    comparison_chart.py   # Grafici confronto tecnologie
  report/         # Output
    executive_summary.py  # Summary testuale
    pdf_generator.py      # Report PDF (ReportLab)
  web/
    app.py              # UI Streamlit (entry point)
tests/            # 89 test inclusi sanity check fisici
```

## Convenzioni codice
- Dataclass per modelli dati (HeatStream, etc.)
- Unita SI internamente (W, K, kg/s, J), conversione solo in UI
- Fluidi: CoolProp per fluidi standard, correlazioni polinomiali per custom
- Funzioni pure dove possibile, side-effect solo in web/ e report/

## Vincoli fisici (sanity check)
- cp acqua ~4186 J/(kg*K), verificato contro CoolProp
- Primo e secondo principio termodinamica rispettati
- Exergia <= Energia sempre
- Efficienza tecnologie: 0 < eta < 1

## Incertezze dichiarate
- CAPEX: +/-30%
- Risparmi stimati: +/-15%
- Modelli efficienza: primo livello (non sostitutivi di studio ingegneristico)

## Test architecture (4 livelli)
1. **Unit test** (test_stream, test_economics, etc.) — baseline funzionale
2. **Sanity check fisici** (test_physics_sanity) — cp, termodinamica, exergia
3. **Property-based** (test_properties) — Hypothesis, invarianti su input random
4. **Snapshot golden** (test_snapshot_examples) — anti-regressione sui 10 esempi
- Golden file: tests/snapshots/golden_examples.json
- Per aggiornare snapshot: python tests/update_snapshots.py (richiede review umana)
5. **Validazione reale** (test_validation_real) — confronto con dati misurati da impianti reali
- Fonti: DOE Better Buildings, ETEKINA H2020, CORDIS, ScienceDirect, L&L Engineering
- Dati in: tests/validation_data/real_case_studies.json
- Tolleranze: potenza +/-20%, payback +/-50%, savings +/-50%
- Totale: 168 test
6. **Fail-fast assertions** nel codice di produzione (fluid_properties, stream_analyzer, economics)
- Show-your-work: calc_thermal_power(stream, detailed=True) ritorna intermedi verificabili

## Checkpoint forzati
- Dopo ogni subtask: elencare cosa e' cambiato + evidenza pytest
- NON procedere al subtask successivo senza ok dell'utente
- Pre-mortem obbligatorio prima di ogni implementazione

## Stato progetto
- Fase 1+2 COMPLETE: core engine, 10 esempi, UI, PDF report, 163 test
- Fase 3-4: roadmap completa in ROADMAP.md (17 task, da CI/CD a Release v1.0)
- 3A.1 DONE: GitHub pubblico https://github.com/cesabici-bit/heatscout
- 3A.2 DONE: GitHub Actions CI (163 test, verde)
- 3B.1 DONE: Deploy live https://heatscout.streamlit.app
- 3F.1 DONE: Error handling UI (5 scenari errore user-friendly, catch-all con link GitHub)
- 3F.2 DONE: Integration test e2e (5 test: workflow, fonderia, multi-stream, 1kW, 800°C)
- 3C.1 DONE: Certificati Bianchi TEE (incentives.py, confronto con/senza incentivi in UI)
- Totale: 186 test
- Prossimo task: 3C.2 (Transizione 5.0)

## Gotcha
- CoolProp puo' essere lento alla prima chiamata (caricamento tabelle)
- kaleido necessario per export immagini Plotly (usato nei PDF)
- Streamlit: ogni interazione utente ri-esegue lo script, usare st.session_state
- I fluidi custom (fumi, olio) NON usano CoolProp, hanno correlazioni separate
