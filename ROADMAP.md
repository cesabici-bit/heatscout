# HeatScout — Roadmap Completa (Fase 3-4)

**Stato attuale:** Fase 1+2 COMPLETE + 3A/3B/3F/3C.1 DONE. 186 test, core engine stabile, UI funzionante, PDF report, TEE incentivi.
**Modello:** Open source, gratuito. Obiettivo: visibilità e credibilità.
**Data creazione:** 2026-03-09

---

## Legenda

Ogni task ha:
- **Input:** cosa deve esistere prima di iniziare
- **Output:** cosa esiste dopo il completamento
- **Pass/Fail:** criterio oggettivo e verificabile
- **Pre-mortem:** come può fallire e come mitigare

---

## FASE 3A — GitHub Pubblico & CI

> Il repo è il biglietto da visita. Deve fare buona impressione dal primo secondo.

### Task 3A.1: Repository GitHub pubblico

- **Input:** Progetto locale con 163 test passing, pyproject.toml
- **Output:**
  - Repo GitHub pubblico con LICENSE (MIT o Apache 2.0)
  - README.md riscritto per GitHub: hero description, screenshot/GIF dell'UI, quick start, badge CI, link demo live
  - `.gitignore` completo (no __pycache__, .egg-info, .env, IDE files)
  - CONTRIBUTING.md base (come contribuire, come aprire issue)
- **Pass/Fail:**
  - Un visitatore capisce cosa fa HeatScout in 10 secondi leggendo il README
  - Screenshot dell'UI visibile sopra il fold
  - Licenza open source presente
  - Nessun file inutile nel repo (no cache, no build artifacts)
- **Pre-mortem:**
  - README troppo lungo/tecnico → max 100 righe, visuale, non murale di testo
  - Screenshot datato → generarlo dall'app attuale con esempio "fonderia"
  - Credenziali/path locali nel codice → grep per "cesab", "C:\Users", path assoluti prima del push

### Task 3A.2: GitHub Actions CI

- **Input:** Repo GitHub pubblico (Task 3A.1)
- **Output:** `.github/workflows/ci.yml` che esegue `pytest tests/ -v` su ogni push/PR
- **Pass/Fail:** Badge CI verde nel README. Un test rotto blocca il merge.
- **Pre-mortem:**
  - CoolProp wheel non disponibile per runner GitHub → testare `pip install CoolProp` su ubuntu-latest, fallback a conda se fallisce
  - kaleido su Linux headless → skippare test PDF con `pytest.mark` se necessario
  - CI lenta (CoolProp pesante) → cache pip dependencies

### Task 3A.3: Pre-commit hooks (linting) ✅

- **Input:** CI verde (Task 3A.2)
- **Output:** `.pre-commit-config.yaml` con ruff (lint + format)
- **Pass/Fail:** `pre-commit run --all-files` passa senza errori
- **Pre-mortem:**
  - Ruff segnala troppi warning → configurare `ruff.toml` con regole progressive, fixare il grosso prima di attivare
  - Rallenta il commit loop → regole minime, no docstring enforcement

---

## FASE 3B — Deploy Pubblico

> L'app deve essere provabile da chiunque con un click, senza installare nulla.

### Task 3B.1: Deploy su Streamlit Community Cloud

- **Input:** Repo GitHub pubblico con app funzionante
- **Output:**
  - App live su URL pubblico (es. heatscout.streamlit.app)
  - Link alla demo nel README
  - `requirements.txt` verificato per Streamlit Cloud (compatibilità dipendenze)
- **Pass/Fail:**
  - URL accessibile da browser senza login
  - Esempio "fonderia" funziona end-to-end (analisi + PDF download)
  - Tempo di caricamento iniziale < 30 secondi
- **Pre-mortem:**
  - CoolProp non installa su Streamlit Cloud → verificare compatibilità, eventualmente `packages.txt` con dipendenze sistema
  - Memoria limitata (1GB su free tier) → verificare che 10 stream non sfori
  - App va in sleep dopo inattività → accettabile per free tier, documentare nel README
  - kaleido per PDF images → potrebbe fallire, avere fallback testuale

---

## FASE 3C — Incentivi Italiani (feature differenziante)

> Nessun tool gratuito calcola l'impatto degli incentivi italiani sul recupero calore. Questo è il differenziatore.

### Task 3C.1: Modulo Certificati Bianchi (TEE)

- **Input:** economics.py con NPV/payback funzionanti, dati dal decreto TEE 2025-2030
- **Output:**
  - Nuovo modulo `knowledge/incentives.py` con calcolo TEE: energia risparmiata (TEP) × valore TEE (€/TEE) × durata incentivo
  - Integrazione in economics.py: NPV e payback ricalcolati CON e SENZA incentivo
  - UI mostra entrambi gli scenari (tabella: "senza incentivi" vs "con Certificati Bianchi")
- **Pass/Fail:**
  - TEP calcolati coerenti con fattori di conversione ARERA
  - NPV con incentivo > NPV senza incentivo (sempre)
  - Payback con incentivo < payback senza incentivo (sempre)
  - Test: `test_incentives.py` con 3+ esempi verificati manualmente
  - Fonti normative citate nel codice e nella UI
- **Pre-mortem:**
  - Decreto TEE 2025-2030 complesso, con categorie e vita utile variabile → semplificare al caso "recupero calore" specifico, non generalizzare
  - Valore TEE variabile nel tempo (mercato GME) → usare valore medio recente con nota "valore indicativo"
  - Normativa cambia → dichiarare data ultimo aggiornamento nella UI

### Task 3C.2: Modulo Transizione 5.0

- **Input:** Task 3C.1 completato (struttura incentives.py già esistente)
- **Output:**
  - Calcolo tax credit Transizione 5.0: % credito d'imposta su CAPEX (scaglioni per dimensione investimento)
  - Aggiunta alla tabella comparativa: terza colonna "con Transizione 5.0"
- **Pass/Fail:**
  - Aliquote corrette per scaglione (verificare vs MIMIT)
  - CAPEX effettivo ridotto del credito d'imposta
  - Test: verifica che CAPEX netto < CAPEX lordo
- **Pre-mortem:**
  - Transizione 5.0 ha requisiti di ammissibilità complessi (riduzione consumo ≥3%) → semplificare: mostrare il beneficio SE ammissibile, con nota sui requisiti
  - Fondi esauriti / scadenza → mostrare data validità e nota "verificare disponibilità"

---

## FASE 3D — Export & Persistenza

> Gli utenti devono poter portare fuori i risultati e salvare il lavoro.

### Task 3D.1: Export Excel dei risultati

- **Input:** Analisi completata in UI
- **Output:** Bottone "Scarica Excel" → .xlsx con 3 fogli: Stream, Tecnologie, Economia (incluso confronto con/senza incentivi)
- **Pass/Fail:**
  - File .xlsx si apre in Excel/LibreOffice senza errori
  - Contiene tutti i dati visibili nelle tabelle UI (stessi numeri, stesse unità)
  - Test: `test_export.py` genera xlsx da esempio "fonderia", verifica colonne e valori
- **Pre-mortem:**
  - openpyxl come nuova dipendenza → aggiungere a pyproject.toml e requirements.txt
  - Formattazione numeri → usare formato internazionale (punto decimale), l'utente può convertire in Excel

### Task 3D.2: Salva/Carica analisi (JSON)

- **Input:** UI funzionante con stream input
- **Output:**
  - Bottone "Salva analisi" → scarica .json con tutti gli input
  - Bottone "Carica analisi" → upload .json ripristina gli input
- **Pass/Fail:**
  - Round-trip: salva → carica → riesegui → stessi risultati (±0.01%)
  - File .json leggibile (indented, nomi campi chiari)
  - Versione schema inclusa (`"version": "1.0"`)
  - Test: `test_persistence.py` round-trip su 3 esempi
- **Pre-mortem:**
  - Schema JSON non documentato → includere campo version per compatibilità futura
  - Fluidi custom non serializzabili → verificare tutti i campi ThermalStream JSON-safe

### Task 3D.3: Import stream da CSV/Excel

- **Input:** Task 3D.1 completato (formato Excel definito)
- **Output:** Upload file in sidebar → popola gli stream nell'UI
- **Pass/Fail:**
  - Upload di un file esportato ricrea gli stessi stream
  - File malformato → errore chiaro, non crash
  - Template scaricabile disponibile
- **Pre-mortem:**
  - Encoding CSV da Excel italiano (Latin-1) → forzare UTF-8 con BOM
  - File enorme → limitare a 50 stream con messaggio chiaro

---

## FASE 3E — Analisi di Sensitività

> Feature che rende il tool serio: "cosa succede se cambiano i parametri?"

### Task 3E.1: Sensitivity su prezzo energia ✅

- **Input:** Analisi economica funzionante, UI con risultati
- **Output:** Nuova sezione UI "Analisi di sensitività" con slider prezzo energia (±50%) e grafico payback vs prezzo
- **Pass/Fail:**
  - Curva monotona decrescente (payback scende quando prezzo sale)
  - Prezzo 0 → payback infinito; prezzo 2x → payback ~dimezzato
  - Test: `test_sensitivity.py` verifica monotonia e casi limite
- **Pre-mortem:**
  - Ricalcolo lento → precalcolare 10-20 punti, non real-time
  - IRR = None per alcuni prezzi → gestire gracefully nel grafico

### Task 3E.2: Tornado chart multi-parametro ✅

- **Input:** Task 3E.1 completato
- **Output:** Tornado chart: variazione NPV al variare ±20% di prezzo energia, CAPEX, ore operative, efficienza
- **Pass/Fail:**
  - Barre ordinate per impatto (parametro più influente in alto)
  - Test: output ha 4+ barre con valori non-zero
- **Pre-mortem:**
  - Troppi parametri → limitare ai 4 più rilevanti
  - Interazioni ignorate → dichiarare assunzione "one-at-a-time" in UI

---

## FASE 3F — Robustezza

> L'app non deve mai crashare davanti a un utente.

### Task 3F.1: Error handling UI

- **Input:** app.py attuale con try/except generici
- **Output:** Messaggi errore user-friendly:
  - Nessuno stream → "Aggiungi almeno uno stream prima di analizzare"
  - Tutti COLD_DEMAND → "Serve almeno uno stream HOT_WASTE"
  - CoolProp fallisce → "Errore calcolo proprietà fluido: [dettaglio]"
  - PDF fallisce → "Errore generazione PDF. Prova Excel."
  - Catch-all → "Errore imprevisto. Segnalalo su GitHub."
- **Pass/Fail:**
  - Nessun traceback Python visibile all'utente MAI
  - Ogni errore mostra `st.error()` in italiano comprensibile
  - Test manuale: provocare ognuno dei 5 errori, verificare messaggio
- **Pre-mortem:**
  - Errori non previsti → catch-all finale con link a GitHub issues

### Task 3F.2: Integration test end-to-end

- **Input:** Tutti i moduli core funzionanti
- **Output:** `test_integration.py` con 5 test:
  1. Workflow completo da stream a summary
  2. Esempio "fonderia" end-to-end
  3. Multi-stream (5 stream)
  4. Edge case: stream 1 kW
  5. Edge case: T = 800°C
- **Pass/Fail:** Tutti passano. Nessuna eccezione non gestita.
- **Pre-mortem:**
  - Test lenti (CoolProp) → accettabile, sono 5
  - Path data/ → usare path relative al package

---

## FASE 4A — Documentazione & Metodologia

> Credibilità = trasparenza. Fonti, limiti, assunzioni tutto visibile.

### Task 4A.1: Help in-app (tooltips)

- **Input:** UI attuale senza help contestuale
- **Output:**
  - Tooltips: T_in/T_out, HOT_WASTE vs COLD_DEMAND, NPV, payback
  - Disclaimer visibile PRIMA dei risultati economici: "Analisi di primo livello, CAPEX ±30%, risparmi ±15%"
  - Expander collassabili "Come interpretare questi risultati"
- **Pass/Fail:**
  - Ogni sezione UI ha almeno un tooltip o info box
  - Disclaimer visibile senza scrollare
- **Pre-mortem:**
  - UI cluttered → expander collassabili, max 2 frasi per tooltip

### Task 4A.2: Pagina Metodologia

- **Input:** Fonti già documentate in cost_correlations.py, efficiency_models.py
- **Output:** Pagina Streamlit "Metodologia" con:
  - Tabella: tecnologia → correlazione CAPEX → fonte → anno
  - Modelli efficienza: formula + fonte
  - Range di validità per ogni tecnologia
  - Case study di validazione (summary)
- **Pass/Fail:**
  - Ogni correlazione ha fonte citata (autore/ente, anno)
  - Range di validità espliciti
- **Pre-mortem:**
  - Troppo accademica → bilanciare rigore e leggibilità
  - Fonti datate → segnalare anno

---

## FASE 4B — Beta & Release

> Validazione con utenti reali, poi tag v1.0.

### Task 4B.1: Beta testing (3-5 utenti)

- **Input:** App live su Streamlit Cloud, documentazione in-app
- **Output:**
  - 3-5 utenti (ingegneri/energy manager) testano con dati reali
  - Feedback strutturato (funziona / confonde / manca)
  - Bug list prioritizzata
- **Pass/Fail:**
  - Almeno 3 utenti completano analisi end-to-end senza assistenza
  - Nessun crash durante il test
  - Feedback raccolto e categorizzato
- **Pre-mortem:**
  - Utenti non disponibili → partire con 1-2 contatti
  - Dati fuori range → limiti documentati in UI
  - Aspettative enterprise → chiarire che è screening tool

### Task 4B.2: Release v1.0

- **Input:** Bug list dal beta test
- **Output:**
  - Bug critici fixati
  - Tag git `v1.0.0`
  - CHANGELOG.md
  - Annuncio (LinkedIn, community energetica, FIRE)
- **Pass/Fail:**
  - Zero bug critici aperti
  - 163+ test passano
  - CHANGELOG elenca tutte le modifiche
- **Pre-mortem:**
  - Scope creep dal feedback → solo crash fix e UX confusion, feature request in backlog
  - Regressioni → CI deve catturare tutto

---

## Riepilogo e Dipendenze

```
FASE 3A: GitHub + CI         ←── PRIMO (tutto il resto dipende da qui)
  ├── 3A.1 Repo pubblico + README
  ├── 3A.2 GitHub Actions CI
  └── 3A.3 Pre-commit

FASE 3B: Deploy pubblico     ←── subito dopo 3A (l'app deve essere provabile)
  └── 3B.1 Streamlit Cloud

FASE 3C: Incentivi italiani  ←── feature differenziante
  ├── 3C.1 Certificati Bianchi
  └── 3C.2 Transizione 5.0 (dipende da 3C.1)

FASE 3D: Export/Persistenza  ←── indipendente
  ├── 3D.1 Export Excel
  ├── 3D.2 Salva/Carica JSON
  └── 3D.3 Import CSV/Excel (dipende da 3D.1)

FASE 3E: Sensitività         ←── indipendente
  ├── 3E.1 Sensitivity prezzo
  └── 3E.2 Tornado chart (dipende da 3E.1)

FASE 3F: Robustezza          ←── indipendente
  ├── 3F.1 Error handling UI
  └── 3F.2 Integration test

FASE 4A: Documentazione      ←── dopo 3C-3F (UI stabile)
  ├── 4A.1 Help in-app
  └── 4A.2 Pagina metodologia

FASE 4B: Beta & Release      ←── dopo tutto
  ├── 4B.1 Beta test
  └── 4B.2 Release v1.0
```

## Ordine di esecuzione consigliato

| # | Task | Dipendenze |
|---|------|------------|
| 1 | 3A.1 Repo GitHub + README | nessuna |
| 2 | 3A.2 GitHub Actions CI | 3A.1 |
| 3 | 3A.3 Pre-commit | 3A.2 |
| 4 | 3B.1 Streamlit Cloud deploy | 3A.1 |
| 5 | ~~3F.1 Error handling UI~~ ✅ | nessuna |
| 6 | ~~3F.2 Integration test~~ ✅ | nessuna |
| 7 | ~~3C.1 Certificati Bianchi~~ ✅ | nessuna |
| 8 | ~~3C.2 Generic CAPEX incentive~~ ✅ | 3C.1 |
| 9 | ~~3D.1 Export Excel~~ ✅ | nessuna |
| 10 | ~~3D.2 Salva/Carica JSON~~ ✅ | nessuna |
| 11 | ~~3D.3 Import CSV/Excel~~ ✅ | 3D.1 |
| 12 | 3E.1 Sensitivity prezzo | nessuna |
| 13 | 3E.2 Tornado chart | 3E.1 |
| 14 | 4A.1 Help in-app | 3C-3F |
| 15 | 4A.2 Pagina metodologia | nessuna |
| 16 | 4B.1 Beta test | tutto |
| 17 | 4B.2 Release v1.0 | 4B.1 |

## Feature escluse da v1.0 (backlog v2.0)

- **Autenticazione utente** — open source, non necessaria
- **Database persistente** — JSON locale sufficiente
- **Multi-lingua** (EN/ES/FR) — italiano per ora
- **API REST** — nessun caso d'uso immediato
- **Benchmark database** — richiede dati che non abbiamo
- **Docker** — Streamlit Cloud basta per v1.0, Docker in v2.0 se serve self-hosting
- **Confronto scenari side-by-side** — rimandata, salva/carica copre il bisogno base

---

*Ultimo aggiornamento: 2026-03-09*
