import io
import json
from math import ceil
from datetime import date
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

st.set_page_config(page_title="Maakindustrie Cost Tool+",
                   layout="wide",
                   page_icon="⚙️")

# =============================
# i18n
# =============================
TXT = {
    "app_title":{"nl":"Maakindustrie Cost Tool+","en":"Manufacturing Cost Tool+"},
    "app_caption":{"nl":"BOM routing, Auto-routing, Presets, Forecast, WIP/Capaciteit, CO₂, Monte-Carlo, PDF/Excel",
                   "en":"BOM routing, Auto-routing, Presets, Forecast, WIP/Capacity, CO₂, Monte Carlo, PDF/Excel"},
    "lang":{"nl":"Taal / Language","en":"Language / Taal"},
    "sidebar_input":{"nl":"🔧 Invoer","en":"🔧 Inputs"},
    "project":{"nl":"Projectnaam","en":"Project name"},
    "qty":{"nl":"Aantal stuks (Q)","en":"Quantity (Q)"},
    "material":{"nl":"Materiaal","en":"Material"},
    "net_weight":{"nl":"Netto gewicht per stuk (kg)","en":"Net weight per part (kg)"},
    "learning_curve":{"nl":"Learning curve (op cyclustijd)","en":"Learning curve (on cycle time)"},
    "lc_b":{"nl":"b-exponent (negatief)","en":"b-exponent (negative)"},
    "lc_ref":{"nl":"RefQty","en":"RefQty"},
    "tou":{"nl":"Energie (TOU)","en":"Energy (TOU)"},
    "price_day":{"nl":"Dagprijs €/kWh","en":"Day price €/kWh"},
    "price_eve":{"nl":"Avondprijs €/kWh","en":"Evening price €/kWh"},
    "price_night":{"nl":"Nachtprijs €/kWh","en":"Night price €/kWh"},
    "share_day":{"nl":"Share dag","en":"Share day"},
    "share_eve":{"nl":"Share avond","en":"Share evening"},
    "plant_hdr":{"nl":"Fabriek / Capaciteit","en":"Plant / Capacity"},
    "hours_per_day":{"nl":"Uren productie per dag","en":"Production hours per day"},
    "cap_per_process":{"nl":"Capaciteit per proces (uren/dag)","en":"Capacity per process (hours/day)"},
    "lean_hdr":{"nl":"Lean / Logistiek","en":"Lean / Logistics"},
    "rework_pct":{"nl":"Rework % (op proceskosten)","en":"Rework % (on process costs)"},
    "transport_min":{"nl":"Transport (min/stuk)","en":"Transport (min/part)"},
    "storage_days":{"nl":"Opslag (dagen batch)","en":"Storage (days per batch)"},
    "inventory_rate":{"nl":"Voorraadkosten %/jaar","en":"Inventory cost %/year"},
    "mvb_hdr":{"nl":"Make vs Buy","en":"Make vs Buy"},
    "buy_price":{"nl":"Inkoopprijs/stuk (€)","en":"Purchase price/part (€)"},
    "moq":{"nl":"MOQ","en":"MOQ"},
    "buy_transport":{"nl":"Transport/handling (€/stuk)","en":"Transport/handling (€/part)"},
    "mc_hdr":{"nl":"Monte-Carlo (onzekerheid)","en":"Monte Carlo (uncertainty)"},
    "mc_enable":{"nl":"Monte-Carlo simulatie aan","en":"Enable Monte Carlo simulation"},
    "mc_iter":{"nl":"Iteraties","en":"Iterations"},
    "sd_mat":{"nl":"σ materiaalprijs (%)","en":"σ material price (%)"},
    "sd_cycle":{"nl":"σ cyclustijd (%)","en":"σ cycle time (%)"},
    "sd_scrap":{"nl":"σ scrap additief (abs)","en":"σ scrap additive (abs)"},
    "forecast_hdr":{"nl":"Materiaal prijs forecast","en":"Material price forecast"},
    "horizon":{"nl":"Horizon (maanden)","en":"Horizon (months)"},
    "method":{"nl":"Methode","en":"Method"},
    "drift_abs":{"nl":"Drift (€/kg per maand)","en":"Drift (€/kg per month)"},
    "drift_pct":{"nl":"Drift (% per maand)","en":"Drift (% per month)"},
    "sigma_pct":{"nl":"Onzekerheid σ (%/mnd)","en":"Uncertainty σ (%/month)"},
    "use_fc":{"nl":"Gebruik voorspelde prijs in kostprijs","en":"Use forecasted price in costing"},
    "month_t":{"nl":"Gebruik maand t=","en":"Use month t="},
    "routing_hdr":{"nl":"🧭 Routing (BOM-stappen)","en":"🧭 Routing (BOM steps)"},
    "routing_cap":{"nl":"Definieer bewerkingen in volgorde. Setup over batch; scrap propageert.",
                   "en":"Define operations in order. Setup over batch; scrap propagates."},
    "bom_buy_hdr":{"nl":"🧾 BOM – Ingekochte onderdelen","en":"🧾 BOM – Purchased components"},
    "bom_buy_cap":{"nl":"Inkoopregels per eindproduct; scrapt mee in routing.",
                   "en":"Purchase items per finished unit; scrap cascades in routing."},
    "client_hdr":{"nl":"👤 Klantinformatie","en":"👤 Client information"},
    "client_cap":{"nl":"Komt op PDF/Excel; vul in voor complete offerte.",
                  "en":"Goes on PDF/Excel; fill for a complete quote."},
    "verkoop_stuk":{"nl":"Verkoopprijs/stuk","en":"Sales price/part"},
    "verkoop_totaal":{"nl":"Totale verkoopprijs","en":"Total sales price"},
    "advies":{"nl":"Advies","en":"Recommendation"},
    "split_hdr":{"nl":"💰 Kostensplitsing","en":"💰 Cost breakdown"},
    "chart_hdr":{"nl":"📊 Visualisaties (Plotly)","en":"📊 Visualizations (Plotly)"},
    "trend_hdr":{"nl":"📈 Voorspelde prijs","en":"📈 Forecasted price"},
    "detail_hdr":{"nl":"🔎 Detail per stap (€/stuk)","en":"🔎 Per-step detail (€/part)"},
    "capacity_hdr":{"nl":"🏭 Capaciteit & Doorlooptijd","en":"🏭 Capacity & Lead time"},
    "lead_time":{"nl":"Totale doorlooptijd (dagen)","en":"Total lead time (days)"},
    "bottleneck":{"nl":"Bottleneck (proces)","en":"Bottleneck (process)"},
    "shadow_profit":{"nl":"Shadow €/h (profit-only)","en":"Shadow €/h (profit-only)"},
    "shadow_margin":{"nl":"Shadow €/h (gross margin)","en":"Shadow €/h (gross margin)"},
    "co2pp":{"nl":"CO₂ kg/stuk","en":"CO₂ kg/part"},
    "p50":{"nl":"P50 €/stuk","en":"P50 €/part"},
    "p80":{"nl":"P80 €/stuk","en":"P80 €/part"},
    "p90":{"nl":"P90 €/stuk","en":"P90 €/part"},
    "pdf_btn":{"nl":"📄 Download offerte (PDF)","en":"📄 Download quote (PDF)"},
    "xls_btn":{"nl":"📊 Download Excel","en":"📊 Download Excel"},
    "make":{"nl":"MAKE","en":"MAKE"},
    "buy":{"nl":"BUY","en":"BUY"},
    "used_price":{"nl":"Gebruikte materiaalprijs","en":"Material price used"},
    "month":{"nl":"maand","en":"month"},
    "tooling":{"nl":"Tooling/Consumables","en":"Tooling/Consumables"},
    "material_lbl":{"nl":"Materiaal","en":"Material"},
    "mat_base":{"nl":"Materiaal (basis)","en":"Material (base)"},
    "mat_conv":{"nl":"Conversie (gieten/smeden/extrusie)","en":"Conversion (casting/forging/extrusion)"},
    "mat_waste":{"nl":"Materiaalverlies/waste","en":"Material waste"},
    "wip_cost":{"nl":"WIP/Flow holding","en":"WIP/Flow holding"},
    "transport":{"nl":"Transport","en":"Transport"},
    "storage":{"nl":"Opslag","en":"Storage"},
    "rework":{"nl":"Rework","en":"Rework"},
    "overhead":{"nl":"Overhead","en":"Overhead"},
    "contingency":{"nl":"Contingency","en":"Contingency"},
    "profit":{"nl":"Profit","en":"Profit"},
}
def tr(key, lang="nl", **fmt):
    s = TXT.get(key, {}).get(lang, key)
    return s.format(**fmt) if fmt else s

# =============================
# Materialen (incl. ruwe vormen + CO2)
# =============================
materials = {
    # Staal / constructie
    "S235JR_steel":{"price":1.40,"waste":0.08,"k_cycle":1.00,"tool_wear_eur_pc":0.02,"co2e_kgkg":1.9},
    "S355J2_steel":{"price":1.70,"waste":0.08,"k_cycle":1.05,"tool_wear_eur_pc":0.03,"co2e_kgkg":2.0},
    "C45":{"price":1.90,"waste":0.06,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":2.0},
    "42CrMo4":{"price":2.60,"waste":0.06,"k_cycle":1.20,"tool_wear_eur_pc":0.07,"co2e_kgkg":2.3},
    # RVS
    "SS304":{"price":3.50,"waste":0.06,"k_cycle":1.15,"tool_wear_eur_pc":0.06,"co2e_kgkg":6.5},
    "SS316L":{"price":4.20,"waste":0.06,"k_cycle":1.20,"tool_wear_eur_pc":0.08,"co2e_kgkg":6.8},
    "SS904L":{"price":8.50,"waste":0.06,"k_cycle":1.25,"tool_wear_eur_pc":0.10,"co2e_kgkg":8.5},
    # Duplex / super duplex
    "1.4462_Duplex":{"price":5.50,"waste":0.07,"k_cycle":1.30,"tool_wear_eur_pc":0.12,"co2e_kgkg":7.5},
    "SuperDuplex_2507":{"price":7.50,"waste":0.07,"k_cycle":1.45,"tool_wear_eur_pc":0.18,"co2e_kgkg":10.5},
    # Al / Cu
    "Al_6082":{"price":4.20,"waste":0.07,"k_cycle":0.80,"tool_wear_eur_pc":0.01,"co2e_kgkg":8.0},
    "Cast_Aluminium":{"price":3.20,"waste":0.07,"k_cycle":0.90,"tool_wear_eur_pc":0.02,"co2e_kgkg":8.5},
    "Cu_ECW":{"price":8.00,"waste":0.05,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":3.5},
    # Gietwerk
    "Cast_Steel_GS45":{"price":1.60,"waste":0.05,"yield":0.80,"conv_cost":0.80,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":2.1},
    "Cast_Iron_GG25":{"price":1.20,"waste":0.05,"yield":0.85,"conv_cost":0.60,"k_cycle":1.05,"tool_wear_eur_pc":0.04,"co2e_kgkg":1.8},
    "Cast_AlSi10Mg":{"price":3.00,"waste":0.05,"yield":0.75,"conv_cost":1.00,"k_cycle":0.90,"tool_wear_eur_pc":0.02,"co2e_kgkg":8.5},
    # Smeedwerk
    "Forged_C45":{"price":1.90,"waste":0.04,"yield":0.90,"conv_cost":1.20,"k_cycle":1.20,"tool_wear_eur_pc":0.06,"co2e_kgkg":2.2},
    "Forged_42CrMo4":{"price":2.80,"waste":0.04,"yield":0.92,"conv_cost":1.40,"k_cycle":1.30,"tool_wear_eur_pc":0.08,"co2e_kgkg":2.5},
    "Forged_1.4462":{"price":6.00,"waste":0.04,"yield":0.88,"conv_cost":1.60,"k_cycle":1.40,"tool_wear_eur_pc":0.12,"co2e_kgkg":8.0},
    # Extrusie
    "Extruded_Al_6060":{"price":3.50,"waste":0.03,"yield":0.95,"conv_cost":0.50,"k_cycle":0.85,"tool_wear_eur_pc":0.01,"co2e_kgkg":7.5},
    "Extruded_Cu":{"price":7.50,"waste":0.03,"yield":0.92,"conv_cost":0.70,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":3.5},
}

# Tarieven (€/uur) – incl. Casting
machine_rates = {"CNC":85.0,"Laser":110.0,"Lassen":55.0,"Buigen":75.0,"Montage":40.0,"Casting":65.0}
labor_rate = 45.0
overhead_pct = 0.20
profit_pct = 0.12
contingency_pct = 0.05
co2_per_kwh = 0.35  # kg CO2/kWh (simple factor; pas aan op je regio)

# =============================
# Sidebar – Invoer
# =============================
lang_choice = st.sidebar.selectbox(TXT["lang"]["nl"], options=["nl","en"], index=0,
                                   format_func=lambda x: "Nederlands" if x=="nl" else "English")

st.title(tr("app_title", lang_choice))
st.caption(tr("app_caption", lang_choice))

st.sidebar.header(tr("sidebar_input", lang_choice))
project = st.sidebar.text_input(tr("project", lang_choice), "Demo")
Q = st.sidebar.number_input(tr("qty", lang_choice), min_value=1, value=50, step=1)
material = st.sidebar.selectbox(tr("material", lang_choice), list(materials.keys()))
gewicht = st.sidebar.number_input(tr("net_weight", lang_choice), min_value=0.01, value=2.0)

st.sidebar.subheader(tr("learning_curve", lang_choice))
lc_b = st.sidebar.number_input(tr("lc_b", lang_choice), value=-0.15, step=0.01, format="%.2f")
lc_ref = st.sidebar.number_input(tr("lc_ref", lang_choice), min_value=1, value=10, step=1)

st.sidebar.subheader(tr("tou", lang_choice))
price_day = st.sidebar.number_input(tr("price_day", lang_choice), value=0.24, step=0.01)
price_eve = st.sidebar.number_input(tr("price_eve", lang_choice), value=0.18, step=0.01)
price_night = st.sidebar.number_input(tr("price_night", lang_choice), value=0.12, step=0.01)
tou_day = st.sidebar.slider(tr("share_day", lang_choice), 0.0, 1.0, 0.60, 0.05)
tou_eve = st.sidebar.slider(tr("share_eve", lang_choice), 0.0, 1.0, 0.30, 0.05)
tou_night = max(0.0, 1.0 - tou_day - tou_eve)
st.sidebar.caption(f"Night share: {tou_night:.2f}")

st.sidebar.subheader(tr("plant_hdr", lang_choice))
hours_per_day = st.sidebar.number_input(tr("hours_per_day", lang_choice), 1.0, 24.0, 8.0, step=0.5)
with st.sidebar.expander(tr("cap_per_process", lang_choice), expanded=False):
    cap_per_process = {p: st.number_input(f"{p} (h/dag)", 0.0, 24.0, 8.0, key=f"cap_{p}") for p in machine_rates.keys()}

st.sidebar.subheader(tr("lean_hdr", lang_choice))
rework_pct = st.sidebar.number_input(tr("rework_pct", lang_choice), 0.0, 1.0, 0.05, step=0.01)
transport_min = st.sidebar.number_input(tr("transport_min", lang_choice), 0.0, 60.0, 0.5)
storage_days = st.sidebar.number_input(tr("storage_days", lang_choice), 0, 365, 30)
inventory_cost_year = st.sidebar.number_input(tr("inventory_rate", lang_choice), 0.0, 1.0, 0.12, step=0.01)

st.sidebar.subheader(tr("mvb_hdr", lang_choice))
buy_price = st.sidebar.number_input(tr("buy_price", lang_choice), 0.0, 1e6, 15.0)
moq = st.sidebar.number_input(tr("moq", lang_choice), 1, 100000, 250)
transport_buy = st.sidebar.number_input(tr("buy_transport", lang_choice), 0.0, 1e6, 0.6)

st.sidebar.subheader(tr("mc_hdr", lang_choice))
mc_on = st.sidebar.checkbox(tr("mc_enable", lang_choice), value=False)
mc_iter = st.sidebar.number_input(tr("mc_iter", lang_choice), 100, 20000, 1000, step=100)
sd_mat = st.sidebar.number_input(tr("sd_mat", lang_choice), 0.0, 0.5, 0.05, step=0.01)
sd_cycle = st.sidebar.number_input(tr("sd_cycle", lang_choice), 0.0, 0.5, 0.08, step=0.01)
sd_scrap = st.sidebar.number_input(tr("sd_scrap", lang_choice), 0.0, 0.5, 0.01, step=0.005)

st.sidebar.subheader(tr("forecast_hdr", lang_choice))
forecast_horizon = st.sidebar.slider(tr("horizon", lang_choice), 1, 12, 12)
forecast_method = st.sidebar.selectbox(tr("method", lang_choice), ["Drift (€/mnd)","Drift (%/mnd) + onzekerheid"])
drift_abs = st.sidebar.number_input(tr("drift_abs", lang_choice), value=0.00, step=0.05, format="%.2f")
drift_pct = st.sidebar.number_input(tr("drift_pct", lang_choice), value=0.00, step=0.01, format="%.2f")
sigma_pct = st.sidebar.number_input(tr("sigma_pct", lang_choice), value=1.50, step=0.25, format="%.2f")
use_forecast_for_cost = st.sidebar.checkbox(tr("use_fc", lang_choice), value=False)
quote_month_offset = st.sidebar.slider(tr("month_t", lang_choice), 0, forecast_horizon, 0)

# =============================
# Helpers
# =============================
def lc_factor(Q, ref, b):
    try: return (max(Q,1)/max(ref,1))**b
    except: return 1.0

def forecast_series(p0, months, method, drift_abs, drift_pct, sigma_pct, seed=42):
    idx = pd.date_range(date.today(), periods=months+1, freq="MS")
    if method=="Drift (€/mnd)":
        vals=[max(0.01,p0+i*drift_abs) for i in range(months+1)]
        return pd.DataFrame({"Datum":idx,"€/kg":vals})
    rng=np.random.default_rng(seed)
    vals=[p0]; low=[p0]; high=[p0]
    for _ in range(months):
        mu=1+drift_pct/100; shock=rng.normal(0.0, sigma_pct/100.0)
        nxt=max(0.01, vals[-1]*(mu+shock)); vals.append(nxt)
        trend=vals[-2]*mu; low.append(max(0.01, trend*(1-2*sigma_pct/100))); high.append(trend*(1+2*sigma_pct/100))
    return pd.DataFrame({"Datum":idx,"€/kg":vals,"Low":low,"High":high})

# =============================
# Forecast bouwen
# =============================
mat = materials[material]; p0 = mat["price"]
df_fc = forecast_series(p0, forecast_horizon, forecast_method, drift_abs, drift_pct, sigma_pct)

st.markdown("---")
st.subheader(f"{tr('trend_hdr', lang_choice)} – {material} ({forecast_horizon} mnd)")
if "Low" in df_fc.columns:
    fig_fc = px.line(df_fc, x="Datum", y=["€/kg","Low","High"], markers=True,
                     labels={"value":"€/kg","variable":"Serie"})
else:
    fig_fc = px.line(df_fc, x="Datum", y="€/kg", markers=True, labels={"€/kg":"€/kg"})
st.plotly_chart(fig_fc, use_container_width=True)

if use_forecast_for_cost:
    try: mat_price_used = float(df_fc.loc[df_fc.index[quote_month_offset], "€/kg"])
    except: mat_price_used = p0
    used_note = f"{tr('used_price', lang_choice)}: € {mat_price_used:.2f}/kg ({tr('month', lang_choice)} t={quote_month_offset})"
else:
    mat_price_used = p0
    used_note = f"{tr('used_price', lang_choice)}: € {mat_price_used:.2f}/kg (t=0)"

# =============================
# Klantinformatie
# =============================
st.markdown(f"## {tr('client_hdr', lang_choice)}")
st.caption(tr("client_cap", lang_choice))
with st.form("client_form"):
    c1, c2 = st.columns(2)
    with c1:
        client_company = st.text_input("Bedrijf / Company", "")
        client_contact = st.text_input("Contactpersoon / Contact", "")
        client_email = st.text_input("E-mail", "")
        client_phone = st.text_input("Telefoon / Phone", "")
        rfq_ref = st.text_input("RFQ / Referentie", "")
        incoterms = st.text_input("Incoterms (bijv. EXW, DAP)", "EXW")
    with c2:
        currency = st.text_input("Valuta / Currency", "EUR")
        pay_terms = st.text_input("Betalingscondities / Payment terms", "30 dagen netto")
        delivery_addr = st.text_area("Leveradres / Delivery address", "")
        req_delivery = st.text_input("Gewenste leverdatum / Required delivery", "")
        quote_valid = st.text_input("Offertegeldigheid / Quote validity", "60 dagen")
        nda_flag = st.checkbox("NDA van toepassing / NDA applies", value=False)
    submitted = st.form_submit_button("Opslaan / Save")
client_info = {
    "Company":client_company if 'client_company' in locals() else "",
    "Contact":client_contact if 'client_contact' in locals() else "",
    "Email":client_email if 'client_email' in locals() else "",
    "Phone":client_phone if 'client_phone' in locals() else "",
    "RFQ":rfq_ref if 'rfq_ref' in locals() else "",
    "Incoterms":incoterms if 'incoterms' in locals() else "",
    "Currency":currency if 'currency' in locals() else "EUR",
    "PaymentTerms":pay_terms if 'pay_terms' in locals() else "",
    "DeliveryAddress":delivery_addr if 'delivery_addr' in locals() else "",
    "RequiredDelivery":req_delivery if 'req_delivery' in locals() else "",
    "QuoteValidity":quote_valid if 'quote_valid' in locals() else "",
    "NDA": "Yes" if ('nda_flag' in locals() and nda_flag) else "No",
}

# =============================
# 🧩 Product specificatie & Auto-routing
# =============================
st.markdown("## 🧩 Product specificatie & Auto-routing")
st.caption("Kies producttype en kenmerken → ‘Genereer routing’ → daarna kun je handmatig bijstellen.")

part_type = st.selectbox(
    "Type product",
    [
        "Gedraaide as / gefreesd deel",
        "Gefreesde beugel (massief)",
        "Lasframe / samenstel",
        "Plaatwerk kast / bracket",
        "Gietstuk behuizing (CNC na-frees)",
        "Gesmede flens (CNC na-bewerking)"
    ]
)

colA, colB, colC = st.columns(3)
with colA:
    tol_class = st.selectbox("Tolerantieklasse", ["Normaal", "Nauwkeurig", "Zeer nauwkeurig"], index=0)
    surface = st.selectbox("Oppervlakteruwheid", ["Standaard", "Fijn", "Zeer fijn"], index=0)
with colB:
    holes = st.number_input("Aantal gaten (boren/tappen)", min_value=0, value=4, step=1)
    bends = st.number_input("Aantal zetten (alleen voor plaatwerk)", min_value=0, value=0, step=1)
with colC:
    weld_m = st.number_input("Laslengte totaal (meter)", min_value=0.0, value=0.0, step=0.5)
    panels = st.number_input("Aantal plaatdelen (plaatwerk/samenstel)", min_value=0, value=2, step=1)

tol_k = {"Normaal": 1.00, "Nauwkeurig": 1.20, "Zeer nauwkeurig": 1.45}[tol_class]
surf_k = {"Standaard": 1.00, "Fijn": 1.15, "Zeer fijn": 1.30}[surface]

def _base_scrap(pt):
    return {
        "Gedraaide as / gefreesd deel": 0.02,
        "Gefreesde beugel (massief)": 0.025,
        "Lasframe / samenstel": 0.015,
        "Plaatwerk kast / bracket": 0.02,
        "Gietstuk behuizing (CNC na-frees)": 0.03,
        "Gesmede flens (CNC na-bewerking)": 0.02
    }[pt]

def generate_autorouting(pt: str, Q: int, gross_kg_pc: float, holes: int, bends: int, weld_m: float, panels: int,
                         tol_k: float, surf_k: float):
    rows = []
    scrap_default = _base_scrap(pt)
    def row(step, proces, qpp, cyc, setup, attend, kwh, qa, scrap, par=1, bsize=50, qd=0.5):
        rows.append({
            "Step": step, "Proces": proces, "Qty_per_parent": qpp, "Cycle_min": max(0.1, cyc),
            "Setup_min": max(0.0, setup), "Attend_pct": attend, "kWh_pc": max(0.0, kwh),
            "QA_min_pc": max(0.0, qa), "Scrap_pct": max(0.0, min(0.9, scrap)),
            "Parallel_machines": max(1, int(par)), "Batch_size": max(1, int(bsize)), "Queue_days": max(0.0, qd)
        })

    if pt == "Gedraaide as / gefreesd deel":
        cyc_cnc = (8.0 * tol_k * surf_k) + 0.4*holes + 2.0*(gross_kg_pc**0.5)
        row(10, "CNC", 1.0, cyc_cnc, 25.0, 100, 0.20, 0.5, scrap_default, par=1, bsize=50, qd=0.4)
        row(20, "Montage", 1.0, 4.0 + 0.3*holes, 10.0, 100, 0.05, 0.8, 0.0, par=1, bsize=100, qd=0.2)

    elif pt == "Gefreesde beugel (massief)":
        cyc_cnc = (10.0 * tol_k * surf_k) + 0.5*holes + 3.0*(gross_kg_pc**0.6)
        row(10, "CNC", 1.0, cyc_cnc, 30.0, 100, 0.25, 0.6, scrap_default, par=1, bsize=40, qd=0.5)
        row(20, "Montage", 1.0, 5.0 + 0.3*holes, 10.0, 100, 0.05, 1.0, 0.0, par=1, bsize=80, qd=0.3)

    elif pt == "Lasframe / samenstel":
        cut_time = 3.0 + 0.8 * panels
        row(10, "Laser", panels, cut_time, 20.0, 50, 0.50, 0.3, scrap_default*0.5, par=1, bsize=80, qd=0.5)
        weld_time = 6.0 + 6.0*weld_m + 0.5*panels
        row(20, "Lassen", 1.0, weld_time, 20.0, 100, 0.35, 0.5, scrap_default, par=1, bsize=30, qd=0.8)
        cnc_time = 4.0*tol_k + 0.3*holes + 1.5*(gross_kg_pc**0.4)
        row(30, "CNC", 1.0, cnc_time, 15.0, 100, 0.20, 0.5, 0.01, par=1, bsize=40, qd=0.4)
        row(40, "Montage", 1.0, 6.0 + 0.3*holes, 10.0, 100, 0.05, 1.0, 0.0, par=1, bsize=60, qd=0.3)

    elif pt == "Plaatwerk kast / bracket":
        laser_time = 3.0 + 0.6 * panels
        row(10, "Laser", panels, laser_time, 20.0, 50, 0.50, 0.3, scrap_default*0.6, par=1, bsize=100, qd=0.5)
        if bends > 0:
            bend_time = 1.6*bends + 0.2*panels
            row(20, "Buigen", 1.0, bend_time, 15.0, 100, 0.10, 0.2, scrap_default*0.4, par=1, bsize=80, qd=0.3)
        cnc_time = 2.5*tol_k + 0.25*holes
        row(30, "CNC", 1.0, cnc_time, 10.0, 100, 0.15, 0.4, 0.01, par=1, bsize=60, qd=0.3)
        row(40, "Montage", 1.0, 5.0 + 0.25*holes, 8.0, 100, 0.05, 0.8, 0.0, par=1, bsize=80, qd=0.2)

    elif pt == "Gietstuk behuizing (CNC na-frees)":
        cast_cyc = 1.2 + 0.4*(gross_kg_pc**0.7)
        row(10, "Casting", 1.0, cast_cyc, 60.0, 50, 0.40, 0.2, scrap_default, par=1, bsize=60, qd=1.0)
        cnc_time = 6.0*tol_k*surf_k + 0.4*holes + 1.5*(gross_kg_pc**0.5)
        row(20, "CNC", 1.0, cnc_time, 25.0, 100, 0.25, 0.6, 0.015, par=1, bsize=40, qd=0.6)
        row(30, "Montage", 1.0, 4.0 + 0.2*holes, 8.0, 100, 0.05, 0.8, 0.0, par=1, bsize=80, qd=0.2)

    elif pt == "Gesmede flens (CNC na-bewerking)":
        cnc_time = 5.0*tol_k + 0.2*holes + 1.0*(gross_kg_pc**0.5)
        row(10, "CNC", 1.0, cnc_time, 20.0, 100, 0.20, 0.5, scrap_default, par=1, bsize=60, qd=0.4)
        row(20, "Montage", 1.0, 3.5 + 0.2*holes, 8.0, 100, 0.05, 0.8, 0.0, par=1, bsize=100, qd=0.2)

    return pd.DataFrame(rows).sort_values("Step").reset_index(drop=True)

# knop auto-routing
if st.button("🔮 Genereer routing"):
    yfac = float(materials[material].get("yield",1.0))
    bruto_kg_pc = gewicht / yfac
    gen_df = generate_autorouting(part_type, Q, bruto_kg_pc, holes, bends, weld_m, panels, tol_k, surf_k)
    st.session_state["routing_editor"] = gen_df
    st.success("Routing gegenereerd – bewerk ‘m hieronder naar wens.")
    st.experimental_rerun()

# =============================
# Preset-bibliotheek + Save/Load JSON
# =============================
st.markdown("### 📚 Presets & JSON")
preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)

def preset_dataframe(name:str):
    yfac = float(materials[material].get("yield",1.0))
    bruto_kg = gewicht / yfac
    mapping = {
        "Typische as": ("Gedraaide as / gefreesd deel", dict(holes=2,bends=0,weld_m=0.0,panels=1)),
        "Typische bracket": ("Gefreesde beugel (massief)", dict(holes=6,bends=0,weld_m=0.0,panels=1)),
        "Typisch lasframe": ("Lasframe / samenstel", dict(holes=8,bends=0,weld_m=2.0,panels=6)),
        "Plaatwerk kast": ("Plaatwerk kast / bracket", dict(holes=12,bends=8,weld_m=0.0,panels=8)),
        "Gietstuk behuizing": ("Gietstuk behuizing (CNC na-frees)", dict(holes=6,bends=0,weld_m=0.0,panels=1)),
        "Gesmede flens": ("Gesmede flens (CNC na-bewerking)", dict(holes=8,bends=0,weld_m=0.0,panels=1)),
    }
    pt, feat = mapping[name]
    return generate_autorouting(pt, Q, bruto_kg, feat["holes"], feat["bends"], feat["weld_m"], feat["panels"], tol_k, surf_k)

with preset_col1:
    if st.button("⭐ Typische as"):
        st.session_state["routing_editor"] = preset_dataframe("Typische as"); st.experimental_rerun()
with preset_col2:
    if st.button("⭐ Typische bracket"):
        st.session_state["routing_editor"] = preset_dataframe("Typische bracket"); st.experimental_rerun()
with preset_col3:
    if st.button("⭐ Typisch lasframe"):
        st.session_state["routing_editor"] = preset_dataframe("Typisch lasframe"); st.experimental_rerun()
with preset_col4:
    if st.button("⭐ Plaatwerk kast"):
        st.session_state["routing_editor"] = preset_dataframe("Plaatwerk kast"); st.experimental_rerun()

preset_col5, preset_col6 = st.columns(2)
with preset_col5:
    if st.button("⭐ Gietstuk behuizing"):
        st.session_state["routing_editor"] = preset_dataframe("Gietstuk behuizing"); st.experimental_rerun()
with preset_col6:
    if st.button("⭐ Gesmede flens"):
        st.session_state["routing_editor"] = preset_dataframe("Gesmede flens"); st.experimental_rerun()

# JSON save/load
json_left, json_right = st.columns([0.6,0.4])
with json_left:
    st.caption("Exporteer huidige Routing + BOM + Client + Basisinstellingen als JSON")
    # Placeholder; filled later once routing/bom exist
with json_right:
    uploaded = st.file_uploader("Laad preset JSON", type=["json"])
    if uploaded:
        try:
            payload = json.load(uploaded)
            if "routing" in payload:
                st.session_state["routing_editor"] = pd.DataFrame(payload["routing"])
            if "bom_buy" in payload:
                st.session_state["bom_buy_editor"] = pd.DataFrame(payload["bom_buy"])
            st.success("Preset geladen.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Kon JSON niet laden: {e}")

# =============================
# ROUTING (BOM-stappen)
# =============================
st.markdown(f"## {tr('routing_hdr', lang_choice)}")
st.caption(tr("routing_cap", lang_choice))

process_choices = list(machine_rates.keys())
default_routing = pd.DataFrame([
    {"Step":10,"Proces":"Casting","Qty_per_parent":1.0,"Cycle_min":2.0,"Setup_min":60.0,"Attend_pct":50,
     "kWh_pc":0.4,"QA_min_pc":0.2,"Scrap_pct":0.03,"Parallel_machines":1,"Batch_size":50,"Queue_days":1.0},
    {"Step":20,"Proces":"CNC","Qty_per_parent":1.0,"Cycle_min":7.5,"Setup_min":30.0,"Attend_pct":100,
     "kWh_pc":0.2,"QA_min_pc":0.5,"Scrap_pct":0.02,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.5},
    {"Step":30,"Proces":"Montage","Qty_per_parent":1.0,"Cycle_min":6.0,"Setup_min":10.0,"Attend_pct":100,
     "kWh_pc":0.1,"QA_min_pc":1.0,"Scrap_pct":0.00,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.2},
])
routing = st.data_editor(
    default_routing,
    key="routing_editor",
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Proces": st.column_config.SelectboxColumn(options=process_choices, required=True),
        "Step": st.column_config.NumberColumn(),
        "Qty_per_parent": st.column_config.NumberColumn(),
        "Cycle_min": st.column_config.NumberColumn(),
        "Setup_min": st.column_config.NumberColumn(),
        "Attend_pct": st.column_config.NumberColumn(),
        "kWh_pc": st.column_config.NumberColumn(),
        "QA_min_pc": st.column_config.NumberColumn(),
        "Scrap_pct": st.column_config.NumberColumn(),
        "Parallel_machines": st.column_config.NumberColumn(),
        "Batch_size": st.column_config.NumberColumn(),
        "Queue_days": st.column_config.NumberColumn(),
    }
).sort_values("Step").reset_index(drop=True)

# =============================
# BOM – Ingekochte onderdelen
# =============================
st.markdown(f"## {tr('bom_buy_hdr', lang_choice)}")
st.caption(tr("bom_buy_cap", lang_choice))
default_bom_buy = pd.DataFrame([{"Item":"Bevestigingsset","UnitCost_eur":1.20,"Qty_per_parent":1.0,"Scrap_pct":0.00}])
bom_buy = st.data_editor(default_bom_buy, key="bom_buy_editor", num_rows="dynamic", use_container_width=True)
bom_buy_cost_pc = 0.0 if bom_buy.empty else (bom_buy["UnitCost_eur"]*bom_buy["Qty_per_parent"]/(1-bom_buy["Scrap_pct"].clip(upper=0.9))).sum()
bom_buy_total = bom_buy_cost_pc * Q

# =============================
# Materiaal & CO2 (yield + conv + waste)
# =============================
yield_fac = float(mat.get("yield",1.0))
bruto_kg_pc = gewicht / yield_fac
base_mat_total = bruto_kg_pc * mat_price_used * Q
waste_total = base_mat_total * float(mat.get("waste",0.0))
conv_total = bruto_kg_pc * float(mat.get("conv_cost",0.0)) * Q
mat_cost_total = base_mat_total + waste_total + conv_total
mat_value_pc = bruto_kg_pc * mat_price_used * (1+float(mat.get("waste",0.0))) + bruto_kg_pc * float(mat.get("conv_cost",0.0))
co2e_kgkg = float(mat.get("co2e_kgkg", 0.0))
co2_total_material = bruto_kg_pc * co2e_kgkg * Q  # materiaal CO2
co2_per_part_material = co2_total_material / Q if Q else 0.0

# Energieprijs mix & LC
eff_kwh_price = (tou_day*price_day + tou_eve*price_eve + tou_night*price_night)
lc_fac = lc_factor(Q, lc_ref, lc_b)

# =============================
# Routing-berekening (batches, parallel, WIP, CO2 energie)
# =============================
def compute_costs_routing(routing_df):
    if routing_df is None or routing_df.empty:
        return dict(proc_cost=0.0,labor_cost=0.0,machine_cost=0.0,energy_cost=0.0,qa_cost=0.0,
                    tooling_cost=0.0,scrap_impact=0.0,wip_cost=0.0,detail=[],cap_hours_per_process={},
                    lead_time_days=0.0,bottleneck=None, co2_energy_total=0.0)

    mat_k = materials[material].get("k_cycle",1.0)
    tool_pc_base = materials[material].get("tool_wear_eur_pc",0.0)
    hold_rate_day = inventory_cost_year/365.0

    rows=[]; labor_total=machine_total=energy_total=qa_total=scrap_total=tooling_total=0.0
    wip_total=0.0; cap_hours={}; total_lead_days=0.0
    cum_cost_pc_before = (mat_value_pc + bom_buy_cost_pc)
    co2_energy_total = 0.0

    for _, r in routing_df.iterrows():
        p=r["Proces"]; rate=machine_rates.get(p,0.0)
        qty_par=float(r.get("Qty_per_parent",1.0))
        cyc=float(r.get("Cycle_min",0.0))*lc_fac*mat_k
        setup=float(r.get("Setup_min",0.0))
        attend=float(r.get("Attend_pct",100))/100.0
        kwh=float(r.get("kWh_pc",0.0)); qa_min=float(r.get("QA_min_pc",0.0))
        scrap=float(r.get("Scrap_pct",0.0))
        parallel=max(1,int(r.get("Parallel_machines",1)))
        batch_size=max(1,int(r.get("Batch_size",max(Q,1))))
        queue_days=max(0.0,float(r.get("Queue_days",0.0)))

        units = Q*qty_par
        batches = ceil(units/batch_size)

        run_min = (units*cyc)/parallel
        setup_min_total = (batches*setup)/parallel

        labor_pc = (cyc/60)*labor_rate*attend*qty_par + (setup/60)*labor_rate*attend/max(batch_size,1)/parallel
        mach_pc  = (cyc/60)*rate*qry if (qry:=qty_par) else (cyc/60)*rate*qty_par  # tiny guard
        mach_pc  = (cyc/60)*rate*qty_par + (setup/60)*rate/max(batch_size,1)/parallel
        energy_pc = kwh*eff_kwh_price*qty_par
        qa_pc = (qa_min/60)*labor_rate*qty_par
        tool_pc = tool_pc_base*qty_par
        base_pc = labor_pc+mach_pc+energy_pc+qa_pc+tool_pc
        scrap_imp_pc = (base_pc + mat_value_pc + bom_buy_cost_pc)*scrap/(1-min(0.9,scrap))

        # CO2 energie per stap
        co2_energy_step = (kwh*qty_par*Q) * co2_per_kwh
        co2_energy_total += co2_energy_step

        labor_total += labor_pc*Q; machine_total += mach_pc*Q; energy_total += energy_pc*Q
        qa_total += qa_pc*Q; tooling_total += tool_pc*Q; scrap_total += scrap_imp_pc*Q

        step_mach_hours = (run_min+setup_min_total)/60
        cap_hours[p] = cap_hours.get(p,0.0)+step_mach_hours

        proc_days = step_mach_hours / max(hours_per_day, 0.1)
        step_lead = queue_days + proc_days
        total_lead_days += step_lead

        wip_days = queue_days + proc_days/2.0
        wip_total += hold_rate_day * wip_days * cum_cost_pc_before * Q

        cum_cost_pc_before += base_pc + scrap_imp_pc

        rows.append([
            int(r.get("Step",0)), p, qty_par, cyc, setup, parallel, batch_size, batches, queue_days,
            labor_pc, mach_pc, energy_pc, qa_pc, tool_pc, scrap_imp_pc, base_pc+scrap_imp_pc,
            run_min, setup_min_total, proc_days, step_lead, co2_energy_step/Q if Q else 0.0
        ])

    proc_total = labor_total+machine_total+energy_total+qa_total+tooling_total+scrap_total
    bottleneck_proc = max(cap_hours.items(), key=lambda kv: kv[1])[0] if cap_hours else None
    return dict(proc_cost=proc_total,labor_cost=labor_total,machine_cost=machine_total,energy_cost=energy_total,
                qa_cost=qa_total,tooling_cost=tooling_total,scrap_impact=scrap_total,wip_cost=wip_total,
                detail=rows,cap_hours_per_process=cap_hours,lead_time_days=total_lead_days,bottleneck=bottleneck_proc,
                co2_energy_total=co2_energy_total)

res = compute_costs_routing(routing)

# Overige posten
transport_cost = (transport_min/60.0)*labor_rate*Q
storage_cost = (storage_days/365.0)*inventory_cost_year*(res["proc_cost"])
rework_cost = rework_pct*res["proc_cost"]

# CO2 totaal (materiaal + energie)
co2_total_energy = res["co2_energy_total"]
co2_per_part = (co2_total_material + co2_total_energy) / Q if Q else 0.0

# Totaal & schaduwprijzen
direct_cost = mat_cost_total + bom_buy_total + res["proc_cost"] + transport_cost + storage_cost + res["wip_cost"] + rework_cost
overhead = direct_cost*overhead_pct
contingency = direct_cost*contingency_pct
cost_total = direct_cost + overhead + contingency
profit = cost_total*profit_pct
sales_total = cost_total + profit
sales_per_part = sales_total / Q

buy_total = (buy_price + transport_buy) * max(Q, moq)
decision = tr("make", lang_choice) if sales_total/Q < buy_total/Q else tr("buy", lang_choice)

bottleneck = res["bottleneck"]
bottleneck_hours = res["cap_hours_per_process"].get(bottleneck, 0.0) if bottleneck else 0.0
variable_cost_total = direct_cost
gross_margin_total = sales_total - variable_cost_total
shadow_profit_only = (profit / bottleneck_hours) if bottleneck_hours > 0 else 0.0
shadow_gross_margin = (gross_margin_total / bottleneck_hours) if bottleneck_hours > 0 else 0.0

# =============================
# JSON export payload nu we alles hebben
# =============================
with json_left:
    payload = {
        "project": project, "Q": int(Q), "material": material, "net_weight": gewicht,
        "routing": routing.to_dict(orient="records"),
        "bom_buy": bom_buy.to_dict(orient="records"),
        "client": client_info,
        "settings": {
            "lc_b": lc_b, "lc_ref": int(lc_ref),
            "prices_kwh": {"day":price_day,"eve":price_eve,"night":price_night},
            "tou_share": {"day":float(tou_day),"eve":float(tou_eve),"night":float(tou_night)},
            "hours_per_day": hours_per_day,
            "inventory_rate": inventory_cost_year,
            "co2_per_kwh": co2_per_kwh
        }
    }
    st.download_button("⬇️ Download preset JSON", data=json.dumps(payload, indent=2),
                       file_name=f"preset_{project}.json", mime="application/json")

# =============================
# Klant-prioriteiten & advies
# =============================
st.markdown("### 🎯 Prioriteiten klant")
prio_col1, prio_col2, prio_col3 = st.columns(3)
with prio_col1:
    prio_price = st.slider("Belang: Prijs", 0, 100, 50)
with prio_col2:
    prio_lead  = st.slider("Belang: Levertijd", 0, 100, 30)
with prio_col3:
    prio_co2   = st.slider("Belang: Footprint", 0, 100, 20)

score_make = (100 - sales_per_part) * (prio_price/100.0) + (-res["lead_time_days"]) * (prio_lead/100.0) + (-co2_per_part) * (prio_co2/100.0)
score_buy  = (100 - (buy_total/max(Q,1))) * (prio_price/100.0) + (-res["lead_time_days"]) * (prio_lead/100.0) + (-co2_per_part) * (prio_co2/100.0)
advice_text = f"{'MAKE' if score_make >= score_buy else 'BUY'} – afgestemd op prioriteiten (Prijs:{prio_price}%, Lead:{prio_lead}%, CO₂:{prio_co2}%)"

# =============================
# UI – Resultaten
# =============================
c0, c00 = st.columns([0.5, 0.5])
c00.info(used_note)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric(tr("verkoop_stuk", lang_choice), f"€ {sales_per_part:,.2f}")
m2.metric(tr("verkoop_totaal", lang_choice), f"€ {sales_total:,.2f}")
m3.metric(tr("advies", lang_choice), decision)
m4.metric(tr("shadow_profit", lang_choice), f"€ {shadow_profit_only:,.2f}/h")
m5.metric(tr("co2pp", lang_choice), f"{co2_per_part:,.2f} kg")

st.info(advice_text)

# Kostensplitsing
split_df = pd.DataFrame({
    "Categorie":[
        tr("mat_base", lang_choice), tr("mat_conv", lang_choice), tr("mat_waste", lang_choice),
        "Inkoopdelen (BOM)","Arbeid","Machine","Energie","QA",tr("tooling", lang_choice),
        "Scrap-impact",tr("transport", lang_choice),tr("storage", lang_choice),
        tr("wip_cost", lang_choice),tr("rework", lang_choice),tr("overhead", lang_choice),
        tr("contingency", lang_choice),tr("profit", lang_choice)
    ],
    "Kosten (€)":[
        base_mat_total, conv_total, waste_total,
        bom_buy_total, res["labor_cost"], res["machine_cost"], res["energy_cost"], res["qa_cost"],
        res["tooling_cost"], res["scrap_impact"], transport_cost, storage_cost,
        res["wip_cost"], rework_cost, overhead, contingency, profit
    ]
})

left, right = st.columns([0.55,0.45], gap="large")
with left:
    st.subheader(tr("split_hdr", lang_choice))
    st.dataframe(split_df, use_container_width=True, hide_index=True)
with right:
    st.subheader(tr("chart_hdr", lang_choice))
    fig = px.pie(split_df, names="Categorie", values="Kosten (€)", hole=0.35)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Kostenopbouw (Waterfall)")
    wf_categories = ["Mat. basis","Conversie","Waste","BOM-inkoop","Arbeid","Machine","Energie","QA","Tooling","Scrap","Transport","Opslag","WIP","Rework","Overhead","Contingency","Profit"]
    wf_values = [
        base_mat_total, conv_total, waste_total, bom_buy_total,
        res["labor_cost"], res["machine_cost"], res["energy_cost"], res["qa_cost"], res["tooling_cost"],
        res["scrap_impact"], transport_cost, storage_cost, res["wip_cost"], rework_cost, overhead, contingency, profit
    ]
    fig_wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"]*len(wf_values) + ["total"],
        x=wf_categories + ["Totaal"],
        text=[f"€ {v:,.0f}" for v in wf_values] + [f"€ {sales_total:,.0f}"],
        y=wf_values + [sum(wf_values)],
    ))
    st.plotly_chart(fig_wf, use_container_width=True)

# Detail per stap (incl. CO2 energie/stap)
if res["detail"]:
    det_df = pd.DataFrame(res["detail"], columns=[
        "Step","Proces","Qty/parent","Cycle_min_eff","Setup_min","Parallel","Batch_size","Batches","Queue_days",
        "Arbeid €/st","Machine €/st","Energie €/st","QA €/st","Tooling €/st","Scrap-impact €/st","Totaal €/st",
        "Run_min","Setup_min_total","Proc_days","Step_lead_days","CO2_energy_kg/st"
    ])
    st.expander(tr("detail_hdr", lang_choice), expanded=False).dataframe(det_df, use_container_width=True, hide_index=True)

# Capaciteit & doorlooptijd
st.subheader(tr("capacity_hdr", lang_choice))
cap_df = pd.DataFrame(
    [{"Proces":k,"Belasting (h)":v,"Capaciteit (h/dag)":cap_per_process.get(k,0.0),
      "Dagen nodig": (v/max(cap_per_process.get(k,0.0),0.0001)) if cap_per_process.get(k,0.0)>0 else np.nan}
     for k,v in res["cap_hours_per_process"].items()]
).sort_values("Belasting (h)", ascending=False)
c_left, c_right = st.columns([0.6,0.4])
with c_left:
    st.dataframe(cap_df, use_container_width=True, hide_index=True)
with c_right:
    st.metric(tr("lead_time", lang_choice), f"{res['lead_time_days']:.2f}")
    st.metric(tr("bottleneck", lang_choice), bottleneck or "-")
    st.metric(tr("shadow_margin", lang_choice), f"€ {shadow_gross_margin:,.2f}/h")

# =============================
# 🔁 Scenario-vergelijker
# =============================
st.markdown("## 🔁 Scenario-vergelijker")
st.caption("Vergelijk tot 3 materialen met huidige routing & instellingen.")
all_mats = list(materials.keys())
sc_a = st.selectbox("Scenario A – materiaal", all_mats, index=all_mats.index(material) if material in all_mats else 0)
sc_b = st.selectbox("Scenario B – materiaal", all_mats, index=min(len(all_mats)-1, (all_mats.index(material)+1) if material in all_mats else 1))
enable_c = st.checkbox("Derde scenario (C) aan", value=False)
sc_c = st.selectbox("Scenario C – materiaal", all_mats, index=min(len(all_mats)-1, (all_mats.index(material)+2) if material in all_mats else 2)) if enable_c else None

def quick_eval(mat_key:str):
    m = materials[mat_key]
    p_used = mat_price_used if mat_key==material else m["price"]
    y = float(m.get("yield",1.0))
    gross = gewicht / y
    base  = gross * p_used * Q
    waste = base * float(m.get("waste",0.0))
    conv  = gross * float(m.get("conv_cost",0.0)) * Q
    mat_val_pc = gross * p_used * (1+float(m.get("waste",0.0))) + gross*float(m.get("conv_cost",0.0))
    def eval_rout():
        if routing.empty: return 0, 0, 0, 0
        mat_k = m.get("k_cycle",1.0)
        tool_pc = m.get("tool_wear_eur_pc",0.0)
        hold_rate_day = inventory_cost_year/365.0
        lc = lc_factor(Q, lc_ref, lc_b)
        labor=mach=eng=qa=tool=scrap=wip=0.0; lead=0.0; cap={}
        cum_pc = mat_val_pc + bom_buy_cost_pc
        for _, r in routing.iterrows():
            rate = machine_rates.get(r["Proces"],0.0)
            qpp=float(r["Qty_per_parent"]); cyc=float(r["Cycle_min"])*lc*mat_k
            setup=float(r["Setup_min"]); att=float(r["Attend_pct"])/100.0
            kwh=float(r["kWh_pc"]); qa_min=float(r["QA_min_pc"]); s=float(r["Scrap_pct"])
            par=max(1,int(r["Parallel_machines"])); bsize=max(1,int(r["Batch_size"])); qd=float(r["Queue_days"])
            units = Q*qpp; batches = ceil(units/bsize)
            run_min=(units*cyc)/par; setup_min=(batches*setup)/par
            labor_pc=(cyc/60)*labor_rate*att*qpp + (setup/60)*labor_rate*att/max(bsize,1)/par
            mach_pc =(cyc/60)*rate*qpp + (setup/60)*rate/max(bsize,1)/par
            eng_pc = kwh*eff_kwh_price*qpp; qa_pc=(qa_min/60)*labor_rate*qpp; tl_pc = tool_pc*qpp
            base_pc=labor_pc+mach_pc+eng_pc+qa_pc+tl_pc
            scrap_pc=(base_pc + mat_val_pc + bom_buy_cost_pc)*s/(1-min(0.9,s))
            labor+=labor_pc*Q; mach+=mach_pc*Q; eng+=eng_pc*Q; qa+=qa_pc*Q; tool+=tl_pc*Q; scrap+=scrap_pc*Q
            hours=(run_min+setup_min)/60; lead += (hours/max(hours_per_day,0.1)) + qd
            wip += (inventory_cost_year/365.0) * (qd + (hours/max(hours_per_day,0.1))/2.0) * cum_pc * Q
            cum_pc += base_pc + scrap_pc
            cap[r["Proces"]] = cap.get(r["Proces"],0.0)+hours
        proc = labor+mach+eng+qa+tool+scrap
        return proc, wip, lead, cap
    proc_cost, wip_cost, lead_days, cap = eval_rout()
    direct = (base+waste+conv) + bom_buy_total + proc_cost + transport_cost + storage_cost + wip_cost + rework_cost
    oh = direct*overhead_pct; cg = direct*contingency_pct; cost = direct + oh + cg; prof = cost*profit_pct
    sales = cost + prof
    co2pp = (gross * float(m.get("co2e_kgkg",0.0)))  # alleen materiaal voor snelle vergelijking
    bottleneck = max(cap.items(), key=lambda kv: kv[1])[0] if cap else None
    return dict(Material=mat_key, Price_per_part=sales/Q, Lead_days=lead_days, CO2_per_part=co2pp, Bottleneck=bottleneck or "-")

sc_results = [quick_eval(sc_a), quick_eval(sc_b)] + ([quick_eval(sc_c)] if enable_c else [])
sc_df = pd.DataFrame(sc_results)
st.dataframe(sc_df, use_container_width=True, hide_index=True)
st.plotly_chart(px.bar(sc_df, x="Material", y="Price_per_part", title="Prijs per stuk (scenario’s)"), use_container_width=True)

# =============================
# Monte-Carlo (optioneel)
# =============================
if mc_on:
    st.subheader(tr("mc_results", lang_choice))
    rng=np.random.default_rng(42)
    mat_mul=rng.normal(1.0, sd_mat, size=mc_iter)
    cyc_mul=rng.normal(1.0, sd_cycle, size=mc_iter)
    scrap_add=np.clip(rng.normal(0.0, sd_scrap, size=mc_iter), -0.49, 0.9)
    mc_vals=[]
    for i in range(mc_iter):
        m_total=(bruto_kg_pc*mat_price_used*(1+float(mat.get("waste",0.0)))+bruto_kg_pc*float(mat.get("conv_cost",0.0)))*mat_mul[i]*Q + bom_buy_total
        mod=routing.copy()
        if not mod.empty:
            mod["Cycle_min"]=mod["Cycle_min"]*(lc_fac*materials[material].get("k_cycle",1.0)*cyc_mul[i])
            mod["Scrap_pct"]=np.clip(mod["Scrap_pct"]+scrap_add[i], 0.0, 0.9)
        res_mc=compute_costs_routing(mod)
        d=m_total+res_mc["proc_cost"]+transport_cost+(storage_days/365.0)*inventory_cost_year*(res_mc["proc_cost"])+res_mc["wip_cost"]+rework_cost
        oh=d*overhead_pct; cg=d*contingency_pct; ct=d+oh+cg; pf=ct*profit_pct
        sale_pp=(ct+pf)/Q; mc_vals.append(sale_pp)
    mc_vals=np.array(mc_vals)
    cc1,cc2,cc3=st.columns(3)
    cc1.metric(tr("p50", lang_choice), f"€ {np.percentile(mc_vals,50):,.2f}")
    cc2.metric(tr("p80", lang_choice), f"€ {np.percentile(mc_vals,80):,.2f}")
    cc3.metric(tr("p90", lang_choice), f"€ {np.percentile(mc_vals,90):,.2f}")
    st.plotly_chart(px.histogram(pd.DataFrame({"€/stuk":mc_vals}), x="€/stuk", nbins=40), use_container_width=True)

# =============================
# Export — PDF & Excel
# =============================
def build_pdf(project, Q, material, sales_pp, sales_total, split_df, used_note, lang,
              bruto_kg_pc, yield_fac, conv_cost, waste_frac, lead_days, bottleneck, co2pp, client_info,
              top_drivers=3, advice_text=""):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4); W,H = A4

    # Page 1: Summary
    y = H - 40
    c.setFont("Helvetica-Bold", 14); c.drawString(40,y, f"{tr('app_title',lang)} – {project}"); y-=18
    c.setFont("Helvetica",10)
    c.drawString(40,y, f"Datum/Date: {date.today().isoformat()}"); y-=14
    if client_info.get("Company") or client_info.get("Contact"):
        c.drawString(40,y, f"Client: {client_info.get('Company','')}  |  {client_info.get('Contact','')}"); y-=14
    if client_info.get("Email") or client_info.get("Phone"):
        c.drawString(40,y, f"Email: {client_info.get('Email','')}  |  Phone: {client_info.get('Phone','')}"); y-=14
    if client_info.get("RFQ"):
        c.drawString(40,y, f"RFQ: {client_info.get('RFQ')}"); y-=14

    c.drawString(40,y, f"{tr('qty',lang)}: {Q}  |  {tr('material',lang)}: {material}"); y-=14
    c.drawString(40,y, used_note); y-=10
    c.drawString(40,y, f"Bruto kg/st: {bruto_kg_pc:.3f} / Yield: {yield_fac:.2f} / Conv€/kg: {conv_cost:.2f} / Waste: {waste_frac:.2f}"); y-=10
    c.drawString(40,y, f"Lead time: {lead_days:.2f} d  |  Bottleneck: {bottleneck or '-'}"); y-=10
    c.drawString(40,y, f"CO₂ per stuk: {co2pp:.2f} kg"); y-=16

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40,y, f"{tr('verkoop_stuk',lang)}: € {sales_pp:,.2f}"); y-=16
    c.drawString(40,y, f"{tr('verkoop_totaal',lang)}: € {sales_total:,.2f}"); y-=20

    c.setFont("Helvetica-Bold", 11); c.drawString(40,y, "Belangrijkste kostendrivers:"); y-=12
    sd = split_df.sort_values("Kosten (€)", ascending=False).head(top_drivers)
    for _,r in sd.iterrows():
        c.setFont("Helvetica",10); c.drawString(50,y, f"• {r['Categorie']}: € {r['Kosten (€)']:.2f}"); y-=12

    y -= 6
    c.setFont("Helvetica-Bold", 11); c.drawString(40,y, "Advies:"); y-=12
    c.setFont("Helvetica",10); c.drawString(50,y, advice_text); y-=14

    c.showPage()

    # Page 2: Detailed breakdown
    y = H - 40
    c.setFont("Helvetica-Bold", 12); c.drawString(40,y, "Kostensplitsing – Details"); y-=18
    data = [["Categorie","Kosten (€)"]] + [[r["Categorie"], f"€ {r['Kosten (€)']:.2f}"] for _,r in split_df.iterrows()]
    tbl = Table(data, colWidths=[260, 120])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(1,0), colors.lightgrey),
        ('GRID',(0,0),(-1,-1), 0.25, colors.grey),
        ('ALIGN',(1,1),(1,-1),'RIGHT'),
        ('FONT',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONT',(0,1),(-1,-1),'Helvetica'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.whitesmoke, colors.lightyellow]),
    ]))
    tw, th = tbl.wrapOn(c, 40, y)
    tbl.drawOn(c, 40, max(40, y - th))

    c.showPage(); c.save(); buf.seek(0)
    return buf

exp_col1, exp_col2 = st.columns(2)
with exp_col1:
    pdf_buf = build_pdf(project,Q,material,sales_per_part,sales_total,split_df,used_note,lang_choice,
                        bruto_kg_pc,yield_fac,float(mat.get("conv_cost",0.0)),float(mat.get("waste",0.0)),
                        res["lead_time_days"], bottleneck, co2_per_part, client_info, advice_text=advice_text)
    st.download_button(tr("pdf_btn", lang_choice), data=pdf_buf,
                       file_name=f"Offerte_{project}.pdf", mime="application/pdf")
with exp_col2:
    xls_buf=io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="xlsxwriter") as xlw:
        split_df.to_excel(xlw, index=False, sheet_name="Cost_Split")
        if res["detail"]:
            det_df.to_excel(xlw, index=False, sheet_name="Routing")
        if not bom_buy.empty:
            bom_buy.to_excel(xlw, index=False, sheet_name="BOM_Buy")
        if res["cap_hours_per_process"]:
            cap_tab=pd.DataFrame(
                [{"Proces":k,"Belasting (h)":v,"Capaciteit (h/dag)":cap_per_process.get(k,0.0),
                  "Dagen nodig": (v/max(cap_per_process.get(k,0.0),0.0001)) if cap_per_process.get(k,0.0)>0 else np.nan}
                 for k,v in res["cap_hours_per_process"].items()]
            ).sort_values("Belasting (h)", ascending=False)
            cap_tab.to_excel(xlw, index=False, sheet_name="Capacity")
        # Meta
        meta = pd.DataFrame({
            "Key":[
                "Project","Q","Material","Net_kg_per_part","Gross_kg_per_part","Yield","Conv_cost_per_kg","Waste_frac",
                "LC_b","LC_ref","TOU_day","TOU_eve","TOU_night",
                "E_price_day","E_price_eve","E_price_night","Used_price_note",
                "Lead_time_days","Bottleneck","CO2_per_part_kg",
                "Shadow_per_h_profit","Shadow_per_h_gross_margin"
            ],
            "Value":[
                project,Q,material,gewicht,bruto_kg_pc,yield_fac,float(mat.get("conv_cost",0.0)),float(mat.get("waste",0.0)),
                lc_b,lc_ref,tou_day,tou_eve,tou_night,price_day,price_eve,price_night,used_note,
                res["lead_time_days"], bottleneck or "", co2_per_part,
                shadow_profit_only, shadow_gross_margin
            ]
        })
        meta.to_excel(xlw, index=False, sheet_name="Meta")
        # Client info tab
        pd.DataFrame(list(client_info.items()), columns=["Field","Value"]).to_excel(xlw, index=False, sheet_name="Client_Info")
        # Forecast
        df_fc.to_excel(xlw, index=False, sheet_name="Forecast")
        # Summary_KPIs (PowerBI)
        summary_kpis = pd.DataFrame({
            "KPI":[
                "Sales_per_part","Sales_total","Lead_time_days","CO2_per_part",
                "Bottleneck","Shadow_per_h_profit","Shadow_per_h_gross_margin",
                "Priority_Price","Priority_Lead","Priority_CO2"
            ],
            "Value":[
                sales_per_part, sales_total, res["lead_time_days"], co2_per_part,
                bottleneck or "", shadow_profit_only, shadow_gross_margin,
                prio_price, prio_lead, prio_co2
            ]
        })
        summary_kpis.to_excel(xlw, index=False, sheet_name="Summary_KPIs")
        # Scenarios
        if len(sc_df) > 0:
            sc_df.to_excel(xlw, index=False, sheet_name="Scenarios")
    xls_buf.seek(0)
    st.download_button(tr("xls_btn", lang_choice), data=xls_buf,
                       file_name=f"Cost_{project}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
