"""Calcolo incentivi per recupero calore industriale.

Modulo 1: Certificati Bianchi (TEE) — incentivo italiano
Modulo 2: Riduzione CAPEX generica — qualsiasi incentivo internazionale
  (tax credit, grant, sussidio: IRA §48C, UK IETF, Transizione 5.0, ecc.)
"""

from __future__ import annotations

from dataclasses import dataclass


# --- Costanti normative ---

# Conversione: 1 TEP = 11.628 MWh → 1 MWh = 0.08600 TEP
# Fonte: ARERA delibera EEN 3/08
TEP_PER_MWH_THERMAL: float = 0.086

# Vita utile per recupero calore (DM MASE 2025, Allegato 2)
TEE_VITA_UTILE_ANNI: int = 7

# Coefficiente K (DM 2017+, sostituisce tau)
# Prima metà vita utile: K = 1.2, seconda metà: K = 0.8
# Per 7 anni: primi 3 anni K=1.2, ultimi 4 anni K=0.8
# (Il totale ponderato = (3*1.2 + 4*0.8)/7 = 1.017 ≈ 1.0, neutro su vita intera)
TEE_K_PRIMA_META: float = 1.2
TEE_K_SECONDA_META: float = 0.8

# Soglia minima progetto a consuntivo [TEP/anno]
TEE_SOGLIA_MINIMA_TEP: float = 10.0

# Prezzo TEE indicativo [€/TEE] — media mercato GME feb 2026
# Nota: valore soggetto a variazioni di mercato
TEE_PREZZO_DEFAULT: float = 250.0

# Rendimento caldaia di riferimento (gas naturale)
# Usato per convertire energia termica recuperata in combustibile risparmiato
ETA_CALDAIA_RIFERIMENTO: float = 0.90

# Data ultimo aggiornamento normativa
TEE_DATA_AGGIORNAMENTO: str = "2026-03"


@dataclass
class TEEResult:
    """Risultato del calcolo Certificati Bianchi per un progetto di recupero calore."""

    # Input
    E_recovered_MWh_anno: float  # Energia termica recuperata [MWh/anno]
    eta_riferimento: float  # Rendimento generazione sostituita

    # TEP e TEE
    tep_risparmiati_anno: float  # TEP risparmiati per anno [TEP/anno]
    sopra_soglia: bool  # True se >= 10 TEP/anno (ammissibile)

    # Cashflow incentivo per anno (7 anni, con coefficiente K)
    tee_per_anno: list[float]  # TEE ottenuti per anno
    ricavo_per_anno: list[float]  # € ricavo per anno
    ricavo_totale: float  # Somma ricavi su vita utile [€]
    ricavo_medio_anno: float  # Media annua [€/anno]

    # Parametri usati
    prezzo_tee: float  # €/TEE usato nel calcolo
    vita_utile: int  # Anni di incentivo


def calc_tee(
    E_recovered_MWh_anno: float,
    prezzo_tee: float = TEE_PREZZO_DEFAULT,
    eta_riferimento: float = ETA_CALDAIA_RIFERIMENTO,
) -> TEEResult:
    """Calcola i Certificati Bianchi per un progetto di recupero calore.

    Args:
        E_recovered_MWh_anno: Energia termica recuperata [MWh/anno]
        prezzo_tee: Prezzo di mercato TEE [€/TEE]
        eta_riferimento: Rendimento caldaia di riferimento (default 0.90)

    Returns:
        TEEResult con dettaglio annuale e totale.

    Il risparmio in energia primaria tiene conto del rendimento della
    caldaia sostituita: si risparmia il combustibile, non solo il calore.

    Fonte: DM MASE 21/07/2025, art. 6-7
    """
    assert E_recovered_MWh_anno >= 0, (
        f"Energia recuperata negativa: {E_recovered_MWh_anno}"
    )
    assert 0.5 <= eta_riferimento <= 1.0, (
        f"Rendimento riferimento fuori range: {eta_riferimento}"
    )
    assert prezzo_tee > 0, f"Prezzo TEE non valido: {prezzo_tee}"

    # Conversione energia termica → energia primaria risparmiata → TEP
    # TEP = (MWh_th / eta_caldaia) × 0.086
    tep_anno = (E_recovered_MWh_anno / eta_riferimento) * TEP_PER_MWH_THERMAL

    sopra_soglia = tep_anno >= TEE_SOGLIA_MINIMA_TEP

    # Calcolo TEE annuali con coefficiente K
    vita = TEE_VITA_UTILE_ANNI
    meta = vita // 2  # 3 per vita=7

    tee_per_anno: list[float] = []
    ricavo_per_anno: list[float] = []

    for anno in range(1, vita + 1):
        k = TEE_K_PRIMA_META if anno <= meta else TEE_K_SECONDA_META
        tee = tep_anno * k
        ricavo = tee * prezzo_tee
        tee_per_anno.append(round(tee, 2))
        ricavo_per_anno.append(round(ricavo, 2))

    ricavo_totale = sum(ricavo_per_anno)
    ricavo_medio = ricavo_totale / vita

    return TEEResult(
        E_recovered_MWh_anno=E_recovered_MWh_anno,
        eta_riferimento=eta_riferimento,
        tep_risparmiati_anno=round(tep_anno, 2),
        sopra_soglia=sopra_soglia,
        tee_per_anno=tee_per_anno,
        ricavo_per_anno=ricavo_per_anno,
        ricavo_totale=round(ricavo_totale, 2),
        ricavo_medio_anno=round(ricavo_medio, 2),
        prezzo_tee=prezzo_tee,
        vita_utile=vita,
    )


# ── Modulo 2: Riduzione CAPEX generica ──────────────────────────────────────
# Copre qualsiasi incentivo che riduca il costo di investimento:
# - Tax credit (IRA §48C USA, Transizione 5.0 Italia, ...)
# - Grant / sussidi (UK IETF, EU Innovation Fund, ...)
# - Deduzioni fiscali maggiorate (Iperammortamento Italia 2026, ...)


@dataclass
class CapexIncentiveResult:
    """Risultato del calcolo incentivo generico su CAPEX."""

    capex_lordo: float  # CAPEX originale [€]
    riduzione_pct: float  # % di riduzione applicata
    riduzione_EUR: float  # Importo riduzione [€]
    capex_netto: float  # CAPEX dopo incentivo [€]
    nome_incentivo: str  # Nome incentivo (libero)


def calc_capex_incentive(
    capex: float,
    riduzione_pct: float,
    nome_incentivo: str = "Tax credit / Grant",
) -> CapexIncentiveResult:
    """Calcola la riduzione CAPEX da un incentivo generico.

    Funziona per qualsiasi programma di incentivi che riduca il costo
    di investimento: tax credit, grant, sussidi, deduzioni fiscali.

    Args:
        capex: CAPEX originale (investimento totale) [€]
        riduzione_pct: Percentuale di riduzione [0-100]
        nome_incentivo: Nome descrittivo dell'incentivo

    Returns:
        CapexIncentiveResult con CAPEX netto
    """
    assert capex >= 0, f"CAPEX negativo: {capex}"
    assert 0 <= riduzione_pct <= 100, (
        f"Riduzione % fuori range [0-100]: {riduzione_pct}"
    )

    riduzione = capex * riduzione_pct / 100
    netto = capex - riduzione

    return CapexIncentiveResult(
        capex_lordo=round(capex, 2),
        riduzione_pct=riduzione_pct,
        riduzione_EUR=round(riduzione, 2),
        capex_netto=round(netto, 2),
        nome_incentivo=nome_incentivo,
    )
