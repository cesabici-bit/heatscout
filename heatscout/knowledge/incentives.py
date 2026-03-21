"""Incentive calculations for industrial heat recovery.

Module 1: White Certificates (TEE) — Italian incentive
Module 2: Generic CAPEX reduction — any international incentive
  (tax credit, grant, subsidy: IRA §48C, UK IETF, Transizione 5.0, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Regulatory constants ---

# Conversion: 1 TEP = 11.628 MWh → 1 MWh = 0.08600 TEP
# Source: ARERA resolution EEN 3/08
TEP_PER_MWH_THERMAL: float = 0.086

# Useful life for heat recovery (DM MASE 2025, Annex 2)
TEE_VITA_UTILE_ANNI: int = 7

# K coefficient (DM 2017+, replaces tau)
# First half of useful life: K = 1.2, second half: K = 0.8
# For 7 years: first 3 years K=1.2, last 4 years K=0.8
# (Weighted total = (3*1.2 + 4*0.8)/7 = 1.017 ≈ 1.0, neutral over full life)
TEE_K_PRIMA_META: float = 1.2
TEE_K_SECONDA_META: float = 0.8

# Minimum threshold for metered projects [TEP/year]
TEE_SOGLIA_MINIMA_TEP: float = 10.0

# Indicative TEE price [€/TEE] — GME market average Feb 2026
# Note: value subject to market variations
TEE_PREZZO_DEFAULT: float = 250.0

# Reference boiler efficiency (natural gas)
# Used to convert recovered thermal energy to saved fuel
ETA_CALDAIA_RIFERIMENTO: float = 0.90

# Last regulatory update date
TEE_DATA_AGGIORNAMENTO: str = "2026-03"


@dataclass
class TEEResult:
    """White Certificates calculation result for a heat recovery project."""

    # Input
    E_recovered_MWh_anno: float  # Recovered thermal energy [MWh/year]
    eta_riferimento: float  # Replaced generation efficiency

    # TEP and TEE
    tep_risparmiati_anno: float  # TEP saved per year [TEP/year]
    sopra_soglia: bool  # True if >= 10 TEP/year (eligible)

    # Incentive cashflow per year (7 years, with K coefficient)
    tee_per_anno: list[float]  # TEE earned per year
    ricavo_per_anno: list[float]  # € revenue per year
    ricavo_totale: float  # Total revenue over useful life [€]
    ricavo_medio_anno: float  # Annual average [€/year]

    # Parameters used
    prezzo_tee: float  # €/TEE used in calculation
    vita_utile: int  # Incentive years


def calc_tee(
    E_recovered_MWh_anno: float,
    prezzo_tee: float = TEE_PREZZO_DEFAULT,
    eta_riferimento: float = ETA_CALDAIA_RIFERIMENTO,
) -> TEEResult:
    """Calculate White Certificates for a heat recovery project.

    Args:
        E_recovered_MWh_anno: Recovered thermal energy [MWh/year]
        prezzo_tee: TEE market price [€/TEE]
        eta_riferimento: Reference boiler efficiency (default 0.90)

    Returns:
        TEEResult with annual detail and totals.

    Primary energy savings account for the replaced boiler efficiency:
    fuel is saved, not just heat.

    Source: DM MASE 21/07/2025, art. 6-7
    """
    assert E_recovered_MWh_anno >= 0, f"Negative recovered energy: {E_recovered_MWh_anno}"
    assert 0.5 <= eta_riferimento <= 1.0, f"Reference efficiency out of range: {eta_riferimento}"
    assert prezzo_tee > 0, f"Invalid TEE price: {prezzo_tee}"

    # Conversion: thermal energy → saved primary energy → TEP
    # TEP = (MWh_th / eta_boiler) × 0.086
    tep_anno = (E_recovered_MWh_anno / eta_riferimento) * TEP_PER_MWH_THERMAL

    sopra_soglia = tep_anno >= TEE_SOGLIA_MINIMA_TEP

    # Annual TEE calculation with K coefficient
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


# ── Module 2: Generic CAPEX reduction ───────────────────────────────────────
# Covers any incentive that reduces investment cost:
# - Tax credit (IRA §48C USA, Transizione 5.0 Italy, ...)
# - Grant / subsidies (UK IETF, EU Innovation Fund, ...)
# - Enhanced tax deductions (Iperammortamento Italy 2026, ...)


@dataclass
class CapexIncentiveResult:
    """Generic CAPEX incentive calculation result."""

    capex_lordo: float  # Original CAPEX [€]
    riduzione_pct: float  # % reduction applied
    riduzione_EUR: float  # Reduction amount [€]
    capex_netto: float  # CAPEX after incentive [€]
    nome_incentivo: str  # Incentive name (free text)


def calc_capex_incentive(
    capex: float,
    riduzione_pct: float,
    nome_incentivo: str = "Tax credit / Grant",
) -> CapexIncentiveResult:
    """Calculate CAPEX reduction from a generic incentive.

    Works for any incentive program that reduces investment cost:
    tax credit, grant, subsidy, enhanced tax deductions.

    Args:
        capex: Original CAPEX (total investment) [€]
        riduzione_pct: Reduction percentage [0-100]
        nome_incentivo: Descriptive incentive name

    Returns:
        CapexIncentiveResult with net CAPEX.
    """
    assert capex >= 0, f"Negative CAPEX: {capex}"
    assert 0 <= riduzione_pct <= 100, f"Reduction % out of range [0-100]: {riduzione_pct}"

    riduzione = capex * riduzione_pct / 100
    netto = capex - riduzione

    return CapexIncentiveResult(
        capex_lordo=round(capex, 2),
        riduzione_pct=riduzione_pct,
        riduzione_EUR=round(riduzione, 2),
        capex_netto=round(netto, 2),
        nome_incentivo=nome_incentivo,
    )
