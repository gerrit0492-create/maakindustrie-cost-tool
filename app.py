import io
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
    "app_caption":      {"nl": "Incl. learning curve, TOU-energie, Forecast, Monte-Carlo, PDF/Excel export",
                         "en": "Incl. learning curve, TOU energy, Forecast, Monte Carlo, PDF/Excel export"},
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
    "proc_hdr":         {"nl": "Processen", "en": "Processes"},
    "proc_choose":      {"nl": "Kies processen", "en": "Choose processes"},
    "cycle_time":       {"nl": "cyclustijd (min/stuk)", "en": "cycle time (min/part)"},
    "attend":           {"nl": "operator attend %", "en": "operator attend %"},
    "energy_per":       {"nl": "energie (kWh/stuk)", "en": "energy (kWh/part)"},
    "qa_per":           {"nl": "QA (min/stuk)", "en": "QA (min/part)"},
    "scrap_pct":        {"nl": "scrap %", "en": "scrap %"},
    "lean_hdr":         {"nl": "Lean / Logistiek", "en": "Lean / Logistics"},
    "rework_pct":       {"nl": "Rework % (op proceskosten)", "en": "Rework % (on process costs)"},
    "transport_min":    {"nl": "Transport (min/stuk)", "en": "Transport (min/part)"},
    "storage_days":     {"nl": "Opslag (dagen batch)", "en": "Storage (days per batch)"},
    "inventory_rate":   {"nl": "Voorraadkosten %/jaar", "en": "Inventory cost %/year"},
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
    "verkoop_stuk":     {"nl": "Verkoopprijs/stuk", "en": "Sales price/part"},
    "verkoop_totaal":   {"nl": "Totale verkoopprijs", "en": "Total sales price"},
    "advies":           {"nl": "Advies", "en": "Recommendation"},
    "split_hdr":        {"nl": "💰 Kostensplitsing", "en": "💰 Cost breakdown"},
    "chart_hdr":        {"nl": "📊 Visualisaties (Plotly)", "en": "📊 Visualizations (Plotly)"},
    "trend_hdr":        {"nl": "📈 Voorspelde prijs", "en": "📈 Forecasted price"},
    "trend_title":      {"nl": "Materiaaltrend", "en": "Material trend"},
    "detail_hdr":       {"nl": "🔎 Detail per proces (€/stuk)", "en": "🔎 Per-process detail (€/part)"},
    "mc_results":       {"nl": "🎲 Monte-Carlo resultaten", "en": "🎲 Monte Carlo results"},
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
    "material":         {"nl": "Materiaal", "en": "Material"},  # reused
}

def tr(key: str, lang: str = "nl", **fmt):
    s = TXT.get(key, {}).get(lang, key)
    return s.format(**fmt) if fmt else s

# =============================
# Materialen (uitgebreid)
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
    "1.4462_Duplex":    {"price": 5.50, "waste": 0.07, "k_cycle": 1.30, "tool_wear_eur_pc": 0.12},  # = 2205
    "SuperDuplex_2507": {"price": 7.50, "waste": 0.07, "k_cycle": 1.45, "tool_wear_eur_pc": 0.18},

    # --- Aluminium / Koper ---
    "Al_6082":          {"price": 4.20, "waste": 0.07, "k_cycle": 0.80, "tool_wear_eur_pc": 0.01},
    "Cast_Aluminium":   {"price": 3.20, "waste": 0.07, "k_cycle": 0.90, "tool_wear_eur_pc": 0.02},  # giet Al (bijv. AlSi10Mg)
    "Cu_ECW":           {"price": 8.00, "waste": 0.05, "k_cycle": 1.10, "tool_wear_eur_pc": 0.05},
}

# machine- en operatorrates (€/uur)
machine_rates = {"CNC": 85.0, "Laser": 110.0, "Lassen": 55.0, "Buigen": 75.0, "Montage": 40.0}
labor_rate = 45.0
overhead_pct = 0.20
profit_pct = 0.12
contingency_pct = 0.05

# =============================
# Sidebar — Invoer
# =============================
# Taalkeuze
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

# Processen
st.sidebar.subheader(tr("proc_hdr", lang_choice))
default_sel = ["CNC", "Montage"]
processen = st.sidebar.multiselect(tr("proc_choose", lang_choice), list(machine_rates.keys()), default=default_sel)

# Per-proces parameters
proc_rows = []
for p in processen:
    with st.sidebar.expander(f"⚙️ {p}", expanded=False):
        cycle = st.number_input(f"{p} – {tr('cycle_time', lang_choice)}", min_value=0.0,
                                value={"CNC":7.5,"Laser":5.0,"Lassen":8.0,"Buigen":4.0,"Montage":6.0}.get(p,5.0),
                                key=f"cyc_{p}")
        attend = st.slider(f"{p} – {tr('attend', lang_choice)}", 0, 100, 100 if p!="Laser" else 50, key=f"att_{p}")
        kwh_pc = st.number_input(f"{p} – {tr('energy_per', lang_choice)}", min_value=0.0,
                                 value=0.2 if p!="Laser" else 0.5, key=f"kwh_{p}")
        qa_min = st.number_input(f"{p} – {tr('qa_per', lang_choice)}", min_value=0.0,
                                 value=0.5 if p!="Montage" else 1.0, key=f"qa_{p}")
        scrap = st.number_input(f"{p} – {tr('scrap_pct', lang_choice)}", min_value=0.0, value=0.02, step=0.01, key=f"scrap_{p}")
        proc_rows.append(dict(
            Proces=p, Cycle_min=cycle, Attend_pct=attend, kWh_pc=kwh_pc, QA_min_pc=qa_min, Scrap_pct=scrap
        ))

proc_df = pd.DataFrame(proc_rows) if proc_rows else pd.DataFrame(
    columns=["Proces","Cycle_min","Attend_pct","kWh_pc","QA_min_pc","Scrap_pct"]
)

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
# Helpers
# =============================
def lc_factor(Q, ref, b):
    try:
        return (max(Q, 1) / max(ref, 1)) ** b
    except Exception:
        return 1.0

def forecast_series(p0: float, months: int, method: str,
                    drift_abs: float, drift_pct: float, sigma_pct: float, seed: int = 42):
    idx = pd.date_range(date.today(), periods=months+1, freq="MS")  # month start
    if method == "Drift (€/mnd)":
        vals = [max(0.01, p0 + i*drift_abs) for i in range(months+1)]
        df = pd.DataFrame({"Datum": idx, "€/kg": vals})
        return df
    # % drift + onzekerheid
    rng = np.random.default_rng(seed)
    vals = [p0]
    low = [p0]
    high = [p0]
    for _ in range(months):
        mu = 1.0 + drift_pct/100.0
        shock = rng.normal(0.0, sigma_pct/100.0)
        nxt = max(0.01, vals[-1] * (mu + shock))
        vals.append(nxt)
        trend_val = vals[-2] * mu
        low.append(max(0.01, trend_val*(1 - 2*sigma_pct/100.0)))
        high.append(trend_val*(1 + 2*sigma_pct/100.0))
    df = pd.DataFrame({"Datum": idx, "€/kg": vals, "Low": low, "High": high})
    return df

# =============================
# Berekening
# =============================
mat = materials[material]
p0 = mat["price"]

# Forecast bouwen
df_fc = forecast_series(p0, forecast_horizon, forecast_method, drift_abs, drift_pct, sigma_pct)

# Grafiek forecast
st.markdown("---")
st.subheader(f"{tr('trend_hdr', lang_choice)} – {material} ({forecast_horizon} mnd)")
if "Low" in df_fc.columns:
    fig_fc = px.line(df_fc, x="Datum", y=["€/kg","Low","High"], markers=True,
                     labels={"value":"€/kg","variable":"Serie"})
else:
    fig_fc = px.line(df_fc, x="Datum", y="€/kg", markers=True, labels={"€/kg":"€/kg"})
st.plotly_chart(fig_fc, use_container_width=True)

# Keuze prijs voor kostprijsberekening
if use_forecast_for_cost:
    try:
        mat_price_used = float(df_fc.loc[df_fc.index[quote_month_offset], "€/kg"])
    except Exception:
        mat_price_used = p0
    used_note = f"{tr('used_price', lang_choice)}: € {mat_price_used:.2f}/kg ({tr('month', lang_choice)} t={quote_month_offset})"
else:
    mat_price_used = p0
    used_note = f"{tr('used_price', lang_choice)}: € {mat_price_used:.2f}/kg (t=0)"

# Learning curve & TOU
lc_fac = lc_factor(Q, lc_ref, lc_b)
eff_kwh_price = (tou_day*price_day + tou_eve*price_eve + tou_night*price_night)

def compute_costs(proc_df, lc_fac):
    if proc_df.empty:
        return dict(
            proc_cost=0.0, labor_cost=0.0, machine_cost=0.0, energy_cost=0.0,
            qa_cost=0.0, tooling_cost=0.0, scrap_impact=0.0, detail=[]
        )
    rows = []
    labor_total = machine_total = energy_total = qa_total = scrap_total = tooling_total = 0.0
    mat_k = materials[material].get("k_cycle", 1.0)
    tool_pc_base = materials[material].get("tool_wear_eur_pc", 0.0)

    for _, r in proc_df.iterrows():
        p = r["Proces"]
        rate = machine_rates[p]
        cyc = float(r["Cycle_min"]) * lc_fac * mat_k
        attend_frac = float(r["Attend_pct"])/100.0
        kwh_pc = float(r["kWh_pc"])
        qa_min = float(r["QA_min_pc"])
        scrap = float(r["Scrap_pct"])

        labor_pc = (cyc/60.0) * labor_rate * attend_frac
        mach_pc  = (cyc/60.0) * rate
        energy_pc = kwh_pc * eff_kwh_price
        qa_pc    = (qa_min/60.0) * labor_rate
        tool_pc  = tool_pc_base  # per stuk per proces (simpel model)

        # basis per stuk
        base_pc = labor_pc + mach_pc + energy_pc + qa_pc + tool_pc
        # scrap impact (yield-fout) incl. materiaalcomponent van één stuk
        scrap_imp_pc = (base_pc + (gewicht*mat_price_used*(1+materials[material]["waste"]))) \
                       * scrap / (1 - min(0.9, scrap))

        rows.append([p, cyc, labor_pc, mach_pc, energy_pc, qa_pc, tool_pc, scrap_imp_pc, base_pc + scrap_imp_pc])

        labor_total   += labor_pc  * Q
        machine_total += mach_pc   * Q
        energy_total  += energy_pc * Q
        qa_total      += qa_pc     * Q
        tooling_total += tool_pc   * Q
        scrap_total   += scrap_imp_pc * Q

    proc_total = labor_total + machine_total + energy_total + qa_total + tooling_total + scrap_total
    return dict(
        proc_cost=proc_total,
        labor_cost=labor_total,
        machine_cost=machine_total,
        energy_cost=energy_total,
        qa_cost=qa_total,
        tooling_cost=tooling_total,
        scrap_impact=scrap_total,
        detail=rows
    )

# Materiaalpost
mat_cost_total = (gewicht * mat_price_used * (1 + mat["waste"])) * Q
res = compute_costs(proc_df, lc_fac)

transport_cost = (transport_min/60.0) * labor_rate * Q
storage_cost = (storage_days/365.0) * inventory_cost_year * (res["proc_cost"])
rework_cost = rework_pct * res["proc_cost"]

direct_cost = mat_cost_total + res["proc_cost"] + transport_cost + storage_cost + rework_cost
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
# UI – Resultaten
# =============================
c0, c00 = st.columns([0.6, 0.4])
c00.info(used_note)

c1, c2, c3 = st.columns(3)
c1.metric(tr("verkoop_stuk", lang_choice), f"€ {sales_per_part:,.2f}")
c2.metric(tr("verkoop_totaal", lang_choice), f"€ {sales_total:,.2f}")
c3.metric(tr("advies", lang_choice), decision)

# Tabel kostensplitsing
split_df = pd.DataFrame({
    "Categorie": [
        tr("material", lang_choice), "Arbeid", "Machine", "Energie", "QA",
        tr("tooling", lang_choice), "Scrap-impact", "Transport", "Opslag", "Rework", "Overhead", "Contingency", "Profit"
    ],
    "Kosten (€)": [
        mat_cost_total, res["labor_cost"], res["machine_cost"], res["energy_cost"], res["qa_cost"],
        res["tooling_cost"], res["scrap_impact"], transport_cost, storage_cost, rework_cost, overhead, contingency, profit
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

# Detail per proces
if len(res["detail"]) > 0:
    det_df = pd.DataFrame(
        res["detail"],
        columns=["Proces","Cycle_min_eff","Arbeid €/st","Machine €/st","Energie €/st","QA €/st","Tooling €/st","Scrap-impact €/st","Totaal €/st"]
    )
    st.expander(tr("detail_hdr", lang_choice), expanded=False).dataframe(det_df, use_container_width=True, hide_index=True)

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
        # materiaal
        m_total = (gewicht * mat_price_used * mat_mul[i] * (1 + mat["waste"])) * Q

        # processen (alle cycli * cyc_mul)
        mod_df = proc_df.copy()
        if not mod_df.empty:
            mod_df["Cycle_min"] = mod_df["Cycle_min"] * (lc_fac * materials[material].get("k_cycle",1.0) * cyc_mul[i])
            mod_df["Scrap_pct"] = np.clip(mod_df["Scrap_pct"] + scrap_add[i], 0.0, 0.9)
        mc_res = compute_costs(mod_df, 1.0)  # lc & k already in Cycle_min

        tr_cost = transport_cost  # deterministisch
        stg = (storage_days/365.0) * inventory_cost_year * (mc_res["proc_cost"])
        rw = rework_pct * mc_res["proc_cost"]
        d = m_total + mc_res["proc_cost"] + tr_cost + stg + rw
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
def build_pdf(project, Q, material, sales_pp, sales_total, split_df, used_note, lang):
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
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"{tr('verkoop_stuk', lang)}: € {sales_pp:,.2f}")
    y -= 16
    c.drawString(40, y, f"{tr('verkoop_totaal', lang)}: € {sales_total:,.2f}")
    y -= 24

    # Tabel
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
    pdf_buf = build_pdf(project, Q, material, sales_per_part, sales_total, split_df, used_note, lang_choice)
    st.download_button(tr("pdf_btn", lang_choice), data=pdf_buf,
                       file_name=f"Offerte_{project}.pdf", mime="application/pdf")
with exp_col2:
    # Excel export
    xls_buf = io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="xlsxwriter") as xlw:
        split_df.to_excel(xlw, index=False, sheet_name="Cost_Split")
        if len(res["detail"])>0:
            det_df.to_excel(xlw, index=False, sheet_name="Process_Detail")
        meta = pd.DataFrame({
            "Key":["Project","Q","Material","LC_b","LC_ref","TOU_day","TOU_eve","TOU_night",
                   "E_price_day","E_price_eve","E_price_night","Used_price_note"],
            "Value":[project,Q,material,lc_b,lc_ref,tou_day,tou_eve,tou_night,price_day,price_eve,price_night,used_note]
        })
        meta.to_excel(xlw, index=False, sheet_name="Meta")
        # Forecast-tab
        df_fc.to_excel(xlw, index=False, sheet_name="Forecast")
    xls_buf.seek(0)
    st.download_button(tr("xls_btn", lang_choice), data=xls_buf,
                       file_name=f"Cost_{project}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
