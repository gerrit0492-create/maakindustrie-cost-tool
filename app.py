import io
from math import ceil
from datetime import date
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

st.set_page_config(page_title="Maakindustrie Cost Tool+",
                   layout="wide",
                   page_icon="⚙️")

# =============================
# i18n / Meertaligheid
# =============================
TXT = {
    "app_title":        {"nl": "Maakindustrie Cost Tool+", "en": "Manufacturing Cost Tool+"},
    "app_caption":      {"nl": "Incl. BOM routing, Learning curve, TOU-energie, Forecast, WIP/Capaciteit, Monte-Carlo, PDF/Excel",
                         "en": "Incl. BOM routing, Learning curve, TOU energy, Forecast, WIP/Capacity, Monte Carlo, PDF/Excel"},
    "lang":             {"nl": "Taal / Language", "en": "Language / Taal"},
    "sidebar_input":    {"nl": "🔧 Invoer", "en": "🔧 Inputs"},
    "project":          {"nl": "Projectnaam", "en": "Project name"},
    "qty":              {"nl": "Aantal stuks (Q)", "en": "Quantity (Q)"},
    "material":         {"nl": "Materiaal", "en": "Material"},
    "net_weight":       {"nl": "Netto gewicht per stuk (kg)", "en": "Net weight per part (kg)"},
    "learning_curve":   {"nl": "Learning curve (op cyclustijd)", "en": "Learning curve (on cycle time)"},
    "lc_b":             {"nl": "b-exponent (negatief)", "en": "b-exponent (negative)"},
    "lc_ref":           {"nl": "RefQty", "en": "RefQty"},
    "tou":              {"nl": "Energie (TOU)", "en": "Energy (TOU)"},
    "price_day":        {"nl": "Dagprijs €/kWh", "en": "Day price €/kWh"},
    "price_eve":        {"nl": "Avondprijs €/kWh", "en": "Evening price €/kWh"},
    "price_night":      {"nl": "Nachtprijs €/kWh", "en": "Night price €/kWh"},
    "share_day":        {"nl": "Share dag", "en": "Share day"},
    "share_eve":        {"nl": "Share avond", "en": "Share evening"},
    "lean_hdr":         {"nl": "Lean / Logistiek", "en": "Lean / Logistics"},
    "rework_pct":       {"nl": "Rework % (op proceskosten)", "en": "Rework % (on process costs)"},
    "transport_min":    {"nl": "Transport (min/stuk)", "en": "Transport (min/part)"},
    "storage_days":     {"nl": "Opslag (dagen batch)", "en": "Storage (days per batch)"},
    "inventory_rate":   {"nl": "Voorraadkosten %/jaar", "en": "Inventory cost %/year"},
    "plant_hdr":        {"nl": "Fabriek / Capaciteit", "en": "Plant / Capacity"},
    "hours_per_day":    {"nl": "Uren productie per dag", "en": "Production hours per day"},
    "cap_per_process":  {"nl": "Capaciteit per proces (uren/dag)", "en": "Capacity per process (hours/day)"},
    "mvb_hdr":          {"nl": "Make vs Buy", "en": "Make vs Buy"},
    "buy_price":        {"nl": "Inkoopprijs/stuk (€)", "en": "Purchase price/part (€)"},
    "moq":              {"nl": "MOQ", "en": "MOQ"},
    "buy_transport":    {"nl": "Transport/handling (€/stuk)", "en": "Transport/handling (€/part)"},
    "mc_hdr":           {"nl": "Monte-Carlo (onzekerheid)", "en": "Monte Carlo (uncertainty)"},
    "mc_enable":        {"nl": "Monte-Carlo simulatie aan", "en": "Enable Monte Carlo simulation"},
    "mc_iter":          {"nl": "Iteraties", "en": "Iterations"},
    "sd_mat":           {"nl": "σ materiaalprijs (%)", "en": "σ material price (%)"},
    "sd_cycle":         {"nl": "σ cyclustijd (%)", "en": "σ cycle time (%)"},
    "sd_scrap":         {"nl": "σ scrap additief (abs)", "en": "σ scrap additive (abs)"},
    "forecast_hdr":     {"nl": "Materiaal prijs forecast", "en": "Material price forecast"},
    "horizon":          {"nl": "Horizon (maanden)", "en": "Horizon (months)"},
    "method":           {"nl": "Methode", "en": "Method"},
    "drift_abs":        {"nl": "Drift (€/kg per maand)", "en": "Drift (€/kg per month)"},
    "drift_pct":        {"nl": "Drift (% per maand)", "en": "Drift (% per month)"},
    "sigma_pct":        {"nl": "Onzekerheid σ (%/mnd)", "en": "Uncertainty σ (%/month)"},
    "use_fc":           {"nl": "Gebruik voorspelde prijs in kostprijs", "en": "Use forecasted price in costing"},
    "month_t":          {"nl": "Gebruik maand t=", "en": "Use month t="},
    "routing_hdr":      {"nl": "🧭 Routing (BOM-stappen)", "en": "🧭 Routing (BOM steps)"},
    "routing_cap":      {"nl": "Definieer alle bewerkingen in volgorde. Setup over batch; scrap per stap propageert.",
                         "en": "Define all operations in order. Setup over batch; step scrap propagates."},
    "bom_buy_hdr":      {"nl": "🧾 BOM – Ingekochte onderdelen", "en": "🧾 BOM – Purchased components"},
    "bom_buy_cap":      {"nl": "Inkoopregels tellen per eindproduct; scrapt mee in routing.", "en": "Purchase items per finished unit; scrape cascades in routing."},
    "verkoop_stuk":     {"nl": "Verkoopprijs/stuk", "en": "Sales price/part"},
    "verkoop_totaal":   {"nl": "Totale verkoopprijs", "en": "Total sales price"},
    "advies":           {"nl": "Advies", "en": "Recommendation"},
    "split_hdr":        {"nl": "💰 Kostensplitsing", "en": "💰 Cost breakdown"},
    "chart_hdr":        {"nl": "📊 Visualisaties (Plotly)", "en": "📊 Visualizations (Plotly)"},
    "trend_hdr":        {"nl": "📈 Voorspelde prijs", "en": "📈 Forecasted price"},
    "detail_hdr":       {"nl": "🔎 Detail per stap (€/stuk)", "en": "🔎 Per-step detail (€/part)"},
    "capacity_hdr":     {"nl": "🏭 Capaciteit & Doorlooptijd", "en": "🏭 Capacity & Lead time"},
    "lead_time":        {"nl": "Totale doorlooptijd (dagen)", "en": "Total lead time (days)"},
    "bottleneck":       {"nl": "Bottleneck (proces)", "en": "Bottleneck (process)"},
    "p50":              {"nl": "P50 €/stuk", "en": "P50 €/part"},
    "p80":              {"nl": "P80 €/stuk", "en": "P80 €/part"},
    "p90":              {"nl": "P90 €/stuk", "en": "P90 €/part"},
    "pdf_btn":          {"nl": "📄 Download offerte (PDF)", "en": "📄 Download quote (PDF)"},
    "xls_btn":          {"nl": "📊 Download Excel", "en": "📊 Download Excel"},
    "make":             {"nl": "MAKE", "en": "MAKE"},
    "buy":              {"nl": "BUY", "en": "BUY"},
    "used_price":       {"nl": "Gebruikte materiaalprijs", "en": "Material price used"},
    "month":            {"nl": "maand", "en": "month"},
    "tooling":          {"nl": "Tooling/Consumables", "en": "Tooling/Consumables"},
    "material_lbl":     {"nl": "Materiaal", "en": "Material"},
    "mat_base":         {"nl": "Materiaal (basis)", "en": "Material (base)"},
    "mat_conv":         {"nl": "Conversie (gieten/smeden/extrusie)", "en": "Conversion (casting/forging/extrusion)"},
    "mat_waste":        {"nl": "Materiaalverlies/waste", "en": "Material waste"},
    "wip_cost":         {"nl": "WIP/Flow holding", "en": "WIP/Flow holding"},
    "transport":        {"nl": "Transport", "en": "Transport"},
    "storage":          {"nl": "Opslag", "en": "Storage"},
    "rework":           {"nl": "Rework", "en": "Rework"},
    "overhead":         {"nl": "Overhead", "en": "Overhead"},
    "contingency":      {"nl": "Contingency", "en": "Contingency"},
    "profit":           {"nl": "Profit", "en": "Profit"},
}

def tr(key: str, lang: str = "nl", **fmt):
    s = TXT.get(key, {}).get(lang, key)
    return s.format(**fmt) if fmt else s

# =============================
# Materialen (incl. ruwe vormen)
# =============================
materials = {
    # --- Koolstof / Constructie ---
    "S235JR_steel": {"price": 1.40, "waste": 0.08, "k_cycle": 1.00, "tool_wear_eur_pc": 0.02},
    "S355J2_steel": {"price": 1.70, "waste": 0.08, "k_cycle": 1.05, "tool_wear_eur_pc": 0.03},
    "C45":          {"price": 1.90, "waste": 0.06, "k_cycle": 1.10, "tool_wear_eur_pc": 0.05},
    "42CrMo4":      {"price": 2.60, "waste": 0.06, "k_cycle": 1.20, "tool_wear_eur_pc": 0.07},

    # --- RVS / Hoog gelegeerd ---
    "SS304":        {"price": 3.50, "waste": 0.06, "k_cycle": 1.15, "tool_wear_eur_pc": 0.06},
    "SS316L":       {"price": 4.20, "waste": 0.06, "k_cycle": 1.20, "tool_wear_eur_pc": 0.08},
    "SS904L":       {"price": 8.50, "waste": 0.06, "k_cycle": 1.25, "tool_wear_eur_pc": 0.10},

    # --- Duplex / Super Duplex ---
    "1.4462_Duplex":    {"price": 5.50, "waste": 0.07, "k_cycle": 1.30, "tool_wear_eur_pc": 0.12},
    "SuperDuplex_2507": {"price": 7.50, "waste": 0.07, "k_cycle": 1.45, "tool_wear_eur_pc": 0.18},

    # --- Aluminium / Koper ---
    "Al_6082":          {"price": 4.20, "waste": 0.07, "k_cycle": 0.80, "tool_wear_eur_pc": 0.01},
    "Cast_Aluminium":   {"price": 3.20, "waste": 0.07, "k_cycle": 0.90, "tool_wear_eur_pc": 0.02},
    "Cu_ECW":           {"price": 8.00, "waste": 0.05, "k_cycle": 1.10, "tool_wear_eur_pc": 0.05},

    # --- Castings (gietwerk) ---
    "Cast_Steel_GS45":  {"price": 1.60, "waste": 0.05, "yield": 0.80, "conv_cost": 0.80, "k_cycle": 1.10, "tool_wear_eur_pc": 0.05},
    "Cast_Iron_GG25":   {"price": 1.20, "waste": 0.05, "yield": 0.85, "conv_cost": 0.60, "k_cycle": 1.05, "tool_wear_eur_pc": 0.04},
    "Cast_AlSi10Mg":    {"price": 3.00, "waste": 0.05, "yield": 0.75, "conv_cost": 1.00, "k_cycle": 0.90, "tool_wear_eur_pc": 0.02},

    # --- Forgings (smeedwerk) ---
    "Forged_C45":       {"price": 1.90, "waste": 0.04, "yield": 0.90, "conv_cost": 1.20, "k_cycle": 1.20, "tool_wear_eur_pc": 0.06},
    "Forged_42CrMo4":   {"price": 2.80, "waste": 0.04, "yield": 0.92, "conv_cost": 1.40, "k_cycle": 1.30, "tool_wear_eur_pc": 0.08},
    "Forged_1.4462":    {"price": 6.00, "waste": 0.04, "yield": 0.88, "conv_cost": 1.60, "k_cycle": 1.40, "tool_wear_eur_pc": 0.12},

    # --- Extrusions (extrusie) ---
    "Extruded_Al_6060": {"price": 3.50, "waste": 0.03, "yield": 0.95, "conv_cost": 0.50, "k_cycle": 0.85, "tool_wear_eur_pc": 0.01},
    "Extruded_Cu":      {"price": 7.50, "waste": 0.03, "yield": 0.92, "conv_cost": 0.70, "k_cycle": 1.10, "tool_wear_eur_pc": 0.05},
}

# Tarieven (€/uur)
machine_rates = {"CNC": 85.0, "Laser": 110.0, "Lassen": 55.0, "Buigen": 75.0, "Montage": 40.0}
labor_rate = 45.0
overhead_pct = 0.20
profit_pct = 0.12
contingency_pct = 0.05

# =============================
# Sidebar – Invoer
# =============================
lang_choice = st.sidebar.selectbox(TXT["lang"]["nl"], options=["nl", "en"], index=0,
                                   format_func=lambda x: "Nederlands" if x=="nl" else "English")

st.title(tr("app_title", lang_choice))
st.caption(tr("app_caption", lang_choice))

st.sidebar.header(tr("sidebar_input", lang_choice))
project = st.sidebar.text_input(tr("project", lang_choice), "Demo")
Q = st.sidebar.number_input(tr("qty", lang_choice), min_value=1, value=50, step=1)
material = st.sidebar.selectbox(tr("material", lang_choice), list(materials.keys()))
gewicht = st.sidebar.number_input(tr("net_weight", lang_choice), min_value=0.01, value=2.0)

# Learning curve
st.sidebar.subheader(tr("learning_curve", lang_choice))
lc_b = st.sidebar.number_input(tr("lc_b", lang_choice), value=-0.15, step=0.01, format="%.2f")
lc_ref = st.sidebar.number_input(tr("lc_ref", lang_choice), min_value=1, value=10, step=1)

# TOU energie
st.sidebar.subheader(tr("tou", lang_choice))
price_day = st.sidebar.number_input(tr("price_day", lang_choice), value=0.24, step=0.01)
price_eve = st.sidebar.number_input(tr("price_eve", lang_choice), value=0.18, step=0.01)
price_night = st.sidebar.number_input(tr("price_night", lang_choice), value=0.12, step=0.01)
tou_day = st.sidebar.slider(tr("share_day", lang_choice), 0.0, 1.0, 0.60, 0.05)
tou_eve = st.sidebar.slider(tr("share_eve", lang_choice), 0.0, 1.0, 0.30, 0.05)
tou_night = max(0.0, 1.0 - tou_day - tou_eve)
st.sidebar.caption(f"Night share: {tou_night:.2f}")

# Fabriek / capaciteit
st.sidebar.subheader(tr("plant_hdr", lang_choice))
hours_per_day = st.sidebar.number_input(tr("hours_per_day", lang_choice), 1.0, 24.0, 8.0, step=0.5)
with st.sidebar.expander(tr("cap_per_process", lang_choice), expanded=False):
    cap_per_process = {}
    for p in machine_rates.keys():
        cap_per_process[p] = st.number_input(f"{p} (h/dag)", 0.0, 24.0, 8.0, key=f"cap_{p}")

# Lean & logistiek
st.sidebar.subheader(tr("lean_hdr", lang_choice))
rework_pct = st.sidebar.number_input(tr("rework_pct", lang_choice), 0.0, 1.0, 0.05, step=0.01)
transport_min = st.sidebar.number_input(tr("transport_min", lang_choice), 0.0, 60.0, 0.5)
storage_days = st.sidebar.number_input(tr("storage_days", lang_choice), 0, 365, 30)
inventory_cost_year = st.sidebar.number_input(tr("inventory_rate", lang_choice), 0.0, 1.0, 0.12, step=0.01)

# Make vs Buy
st.sidebar.subheader(tr("mvb_hdr", lang_choice))
buy_price = st.sidebar.number_input(tr("buy_price", lang_choice), 0.0, 1e6, 15.0)
moq = st.sidebar.number_input(tr("moq", lang_choice), 1, 100000, 250)
transport_buy = st.sidebar.number_input(tr("buy_transport", lang_choice), 0.0, 1e6, 0.6)

# Monte-Carlo
st.sidebar.subheader(tr("mc_hdr", lang_choice))
mc_on = st.sidebar.checkbox(tr("mc_enable", lang_choice), value=False)
mc_iter = st.sidebar.number_input(tr("mc_iter", lang_choice), 100, 20000, 1000, step=100)
sd_mat = st.sidebar.number_input(tr("sd_mat", lang_choice), 0.0, 0.5, 0.05, step=0.01)
sd_cycle = st.sidebar.number_input(tr("sd_cycle", lang_choice), 0.0, 0.5, 0.08, step=0.01)
sd_scrap = st.sidebar.number_input(tr("sd_scrap", lang_choice), 0.0, 0.5, 0.01, step=0.005)

# Forecast controls
st.sidebar.subheader(tr("forecast_hdr", lang_choice))
forecast_horizon = st.sidebar.slider(tr("horizon", lang_choice), 1, 12, 12)
forecast_method = st.sidebar.selectbox(tr("method", lang_choice),
                                       ["Drift (€/mnd)", "Drift (%/mnd) + onzekerheid"])
drift_abs = st.sidebar.number_input(tr("drift_abs", lang_choice), value=0.00, step=0.05, format="%.2f")
drift_pct = st.sidebar.number_input(tr("drift_pct", lang_choice), value=0.00, step=0.01, format="%.2f")
sigma_pct = st.sidebar.number_input(tr("sigma_pct", lang_choice), value=1.50, step=0.25, format="%.2f")
use_forecast_for_cost = st.sidebar.checkbox(tr("use_fc", lang_choice), value=False)
quote_month_offset = st.sidebar.slider(tr("month_t", lang_choice), 0, forecast_horizon, 0)

# =============================
# HELPER functies
# =============================
def lc_factor(Q, ref, b):
    try:
        return (max(Q, 1) / max(ref, 1)) ** b
    except Exception:
        return 1.0

def forecast_series(p0: float, months: int, method: str,
                    drift_abs: float, drift_pct: float, sigma_pct: float, seed: int = 42):
    idx = pd.date_range(date.today(), periods=months+1, freq="MS")
    if method == "Drift (€/mnd)":
        vals = [max(0.01, p0 + i*drift_abs) for i in range(months+1)]
        return pd.DataFrame({"Datum": idx, "€/kg": vals})
    rng = np.random.default_rng(seed)
    vals = [p0]; low = [p0]; high = [p0]
    for _ in range(months):
        mu = 1.0 + drift_pct/100.0
        shock = rng.normal(0.0, sigma_pct/100.0)
        nxt = max(0.01, vals[-1]*(mu + shock))
        vals.append(nxt)
        trend_val = vals[-2]*mu
        low.append(max(0.01, trend_val*(1 - 2*sigma_pct/100.0)))
        high.append(trend_val*(1 + 2*sigma_pct/100.0))
    return pd.DataFrame({"Datum": idx, "€/kg": vals, "Low": low, "High": high})

# =============================
# FORECAST bouwen
# =============================
mat = materials[material]
p0 = mat["price"]
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
    try:
        mat_price_used = float(df_fc.loc[df_fc.index[quote_month_offset], "€/kg"])
    except Exception:
        mat_price_used = p0
    used_note = f"{tr('used_price', lang_choice)}: € {mat_price_used:.2f}/kg ({tr('month', lang_choice)} t={quote_month_offset})"
else:
    mat_price_used = p0
    used_note = f"{tr('used_price', lang_choice)}: € {mat_price_used:.2f}/kg (t=0)"

# =============================
# ROUTING (BOM-stappen)
# =============================
st.markdown(f"## {tr('routing_hdr', lang_choice)}")
st.caption(tr("routing_cap", lang_choice))

process_choices = list(machine_rates.keys())
default_routing = pd.DataFrame([
    {"Step": 10, "Proces": "CNC",     "Qty_per_parent": 1.0, "Cycle_min": 7.5, "Setup_min": 30.0, "Attend_pct": 100,
     "kWh_pc": 0.2, "QA_min_pc": 0.5, "Scrap_pct": 0.02, "Parallel_machines": 1, "Batch_size": 50, "Queue_days": 0.5},
    {"Step": 20, "Proces": "Lassen",  "Qty_per_parent": 1.0, "Cycle_min": 8.0, "Setup_min": 15.0, "Attend_pct": 100,
     "kWh_pc": 0.3, "QA_min_pc": 0.6, "Scrap_pct": 0.01, "Parallel_machines": 1, "Batch_size": 50, "Queue_days": 0.5},
    {"Step": 30, "Proces": "Montage", "Qty_per_parent": 1.0, "Cycle_min": 6.0, "Setup_min": 10.0, "Attend_pct": 100,
     "kWh_pc": 0.1, "QA_min_pc": 1.0, "Scrap_pct": 0.00, "Parallel_machines": 1, "Batch_size": 50, "Queue_days": 0.2},
])

routing = st.data_editor(
    default_routing,
    key="routing_editor",
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Proces": st.column_config.SelectboxColumn(options=process_choices, required=True),
        "Step": st.column_config.NumberColumn(help="Volgorde (bijv. 10, 20, 30)"),
        "Qty_per_parent": st.column_config.NumberColumn(help="Hoe vaak deze stap per eindproduct"),
        "Cycle_min": st.column_config.NumberColumn(help="Minuten per stuk"),
        "Setup_min": st.column_config.NumberColumn(help="Omsteltijd per batch (min)"),
        "Attend_pct": st.column_config.NumberColumn(help="Operator attentie (%)"),
        "kWh_pc": st.column_config.NumberColumn(help="Energie (kWh/stuk)"),
        "QA_min_pc": st.column_config.NumberColumn(help="QA (min/stuk)"),
        "Scrap_pct": st.column_config.NumberColumn(help="Scrap fractie 0–1"),
        "Parallel_machines": st.column_config.NumberColumn(help="Gelijktijdige machines"),
        "Batch_size": st.column_config.NumberColumn(help="Batchgrootte deze stap"),
        "Queue_days": st.column_config.NumberColumn(help="Wachttijd vóór stap (dagen)"),
    }
).sort_values("Step").reset_index(drop=True)

# =============================
# BOM – Ingekochte onderdelen
# =============================
st.markdown(f"## {tr('bom_buy_hdr', lang_choice)}")
st.caption(tr("bom_buy_cap", lang_choice))

default_bom_buy = pd.DataFrame([
    {"Item": "Bevestigingsset", "UnitCost_eur": 1.20, "Qty_per_parent": 1.0, "Scrap_pct": 0.00},
])
bom_buy = st.data_editor(
    default_bom_buy,
    key="bom_buy_editor",
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Item": st.column_config.TextColumn(),
        "UnitCost_eur": st.column_config.NumberColumn(help="€ per stuk component"),
        "Qty_per_parent": st.column_config.NumberColumn(help="Aantal per eindproduct"),
        "Scrap_pct": st.column_config.NumberColumn(help="Scrap fractie 0–1"),
    }
)

if not bom_buy.empty:
    bom_buy_cost_pc = (bom_buy["UnitCost_eur"] * bom_buy["Qty_per_parent"] / (1 - bom_buy["Scrap_pct"].clip(upper=0.9))).sum()
else:
    bom_buy_cost_pc = 0.0
bom_buy_total = bom_buy_cost_pc * Q

# =============================
# Materiaalcomponent (yield + conv + waste)
# =============================
yield_fac = float(mat.get("yield", 1.0))
bruto_kg_pc = gewicht / yield_fac
base_mat_total = bruto_kg_pc * mat_price_used * Q
waste_total = base_mat_total * float(mat.get("waste", 0.0))
conv_total = bruto_kg_pc * float(mat.get("conv_cost", 0.0)) * Q
mat_cost_total = base_mat_total + waste_total + conv_total
mat_value_pc = bruto_kg_pc * mat_price_used * (1 + float(mat.get("waste",0.0))) + bruto_kg_pc * float(mat.get("conv_cost",0.0))

# Energieprijs mix
eff_kwh_price = (tou_day*price_day + tou_eve*price_eve + tou_night*price_night)
lc_fac = lc_factor(Q, lc_ref, lc_b)

# =============================
# Routing-berekening met batches, parallel & WIP
# =============================
def compute_costs_routing(routing_df):
    if routing_df is None or routing_df.empty:
        return dict(proc_cost=0.0, labor_cost=0.0, machine_cost=0.0, energy_cost=0.0,
                    qa_cost=0.0, tooling_cost=0.0, scrap_impact=0.0, wip_cost=0.0,
                    detail=[], cap_hours_per_process={}, lead_time_days=0.0, bottleneck=None)

    mat_k = materials[material].get("k_cycle", 1.0)
    tool_pc_base = materials[material].get("tool_wear_eur_pc", 0.0)
    hold_rate_day = inventory_cost_year / 365.0

    rows = []
    labor_total = machine_total = energy_total = qa_total = scrap_total = tooling_total = 0.0
    wip_total = 0.0
    cap_hours = {}
    cum_cost_pc_before = (mat_value_pc + bom_buy_cost_pc)  # waarde vóór stap 1
    total_lead_days = 0.0

    for _, r in routing_df.iterrows():
        p = r["Proces"]; rate = machine_rates.get(p, 0.0)
        qty_per_parent = float(r.get("Qty_per_parent", 1.0))
        cyc = float(r.get("Cycle_min", 0.0)) * lc_fac * mat_k
        setup = float(r.get("Setup_min", 0.0))
        attend_frac = float(r.get("Attend_pct", 100))/100.0
        kwh_pc = float(r.get("kWh_pc", 0.0))
        qa_min = float(r.get("QA_min_pc", 0.0))
        scrap = float(r.get("Scrap_pct", 0.0))
        parallel = max(1, int(r.get("Parallel_machines", 1)))
        batch_size = max(1, int(r.get("Batch_size", max(Q,1))))
        queue_days = max(0.0, float(r.get("Queue_days", 0.0)))

        units = Q * qty_per_parent
        batches = ceil(units / batch_size)

        # minuten
        run_min = (units * cyc) / parallel
        setup_min_total = (batches * setup) / parallel

        # kosten per stuk (op basis van 1x uitvoering + uitgesmeerde setup)
        labor_pc = (cyc/60.0) * labor_rate * attend_frac * qty_per_parent + (setup/60.0) * labor_rate * attend_frac / max(batch_size,1) / parallel
        mach_pc  = (cyc/60.0) * rate * qty_per_parent + (setup/60.0) * rate / max(batch_size,1) / parallel
        energy_pc = kwh_pc * eff_kwh_price * qty_per_parent
        qa_pc    = (qa_min/60.0) * labor_rate * qty_per_parent
        tool_pc  = tool_pc_base * qty_per_parent

        base_pc = labor_pc + mach_pc + energy_pc + qa_pc + tool_pc
        scrap_imp_pc = (base_pc + mat_value_pc + bom_buy_cost_pc) * scrap / (1 - min(0.9, scrap))

        # totals
        labor_total   += labor_pc  * Q
        machine_total += mach_pc   * Q
        energy_total  += energy_pc * Q
        qa_total      += qa_pc     * Q
        tooling_total += tool_pc   * Q
        scrap_total   += scrap_imp_pc * Q

        # capaciteitsbelasting (machine-uren)
        step_mach_hours = (run_min + setup_min_total) / 60.0
        cap_hours[p] = cap_hours.get(p, 0.0) + step_mach_hours

        # doorlooptijd (productiedagen + wachttijd)
        proc_days = step_mach_hours / max(hours_per_day, 0.1)  # eenvoudige benadering
        step_lead = queue_days + proc_days
        total_lead_days += step_lead

        # WIP holding (queue + half process): waarde vóór stap * tijd
        wip_days = queue_days + proc_days/2.0
        wip_total += hold_rate_day * wip_days * cum_cost_pc_before * Q

        # waarde na stap (voor volgende WIP)
        cum_cost_pc_before += base_pc + scrap_imp_pc

        rows.append([
            int(r.get("Step", 0)), p, qty_per_parent, cyc, setup, parallel, batch_size, batches, queue_days,
            labor_pc, mach_pc, energy_pc, qa_pc, tool_pc, scrap_imp_pc, base_pc + scrap_imp_pc,
            run_min, setup_min_total, proc_days, step_lead
        ])

    # proc som
    proc_total = labor_total + machine_total + energy_total + qa_total + tooling_total + scrap_total
    bottleneck_proc = max(cap_hours.items(), key=lambda kv: kv[1])[0] if cap_hours else None

    return dict(
        proc_cost=proc_total, labor_cost=labor_total, machine_cost=machine_total, energy_cost=energy_total,
        qa_cost=qa_total, tooling_cost=tooling_total, scrap_impact=scrap_total, wip_cost=wip_total,
        detail=rows, cap_hours_per_process=cap_hours, lead_time_days=total_lead_days, bottleneck=bottleneck_proc
    )

res = compute_costs_routing(routing)

# Overige posten (transport/opslag/rework)
transport_cost = (transport_min/60.0) * labor_rate * Q
storage_cost = (storage_days/365.0) * inventory_cost_year * (res["proc_cost"])
rework_cost = rework_pct * res["proc_cost"]

# Totale kosten
direct_cost = mat_cost_total + bom_buy_total + res["proc_cost"] + transport_cost + storage_cost + res["wip_cost"] + rework_cost
overhead = direct_cost * overhead_pct
contingency = direct_cost * contingency_pct
cost_total = direct_cost + overhead + contingency
profit = cost_total * profit_pct
sales_total = cost_total + profit
sales_per_part = sales_total / Q

# Make vs Buy
buy_total = (buy_price + transport_buy) * max(Q, moq)
decision = tr("make", lang_choice) if sales_total/Q < buy_total/Q else tr("buy", lang_choice)

# =============================
# UI – Resultaten & Capacity
# =============================
c0, c00 = st.columns([0.6, 0.4])
c00.info(used_note)

c1, c2, c3 = st.columns(3)
c1.metric(tr("verkoop_stuk", lang_choice), f"€ {sales_per_part:,.2f}")
c2.metric(tr("verkoop_totaal", lang_choice), f"€ {sales_total:,.2f}")
c3.metric(tr("advies", lang_choice), decision)

# Kostensplitsing
split_df = pd.DataFrame({
    "Categorie": [
        tr("mat_base", lang_choice), tr("mat_conv", lang_choice), tr("mat_waste", lang_choice),
        "Inkoopdelen (BOM)",
        "Arbeid", "Machine", "Energie", "QA", tr("tooling", lang_choice),
        "Scrap-impact", tr("transport", lang_choice), tr("storage", lang_choice),
        tr("wip_cost", lang_choice), tr("rework", lang_choice), tr("overhead", lang_choice),
        tr("contingency", lang_choice), tr("profit", lang_choice)
    ],
    "Kosten (€)": [
        base_mat_total, conv_total, waste_total,
        bom_buy_total,
        res["labor_cost"], res["machine_cost"], res["energy_cost"], res["qa_cost"], res["tooling_cost"],
        res["scrap_impact"], transport_cost, storage_cost,
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

# Detail per stap
if res["detail"]:
    det_df = pd.DataFrame(
        res["detail"],
        columns=[
            "Step","Proces","Qty/parent","Cycle_min_eff","Setup_min","Parallel","Batch_size","Batches","Queue_days",
            "Arbeid €/st","Machine €/st","Energie €/st","QA €/st","Tooling €/st","Scrap-impact €/st","Totaal €/st",
            "Run_min","Setup_min_total","Proc_days","Step_lead_days"
        ]
    )
    st.expander(tr("detail_hdr", lang_choice), expanded=False).dataframe(det_df, use_container_width=True, hide_index=True)

# Capaciteit & doorlooptijd
st.subheader(tr("capacity_hdr", lang_choice))
cap_df = pd.DataFrame(
    [{"Proces": k, "Belasting (h)": v, "Capaciteit (h/dag)": cap_per_process.get(k, 0.0),
      "Dagen nodig": (v / max(cap_per_process.get(k, 0.0), 0.0001)) if cap_per_process.get(k, 0.0) > 0 else np.nan}
     for k, v in res["cap_hours_per_process"].items()]
).sort_values("Belasting (h)", ascending=False)
c_left, c_right = st.columns([0.6, 0.4])
with c_left:
    st.dataframe(cap_df, use_container_width=True, hide_index=True)
with c_right:
    st.metric(tr("lead_time", lang_choice), f"{res['lead_time_days']:.2f}")
    if res["bottleneck"]:
        st.metric(tr("bottleneck", lang_choice), res["bottleneck"])

# =============================
# Monte-Carlo
# =============================
if mc_on:
    st.subheader(tr("mc_results", lang_choice))
    rng = np.random.default_rng(42)
    mat_mul = rng.normal(1.0, sd_mat, size=mc_iter)
    cyc_mul = rng.normal(1.0, sd_cycle, size=mc_iter)
    scrap_add = np.clip(rng.normal(0.0, sd_scrap, size=mc_iter), -0.49, 0.9)

    mc_vals = []
    for i in range(mc_iter):
        m_total = (bruto_kg_pc * mat_price_used * (1 + float(mat.get("waste",0.0))) + bruto_kg_pc * float(mat.get("conv_cost",0.0))) \
                  * mat_mul[i] * Q + bom_buy_total
        # copy routing & perturb
        mod = routing.copy()
        if not mod.empty:
            mod["Cycle_min"] = mod["Cycle_min"] * (lc_fac * materials[material].get("k_cycle",1.0) * cyc_mul[i])
            mod["Scrap_pct"] = np.clip(mod["Scrap_pct"] + scrap_add[i], 0.0, 0.9)
        res_mc = compute_costs_routing(mod)
        tr_cost = transport_cost
        stg = (storage_days/365.0) * inventory_cost_year * (res_mc["proc_cost"])
        rw = rework_pct * res_mc["proc_cost"]
        d = m_total + res_mc["proc_cost"] + tr_cost + stg + res_mc["wip_cost"] + rw
        oh = d * overhead_pct
        cg = d * contingency_pct
        ct = d + oh + cg
        pf = ct * profit_pct
        sale_pp = (ct + pf) / Q
        mc_vals.append(sale_pp)

    mc_vals = np.array(mc_vals)
    p50 = float(np.percentile(mc_vals, 50))
    p80 = float(np.percentile(mc_vals, 80))
    p90 = float(np.percentile(mc_vals, 90))
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric(tr("p50", lang_choice), f"€ {p50:,.2f}")
    cc2.metric(tr("p80", lang_choice), f"€ {p80:,.2f}")
    cc3.metric(tr("p90", lang_choice), f"€ {p90:,.2f}")
    hist = pd.DataFrame({"€/stuk": mc_vals})
    figh = px.histogram(hist, x="€/stuk", nbins=40, title="Verdeling verkoopprijs/stuk")
    st.plotly_chart(figh, use_container_width=True)

# =============================
# Export — PDF & Excel
# =============================
def build_pdf(project, Q, material, sales_pp, sales_total, split_df, used_note, lang,
              bruto_kg_pc, yield_fac, conv_cost, waste_frac, lead_days, bottleneck):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    y = H - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"{tr('app_title', lang)} – {project}")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Date/Datum: {date.today().isoformat()}")
    y -= 14
    c.drawString(40, y, f"{tr('qty', lang)}: {Q}  |  {tr('material', lang)}: {material}")
    y -= 14
    c.drawString(40, y, used_note)
    y -= 14
    c.drawString(40, y, f"Bruto kg/st: {bruto_kg_pc:.3f}  |  Yield: {yield_fac:.2f}  |  Conv€/kg: {conv_cost:.2f}  |  Waste: {waste_frac:.2f}")
    y -= 14
    if bottleneck:
        c.drawString(40, y, f"Lead time: {lead_days:.2f} d  |  Bottleneck: {bottleneck}")
    else:
        c.drawString(40, y, f"Lead time: {lead_days:.2f} d")
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"{tr('verkoop_stuk', lang)}: € {sales_pp:,.2f}")
    y -= 16
    c.drawString(40, y, f"{tr('verkoop_totaal', lang)}: € {sales_total:,.2f}")
    y -= 24

    data = [["Categorie","Kosten (€)"]] + [[r["Categorie"], f"€ {r['Kosten (€)']:.2f}"] for _, r in split_df.iterrows()]
    tbl = Table(data, colWidths=[260, 120])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(1,0), colors.lightgrey),
        ('TEXTCOLOR',(0,0),(1,0), colors.black),
        ('GRID',(0,0),(-1,-1), 0.25, colors.grey),
        ('ALIGN',(1,1),(1,-1),'RIGHT'),
        ('FONT',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONT',(0,1),(-1,-1),'Helvetica'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.whitesmoke, colors.lightyellow]),
    ]))
    tw, th = tbl.wrapOn(c, 40, y)
    tbl.drawOn(c, 40, max(40, y - th))
    c.showPage()
    c.save()
    buf.seek(0)
    return buf

exp_col1, exp_col2 = st.columns(2)
with exp_col1:
    pdf_buf = build_pdf(project, Q, material, sales_per_part, sales_total, split_df, used_note, lang_choice,
                        bruto_kg_pc, yield_fac, float(mat.get("conv_cost",0.0)), float(mat.get("waste",0.0)),
                        res["lead_time_days"], res["bottleneck"])
    st.download_button(tr("pdf_btn", lang_choice), data=pdf_buf,
                       file_name=f"Offerte_{project}.pdf", mime="application/pdf")
with exp_col2:
    xls_buf = io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="xlsxwriter") as xlw:
        split_df.to_excel(xlw, index=False, sheet_name="Cost_Split")
        if res["detail"]:
            det_df.to_excel(xlw, index=False, sheet_name="Routing")
        if not bom_buy.empty:
            bom_buy.to_excel(xlw, index=False, sheet_name="BOM_Buy")
        # Capaciteit
        if not res["cap_hours_per_process"] == {}:
            cap_tab = pd.DataFrame(
                [{"Proces": k, "Belasting (h)": v, "Capaciteit (h/dag)": cap_per_process.get(k, 0.0),
                  "Dagen nodig": (v / max(cap_per_process.get(k, 0.0), 0.0001)) if cap_per_process.get(k, 0.0) > 0 else np.nan}
                 for k, v in res["cap_hours_per_process"].items()]
            ).sort_values("Belasting (h)", ascending=False)
            cap_tab.to_excel(xlw, index=False, sheet_name="Capacity")
        # Meta + Forecast
        meta = pd.DataFrame({
            "Key":[
                "Project","Q","Material","Net_kg_per_part","Gross_kg_per_part","Yield","Conv_cost_per_kg","Waste_frac",
                "LC_b","LC_ref","TOU_day","TOU_eve","TOU_night",
                "E_price_day","E_price_eve","E_price_night","Used_price_note",
                "Lead_time_days","Bottleneck"
            ],
            "Value":[
                project,Q,material,gewicht,bruto_kg_pc,yield_fac, float(mat.get("conv_cost",0.0)), float(mat.get("waste",0.0)),
                lc_b,lc_ref,tou_day,tou_eve,tou_night,price_day,price_eve,price_night,used_note,
                res["lead_time_days"], res["bottleneck"] or ""
            ]
        })
        meta.to_excel(xlw, index=False, sheet_name="Meta")
        df_fc.to_excel(xlw, index=False, sheet_name="Forecast")
    xls_buf.seek(0)
    st.download_button(tr("xls_btn", lang_choice), data=xls_buf,
                       file_name=f"Cost_{project}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
