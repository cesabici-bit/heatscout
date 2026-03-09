# Contributing to HeatScout

Grazie per il tuo interesse nel contribuire a HeatScout!

## Come contribuire

### Segnalare bug o proporre feature
- Apri una [Issue](../../issues) descrivendo il problema o la proposta
- Includi: cosa ti aspettavi, cosa è successo, come riprodurre

### Inviare codice
1. Fork del repository
2. Crea un branch (`git checkout -b feature/nome-feature`)
3. Scrivi test per le modifiche
4. Verifica che tutti i test passino: `pytest tests/ -v`
5. Commit e push
6. Apri una Pull Request

### Convenzioni
- **Codice**: Python 3.10+, dataclass per modelli, unità SI internamente
- **Test**: ogni nuova funzionalità deve avere test (unit + sanity check dove applicabile)
- **Commit**: messaggi chiari e concisi in inglese
- **Documentazione**: docstring Google-style sulle funzioni pubbliche

### Setup locale

```bash
git clone https://github.com/YOUR_USERNAME/heatscout.git
cd heatscout
pip install -e ".[dev]"
pytest tests/ -v
streamlit run heatscout/web/app.py
```

## Architettura test (5 livelli)

1. **Unit test** — ogni funzione fa ciò che deve
2. **Sanity check fisici** — cp, termodinamica, exergia vs valori tabulati
3. **Property-based** (Hypothesis) — invarianti su input random
4. **Snapshot golden** — anti-regressione sui 10 esempi
5. **Validazione reale** — confronto con dati misurati da impianti reali

Ogni PR deve passare tutti e 5 i livelli.
