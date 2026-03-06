# HeatScout — Analisi Recupero Calore Industriale

Tool web per analizzare il potenziale di recupero calore in impianti industriali.

## Cosa fa

1. **Input**: inserisci i flussi termici di scarto del tuo impianto (temperatura, portata, fluido)
2. **Analisi**: calcola potenza termica, energia annua, exergia
3. **Sankey**: visualizza il bilancio energetico con diagramma interattivo
4. **Tecnologie**: raccomanda le migliori tecnologie di recupero (scambiatori, pompe di calore, ORC)
5. **Economia**: stima CAPEX, payback, NPV, IRR per ogni tecnologia
6. **Report PDF**: genera un report professionale scaricabile

## Quick Start

```bash
pip install -e ".[dev]"
streamlit run heatscout/web/app.py
```

## 10 Esempi precaricati

Fonderia, Caseificio, Ceramica, Vetreria, Cartiera, Birrificio, Chimica, Tessile, Data Center, Complesso multi-stream.

## Test

```bash
pytest tests/ -v
```

89 test inclusi check di sanita' fisica (cp vs valori tabulati, leggi termodinamica).

## Assunzioni e limitazioni

- Le correlazioni di costo CAPEX hanno incertezza +/-30%
- I risparmi stimati hanno incertezza +/-15%
- I modelli di efficienza sono semplificati (primo livello)
- I fluidi custom (fumi, olio diatermico) usano correlazioni polinomiali
- Lo strumento NON sostituisce uno studio di fattibilita' ingegneristico

## Stack tecnologico

- **CoolProp**: proprieta' termofisiche dei fluidi
- **Plotly**: grafici interattivi e Sankey
- **Streamlit**: interfaccia web
- **ReportLab**: generazione PDF
- **numpy-financial**: calcoli NPV/IRR
