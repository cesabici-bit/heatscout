"""Calcolo incentivi italiani per recupero calore industriale.

Modulo 1: Certificati Bianchi (TEE — Titoli di Efficienza Energetica)
Normativa: DM MASE 21/07/2025 (GU n. 211 dell'11/09/2025)
Tipo progetto: Progetto a Consuntivo (PC)
Vita utile recupero calore: 7 anni
Soglia minima: 10 TEP/anno
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
