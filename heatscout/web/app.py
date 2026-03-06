"""HeatScout — Interfaccia web Streamlit per analisi recupero calore."""

import streamlit as st
import pandas as pd
import json
from pathlib import Path

from heatscout.core.stream import StreamType, ThermalStream
from heatscout.core.heat_balance import FactoryHeatBalance
from heatscout.core.examples import list_examples, load_example
from heatscout.plotting.sankey import create_sankey

# ── Configurazione pagina ────────────────────────────────────────────────────

st.set_page_config(
    page_title="HeatScout — Recupero Calore Industriale",
    page_icon="🔥",
    layout="wide",
)

# ── Carica fluidi disponibili ────────────────────────────────────────────────

FLUIDS_PATH = Path(__file__).parent.parent / "data" / "fluids.json"
with open(FLUIDS_PATH, encoding="utf-8") as f:
    FLUIDS_DB = json.load(f)["fluids"]

FLUID_OPTIONS = {f["id"]: f["name"] for f in FLUIDS_DB}
FLUID_IDS = list(FLUID_OPTIONS.keys())
FLUID_NAMES = list(FLUID_OPTIONS.values())

# ── Sidebar: parametri generali ──────────────────────────────────────────────

st.sidebar.title("⚙️ Parametri Generali")
factory_name = st.sidebar.text_input("Nome impianto", value="Il mio impianto")
T_ambient = st.sidebar.number_input(
    "Temperatura ambiente (°C)", value=25.0, min_value=-20.0, max_value=50.0, step=1.0
)
energy_price = st.sidebar.number_input(
    "Prezzo energia (€/kWh)", value=0.08, min_value=0.01, max_value=1.0,
    step=0.01, format="%.3f"
)

# ── Sidebar: input energetico (opzionale) ────────────────────────────────────

st.sidebar.divider()
st.sidebar.subheader("📥 Input Energetico (opzionale)")
energy_input_mode = st.sidebar.radio(
    "Come stimi l'input energetico?",
    ["Stima automatica (eff. 85%)", "Inserisci manualmente"],
    key="energy_input_mode",
)
manual_consumption = None
manual_unit = None
if energy_input_mode == "Inserisci manualmente":
    manual_consumption = st.sidebar.number_input(
        "Consumo annuo", value=100000.0, min_value=0.0, step=1000.0
    )
    manual_unit = st.sidebar.selectbox(
        "Unità", ["Sm3/anno", "MWh/anno", "kWh/anno", "tep/anno"]
    )

# ── Sidebar: carica esempio ──────────────────────────────────────────────────

st.sidebar.divider()
st.sidebar.subheader("📂 Carica Esempio")
examples = list_examples()
example_options = ["-- Nessuno --"] + [f"{e['name']} ({e['n_streams']} stream)" for e in examples]
example_choice = st.sidebar.selectbox("Esempio precaricato", example_options)


def _load_selected_example():
    """Carica esempio selezionato nel session state."""
    if example_choice != "-- Nessuno --":
        idx = example_options.index(example_choice) - 1
        example_id = examples[idx]["id"]
        streams, meta = load_example(example_id)
        st.session_state.n_streams = len(streams)
        st.session_state.loaded_example = {
            "streams": streams,
            "meta": meta,
        }
    else:
        st.session_state.pop("loaded_example", None)


st.sidebar.button("Carica", on_click=_load_selected_example)

# ── Titolo principale ────────────────────────────────────────────────────────

st.title("🔥 HeatScout")
st.markdown("**Analisi recupero calore industriale** — dal calore sprecato al risparmio")
st.divider()

# ── Gestione stream nel session state ────────────────────────────────────────

if "n_streams" not in st.session_state:
    st.session_state.n_streams = 1


def add_stream():
    st.session_state.n_streams = min(st.session_state.n_streams + 1, 10)


def remove_stream():
    st.session_state.n_streams = max(st.session_state.n_streams - 1, 1)


# ── Input stream termici ─────────────────────────────────────────────────────

st.header("📊 Stream Termici")
st.markdown(f"Inserisci fino a 10 stream termici. Stream attivi: **{st.session_state.n_streams}**")

col_add, col_rem, _ = st.columns([1, 1, 4])
with col_add:
    st.button("➕ Aggiungi stream", on_click=add_stream, use_container_width=True)
with col_rem:
    st.button("➖ Rimuovi ultimo", on_click=remove_stream, use_container_width=True)

# Pre-fill da esempio se caricato
loaded = st.session_state.get("loaded_example")

streams_input = []
for i in range(st.session_state.n_streams):
    # Default da esempio se disponibile
    ex = None
    if loaded and i < len(loaded["streams"]):
        ex = loaded["streams"][i]

    with st.expander(f"Stream {i+1}" + (f" — {ex.name}" if ex else ""), expanded=(i == 0)):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input(
                "Nome",
                value=ex.name if ex else f"Stream {i+1}",
                key=f"name_{i}",
            )
            default_fluid_idx = FLUID_IDS.index(ex.fluid_type) if ex and ex.fluid_type in FLUID_IDS else 0
            fluid_idx = st.selectbox(
                "Fluido", range(len(FLUID_IDS)),
                format_func=lambda x: FLUID_NAMES[x],
                index=default_fluid_idx,
                key=f"fluid_{i}",
            )
            default_type_idx = 0 if (ex is None or ex.stream_type == StreamType.HOT_WASTE) else 1
            stream_type = st.selectbox(
                "Tipo",
                [StreamType.HOT_WASTE, StreamType.COLD_DEMAND],
                format_func=lambda x: "🔴 Calore di scarto" if x == StreamType.HOT_WASTE else "🔵 Domanda termica",
                index=default_type_idx,
                key=f"type_{i}",
            )
        with col2:
            T_in = st.number_input(
                "T ingresso (°C)",
                value=ex.T_in if ex else 200.0,
                min_value=-200.0, max_value=1500.0, step=10.0, key=f"Tin_{i}",
            )
            T_out = st.number_input(
                "T uscita (°C)",
                value=ex.T_out if ex else 80.0,
                min_value=-200.0, max_value=1500.0, step=10.0, key=f"Tout_{i}",
            )
        with col3:
            mass_flow = st.number_input(
                "Portata (kg/s)",
                value=ex.mass_flow if ex else 1.0,
                min_value=0.01, max_value=1000.0, step=0.1, key=f"mflow_{i}",
            )
            hours = st.number_input(
                "Ore/giorno",
                value=ex.hours_per_day if ex else 16.0,
                min_value=0.5, max_value=24.0, step=0.5, key=f"hours_{i}",
            )
            days = st.number_input(
                "Giorni/anno",
                value=ex.days_per_year if ex else 250.0,
                min_value=1.0, max_value=366.0, step=1.0, key=f"days_{i}",
            )

        streams_input.append({
            "name": name,
            "fluid_type": FLUID_IDS[fluid_idx],
            "T_in": T_in,
            "T_out": T_out,
            "mass_flow": mass_flow,
            "hours_per_day": hours,
            "days_per_year": days,
            "stream_type": stream_type,
        })

# ── Bottone Analizza ─────────────────────────────────────────────────────────

st.divider()

if st.button("🔍 Analizza", type="primary", use_container_width=True):
    # Validazione e creazione stream
    hb = FactoryHeatBalance(factory_name=factory_name, T_ambient=T_ambient)
    errors = []

    for i, data in enumerate(streams_input):
        try:
            stream = ThermalStream(**data)
            hb.add_stream(stream)
        except ValueError as e:
            errors.append(f"Stream {i+1} ({data['name']}): {e}")

    if errors:
        for err in errors:
            st.error(err)
    else:
        # Input energetico
        if energy_input_mode == "Inserisci manualmente" and manual_consumption:
            hb.set_energy_input("gas_naturale", manual_consumption, manual_unit)
        else:
            hb.estimate_energy_input(efficiency=0.85)

        # Calcola risultati
        summary = hb.summary()
        st.session_state.last_summary = summary
        st.session_state.last_hb = hb

        st.success(f"Analisi completata per {summary['n_streams']} stream")

        # ── Metriche in evidenza ─────────────────────────────────────────
        st.header("📈 Risultati Analisi")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Potenza scarto totale", f"{summary['total_waste_kW']:,.1f} kW")
        m2.metric("Energia scarto annua", f"{summary['total_waste_MWh_anno']:,.1f} MWh/a")
        m3.metric("Exergia totale scarto", f"{summary['total_waste_exergy_kW']:,.1f} kW")
        m4.metric(
            "Costo annuo scarto",
            f"€ {summary['total_waste_MWh_anno'] * 1000 * energy_price:,.0f}"
        )

        # ── Diagramma Sankey ─────────────────────────────────────────────
        st.header("🔄 Diagramma Sankey — Bilancio Energetico")
        fig_sankey = create_sankey(hb, factory_name)
        st.plotly_chart(fig_sankey, use_container_width=True)

        # ── Tabella risultati per stream ─────────────────────────────────
        st.subheader("Dettaglio per stream")

        rows = []
        for r in summary["stream_results"]:
            rows.append({
                "Nome": r["name"],
                "Tipo": "🔴 Scarto" if r["stream_type"] == "hot_waste" else "🔵 Domanda",
                "Fluido": r["fluid_type"],
                "T_in (°C)": r["T_in"],
                "T_out (°C)": r["T_out"],
                "Q (kW)": r["Q_kW"],
                "E (MWh/a)": r["E_MWh_anno"],
                "Exergia (kW)": r["Ex_kW"],
                "Classe T": r["T_class"].capitalize(),
                "Qualità": f"{r['quality_ratio']:.1%}",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ── Breakdown per classe temperatura ─────────────────────────────
        st.subheader("Breakdown per classe di temperatura")
        by_class = summary["by_temperature_class"]

        tc1, tc2, tc3 = st.columns(3)
        for col, (cls, label, color) in zip(
            [tc1, tc2, tc3],
            [("alta", "Alta (>250°C)", "🔴"), ("media", "Media (80-250°C)", "🟠"), ("bassa", "Bassa (<80°C)", "🟡")]
        ):
            cls_data = by_class[cls]
            col.markdown(f"### {color} {label}")
            col.markdown(f"**{cls_data['count']}** stream — **{cls_data['Q_kW']:,.1f} kW** ({cls_data['pct_of_waste']:.1f}%)")

        # ── Messaggio impatto ────────────────────────────────────────────
        st.divider()
        waste_pct = summary.get("waste_pct_of_input")
        waste_pct_str = f" ({waste_pct:.0f}% dell'input)" if waste_pct else ""
        st.markdown(
            f"### 💡 Stai sprecando **{summary['total_waste_kW']:,.1f} kW** di calore{waste_pct_str}, "
            f"pari a **{summary['total_waste_MWh_anno']:,.1f} MWh/anno**, "
            f"che costano circa **€ {summary['total_waste_MWh_anno'] * 1000 * energy_price:,.0f}/anno**."
        )

        # ══════════════════════════════════════════════════════════════════
        # SEZIONE: Tecnologie Raccomandate
        # ══════════════════════════════════════════════════════════════════
        st.header("🔧 Tecnologie Raccomandate")

        from heatscout.core.technology_selector import select_technologies
        from heatscout.core.economics import economic_analysis
        from heatscout.plotting.comparison_chart import (
            capex_comparison_chart,
            payback_comparison_chart,
            npv_comparison_chart,
            cumulative_cashflow_chart,
            do_nothing_comparison,
        )

        all_econ_results = []

        for stream in hb.streams:
            if stream.stream_type != StreamType.HOT_WASTE:
                continue

            recs = select_technologies(stream, energy_price_EUR_kWh=energy_price)
            if not recs:
                st.info(f"**{stream.name}**: nessuna tecnologia compatibile trovata")
                continue

            with st.expander(f"🔥 {stream.name} — {len(recs)} tecnologie", expanded=True):
                tech_rows = []
                for rec in recs:
                    econ = economic_analysis(rec, energy_price_EUR_kWh=energy_price,
                                            discount_rate=0.05, years=10)
                    all_econ_results.append(econ)
                    eff_str = f"COP {rec.efficiency:.1f}" if rec.is_heat_pump else f"{rec.efficiency:.0%}"
                    tech_rows.append({
                        "Tecnologia": rec.technology.name,
                        "Q recup. (kW)": rec.Q_recovered_kW,
                        "E recup. (MWh/a)": rec.E_recovered_MWh,
                        "Efficienza": eff_str,
                        "CAPEX (€)": f"{econ.capex_EUR:,.0f}",
                        "Risparmio/a (€)": f"{econ.annual_savings_EUR:,.0f}",
                        "Payback (anni)": f"{econ.payback_years:.1f}" if econ.payback_years < 50 else ">50",
                        "NPV 10a (€)": f"{econ.npv_EUR:,.0f}",
                    })

                st.dataframe(pd.DataFrame(tech_rows), use_container_width=True, hide_index=True)

        # ══════════════════════════════════════════════════════════════════
        # SEZIONE: Analisi Economica
        # ══════════════════════════════════════════════════════════════════
        if all_econ_results:
            st.header("💰 Analisi Economica")

            # Metriche riassuntive
            best = min(all_econ_results, key=lambda e: e.payback_years)
            total_capex = sum(e.total_investment_EUR for e in all_econ_results)
            total_savings = sum(e.annual_savings_EUR for e in all_econ_results)
            total_npv = sum(e.npv_EUR for e in all_econ_results)

            e1, e2, e3 = st.columns(3)
            e1.metric("Investimento totale", f"€ {total_capex:,.0f}")
            e2.metric("Risparmio annuo totale", f"€ {total_savings:,.0f}")
            e3.metric("Payback migliore", f"{best.payback_years:.1f} anni",
                      delta=best.tech_recommendation.technology.name)

            # Grafici confronto
            gc1, gc2 = st.columns(2)
            with gc1:
                st.plotly_chart(payback_comparison_chart(all_econ_results), use_container_width=True)
            with gc2:
                st.plotly_chart(npv_comparison_chart(all_econ_results), use_container_width=True)

            gc3, gc4 = st.columns(2)
            with gc3:
                st.plotly_chart(capex_comparison_chart(all_econ_results), use_container_width=True)
            with gc4:
                st.plotly_chart(do_nothing_comparison(all_econ_results), use_container_width=True)

            # Cashflow cumulativo del miglior progetto
            st.subheader("Cashflow cumulativo — progetto migliore")
            st.plotly_chart(cumulative_cashflow_chart(best), use_container_width=True)

            # Tabella riassuntiva finale
            st.subheader("Riepilogo investimenti")
            st.markdown(
                f"**Investimento totale: € {total_capex:,.0f}** — "
                f"**Rientro migliore in {best.payback_years:.1f} anni** — "
                f"**Risparmio netto a 10 anni: € {total_npv:,.0f}**"
            )

            # ══════════════════════════════════════════════════════════════
            # SEZIONE: Report PDF
            # ══════════════════════════════════════════════════════════════
            st.header("📄 Report PDF")

            from heatscout.report.pdf_generator import generate_report
            from heatscout.report.executive_summary import generate_executive_summary

            # Mostra anteprima executive summary
            exec_text = generate_executive_summary(summary, all_econ_results, energy_price)
            with st.expander("Anteprima Executive Summary", expanded=False):
                st.text(exec_text)

            # Genera e scarica PDF
            try:
                fig_sankey = create_sankey(hb, factory_name)
                pdf_bytes = generate_report(
                    summary, all_econ_results, fig_sankey, energy_price=energy_price
                )
                st.download_button(
                    label="📥 Scarica Report PDF",
                    data=pdf_bytes,
                    file_name=f"HeatScout_Report_{factory_name.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as ex:
                st.error(f"Errore nella generazione del PDF: {ex}")
