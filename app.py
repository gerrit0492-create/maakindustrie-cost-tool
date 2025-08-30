import io
import json
import base64
import requests
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
# Tarieven (€/uur)
machine_rates = {
    "CNC":85.0,
    "Laser":110.0,
    "Lassen":55.0,
    "Buigen":75.0,
    "Montage":40.0,
    "Casting":65.0
}
labor_rate = 45.0
overhead_pct = 0.20
profit_pct = 0.12
contingency_pct = 0.05
co2_per_kwh = 0.35  # kg CO2/kWh

# =============================
# Sidebar – Invoer
# =============================
lang_choice = st.sidebar.selectbox(
    TXT["lang"]["nl"],
    options=["nl","en"],
    index=0,
    format_func=lambda x: "Nederlands" if x=="nl" else "English"
)

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
    cap_per_process = {
        p: st.number_input(f"{p} (h/dag)", 0.0, 24.0, 8.0, key=f"cap_{p}")
        for p in machine_rates.keys()
    }

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
    try:
        return (max(Q,1)/max(ref,1))**b
    except:
        return 1.0

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
        trend=vals[-2]*mu
        low.append(max(0.01, trend*(1-2*sigma_pct/100)))
        high.append(trend*(1+2*sigma_pct/100))
    return pd.DataFrame({"Datum":idx,"€/kg":vals,"Low":low,"High":high})

# ---- GitHub helpers (presets uit repo laden) ----
@st.cache_data(ttl=300)
def gh_list_files(owner:str, repo:str, folder:str, branch:str="main", token:str|None=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder}"
    params = {"ref": branch}
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    items = r.json()
    return [
        it for it in items
        if isinstance(it, dict) and it.get("type")=="file" and it.get("name","").lower().endswith(".json")
    ]

@st.cache_data(ttl=300)
def gh_fetch_json(owner:str, repo:str, path:str, branch:str="main", token:str|None=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": branch}
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    obj = r.json()
    if "content" in obj and obj.get("encoding")=="base64":
        raw = base64.b64decode(obj["content"])
        return json.loads(raw.decode("utf-8"))
    if "download_url" in obj and obj["download_url"]:
        r2 = requests.get(obj["download_url"], timeout=20)
        r2.raise_for_status()
        return r2.json()
      
    raise RuntimeError("Onverwachte GitHub API-respons; geen content gevonden.")
  # =============================
# Forecast bouwen
# =============================
mat = materials[material]
p0 = mat["price"]
df_fc = forecast_series(p0, forecast_horizon, forecast_method, drift_abs, drift_pct, sigma_pct)

st.markdown("---")
st.subheader(f"📈 {tr('forecast_hdr', lang_choice)} – {material} ({forecast_horizon} mnd)")
if "Low" in df_fc.columns:
    fig_fc = px.line(
        df_fc, x="Datum", y=["€/kg","Low","High"], markers=True,
        labels={"value":"€/kg","variable":"Serie"}
    )
else:
    fig_fc = px.line(df_fc, x="Datum", y="€/kg", markers=True, labels={"€/kg":"€/kg"})
st.plotly_chart(fig_fc, use_container_width=True)

if use_forecast_for_cost:
    try:
        mat_price_used = float(df_fc.loc[df_fc.index[quote_month_offset], "€/kg"])
    except Exception:
        mat_price_used = p0
    used_note = f"{tr('use_fc', lang_choice)} → € {mat_price_used:.2f}/kg ({tr('month', lang_choice)} t={quote_month_offset})"
else:
    mat_price_used = p0
    used_note = f"Prijs basis: € {mat_price_used:.2f}/kg (t=0)"

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
    "Company": client_company if 'client_company' in locals() else "",
    "Contact": client_contact if 'client_contact' in locals() else "",
    "Email": client_email if 'client_email' in locals() else "",
    "Phone": client_phone if 'client_phone' in locals() else "",
    "RFQ": rfq_ref if 'rfq_ref' in locals() else "",
    "Incoterms": incoterms if 'incoterms' in locals() else "",
    "Currency": currency if 'currency' in locals() else "EUR",
    "PaymentTerms": pay_terms if 'pay_terms' in locals() else "",
    "DeliveryAddress": delivery_addr if 'delivery_addr' in locals() else "",
    "RequiredDelivery": req_delivery if 'req_delivery' in locals() else "",
    "QuoteValidity": quote_valid if 'quote_valid' in locals() else "",
    "NDA": "Yes" if ('nda_flag' in locals() and nda_flag) else "No",
}

# =============================
# Routing placeholder
# =============================
st.markdown(f"## {tr('routing_hdr', lang_choice)}")
st.caption(tr("routing_cap", lang_choice))

default_routing = pd.DataFrame([
    {"Step":10,"Proces":"Casting","Qty_per_parent":1.0,"Cycle_min":2.0,"Setup_min":60.0,"Attend_pct":50,
     "kWh_pc":0.4,"QA_min_pc":0.2,"Scrap_pct":0.03,"Parallel_machines":1,"Batch_size":50,"Queue_days":1.0},
    {"Step":20,"Proces":"CNC","Qty_per_parent":1.0,"Cycle_min":7.5,"Setup_min":30.0,"Attend_pct":100,
     "kWh_pc":0.2,"QA_min_pc":0.5,"Scrap_pct":0.02,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.5},
    {"Step":30,"Proces":"Montage","Qty_per_parent":1.0,"Cycle_min":6.0,"Setup_min":10.0,"Attend_pct":100,
     "kWh_pc":0.1,"QA_min_pc":1.0,"Scrap_pct":0.00,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.2},
])
routing = st.data_editor(default_routing, key="routing_editor", num_rows="dynamic", use_container_width=True)

# =============================
# BOM – Ingekochte onderdelen
# =============================
st.markdown(f"## {tr('bom_buy_hdr', lang_choice)}")
st.caption(tr("bom_buy_cap", lang_choice))

default_bom = pd.DataFrame([
    {"Part":"Handgreep","Qty":2,"UnitPrice":3.5,"Scrap_pct":0.01},
    {"Part":"Schroef M8","Qty":8,"UnitPrice":0.1,"Scrap_pct":0.02}
])
bom_buy = st.data_editor(default_bom, key="bom_buy_editor", num_rows="dynamic", use_container_width=True)

# =============================
# Simpele kostencalculatie
# =============================
st.markdown("---")
st.subheader("📊 Kostencalculatie (basis placeholders)")
st.write(f"Project: **{project}** – {Q} stuks van {material}")
st.write(f"Gebruikte materiaalprijs: {mat_price_used:.2f} €/kg")

base_mat_cost = gewicht * mat_price_used
conv_cost = sum(routing["Cycle_min"]) * (labor_rate/60)
buy_cost = (bom_buy["Qty"]*bom_buy["UnitPrice"]).sum()

total_cost = base_mat_cost + conv_cost + buy_cost
sales_price = total_cost * (1+profit_pct+contingency_pct)

st.metric("Totale kostprijs/stuk", f"€ {total_cost:.2f}")
st.metric("Verkoopprijs/stuk (incl. marge)", f"€ {sales_price:.2f}")

st.markdown("### Breakdown")
st.write({
    "Materiaal": base_mat_cost,
    "Conversie": conv_cost,
    "Inkoopdelen": buy_cost,
    "Marge/Contingency": sales_price-total_cost
})

fig = go.Figure(go.Pie(labels=["Materiaal","Conversie","Inkoopdelen","Marge"],
                       values=[base_mat_cost, conv_cost, buy_cost, sales_price-total_cost]))
st.plotly_chart(fig, use_container_width=True)

# =============================
# Export naar PDF en Excel
# =============================
st.subheader("📤 Export opties")
exp_col1, exp_col2 = st.columns(2)

with exp_col1:
    if st.button("📄 Genereer PDF"):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(30, 800, f"Offerte – {project}")
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
        table.setStyle(style)
        table.wrapOn(c, 400, 600)
        table.drawOn(c, 30, 700-20*len(data))

        c.save()
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="quote.pdf">Download PDF</a>'
        st.markdown(href, unsafe_allow_html=True)

with exp_col2:
    out_buf = io.BytesIO()
    with pd.ExcelWriter(out_buf, engine="xlsxwriter") as writer:
        st.session_state.get("routing_editor", routing).to_excel(writer, index=False, sheet_name="Routing")
        st.session_state.get("bom_buy_editor", bom_buy).to_excel(writer, index=False, sheet_name="BOM_buy")
        pd.DataFrame([
            {"Post":"Materiaal","Bedrag":base_mat_cost},
            {"Post":"Conversie","Bedrag":conv_cost},
            {"Post":"Inkoopdelen","Bedrag":buy_cost},
            {"Post":"Totaal","Bedrag":total_cost},
            {"Post":"Verkoop (incl. marge)","Bedrag":sales_price}
        ]).to_excel(writer, index=False, sheet_name="Summary")
    out_buf.seek(0)
    st.download_button("📊 Download Excel",
                       data=out_buf,
                       file_name=f"{project}_calc.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =============================
# Einde app
# =============================
st.markdown("✅ Klaar – dit is de huidige versie van de Maakindustrie Cost Tool+.")
  
