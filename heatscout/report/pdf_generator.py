"""Generatore report PDF con reportlab."""

from __future__ import annotations

import io
import tempfile
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from heatscout.core.economics import EconomicResult
from heatscout.report.executive_summary import generate_executive_summary


def _styles():
    """Stili personalizzati per il report."""
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(
        "CoverTitle",
        parent=ss["Title"],
        fontSize=28,
        spaceAfter=20,
        textColor=colors.HexColor("#B22222"),
    ))
    ss.add(ParagraphStyle(
        "CoverSubtitle",
        parent=ss["Normal"],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.HexColor("#555555"),
    ))
    ss.add(ParagraphStyle(
        "SectionTitle",
        parent=ss["Heading1"],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor("#B22222"),
    ))
    ss.add(ParagraphStyle(
        "SubSection",
        parent=ss["Heading2"],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#333333"),
    ))
    ss.add(ParagraphStyle(
        "BodyItalic",
        parent=ss["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=colors.HexColor("#777777"),
    ))
    return ss


def _make_table(headers: list[str], rows: list[list], col_widths=None) -> Table:
    """Crea una tabella formattata."""
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B22222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _export_plotly_image(fig, width=600, height=350) -> bytes | None:
    """Esporta una figura Plotly come immagine PNG."""
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        return None


def generate_report(
    summary: dict,
    econ_results: list[EconomicResult],
    sankey_fig=None,
    comparison_figs: dict | None = None,
    energy_price: float = 0.08,
) -> bytes:
    """Genera il report PDF completo.

    Args:
        summary: Output di FactoryHeatBalance.summary()
        econ_results: Lista di EconomicResult
        sankey_fig: Figura Plotly del Sankey (opzionale)
        comparison_figs: Dict di figure Plotly per grafici comparativi
        energy_price: Prezzo energia EUR/kWh

    Returns:
        bytes del file PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    ss = _styles()
    elements = []

    factory_name = summary.get("factory_name", "Impianto")
    today = date.today().strftime("%d/%m/%Y")

    # ── COPERTINA ────────────────────────────────────────────────────────
    elements.append(Spacer(1, 4 * cm))
    elements.append(Paragraph("HeatScout", ss["CoverTitle"]))
    elements.append(Paragraph(
        "Analisi Recupero Calore Industriale", ss["CoverSubtitle"]
    ))
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph(f"<b>Impianto:</b> {factory_name}", ss["Normal"]))
    elements.append(Paragraph(f"<b>Data:</b> {today}", ss["Normal"]))
    elements.append(Spacer(1, 2 * cm))
    elements.append(Paragraph(
        "Questo report e' stato generato automaticamente dal tool HeatScout. "
        "I risultati sono stime di primo livello e richiedono validazione "
        "ingegneristica prima di procedere con investimenti.",
        ss["BodyItalic"],
    ))
    elements.append(PageBreak())

    # ── EXECUTIVE SUMMARY ────────────────────────────────────────────────
    elements.append(Paragraph("Executive Summary", ss["SectionTitle"]))
    exec_text = generate_executive_summary(summary, econ_results, energy_price)
    for line in exec_text.split("\n"):
        if line.startswith("=") or line.startswith("-"):
            continue
        if line.strip():
            elements.append(Paragraph(line, ss["Normal"]))
        else:
            elements.append(Spacer(1, 4 * mm))
    elements.append(PageBreak())

    # ── SEZIONE 1: STREAM TERMICI ────────────────────────────────────────
    elements.append(Paragraph("1. Stream Termici Analizzati", ss["SectionTitle"]))
    elements.append(Paragraph(
        f"Sono stati analizzati {summary['n_streams']} flussi termici, "
        f"di cui {summary['n_hot_waste']} di scarto.",
        ss["Normal"],
    ))
    elements.append(Spacer(1, 4 * mm))

    stream_headers = ["Nome", "Fluido", "T_in (°C)", "T_out (°C)", "Q (kW)", "E (MWh/a)", "Classe"]
    stream_rows = []
    for r in summary["stream_results"]:
        stream_rows.append([
            r["name"],
            r["fluid_type"],
            f"{r['T_in']:.0f}",
            f"{r['T_out']:.0f}",
            f"{r['Q_kW']:,.1f}",
            f"{r['E_MWh_anno']:,.1f}",
            r["T_class"].capitalize(),
        ])
    elements.append(_make_table(stream_headers, stream_rows))
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph(
        f"<b>Potenza termica di scarto totale:</b> {summary['total_waste_kW']:,.1f} kW",
        ss["Normal"],
    ))
    elements.append(Paragraph(
        f"<b>Energia di scarto annua:</b> {summary['total_waste_MWh_anno']:,.1f} MWh/anno",
        ss["Normal"],
    ))

    # ── SEZIONE 2: BILANCIO ENERGETICO (Sankey) ─────────────────────────
    elements.append(PageBreak())
    elements.append(Paragraph("2. Bilancio Energetico", ss["SectionTitle"]))

    if sankey_fig:
        img_bytes = _export_plotly_image(sankey_fig, 700, 400)
        if img_bytes:
            img_buf = io.BytesIO(img_bytes)
            elements.append(Image(img_buf, width=16 * cm, height=9 * cm))
            elements.append(Spacer(1, 4 * mm))

    waste_pct = summary.get("waste_pct_of_input")
    if waste_pct:
        elements.append(Paragraph(
            f"Il calore di scarto rappresenta il <b>{waste_pct:.0f}%</b> dell'input energetico stimato.",
            ss["Normal"],
        ))

    # ── SEZIONE 3: TECNOLOGIE RACCOMANDATE ───────────────────────────────
    elements.append(PageBreak())
    elements.append(Paragraph("3. Tecnologie di Recupero Raccomandate", ss["SectionTitle"]))

    if econ_results:
        tech_headers = ["Stream", "Tecnologia", "Q rec. (kW)", "Eff.", "CAPEX (EUR)", "Payback (a)"]
        tech_rows = []
        for e in econ_results:
            rec = e.tech_recommendation
            eff_str = f"COP {rec.efficiency:.1f}" if rec.is_heat_pump else f"{rec.efficiency:.0%}"
            tech_rows.append([
                rec.stream_name,
                rec.technology.name,
                f"{rec.Q_recovered_kW:,.0f}",
                eff_str,
                f"{e.capex_EUR:,.0f}",
                f"{e.payback_years:.1f}" if e.payback_years < 50 else ">50",
            ])
        elements.append(_make_table(tech_headers, tech_rows))
    else:
        elements.append(Paragraph("Nessuna tecnologia raccomandata.", ss["Normal"]))

    # ── SEZIONE 4: ANALISI ECONOMICA ─────────────────────────────────────
    elements.append(PageBreak())
    elements.append(Paragraph("4. Analisi Economica", ss["SectionTitle"]))

    if econ_results:
        econ_headers = ["Tecnologia", "CAPEX (EUR)", "Invest. tot.", "Risp./anno", "Payback", "NPV 10a", "IRR"]
        econ_rows = []
        for e in econ_results:
            econ_rows.append([
                e.tech_recommendation.technology.name,
                f"{e.capex_EUR:,.0f}",
                f"{e.total_investment_EUR:,.0f}",
                f"{e.annual_savings_EUR:,.0f}",
                f"{e.payback_years:.1f} anni" if e.payback_years < 50 else ">50",
                f"{e.npv_EUR:,.0f}",
                f"{e.irr_pct:.1f}%" if e.irr_pct else "N/A",
            ])
        elements.append(_make_table(econ_headers, econ_rows))
        elements.append(Spacer(1, 6 * mm))

        # Grafici se disponibili
        if comparison_figs:
            for name, fig in comparison_figs.items():
                img_bytes = _export_plotly_image(fig, 600, 300)
                if img_bytes:
                    img_buf = io.BytesIO(img_bytes)
                    elements.append(Image(img_buf, width=14 * cm, height=7 * cm))
                    elements.append(Spacer(1, 4 * mm))

    # ── SEZIONE 5: CONCLUSIONI ───────────────────────────────────────────
    elements.append(PageBreak())
    elements.append(Paragraph("5. Conclusioni e Prossimi Passi", ss["SectionTitle"]))

    total_waste = summary["total_waste_kW"]
    total_MWh = summary["total_waste_MWh_anno"]

    elements.append(Paragraph(
        f"Il potenziale di recupero calore totale e' di <b>{total_waste:,.0f} kW</b> "
        f"(<b>{total_MWh:,.0f} MWh/anno</b>).",
        ss["Normal"],
    ))

    if econ_results:
        best = min(econ_results, key=lambda e: e.payback_years)
        total_npv = sum(e.npv_EUR for e in econ_results)
        elements.append(Paragraph(
            f"L'intervento piu' conveniente e' <b>{best.tech_recommendation.technology.name}</b> "
            f"con payback di <b>{best.payback_years:.1f} anni</b>.",
            ss["Normal"],
        ))
        elements.append(Paragraph(
            f"Il risparmio netto complessivo a 10 anni e' di <b>EUR {total_npv:,.0f}</b>.",
            ss["Normal"],
        ))

    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph("<b>Prossimi passi consigliati:</b>", ss["Normal"]))
    steps = [
        "Validare i dati di input con misure in campo",
        "Richiedere preventivi specifici ai fornitori di tecnologia",
        "Eseguire studio di fattibilita' dettagliato per le tecnologie prioritarie",
        "Verificare la disponibilita' di incentivi (Certificati Bianchi, Conto Termico)",
        "Definire tempistiche di implementazione compatibili con le fermate impianto",
    ]
    for i, step in enumerate(steps, 1):
        elements.append(Paragraph(f"{i}. {step}", ss["Normal"]))

    # ── DISCLAIMER ───────────────────────────────────────────────────────
    elements.append(Spacer(1, 2 * cm))
    elements.append(Paragraph(
        "<b>Disclaimer:</b> Questo report e' generato automaticamente dal tool HeatScout "
        "e fornisce stime di primo livello basate su correlazioni di letteratura. "
        "Le stime di CAPEX hanno un'incertezza indicativa di +/-30%, "
        "i risparmi di +/-15%. I risultati NON sostituiscono uno studio di fattibilita' "
        "ingegneristico dettagliato. L'autore declina ogni responsabilita' per "
        "decisioni di investimento basate esclusivamente su questo report.",
        ss["BodyItalic"],
    ))

    # Build PDF
    doc.build(elements)
    return buffer.getvalue()
