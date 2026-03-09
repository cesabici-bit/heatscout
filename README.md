# HeatScout

**Screening gratuito per il recupero di calore industriale.**

Inserisci i flussi termici di scarto del tuo impianto → ottieni in 5 minuti le tecnologie applicabili, i costi stimati e il tempo di rientro dell'investimento.

<!-- TODO: aggiungere screenshot dell'UI con esempio fonderia -->
<!-- ![HeatScout Screenshot](docs/screenshot.png) -->

<!-- TODO: aggiungere link demo live dopo deploy su Streamlit Cloud -->
<!-- [**Prova la demo live →**](https://heatscout.streamlit.app) -->

[![CI](https://github.com/cesabici-bit/heatscout/actions/workflows/ci.yml/badge.svg)](https://github.com/cesabici-bit/heatscout/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## Cosa fa

| Step | Descrizione |
|------|-------------|
| **1. Input** | Definisci i flussi termici: fluido, temperature, portata, ore di funzionamento |
| **2. Analisi** | Calcola potenza termica (kW), energia annua (MWh), exergia, costo dello spreco |
| **3. Bilancio** | Diagramma Sankey interattivo del bilancio energetico |
| **4. Tecnologie** | Raccomanda tra 9 tecnologie di recupero (scambiatori, pompe di calore, ORC, ...) |
| **5. Economia** | Stima CAPEX (±30%), payback, NPV, IRR per ogni tecnologia |
| **6. Report** | Genera report PDF professionale + export Excel |

## A chi serve

- **Energy manager** che vogliono valutare il recupero calore nel proprio impianto
- **ESCo e consulenti energetici** che fanno audit industriali (D.lgs 102/2014)
- **Studenti e ricercatori** di ingegneria energetica
- Chiunque abbia calore di scarto e si chieda: *"vale la pena recuperarlo?"*

## Quick Start

```bash
# Installa
pip install -e ".[dev]"

# Avvia
streamlit run heatscout/web/app.py
```

L'app si apre su `http://localhost:8501`. Seleziona un esempio precaricato dalla sidebar per iniziare.

## 10 Esempi industriali inclusi

Fonderia · Caseificio · Ceramica · Vetreria · Cartiera · Birrificio · Chimica · Tessile · Data Center · Complesso multi-stream

Ogni esempio ha stream realistici con temperature, portate e ore di funzionamento tipiche del settore.

## Test

```bash
pytest tests/ -v
```

163 test su 5 livelli:

1. **Unit test** — validazione funzionale di ogni modulo
2. **Sanity check fisici** — cp vs valori tabulati (ASHRAE, Perry's), leggi termodinamica
3. **Property-based** (Hypothesis) — invarianti verificate su input random
4. **Snapshot golden** — anti-regressione sui 10 esempi (83 raccomandazioni)
5. **Validazione reale** — confronto con dati misurati da impianti reali (DOE, ETEKINA H2020)

## Stack

| Componente | Tecnologia |
|------------|-----------|
| Proprietà fluidi | [CoolProp](http://www.coolprop.org/) + correlazioni custom |
| Grafici | [Plotly](https://plotly.com/) (Sankey, bar chart, cashflow) |
| UI | [Streamlit](https://streamlit.io/) |
| PDF | [ReportLab](https://www.reportlab.com/) |
| Economia | [numpy-financial](https://numpy.org/numpy-financial/) (NPV, IRR) |

## Assunzioni e limitazioni

- Le correlazioni CAPEX hanno incertezza **±30%** (fonti: Thekdi, ACEEE, IEA)
- I risparmi stimati hanno incertezza **±15%**
- I modelli di efficienza sono di primo livello (correlazioni semplificate)
- Lo strumento è pensato per **screening iniziale**, non sostituisce uno studio di fattibilità ingegneristico

## Contribuire

Vedi [CONTRIBUTING.md](CONTRIBUTING.md) per le linee guida.

## Licenza

[MIT](LICENSE)
