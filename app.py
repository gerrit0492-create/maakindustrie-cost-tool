import io
import json
import base64
import requests
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
    "used_price":{"nl":"Gebruikte materiaalprijs","en":"Material price used"},
    "month":{"nl":"maand","en":"month"}
}
def tr(key, lang="nl", **fmt):
    s = TXT.get(key, {}).get(lang, key)
    return s.format(**fmt) if fmt else s

# =============================
# Materialen incl. CO₂
# =============================
materials = {
    "S235JR_steel":{"price":1.40,"waste":0.08,"k_cycle":1.00,"tool_wear_eur_pc":0.02,"co2e_kgkg":1.9},
    "S355J2_steel":{"price":1.70,"waste":0.08,"k_cycle":1.05,"tool_wear_eur_pc":0.03,"co2e_kgkg":2.0},
    "C45":{"price":1.90,"waste":0.06,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":2.0},
    "42CrMo4":{"price":2.60,"waste":0.06,"k_cycle":1.20,"tool_wear_eur_pc":0.07,"co2e_kgkg":2.3},
    "SS304":{"price":3.50,"waste":0.06,"k_cycle":1.15,"tool_wear_eur_pc":0.06,"co2e_kgkg":6.5},
    "SS316L":{"price":4.20,"waste":0.06,"k_cycle":1.20,"tool_wear_eur_pc":0.08,"co2e_kgkg":6.8},
    "SS904L":{"price":8.50,"waste":0.06,"k_cycle":1.25,"tool_wear_eur_pc":0.10,"co2e_kgkg":8.5},
    "1.4462_Duplex":{"price":5.50,"waste":0.07,"k_cycle":1.30,"tool_wear_eur_pc":0.12,"co2e_kgkg":7.5},
    "SuperDuplex_2507":{"price":7.50,"waste":0.07,"k_cycle":1.45,"tool_wear_eur_pc":0.18,"co2e_kgkg":10.5},
    "Al_6082":{"price":4.20,"waste":0.07,"k_cycle":0.80,"tool_wear_eur_pc":0.01,"co2e_kgkg":8.0},
    "Cast_Aluminium":{"price":3.20,"waste":0.07,"k_cycle":0.90,"tool_wear_eur_pc":0.02,"co2e_kgkg":8.5},
    "Cu_ECW":{"price":8.00,"waste":0.05,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":3.5},
    "Cast_Steel_GS45":{"price":1.60,"waste":0.05,"yield":0.80,"conv_cost":0.80,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":2.1},
    "Cast_Iron_GG25":{"price":1.20,"waste":0.05,"yield":0.85,"conv_cost":0.60,"k_cycle":1.05,"tool_wear_eur_pc":0.04,"co2e_kgkg":1.8},
    "Cast_AlSi10Mg":{"price":3.00,"waste":0.05,"yield":0.75,"conv_cost":1.00,"k_cycle":0.90,"tool_wear_eur_pc":0.02,"co2e_kgkg":8.5},
    "Forged_C45":{"price":1.90,"waste":0.04,"yield":0.90,"conv_cost":1.20,"k_cycle":1.20,"tool_wear_eur_pc":0.06,"co2e_kgkg":2.2},
    "Forged_42CrMo4":{"price":2.80,"waste":0.04,"yield":0.92,"conv_cost":1.40,"k_cycle":1.30,"tool_wear_eur_pc":0.08,"co2e_kgkg":2.5},
    "Forged_1.4462":{"price":6.00,"waste":0.04,"yield":0.88,"conv_cost":1.60,"k_cycle":1.40,"tool_wear_eur_pc":0.12,"co2e_kgkg":8.0},
    "Extruded_Al_6060":{"price":3.50,"waste":0.03,"yield":0.95,"conv_cost":0.50,"k_cycle":0.85,"tool_wear_eur_pc":0.01,"co2e_kgkg":7.5},
    "Extruded_Cu":{"price":7.50,"waste":0.03,"yield":0.92,"conv_cost":0.70,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":3.5},
}

# Tarieven (€/uur) en algemeen
machine_rates = {"CNC":85.0,"Laser":110.0,"Lassen":55.0,"Buigen":75.0,"Montage":40.0,"Casting":65.0}
labor_rate = 45.0
overhead_pct = 0.20
profit_pct = 0.12
contingency_pct = 0.05

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

@st.cache_data(ttl=300)
def gh_list_files(owner:str, repo:str, folder:str, branch:str="main", token:str|None=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder}"
    params = {"ref": branch}
    headers = {"Accept": "application/vnd.github+json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, params=params, headers=headers, timeout=20); r.raise_for_status()
    items = r.json()
    return [it for it in items if isinstance(it, dict) and it.get("type")=="file" and it.get("name","").lower().endswith(".json")]

@st.cache_data(ttl=300)
def gh_fetch_json(owner:str, repo:str, path:str, branch:str="main", token:str|None=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": branch}
    headers = {"Accept": "application/vnd.github+json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, params=params, headers=headers, timeout=20); r.raise_for_status()
    obj = r.json()
    if "content" in obj and obj.get("encoding")=="base64":
        raw = base64.b64decode(obj["content"]); return json.loads(raw.decode("utf-8"))
    if "download_url" in obj and obj["download_url"]:
        r2 = requests.get(obj["download_url"], timeout=20); r2.raise_for_status(); return r2.json()
    raise RuntimeError("Onverwachte GitHub API-respons; geen content gevonden.")

# ---------- scrap-propagatie & 1-run kost ----------
def propagate_scrap(df: pd.DataFrame, Q: int):
    df = df.sort_values("Step").reset_index(drop=True).copy()
    need = float(Q)
    eff_inputs = []
    for _, r in df[::-1].iterrows():
        scrap = float(r.get("Scrap_pct", 0.0))
        good = max(1e-9, 1.0 - scrap)
        input_qty = need / good
        eff_inputs.append(input_qty)
        need = input_qty
    df["Eff_Input_Qty"] = list(reversed(eff_inputs))
    return df

def cost_once(routing_df: pd.DataFrame, bom_df: pd.DataFrame, *,
              Q: int, gewicht: float, mat_price_used: float,
              labor_rate: float, machine_rates: dict, rework_pct: float,
              price_mix=(0.6, 0.3, 0.1), kwh_prices=(0.24, 0.18, 0.12)):
    tou_day, tou_eve, tou_night = price_mix
    p_day, p_eve, p_night = kwh_prices

    mat_cost_pc = gewicht * mat_price_used
    conv_cost_total = 0.0

    if routing_df is not None and len(routing_df) > 0:
        r = propagate_scrap(routing_df.copy(), Q)
        for _, row in r.iterrows():
            proc = str(row["Proces"])
            qty_in = float(row.get("Eff_Input_Qty", Q))
            par = max(1, int(row.get("Parallel_machines", 1)))
            batch = max(1, int(row.get("Batch_size", 50)))
            batches = int(np.ceil(qty_in / batch))

            setup_min = float(row.get("Setup_min", 0.0)) * batches
            cycle_min = float(row.get("Cycle_min", 0.0)) * qty_in
            qa_min = float(row.get("QA_min_pc", 0.0)) * qty_in
            attend = float(row.get("Attend_pct", 100.0)) / 100.0
            kwh = float(row.get("kWh_pc", 0.0)) * qty_in

            mach_rate = float(machine_rates.get(proc, labor_rate))
            machine_min = (setup_min + cycle_min) / par
            labor_min = (setup_min + cycle_min + qa_min) * attend
            conv_cost_total += (machine_min/60.0)*mach_rate + (labor_min/60.0)*labor_rate

            mix = tou_day*p_day + tou_eve*p_eve + tou_night*p_night
            conv_cost_total += kwh * mix

        conv_cost_total *= (1.0 + float(rework_pct))

    buy_total = 0.0
    if bom_df is not None and len(bom_df) > 0:
        b = bom_df.copy()
        b["Line"] = b["Qty"] * b["UnitPrice"]
        b["Line"] *= (1.0 + b.get("Scrap_pct", 0.0))
        buy_total = float(b["Line"].sum()) * Q

    total_per_pc = (mat_cost_pc*Q + conv_cost_total + buy_total) / Q
    return {"mat_pc": mat_cost_pc, "conv_total": conv_cost_total, "buy_total": buy_total, "total_pc": total_per_pc}

# ---------- Monte Carlo ----------
def run_mc(routing_df, bom_df, *, Q, gewicht, mat_mu, sd_mat, sd_cycle, sd_scrap,
           labor_rate, machine_rates, rework_pct, price_mix, kwh_prices,
           iters=1000, seed=123):
    rng = np.random.default_rng(seed)
    out = []
    base_routing = pd.DataFrame(routing_df) if routing_df is not None else pd.DataFrame()
    base_bom = pd.DataFrame(bom_df) if bom_df is not None else pd.DataFrame()

    for _ in range(int(iters)):
        mat_price = max(0.01, rng.normal(mat_mu, sd_mat*mat_mu))
        r = base_routing.copy()
        if not r.empty:
            if "Cycle_min" in r:
                r["Cycle_min"] = r["Cycle_min"] * (1.0 + rng.normal(0.0, sd_cycle, size=len(r)))
                r["Cycle_min"] = r["Cycle_min"].clip(lower=0.05)
            if "Scrap_pct" in r:
                r["Scrap_pct"] = (r["Scrap_pct"] + rng.normal(0.0, sd_scrap, size=len(r))).clip(0.0, 0.35)

        res = cost_once(r, base_bom, Q=Q, gewicht=gewicht, mat_price_used=mat_price,
                        labor_rate=labor_rate, machine_rates=machine_rates, rework_pct=rework_pct,
                        price_mix=price_mix, kwh_prices=kwh_prices)
        out.append(res["total_pc"])
    return np.array(out)

# ---------- Capaciteit / WIP ----------
def capacity_table(routing_df: pd.DataFrame, Q: int, hours_per_day: float, cap_per_process: dict):
    if routing_df is None or len(routing_df)==0:
        return pd.DataFrame(columns=["Proces","Hours_need","Hours_cap","Util_pct","Batches","Setup_min","Cycle_min"])
    r = propagate_scrap(routing_df.copy(), Q)
    rows=[]
    for _, row in r.iterrows():
        proc = str(row["Proces"])
        qty_in = float(row.get("Eff_Input_Qty", Q))
        par = max(1, int(row.get("Parallel_machines", 1)))
        batch = max(1, int(row.get("Batch_size", 50)))
        batches = int(np.ceil(qty_in / batch))
        setup_min = float(row.get("Setup_min", 0.0)) * batches
        cycle_min = float(row.get("Cycle_min", 0.0)) * qty_in
        machine_min = (setup_min + cycle_min) / par
        need_h = machine_min/60.0
        cap_h = float(cap_per_process.get(proc, hours_per_day))
        util = (need_h / max(cap_h, 1e-6)) if cap_h>0 else np.nan
        rows.append([proc, need_h, cap_h, util, batches, setup_min, cycle_min])
    df = pd.DataFrame(rows, columns=["Proces","Hours_need","Hours_cap","Util_pct","Batches","Setup_min","Cycle_min"])
    df = df.groupby("Proces", as_index=False).sum(numeric_only=True)
    df["Util_pct"] = (df["Hours_need"]/df["Hours_cap"]).replace([np.inf, -np.inf], np.nan)
    return df.sort_values("Util_pct", ascending=False)

# =============================
# Forecast
# =============================
mat = materials[material]; p0 = mat["price"]
df_fc = forecast_series(p0, forecast_horizon, forecast_method, drift_abs, drift_pct, sigma_pct)
st.markdown("---")
st.subheader(f"📈 {tr('forecast_hdr', lang_choice)} – {material} ({forecast_horizon} mnd)")
fig_fc = px.line(df_fc, x="Datum", y=(["€/kg","Low","High"] if "Low" in df_fc.columns else "€/kg"),
                 markers=True, labels={"value":"€/kg","variable":"Serie"})
st.plotly_chart(fig_fc, use_container_width=True)
if use_forecast_for_cost:
    try: mat_price_used = float(df_fc.loc[df_fc.index[quote_month_offset], "€/kg"])
    except Exception: mat_price_used = p0
else:
    mat_price_used = p0

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
    st.form_submit_button("Opslaan / Save")

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

def generate_autorouting(pt: str, gross_kg_pc: float, holes: int, bends: int, weld_m: float, panels: int,
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
        row(10, "CNC", 1.0, cyc_cnc, 25.0, 100, 0.20, 0.5, scrap_default)
        row(20, "Montage", 1.0, 4.0 + 0.3*holes, 10.0, 100, 0.05, 0.8, 0.0)
    elif pt == "Gefreesde beugel (massief)":
        cyc_cnc = (10.0 * tol_k * surf_k) + 0.5*holes + 3.0*(gross_kg_pc**0.6)
        row(10, "CNC", 1.0, cyc_cnc, 30.0, 100, 0.25, 0.6, scrap_default)
        row(20, "Montage", 1.0, 5.0 + 0.3*holes, 10.0, 100, 0.05, 1.0, 0.0)
    elif pt == "Lasframe / samenstel":
        cut_time = 3.0 + 0.8 * panels
        row(10, "Laser", panels, cut_time, 20.0, 50, 0.50, 0.3, scrap_default*0.5)
        weld_time = 6.0 + 6.0*weld_m + 0.5*panels
        row(20, "Lassen", 1.0, weld_time, 20.0, 100, 0.35, 0.5, scrap_default)
        cnc_time = 4.0*tol_k + 0.3*holes + 1.5*(gross_kg_pc**0.4)
        row(30, "CNC", 1.0, cnc_time, 15.0, 100, 0.20, 0.5, 0.01)
        row(40, "Montage", 1.0, 6.0 + 0.3*holes, 10.0, 100, 0.05, 1.0, 0.0)
    elif pt == "Plaatwerk kast / bracket":
        laser_time = 3.0 + 0.6 * panels
        row(10, "Laser", panels, laser_time, 20.0, 50, 0.50, 0.3, scrap_default*0.6)
        if bends > 0:
            bend_time = 1.6*bends + 0.2*panels
            row(20, "Buigen", 1.0, bend_time, 15.0, 100, 0.10, 0.2, scrap_default*0.4)
        cnc_time = 2.5*tol_k + 0.25*holes
        row(30, "CNC", 1.0, cnc_time, 10.0, 100, 0.15, 0.4, 0.01)
        row(40, "Montage", 1.0, 5.0 + 0.25*holes, 8.0, 100, 0.05, 0.8, 0.0)
    elif pt == "Gietstuk behuizing (CNC na-frees)":
        cast_cyc = 1.2 + 0.4*(gross_kg_pc**0.7)
        row(10, "Casting", 1.0, cast_cyc, 60.0, 50, 0.40, 0.2, scrap_default)
        cnc_time = 6.0*tol_k*surf_k + 0.4*holes + 1.5*(gross_kg_pc**0.5)
        row(20, "CNC", 1.0, cnc_time, 25.0, 100, 0.25, 0.6, 0.015)
        row(30, "Montage", 1.0, 4.0 + 0.2*holes, 8.0, 100, 0.05, 0.8, 0.0)
    elif pt == "Gesmede flens (CNC na-bewerking)":
        cnc_time = 5.0*tol_k + 0.2*holes + 1.0*(gross_kg_pc**0.5)
        row(10, "CNC", 1.0, cnc_time, 20.0, 100, 0.20, 0.5, scrap_default)
        row(20, "Montage", 1.0, 3.5 + 0.2*holes, 8.0, 100, 0.05, 0.8, 0.0)
    return pd.DataFrame(rows).sort_values("Step").reset_index(drop=True)

if st.button("🔮 Genereer routing"):
    yfac = float(materials[material].get("yield", 1.0))
    bruto_kg_pc = gewicht / yfac
    st.session_state["routing_df"] = generate_autorouting(part_type, bruto_kg_pc, holes, bends, weld_m, panels, tol_k, surf_k)
    st.success("Routing gegenereerd – bewerk ‘m hieronder naar wens.")
    st.rerun()

# =============================
# Presets & JSON
# =============================
st.markdown("## 📂 Presets & JSON")
st.caption("Bewaar of laad routing/BOM configuraties")

# init defaults in state (data, niet widget)
if "routing_df" not in st.session_state:
    st.session_state["routing_df"] = pd.DataFrame([
        {"Step":10,"Proces":"Casting","Qty_per_parent":1.0,"Cycle_min":2.0,"Setup_min":60.0,"Attend_pct":50,
         "kWh_pc":0.4,"QA_min_pc":0.2,"Scrap_pct":0.03,"Parallel_machines":1,"Batch_size":50,"Queue_days":1.0},
        {"Step":20,"Proces":"CNC","Qty_per_parent":1.0,"Cycle_min":7.5,"Setup_min":30.0,"Attend_pct":100,
         "kWh_pc":0.2,"QA_min_pc":0.5,"Scrap_pct":0.02,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.5},
        {"Step":30,"Proces":"Montage","Qty_per_parent":1.0,"Cycle_min":6.0,"Setup_min":10.0,"Attend_pct":100,
         "kWh_pc":0.1,"QA_min_pc":1.0,"Scrap_pct":0.00,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.2},
    ])
if "bom_buy_df" not in st.session_state:
    st.session_state["bom_buy_df"] = pd.DataFrame([
        {"Part":"Handgreep","Qty":2,"UnitPrice":3.5,"Scrap_pct":0.01},
        {"Part":"Schroef M8","Qty":8,"UnitPrice":0.1,"Scrap_pct":0.02}
    ])

preset_col1, preset_col2 = st.columns(2)
with preset_col1:
    if st.button("💾 Save preset (JSON)"):
        preset = {
            "routing": pd.DataFrame(st.session_state["routing_df"]).to_dict(orient="records"),
            "bom_buy": pd.DataFrame(st.session_state["bom_buy_df"]).to_dict(orient="records"),
        }
        js = json.dumps(preset, indent=2)
        b64 = base64.b64encode(js.encode()).decode()
        st.markdown(f'<a href="data:application/json;base64,{b64}" download="preset.json">Download preset.json</a>',
                    unsafe_allow_html=True)

with preset_col2:
    uploaded = st.file_uploader("Upload JSON preset", type="json")
    if uploaded:
        try:
            pl = json.load(uploaded)
            if "routing" in pl: st.session_state["routing_df"] = pd.DataFrame(pl["routing"])
            if "bom_buy" in pl: st.session_state["bom_buy_df"] = pd.DataFrame(pl["bom_buy"])
            st.success("Preset geladen vanaf upload."); st.rerun()
        except Exception as e:
            st.error(f"Kon JSON niet laden: {e}")

with st.expander("🔗 GitHub presets laden"):
    owner = st.text_input("GitHub owner", "gerrit0492-create")
    repo = st.text_input("Repository", "maakindustrie-cost-tool")
    folder = st.text_input("Folder", "presets")
    branch = st.text_input("Branch", "main")
    token = st.text_input("Token (optioneel)", type="password")
    if st.button("📂 Lijst presets"):
        try:
            files = gh_list_files(owner, repo, folder, branch, token or None)
            st.session_state["gh_filelist"] = files
            st.success(f"Gevonden: {[f['name'] for f in files]}")
        except Exception as e:
            st.error(f"GitHub error: {e}")
    files = st.session_state.get("gh_filelist", [])
    if files:
        names = [f['name'] for f in files]
        sel = st.selectbox("Kies preset", names, key="gh_sel_name")
        if st.button("Preset laden uit GitHub"):
            try:
                path = f"{folder}/{sel}".strip("/ ")
                data = gh_fetch_json(owner, repo, path, branch, token or None)
                if "routing" in data: st.session_state["routing_df"] = pd.DataFrame(data["routing"])
                if "bom_buy" in data: st.session_state["bom_buy_df"] = pd.DataFrame(data["bom_buy"])
                st.success(f"Preset '{sel}' geladen uit GitHub."); st.rerun()
            except Exception as e:
                st.error(f"Mislukt: {e}")

# =============================
# ROUTING (BOM-stappen) – editor
# =============================
st.markdown(f"## {tr('routing_hdr', lang_choice)}")
st.caption(tr("routing_cap", lang_choice))
process_choices = list(machine_rates.keys())
routing_view = st.data_editor(
    pd.DataFrame(st.session_state["routing_df"]),
    key="routing_editor_widget",
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Proces": st.column_config.SelectboxColumn(options=process_choices, required=True),
    }
)
# update data (geen widget-key!)
st.session_state["routing_df"] = pd.DataFrame(routing_view)

# =============================
# BOM – Ingekochte onderdelen – editor
# =============================
st.markdown(f"## {tr('bom_buy_hdr', lang_choice)}")
st.caption(tr("bom_buy_cap", lang_choice))
bom_view = st.data_editor(
    pd.DataFrame(st.session_state["bom_buy_df"]),
    key="bom_editor_widget",
    num_rows="dynamic",
    use_container_width=True
)
st.session_state["bom_buy_df"] = pd.DataFrame(bom_view)

# =============================
# Kostencalculatie
# =============================
st.markdown("---")
st.subheader("📊 Kostencalculatie (basis)")
st.write(f"Project: **{project}** – {Q} stuks van {material}")
st.write(f"Gebruikte materiaalprijs: {mat_price_used:.2f} €/kg")

df_routing = pd.DataFrame(st.session_state["routing_df"])
df_bom = pd.DataFrame(st.session_state["bom_buy_df"])
base_res = cost_once(df_routing, df_bom, Q=Q, gewicht=gewicht, mat_price_used=mat_price_used,
                     labor_rate=labor_rate, machine_rates=machine_rates, rework_pct=rework_pct,
                     price_mix=(tou_day,tou_eve,tou_night), kwh_prices=(price_day,price_eve,price_night))

base_mat_cost = base_res["mat_pc"]
conv_cost = base_res["conv_total"]
buy_cost = base_res["buy_total"]
total_cost = base_res["total_pc"]
sales_price = total_cost * (1+profit_pct+contingency_pct)

c1,c2 = st.columns(2)
c1.metric("Totale kostprijs/stuk", f"€ {total_cost:.2f}")
c2.metric("Verkoopprijs/stuk (incl. marge)", f"€ {sales_price:.2f}")

fig = go.Figure(go.Pie(labels=["Materiaal","Conversie","Inkoopdelen","Marge"],
                       values=[base_mat_cost, conv_cost, buy_cost, max(sales_price-total_cost,0.0)]))
st.plotly_chart(fig, use_container_width=True)

# =============================
# Monte Carlo simulatie
# =============================
if mc_on:
    st.markdown("### 🎲 Monte-Carlo simulatie (kostprijs/stuk)")
    samples = run_mc(
        routing_df=df_routing, bom_df=df_bom,
        Q=Q, gewicht=gewicht, mat_mu=mat_price_used,
        sd_mat=sd_mat, sd_cycle=sd_cycle, sd_scrap=sd_scrap,
        labor_rate=labor_rate, machine_rates=machine_rates, rework_pct=rework_pct,
        price_mix=(tou_day,tou_eve,tou_night), kwh_prices=(price_day,price_eve,price_night),
        iters=mc_iter, seed=123
    )
    p50 = float(np.percentile(samples, 50))
    p80 = float(np.percentile(samples, 80))
    p95 = float(np.percentile(samples, 95))

    c1, c2, c3 = st.columns(3)
    c1.metric("P50 (median)", f"€ {p50:.2f}")
    c2.metric("P80", f"€ {p80:.2f}")
    c3.metric("P95 (risk)", f"€ {p95:.2f}")

    df_hist = pd.DataFrame({"Kostprijs/stuk": samples})
    fig_mc = px.histogram(df_hist, x="Kostprijs/stuk", nbins=40, marginal="rug")
    st.plotly_chart(fig_mc, use_container_width=True)
else:
    samples = None
    p50 = p80 = p95 = None

# =============================
# Capaciteit & WIP
# =============================
st.markdown("### 🏭 Capaciteit & WIP")
cap_df = capacity_table(df_routing, Q, hours_per_day, cap_per_process)
if cap_df.empty:
    st.info("Geen routingdata om capaciteit te berekenen.")
else:
    cap_show = cap_df.copy()
    cap_show["Util_%"] = (cap_show["Util_pct"]*100).round(1)
    st.dataframe(cap_show[["Proces","Hours_need","Hours_cap","Util_%","Batches","Setup_min","Cycle_min"]],
                 use_container_width=True)

    fig_util = px.bar(cap_df, x="Proces", y="Util_pct", text=(cap_df["Util_pct"]*100).round(1))
    fig_util.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig_util, use_container_width=True)

    bottleneck = cap_df.sort_values("Util_pct", ascending=False).iloc[0]
    st.warning(f"🔧 Bottleneck: **{bottleneck['Proces']}** – benutting ~ {(bottleneck['Util_pct']*100):.1f}%")

# =============================
# Export naar PDF en Excel
# =============================
st.subheader("📤 Export opties")
exp_col1, exp_col2 = st.columns(2)

with exp_col1:
    if st.button("📄 Genereer PDF"):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 14); c.drawString(30, 800, f"Offerte – {project}")
        c.setFont("Helvetica", 10)
        c.drawString(30, 780, f"Aantal: {Q} stuks")
        c.drawString(30, 765, f"Materiaal: {material} – {mat_price_used:.2f} €/kg")
        data = [["Post","Bedrag (€)"],
                ["Materiaal", f"{base_mat_cost:.2f}"],
                ["Conversie", f"{conv_cost:.2f}"],
                ["Inkoopdelen", f"{buy_cost:.2f}"],
                ["Totaal", f"{total_cost:.2f}"],
                ["Verkoop (incl. marge)", f"{sales_price:.2f}"]]
        table = Table(data, colWidths=[200,100])
        style = TableStyle([("BACKGROUND",(0,0),(-1,0),colors.grey),
                            ("TEXTCOLOR",(0,0),(-1,0),colors.whitesmoke),
                            ("ALIGN",(0,0),(-1,-1),"CENTER"),
                            ("GRID",(0,0),(-1,-1),0.5,colors.black)])
        table.setStyle(style); table.wrapOn(c, 400, 600)
        table.drawOn(c, 30, 700-20*len(data))
        c.save(); buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode()
        st.markdown(f'<a href="data:application/pdf;base64,{b64}" download="quote.pdf">Download PDF</a>', unsafe_allow_html=True)

with exp_col2:
    out_buf = io.BytesIO()
    with pd.ExcelWriter(out_buf, engine="xlsxwriter") as writer:
        df_routing.to_excel(writer, index=False, sheet_name="Routing")
        df_bom.to_excel(writer, index=False, sheet_name="BOM_buy")
        pd.DataFrame([
            {"Post":"Materiaal","Bedrag":base_mat_cost},
            {"Post":"Conversie","Bedrag":conv_cost},
            {"Post":"Inkoopdelen","Bedrag":buy_cost},
            {"Post":"Totaal","Bedrag":total_cost},
            {"Post":"Verkoop (incl. marge)","Bedrag":sales_price}
        ]).to_excel(writer, index=False, sheet_name="Summary")
        if isinstance(samples, np.ndarray):
            pd.DataFrame({"Kostprijs/stuk": samples}).to_excel(writer, index=False, sheet_name="MC_samples")
            pd.DataFrame([{"P50":p50,"P80":p80,"P95":p95}]).to_excel(writer, index=False, sheet_name="MC_stats")
        if not cap_df.empty:
            cap_show.to_excel(writer, index=False, sheet_name="Capacity")
    out_buf.seek(0)
    st.download_button("📊 Download Excel",
                       data=out_buf,
                       file_name=f"{project}_calc.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =============================
# Einde app
# =============================
st.markdown("✅ Klaar – dit is de huidige versie van de Maakindustrie Cost Tool+.")
