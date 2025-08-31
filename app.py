# app.py
# Maakindustrie Cost Tool – complete versie (historisch + nieuw)
# Features: NL/EN toggle, Outokumpu (RVS) scraping, LME (Alu) scraping,
# Lean pijlers (opslag/transport/herbewerking), Routing/BOM editors,
# Auto-routing, Monte Carlo, Capaciteit/WIP, Make vs Buy, GitHub presets,
# PDF/Excel export, ClientInput sheet, 12m prijsprojectie.

import io
import re
import json
import base64
from typing import Dict, Tuple, Optional, List

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

# ---------- App config ----------
st.set_page_config(page_title="Maakindustrie Cost Tool", layout="wide", page_icon="🧮")

# ---------- i18n (NL/EN minimal) ----------
LANG = st.sidebar.radio("Language / Taal", ["Nederlands", "English"], horizontal=True)
T = {
    "Nederlands": {
        "input": "Invoer",
        "project": "Project",
        "qty": "Aantal stuks (Q)",
        "material": "Materiaal",
        "netkg": "Netto gewicht per stuk (kg)",
        "debug": "🧪 Debug Outokumpu parsing",
        "rvs_hdr": "RVS – Outokumpu alloy surcharge (€/ton)",
        "rvs_src": "Bron",
        "auto": "Automatisch (scrape)",
        "manual": "Handmatig",
        "manual_otk": "Handmatig: OTK surcharge (€/ton)",
        "alu_hdr": "Aluminium – LME (€/ton → €/kg)",
        "lme_src": "LME bron",
        "nasdaq": "Automatisch (Nasdaq/TE)",
        "manual_lme": "Handmatig: LME (€/ton)",
        "region_prem": "Regiopremie (€/kg)",
        "conv_add": "Conversie-opslag (€/kg)",
        "mc_hdr": "Monte-Carlo onzekerheid",
        "mc_on": "Monte-Carlo simulatie aan",
        "iters": "Iteraties",
        "sd_mat": "σ materiaalprijs (%)",
        "sd_cycle": "σ cyclustijd (%)",
        "sd_scrap": "σ scrap additief (abs)",
        "mvb_hdr": "Make vs Buy parameters",
        "buy_price": "Inkoopprijs/stuk (€)",
        "moq": "MOQ",
        "transport_buy": "Transport/handling (€/stuk)",
        "cap_hdr": "Capaciteit (uren/dag per proces)",
        "hours_day": "Uren productie per dag",
        "act_price": "Actuele materiaalprijs",
        "source": "Bron",
        "presets": "📂 Presets & JSON",
        "save_preset": "💾 Save preset (JSON)",
        "dl_preset": "⬇️ Download preset.json",
        "upload_preset": "Upload JSON preset",
        "gh_block": "🔗 GitHub presets laden / aanmaken",
        "owner": "GitHub owner",
        "repo": "Repository",
        "folder": "Folder",
        "branch": "Branch (leeg = autodetect)",
        "token": "Token (alleen nodig voor schrijven of private repo)",
        "list": "📂 Lijst presets",
        "load": "⬇️ Preset laden",
        "push": "🆕 Push voorbeeldpreset naar repo",
        "autorouting": "🧩 Auto-routing",
        "product_type": "Type product",
        "holes": "Aantal gaten",
        "bends": "Aantal zetten (plaatwerk)",
        "weld_m": "Laslengte (m)",
        "panels": "Aantal plaatdelen",
        "gen_route": "🔮 Genereer routing",
        "csv_ie": "🧩 CSV import/export",
        "route_tpl": "⬇️ Routing sjabloon",
        "bom_tpl": "⬇️ BOM sjabloon",
        "upload_route": "Upload Routing CSV",
        "upload_bom": "Upload BOM CSV",
        "replace": "Replace",
        "append": "Append",
        "route_editor": "Routing editor",
        "bom_editor": "BOM editor",
        "kpi_hdr": "📊 Kostencalculatie (basis)",
        "mat_pc": "Materiaal €/stuk",
        "conv_total": "Conversie totaal",
        "buy_total": "Inkoopdelen totaal",
        "unit_cost": "Kostprijs/stuk",
        "mc_title": "🎲 Monte-Carlo simulatie (kostprijs/stuk)",
        "cap_title": "🏭 Capaciteit & WIP",
        "bneck": "🔧 Bottleneck",
        "mvb_title": "🔄 Make vs Buy",
        "make": "MAKE",
        "buy": "BUY",
        "export": "📤 Export",
        "dl_route": "⬇️ Download Routing CSV",
        "dl_bom": "⬇️ Download BOM CSV",
        "gen_pdf": "📄 Genereer PDF",
        "dl_pdf": "⬇️ Download PDF",
        "dl_xlsx": "⬇️ Download Excel",
        "ready": "✅ Gereed – alle functies geactiveerd.",
        "lean_hdr": "♻️ Lean-pijlers (opslag/transport/herbewerking)",
        "storage_days": "Opslagdagen (dagen)",
        "storage_cost": "Opslagkosten (€/dag per batch)",
        "transport_km": "Transportafstand (km)",
        "transport_eurkm": "Transporttarief (€/km)",
        "rework_pct": "Herbewerkingskans per stuk (%)",
        "rework_min": "Herbewerkingsminuten per stuk (min)",
        "energy_eur_kwh": "Energiekosten (€/kWh)",
        "forecast_hdr": "📈 Materiaalprijs projectie (12 maanden)",
        "m_chg_stainless": "Maandelijkse mutatie RVS surcharge (%/mnd)",
        "m_chg_al": "Maandelijkse mutatie LME (%/mnd)",
        "apply_proj": "Toon projectie",
    },
    "English": {
        "input": "Inputs",
        "project": "Project",
        "qty": "Quantity (Q)",
        "material": "Material",
        "netkg": "Net weight per piece (kg)",
        "debug": "🧪 Debug Outokumpu parsing",
        "rvs_hdr": "Stainless – Outokumpu alloy surcharge (€/ton)",
        "rvs_src": "Source",
        "auto": "Automatic (scrape)",
        "manual": "Manual",
        "manual_otk": "Manual: OTK surcharge (€/ton)",
        "alu_hdr": "Aluminium – LME (€/ton → €/kg)",
        "lme_src": "LME source",
        "nasdaq": "Automatic (Nasdaq/TE)",
        "manual_lme": "Manual: LME (€/ton)",
        "region_prem": "Regional premium (€/kg)",
        "conv_add": "Conversion adder (€/kg)",
        "mc_hdr": "Monte Carlo uncertainty",
        "mc_on": "Enable Monte Carlo",
        "iters": "Iterations",
        "sd_mat": "σ material price (%)",
        "sd_cycle": "σ cycle time (%)",
        "sd_scrap": "σ scrap additive (abs)",
        "mvb_hdr": "Make vs Buy parameters",
        "buy_price": "Purchase price/unit (€)",
        "moq": "MOQ",
        "transport_buy": "Transport/handling (€/unit)",
        "cap_hdr": "Capacity (hours/day per process)",
        "hours_day": "Production hours per day",
        "act_price": "Actual material price",
        "source": "Source",
        "presets": "📂 Presets & JSON",
        "save_preset": "💾 Save preset (JSON)",
        "dl_preset": "⬇️ Download preset.json",
        "upload_preset": "Upload JSON preset",
        "gh_block": "🔗 GitHub presets load / create",
        "owner": "GitHub owner",
        "repo": "Repository",
        "folder": "Folder",
        "branch": "Branch (empty = autodetect)",
        "token": "Token (only for write/private repo)",
        "list": "📂 List presets",
        "load": "⬇️ Load preset",
        "push": "🆕 Push example preset to repo",
        "autorouting": "🧩 Auto-routing",
        "product_type": "Product type",
        "holes": "Number of holes",
        "bends": "Number of bends (sheet metal)",
        "weld_m": "Weld length (m)",
        "panels": "Number of sheet parts",
        "gen_route": "🔮 Generate routing",
        "csv_ie": "🧩 CSV import/export",
        "route_tpl": "⬇️ Routing template",
        "bom_tpl": "⬇️ BOM template",
        "upload_route": "Upload Routing CSV",
        "upload_bom": "Upload BOM CSV",
        "replace": "Replace",
        "append": "Append",
        "route_editor": "Routing editor",
        "bom_editor": "BOM editor",
        "kpi_hdr": "📊 Costing (base)",
        "mat_pc": "Material €/unit",
        "conv_total": "Conversion total",
        "buy_total": "Purchased items total",
        "unit_cost": "Unit cost",
        "mc_title": "🎲 Monte Carlo (unit cost)",
        "cap_title": "🏭 Capacity & WIP",
        "bneck": "🔧 Bottleneck",
        "mvb_title": "🔄 Make vs Buy",
        "make": "MAKE",
        "buy": "BUY",
        "export": "📤 Export",
        "dl_route": "⬇️ Download Routing CSV",
        "dl_bom": "⬇️ Download BOM CSV",
        "gen_pdf": "📄 Generate PDF",
        "dl_pdf": "⬇️ Download PDF",
        "dl_xlsx": "⬇️ Download Excel",
        "ready": "✅ Ready – all features enabled.",
        "lean_hdr": "♻️ Lean pillars (storage/transport/rework)",
        "storage_days": "Storage days (days)",
        "storage_cost": "Storage cost (€/day per batch)",
        "transport_km": "Transport distance (km)",
        "transport_eurkm": "Transport rate (€/km)",
        "rework_pct": "Rework probability per unit (%)",
        "rework_min": "Rework minutes per unit (min)",
        "energy_eur_kwh": "Energy cost (€/kWh)",
        "forecast_hdr": "📈 Material price projection (12 months)",
        "m_chg_stainless": "Monthly change RVS surcharge (%/mo)",
        "m_chg_al": "Monthly change LME (%/mo)",
        "apply_proj": "Show projection",
    }
}[LANG]

# ---------- constants ----------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (CostTool/1.0; +https://example.local)",
    "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
}

MATERIALS: Dict[str, Dict] = {
    "SS304":            {"base_eurkg": 2.80, "kind": "stainless", "aliases": ["304","1.4301"]},
    "SS316L":           {"base_eurkg": 3.40, "kind": "stainless", "aliases": ["316L","1.4404"]},
    "1.4462_Duplex":    {"base_eurkg": 4.20, "kind": "stainless", "aliases": ["2205","1.4462"]},
    "SuperDuplex_2507": {"base_eurkg": 5.40, "kind": "stainless", "aliases": ["2507","1.4410"]},
    "SS904L":           {"base_eurkg": 6.10, "kind": "stainless", "aliases": ["904L","1.4539"]},

    "Al_6082":          {"base_eurkg": 0.00, "kind": "aluminium", "aliases": ["6082"]},
    "Extruded_Al_6060": {"base_eurkg": 0.00, "kind": "aluminium", "aliases": ["6060"]},
    "Cast_Aluminium":   {"base_eurkg": 0.00, "kind": "aluminium", "aliases": ["Cast Al"]},

    "S235JR_steel":     {"base_eurkg": 1.40, "kind": "other"},
    "S355J2_steel":     {"base_eurkg": 1.70, "kind": "other"},
    "C45":              {"base_eurkg": 1.90, "kind": "other"},
    "42CrMo4":          {"base_eurkg": 2.60, "kind": "other"},
    "Cu_ECW":           {"base_eurkg": 8.00, "kind": "other"},
}
OTK_GRADE_KEY = {"SS304":"304","SS316L":"316L","1.4462_Duplex":"2205","SuperDuplex_2507":"2507","SS904L":"904L"}

MACHINE_RATES = {"CNC":85.0,"Laser":110.0,"Lassen":55.0,"Buigen":75.0,"Montage":40.0,"Casting":65.0}
LABOR_RATE = 45.0
PROFIT_PCT = 0.12
CONTINGENCY_PCT = 0.05

# ---------- helpers ----------
def eurton_to_eurkg(value_eur_per_ton: float) -> float:
    return (value_eur_per_ton or 0.0) / 1000.0

def parse_eur_number(s: str) -> Optional[float]:
    if not s: return None
    s = s.replace("\xa0", " ").strip()
    m = re.search(r"([0-9][0-9\.\,\s]*)", s)
    if not m: return None
    num = m.group(1).replace(" ", "")
    if "," in num and "." in num:
        last = max(num.rfind(","), num.rfind("."))
        dec = num[last]; thou = "." if dec == "," else ","
        num = num.replace(thou, "").replace(dec, ".")
    elif "," in num:
        parts = num.split(",")
        if len(parts[-1]) in (1,2):
            num = num.replace(".", "").replace(",", ".")
        else:
            num = num.replace(",", "")
    else:
        if num.count(".")>1: num = num.replace(".","")
    try: return float(num)
    except: return None

# ---------- scrapers (cached) ----------
@st.cache_data(ttl=60*60*3)
def fetch_outokumpu_surcharge_eur_ton() -> Dict[str,float]:
    url = "https://www.outokumpu.com/en/surcharges"
    r = requests.get(url, headers=HEADERS, timeout=15); r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    grade_aliases = {
        "304":["304","1.4301"], "316L":["316l","1.4404"],
        "2205":["2205","1.4462","duplex 2205"], "2507":["2507","1.4410","super duplex"], "904L":["904l","1.4539"]
    }
    out={}
    # tabelrijen
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th","td"])
        if not cells: continue
        row_txt = " ".join(td.get_text(" ", strip=True) for td in cells)
        low = row_txt.lower()
        for k,als in grade_aliases.items():
            if any(a in low for a in als):
                euros = re.findall(r"€\s*([0-9\.\,\s]+)", row_txt)
                if not euros:
                    euros = re.findall(r"([0-9\.\,\s]+)\s*(?:€/t|€/ton|per ton)", row_txt, flags=re.IGNORECASE)
                vals=[parse_eur_number(e) for e in euros if parse_eur_number(e) is not None]
                if vals: out[k]=max(vals)
    # fallback regex volledige tekst
    if not out:
        text = soup.get_text(" ", strip=True)
        pats = {
            "304":r"(?:304|1\.4301)[^\d€]{0,40}€\s*([0-9\.\, \u00A0]+)",
            "316L":r"(?:316L|1\.4404)[^\d€]{0,40}€\s*([0-9\.\, \u00A0]+)",
            "2205":r"(?:2205|1\.4462)[^\d€]{0,40}€\s*([0-9\.\, \u00A0]+)",
            "2507":r"(?:2507|1\.4410)[^\d€]{0,40}€\s*([0-9\.\, \u00A0]+)",
            "904L":r"(?:904L|1\.4539)[^\d€]{0,40}€\s*([0-9\.\, \u00A0]+)",
        }
        for k,pat in pats.items():
            m=re.search(pat,text,flags=re.IGNORECASE)
            if m:
                v=parse_eur_number(m.group(1))
                if v is not None: out[k]=v
    return out

@st.cache_data(ttl=60*60)
def fetch_ecb_usd_eur() -> Optional[float]:
    try:
        r=requests.get("https://api.exchangerate.host/latest?base=USD&symbols=EUR",headers=HEADERS,timeout=10)
        r.raise_for_status()
        return float(r.json()["rates"]["EUR"])
    except: return None

@st.cache_data(ttl=30*60)
def fetch_lme_via_tradingeconomics() -> Optional[float]:
    try:
        url="https://tradingeconomics.com/commodity/aluminum"
        r=requests.get(url,headers=HEADERS,timeout=12); r.raise_for_status()
        text=r.text
        m=re.search(r'data-price="(\d{3,5}(?:\.\d{1,2})?)"', text)
        if not m:
            m=re.search(r'(?i)Aluminum.*?(\d{3,5}(?:\.\d{1,2})?)', text)
        if not m: return None
        usd=float(m.group(1)); fx=fetch_ecb_usd_eur() or 0.92
        return usd*fx
    except: return None

def fetch_lme_eur_ton(nasdaq_key: Optional[str]) -> Tuple[Optional[float], str]:
    # Nasdaq Data Link optioneel (we houden TE als gratis fallback)
    # Als je een Nasdaq API key wil toevoegen, kun je hieronder extra code plaatsen.
    v = fetch_lme_via_tradingeconomics()
    if v: return v, "TradingEconomics scrape → ECB FX"
    return None, "Geen LME online bron gevonden (fallback handmatig)"

# ---------- Sidebar ----------
st.sidebar.header(T["input"])
project = st.sidebar.text_input(T["project"], "Demo")
Q = st.sidebar.number_input(T["qty"], min_value=1, value=50, step=1)
materiaal = st.sidebar.selectbox(T["material"], list(MATERIALS.keys()))
net_kg = st.sidebar.number_input(T["netkg"], min_value=0.01, value=2.0)

debug_otk = st.sidebar.checkbox(T["debug"], value=False)

st.sidebar.subheader(T["rvs_hdr"])
otk_mode = st.sidebar.radio(T["rvs_src"], [T["auto"], T["manual"]], horizontal=True, key="otk_mode")
manual_otk_eur_ton = st.sidebar.number_input(T["manual_otk"], min_value=0.0, value=0.0, step=10.0)

st.sidebar.subheader(T["alu_hdr"])
lme_mode = st.sidebar.radio(T["lme_src"], [T["nasdaq"], T["manual"]], horizontal=True, key="lme_mode")
nasdaq_key = ""  # veld weggelaten voor eenvoud; kan toegevoegd worden als nodig
manual_lme_eur_ton = st.sidebar.number_input(T["manual_lme"], min_value=0.0, value=2200.0, step=10.0)
region_premium_eurkg = st.sidebar.number_input(T["region_prem"], min_value=0.0, value=0.25, step=0.01)
conversion_adder_eurkg = st.sidebar.number_input(T["conv_add"], min_value=0.0, value=0.40, step=0.01)

# Lean pijlers
st.sidebar.subheader(T["lean_hdr"])
storage_days = st.sidebar.number_input(T["storage_days"], 0.0, 180.0, 0.0, 0.5)
storage_eur_day_per_batch = st.sidebar.number_input(T["storage_cost"], 0.0, 1000.0, 0.0, 0.5)
transport_km = st.sidebar.number_input(T["transport_km"], 0.0, 10000.0, 0.0, 1.0)
transport_eur_km = st.sidebar.number_input(T["transport_eurkm"], 0.0, 20.0, 0.0, 0.1)
rework_pct = st.sidebar.number_input(T["rework_pct"], 0.0, 100.0, 0.0, 0.5) / 100.0
rework_min = st.sidebar.number_input(T["rework_min"], 0.0, 240.0, 0.0, 1.0)
energy_eur_kwh = st.sidebar.number_input(T["energy_eur_kwh"], 0.0, 2.0, 0.20, 0.01)

# Monte Carlo
st.sidebar.subheader(T["mc_hdr"])
mc_on = st.sidebar.checkbox(T["mc_on"], value=False)
mc_iter = st.sidebar.number_input(T["iters"], 100, 20000, 1000, step=100)
sd_mat = st.sidebar.number_input(T["sd_mat"], 0.0, 0.5, 0.05, step=0.01)
sd_cycle = st.sidebar.number_input(T["sd_cycle"], 0.0, 0.5, 0.08, step=0.01)
sd_scrap = st.sidebar.number_input(T["sd_scrap"], 0.0, 0.5, 0.01, step=0.005)

# Make vs Buy
st.sidebar.subheader(T["mvb_hdr"])
buy_price = st.sidebar.number_input(T["buy_price"], 0.0, 1e6, 15.0)
moq = st.sidebar.number_input(T["moq"], 1, 100000, 250)
transport_buy = st.sidebar.number_input(T["transport_buy"], 0.0, 1e6, 0.6)

# Capaciteit
st.sidebar.subheader(T["cap_hdr"])
hours_per_day = st.sidebar.number_input(T["hours_day"], 1.0, 24.0, 8.0, step=0.5)
with st.sidebar.expander(T["cap_hdr"]):
    cap_per_process = {p: st.number_input(f"{p} (h/dag)", 0.0, 24.0, 8.0, key=f"cap_{p}") for p in MACHINE_RATES.keys()}

# ---------- actuele prijs ----------
def get_stainless_price_eurkg(grade_key: str) -> Tuple[float, str]:
    base = MATERIALS[materiaal]["base_eurkg"]
    surcharge_eurkg = 0.0
    source = "OTK: manual (€/ton)"
    if otk_mode == T["auto"]:
        try:
            data = fetch_outokumpu_surcharge_eur_ton()
            if debug_otk: st.sidebar.caption(f"OTK raw: {data}")
            if data and grade_key in data:
                eur_ton = data[grade_key]
                surcharge_eurkg = eurton_to_eurkg(eur_ton)
                source = "OTK: scraped (€/ton)"
            else:
                eur_ton = manual_otk_eur_ton
                surcharge_eurkg = eurton_to_eurkg(eur_ton)
        except Exception as e:
            if debug_otk: st.sidebar.warning(f"OTK scrape error: {e}")
            eur_ton = manual_otk_eur_ton
            surcharge_eurkg = eurton_to_eurkg(eur_ton)
    else:
        eur_ton = manual_otk_eur_ton
        surcharge_eurkg = eurton_to_eurkg(eur_ton)
    if surcharge_eurkg > 20: st.sidebar.error("OTK surcharge lijkt >20 €/kg; controleer site/decimalen.")
    return base + surcharge_eurkg, source

def get_aluminium_price_eurkg() -> Tuple[float, str]:
    if lme_mode == T["nasdaq"]:
        lme_eur_ton, src = fetch_lme_eur_ton(nasdaq_key or None)
        if lme_eur_ton is None:
            lme_eur_ton = manual_lme_eur_ton; src = "LME: fallback manual"
    else:
        lme_eur_ton = manual_lme_eur_ton; src = "LME: manual"
    lme_eurkg = eurton_to_eurkg(lme_eur_ton)
    total = lme_eurkg + float(region_premium_eurkg) + float(conversion_adder_eurkg)
    return total, f"{src} + premium + conversion"

def get_other_price_eurkg() -> Tuple[float, str]:
    return MATERIALS[materiaal]["base_eurkg"], "Fixed base"

kind = MATERIALS[materiaal]["kind"]
if kind == "stainless":
    gradekey = OTK_GRADE_KEY.get(materiaal, "")
    price_eurkg, price_source = get_stainless_price_eurkg(gradekey)
elif kind == "aluminium":
    price_eurkg, price_source = get_aluminium_price_eurkg()
else:
    price_eurkg, price_source = get_other_price_eurkg()

st.sidebar.markdown("---")
st.sidebar.markdown(f"**{T['act_price']}: € {price_eurkg:.3f}/kg**")
st.sidebar.caption(f"{T['source']}: {price_source}")

# ---------- prijsprojectie (12m) ----------
st.sidebar.subheader(T["forecast_hdr"])
mchg_rvs = st.sidebar.number_input(T["m_chg_stainless"], -0.5, 0.5, 0.00, 0.01)
mchg_alu = st.sidebar.number_input(T["m_chg_al"], -0.5, 0.5, 0.00, 0.01)
proj_btn = st.sidebar.checkbox(T["apply_proj"], value=False)

def project_12m(base_eurkg: float, monthly_change: float) -> pd.DataFrame:
    vals=[base_eurkg]
    for _ in range(12):
        vals.append(vals[-1]*(1+monthly_change))
    return pd.DataFrame({"Month": list(range(0,13)), "€/kg": vals})

if proj_btn:
    if kind=="stainless":
        proj=project_12m(price_eurkg, mchg_rvs)
    elif kind=="aluminium":
        proj=project_12m(price_eurkg, mchg_alu)
    else:
        proj=project_12m(price_eurkg, 0.0)
    st.plotly_chart(px.line(proj, x="Month", y="€/kg", title=T["forecast_hdr"]), use_container_width=True)

# ---------- CSV templates ----------
ROUTING_COLS = ["Step","Proces","Qty_per_parent","Cycle_min","Setup_min","Attend_pct",
                "kWh_pc","QA_min_pc","Scrap_pct","Parallel_machines","Batch_size","Queue_days"]
BOM_COLS = ["Part","Qty","UnitPrice","Scrap_pct"]

def routing_template_df():
    return pd.DataFrame([{
        "Step":10,"Proces":"CNC","Qty_per_parent":1.0,"Cycle_min":6.0,"Setup_min":20.0,"Attend_pct":100,
        "kWh_pc":0.18,"QA_min_pc":0.5,"Scrap_pct":0.02,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.5
    }], columns=ROUTING_COLS)

def bom_template_df():
    return pd.DataFrame([{"Part":"Voorbeeld onderdeel","Qty":1,"UnitPrice":1.50,"Scrap_pct":0.01}], columns=BOM_COLS)

def df_to_csv_download(df: pd.DataFrame, filename: str, label: str):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), filename, "text/csv")

def _coerce_numeric(df: pd.DataFrame, cols: List[str]):
    for c in cols:
        if c in df.columns: df[c]=pd.to_numeric(df[c], errors="coerce")
    return df

def validate_routing_csv(df: pd.DataFrame):
    miss=[c for c in ROUTING_COLS if c not in df]
    if miss: return df,[f"Routing CSV mist {miss}"]
    df=_coerce_numeric(df.copy(),[c for c in ROUTING_COLS if c!="Proces"])
    df["Proces"]=df["Proces"].astype(str)
    return df[ROUTING_COLS].sort_values("Step").reset_index(drop=True),[]

def validate_bom_csv(df: pd.DataFrame):
    miss=[c for c in BOM_COLS if c not in df]
    if miss: return df,[f"BOM CSV mist {miss}"]
    df=_coerce_numeric(df.copy(),["Qty","UnitPrice","Scrap_pct"])
    df["Part"]=df["Part"].astype(str)
    return df[BOM_COLS].reset_index(drop=True),[]

# ---------- GitHub presets ----------
def gh_get_default_branch(owner:str, repo:str, token:Optional[str]=None):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code==404: raise FileNotFoundError(f"Repo '{owner}/{repo}' niet gevonden of geen toegang.")
    r.raise_for_status()
    return r.json().get("default_branch","main")

@st.cache_data(ttl=300)
def gh_list_files(owner:str, repo:str, folder:str, branch:Optional[str]=None, token:Optional[str]=None):
    if not branch: branch = gh_get_default_branch(owner, repo, token)
    headers = {"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    def _list(br):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder.strip('/')}"
        r = requests.get(url, params={"ref": br}, headers=headers, timeout=20)
        r.raise_for_status(); return r.json()
    try:
        items = _list(branch)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code==404 and branch!="master":
            items=_list("master"); branch="master"
        else: raise
    files=[it for it in items if isinstance(it,dict) and it.get("type")=="file" and it.get("name","").lower().endswith(".json")]
    return files, branch

@st.cache_data(ttl=300)
def gh_fetch_json(owner:str, repo:str, path:str, branch:Optional[str]=None, token:Optional[str]=None):
    if not branch: branch=gh_get_default_branch(owner, repo, token)
    headers={"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    def _fetch(br):
        url=f"https://api.github.com/repos/{owner}/{repo}/contents/{path.strip('/')}"
        r=requests.get(url, params={"ref":br}, headers=headers, timeout=20); r.raise_for_status()
        obj=r.json()
        if "content" in obj and obj.get("encoding")=="base64":
            raw=base64.b64decode(obj["content"]); return json.loads(raw.decode("utf-8")), br
        if "download_url" in obj and obj["download_url"]:
            r2=requests.get(obj["download_url"],timeout=20); r2.raise_for_status(); return r2.json(), br
        raise RuntimeError("Geen content in GitHub API response.")
    try:
        data, used=_fetch(branch)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code==404 and branch!="master":
            data, used=_fetch("master")
        else: raise
    return data

def gh_put_file(owner:str, repo:str, branch:Optional[str], path:str, content_bytes:bytes, message:str, token:str):
    if not token: raise PermissionError("Token met 'repo' scope vereist voor schrijven.")
    if not branch: branch=gh_get_default_branch(owner, repo, token)
    url=f"https://api.github.com/repos/{owner}/{repo}/contents/{path.strip('/')}"
    headers={"Accept":"application/vnd.github+json","Authorization":f"Bearer {token}"}
    payload={"message":message,"content":base64.b64encode(content_bytes).decode(),"branch":branch}
    r=requests.put(url, headers=headers, json=payload, timeout=20)
    if r.status_code==404: raise FileNotFoundError("Pad of repo niet gevonden (controleer owner/repo/branch).")
    r.raise_for_status(); return r.json()

# ---------- session init ----------
if "routing_df" not in st.session_state:
    st.session_state["routing_df"]=routing_template_df()
if "bom_buy_df" not in st.session_state:
    st.session_state["bom_buy_df"]=bom_template_df()

# ---------- Presets UI ----------
st.markdown(f"## {T['presets']}")
colp1, colp2 = st.columns(2)
with colp1:
    if st.button(T["save_preset"]):
        preset={"routing": st.session_state["routing_df"].to_dict("records"),
                "bom_buy": st.session_state["bom_buy_df"].to_dict("records")}
        js=json.dumps(preset, indent=2)
        st.download_button(T["dl_preset"], js.encode("utf-8"), "preset.json", "application/json")
with colp2:
    uploaded=st.file_uploader(T["upload_preset"], type="json")
    if uploaded:
        try:
            pl=json.load(uploaded)
            if "routing" in pl: st.session_state["routing_df"]=pd.DataFrame(pl["routing"])
            if "bom_buy" in pl: st.session_state["bom_buy_df"]=pd.DataFrame(pl["bom_buy"])
            st.success("Preset geladen.")
        except Exception as e:
            st.error(f"Kon JSON niet laden: {e}")

with st.expander(T["gh_block"]):
    owner=st.text_input(T["owner"], "gerrit0492-create")
    repo=st.text_input(T["repo"], "maakindustrie-cost-tool")
    folder=st.text_input(T["folder"], "presets")
    branch_in=st.text_input(T["branch"], "")
    token=st.text_input(T["token"], type="password")
    cols=st.columns(3)
    if cols[0].button(T["list"]):
        try:
            files, used=gh_list_files(owner, repo, folder, branch_in or None, token or None)
            st.session_state["gh_filelist"]=files
            st.info(f"Branch: {used}")
            if not files: st.warning(f"Geen JSON in '{folder}'.")
            else: st.success(f"Gevonden: {[f['name'] for f in files]}")
        except Exception as e:
            st.error(f"GitHub fout: {e}")
    files=st.session_state.get("gh_filelist", [])
    if files:
        names=[f['name'] for f in files]
        sel=st.selectbox("Preset", names, key="gh_sel_name")
        if st.button(T["load"]):
            try:
                path=f"{folder}/{sel}"
                data=gh_fetch_json(owner, repo, path, branch_in or None, token or None)
                if "routing" in data: st.session_state["routing_df"]=pd.DataFrame(data["routing"])
                if "bom_buy" in data: st.session_state["bom_buy_df"]=pd.DataFrame(data["bom_buy"])
                st.success(f"Preset '{sel}' geladen.")
            except Exception as e:
                st.error(f"Mislukt: {e}")
    st.markdown("---")
    if st.button(T["push"]):
        try:
            preset={"routing": st.session_state["routing_df"].to_dict("records"),
                    "bom_buy": st.session_state["bom_buy_df"].to_dict("records")}
            js=json.dumps(preset, indent=2).encode("utf-8")
            _=gh_put_file(owner, repo, branch_in or None, f"{folder.strip('/')}/preset_example.json",
                          js, "Add preset_example.json via app", token or "")
            st.success("Voorbeeldpreset gepusht.")
        except Exception as e:
            st.error(f"Push mislukt: {e}")

# ---------- Auto-routing ----------
st.markdown(f"## {T['autorouting']}")
part_type = st.selectbox(T["product_type"], [
    "Gedraaide as / gefreesd deel",
    "Gefreesde beugel (massief)",
    "Lasframe / samenstel",
    "Plaatwerk kast / bracket",
    "Gietstuk behuizing (CNC na-frees)"
])
holes  = st.number_input(T["holes"], 0, 500, 4)
bends  = st.number_input(T["bends"], 0, 200, 0)
weld_m = st.number_input(T["weld_m"], 0.0, 1000.0, 0.0, 0.5)
panels = st.number_input(T["panels"], 0, 100, 2)

def generate_autorouting(pt: str, holes: int, bends: int, weld_m: float, panels: int):
    rows=[]
    def row(step, proces, cyc, setup, attend, kwh, qa, scrap, par=1, bsize=50, qd=0.5):
        rows.append({"Step":step,"Proces":proces,"Qty_per_parent":1.0,"Cycle_min":max(0.1,cyc),
                     "Setup_min":max(0.0,setup),"Attend_pct":attend,"kWh_pc":max(0.0,kwh),
                     "QA_min_pc":qa,"Scrap_pct":scrap,"Parallel_machines":par,"Batch_size":bsize,"Queue_days":qd})
    if pt=="Gedraaide as / gefreesd deel":
        row(10,"CNC", 8.0 + 0.4*holes, 25.0, 100, 0.20, 0.5, 0.02)
        row(20,"Montage", 4.0 + 0.3*holes, 10.0, 100, 0.05, 0.8, 0.00)
    elif pt=="Gefreesde beugel (massief)":
        row(10,"CNC", 10.0 + 0.5*holes, 30.0, 100, 0.25, 0.6, 0.025)
        row(20,"Montage", 5.0 + 0.3*holes, 10.0, 100, 0.05, 1.0, 0.00)
    elif pt=="Lasframe / samenstel":
        row(10,"Laser", 3.0 + 0.8*panels, 20.0, 50, 0.50, 0.3, 0.01)
        row(20,"Lassen", 6.0 + 6.0*weld_m, 20.0, 100, 0.35, 0.5, 0.015)
        row(30,"CNC", 4.0 + 0.3*holes, 15.0, 100, 0.20, 0.5, 0.01)
        row(40,"Montage", 6.0 + 0.3*holes, 10.0, 100, 0.05, 1.0, 0.00)
    elif pt=="Plaatwerk kast / bracket":
        row(10,"Laser", 3.0 + 0.6*panels, 20.0, 50, 0.50, 0.3, 0.012)
        if bends>0: row(20,"Buigen", 1.6*bends + 0.2*panels, 15.0, 100, 0.10, 0.2, 0.008)
        row(30,"CNC", 2.5 + 0.25*holes, 10.0, 100, 0.15, 0.4, 0.01)
        row(40,"Montage", 5.0 + 0.25*holes, 8.0, 100, 0.05, 0.8, 0.00)
    elif pt=="Gietstuk behuizing (CNC na-frees)":
        row(10,"Casting", 1.2, 60.0, 50, 0.40, 0.2, 0.03)
        row(20,"CNC", 6.0 + 0.4*holes, 25.0, 100, 0.25, 0.6, 0.015)
        row(30,"Montage", 4.0 + 0.2*holes, 8.0, 100, 0.05, 0.8, 0.00)
    return pd.DataFrame(rows).sort_values("Step").reset_index(drop=True)

if st.button(T["gen_route"]):
    st.session_state["routing_df"] = generate_autorouting(part_type, holes, bends, weld_m, panels)
    st.success("Routing gegenereerd – bewerk hieronder.")

# ---------- CSV import/export ----------
st.markdown(f"## {T['csv_ie']}")
c1,c2=st.columns(2)
with c1: df_to_csv_download(routing_template_df(),"routing_template.csv",T["route_tpl"])
with c2: df_to_csv_download(bom_template_df(),"bom_template.csv",T["bom_tpl"])

imp1,imp2=st.columns(2)
with imp1:
    rout_csv=st.file_uploader(T["upload_route"],type="csv",key="r_csv")
    mode_r=st.radio("Import-modus", [T["replace"],T["append"]], horizontal=True, key="mode_r")
    if rout_csv:
        df_in=pd.read_csv(rout_csv); df_val,errs=validate_routing_csv(df_in)
        if errs: [st.error(e) for e in errs]
        else:
            if mode_r==T["replace"]: st.session_state["routing_df"]=df_val
            else:
                st.session_state["routing_df"]=(
                    pd.concat([st.session_state["routing_df"],df_val], ignore_index=True)
                      .drop_duplicates().sort_values("Step")
                )
            st.success(f"Routing {mode_r} – {len(df_val)} rows.")
with imp2:
    bom_csv=st.file_uploader(T["upload_bom"],type="csv",key="b_csv")
    mode_b=st.radio("Import-modus", [T["replace"],T["append"]], horizontal=True, key="mode_b")
    if bom_csv:
        df_in=pd.read_csv(bom_csv); df_val,errs=validate_bom_csv(df_in)
        if errs: [st.error(e) for e in errs]
        else:
            if mode_b==T["replace"]: st.session_state["bom_buy_df"]=df_val
            else:
                st.session_state["bom_buy_df"]=(
                    pd.concat([st.session_state["bom_buy_df"],df_val], ignore_index=True)
                      .drop_duplicates()
                )
            st.success(f"BOM {mode_b} – {len(df_val)} rows.")

# ---------- editors ----------
st.markdown(f"## {T['route_editor']}")
routing_view=st.data_editor(st.session_state["routing_df"],key="routing_editor_widget",num_rows="dynamic",use_container_width=True)
st.session_state["routing_df"]=pd.DataFrame(routing_view)

st.markdown(f"## {T['bom_editor']}")
bom_view=st.data_editor(st.session_state["bom_buy_df"],key="bom_editor_widget",num_rows="dynamic",use_container_width=True)
st.session_state["bom_buy_df"]=pd.DataFrame(bom_view)

# ---------- core calcs ----------
def propagate_scrap(df: pd.DataFrame, Q: int):
    df=df.sort_values("Step").reset_index(drop=True).copy()
    need=float(Q); eff=[]
    for _,r in df[::-1].iterrows():
        scrap=float(r.get("Scrap_pct",0.0))
        good=max(1e-9,1.0-scrap)
        input_qty=need/good
        eff.append(input_qty)
        need=input_qty
    df["Eff_Input_Qty"]=list(reversed(eff))
    return df

def lean_costs(qty_in: float, batch_size: int, energy_kwh_pc: float) -> float:
    """
    Extra Lean-pijlers:
    - opslag: opslagdagen * €/dag * batches
    - transport: km * €/km (eenmalig per order)
    - herbewerking: p(rework)*minuten/60*h * tarief
    - energie: kWh/pc * € (bovenop per-step energie) – hier nemen we extra algemene energie mee
    """
    batches = int(np.ceil(qty_in / max(1,batch_size)))
    cost_storage = storage_days * storage_eur_day_per_batch * batches
    cost_transport = transport_km * transport_eur_km
    cost_rework = rework_pct * qty_in * (rework_min/60.0) * LABOR_RATE
    cost_energy = qty_in * energy_kwh_pc * energy_eur_kwh
    return cost_storage + cost_transport + cost_rework + cost_energy

def cost_once(routing_df: pd.DataFrame, bom_df: pd.DataFrame,
              Q: int, net_kg: float, mat_price: float,
              labor_rate: float = LABOR_RATE, machine_rates: Optional[Dict[str,float]] = None) -> Dict[str, float]:
    if machine_rates is None: machine_rates = MACHINE_RATES
    mat_pc = net_kg * mat_price

    conv_total = 0.0
    lean_total = 0.0

    if not routing_df.empty:
        r=propagate_scrap(routing_df,Q)
        for _,row in r.iterrows():
            proc=str(row.get("Proces",""))
            qty_in=float(row.get("Eff_Input_Qty",Q))
            par=max(1, int(row.get("Parallel_machines",1)))
            batch=max(1, int(row.get("Batch_size",50)))
            batches=int(np.ceil(qty_in/batch))
            setup_min=float(row.get("Setup_min",0.0))*batches
            cycle_min=float(row.get("Cycle_min",0.0))*qty_in
            qa_min=float(row.get("QA_min_pc",0.0))*qty_in
            attend=float(row.get("Attend_pct",100.0))/100.0
            kwh=float(row.get("kWh_pc",0.0))*qty_in

            mach_rate=float(machine_rates.get(proc, labor_rate))
            machine_min=(setup_min+cycle_min)/par
            labor_min=(setup_min+cycle_min+qa_min)*attend
            conv_total += (machine_min/60.0)*mach_rate + (labor_min/60.0)*labor_rate
            conv_total += kwh * energy_eur_kwh

            # lean adders per step (optioneel – hier nemen we kleine algemene energie 0 aan)
            lean_total += lean_costs(qty_in=qty_in, batch_size=batch, energy_kwh_pc=0.0)

    buy_total = 0.0
    if not bom_df.empty:
        b=bom_df.copy()
        b["Line"]=b["Qty"]*b["UnitPrice"]
        b["Line"]*= (1.0 + b.get("Scrap_pct",0.0))
        buy_total = float(b["Line"].sum()) * Q

    total_pc = (mat_pc*Q + conv_total + lean_total + buy_total) / Q
    return {"mat_pc":mat_pc, "conv_total":conv_total, "lean_total":lean_total, "buy_total":buy_total, "total_pc":total_pc}

res = cost_once(st.session_state["routing_df"], st.session_state["bom_buy_df"], Q, net_kg, price_eurkg)

# ---------- Monte Carlo ----------
def run_mc(routing_df, bom_df, Q, net_kg, mat_mu, sd_mat, sd_cycle, sd_scrap,
           labor_rate, machine_rates, iters=1000, seed=123):
    rng=np.random.default_rng(seed)
    out=[]
    r0=pd.DataFrame(routing_df); b0=pd.DataFrame(bom_df)
    for _ in range(int(iters)):
        mat_price=max(0.01, rng.normal(mat_mu, sd_mat*mat_mu))
        r=r0.copy()
        if not r.empty:
            if "Cycle_min" in r:
                r["Cycle_min"]=r["Cycle_min"]*(1.0+rng.normal(0.0,sd_cycle,size=len(r))).clip(lower=0.05)
            if "Scrap_pct" in r:
                r["Scrap_pct"]=(r["Scrap_pct"]+rng.normal(0.0,sd_scrap,size=len(r))).clip(0.0,0.35)
        rr=cost_once(r,b0,Q,net_kg,mat_price,labor_rate,machine_rates)
        out.append(rr["total_pc"])
    return np.array(out)

# ---------- Capaciteit ----------
def capacity_table(routing_df: pd.DataFrame, Q: int, hours_per_day: float, cap_per_process: dict):
    if routing_df is None or len(routing_df)==0:
        return pd.DataFrame(columns=["Proces","Hours_need","Hours_cap","Util_pct","Batches","Setup_min","Cycle_min"])
    r=propagate_scrap(routing_df.copy(),Q)
    rows=[]
    for _,row in r.iterrows():
        proc=str(row["Proces"])
        qty_in=float(row.get("Eff_Input_Qty",Q))
        par=max(1,int(row.get("Parallel_machines",1)))
        batch=max(1,int(row.get("Batch_size",50)))
        batches=int(np.ceil(qty_in/batch))
        setup_min=float(row.get("Setup_min",0.0))*batches
        cycle_min=float(row.get("Cycle_min",0.0))*qty_in
        machine_min=(setup_min+cycle_min)/par
        need_h=machine_min/60.0
        cap_h=float(cap_per_process.get(proc, hours_per_day))
        util=(need_h/max(cap_h,1e-6)) if cap_h>0 else np.nan
        rows.append([proc,need_h,cap_h,util,batches,setup_min,cycle_min])
    df=pd.DataFrame(rows,columns=["Proces","Hours_need","Hours_cap","Util_pct","Batches","Setup_min","Cycle_min"])
    df=df.groupby("Proces",as_index=False).sum(numeric_only=True)
    df["Util_pct"]=(df["Hours_need"]/df["Hours_cap"]).replace([np.inf,-np.inf],np.nan)
    return df.sort_values("Util_pct",ascending=False)

# ---------- KPI's ----------
st.markdown(f"## {T['kpi_hdr']}")
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric(T["mat_pc"], f"€ {res['mat_pc']:.2f}")
c2.metric(T["conv_total"], f"€ {res['conv_total']:.2f}")
c3.metric("Lean adders", f"€ {res['lean_total']:.2f}")
c4.metric(T["buy_total"], f"€ {res['buy_total']:.2f}")
c5.metric(T["unit_cost"], f"€ {res['total_pc']:.2f}")

fig = go.Figure(go.Pie(labels=["Materiaal","Conversie","Lean","Inkoopdelen"],
                       values=[res['mat_pc'], res['conv_total'], res['lean_total'], res['buy_total']]))
st.plotly_chart(fig, use_container_width=True)

# Monte Carlo
if mc_on:
    st.markdown(f"### {T['mc_title']}")
    samples=run_mc(st.session_state["routing_df"], st.session_state["bom_buy_df"],
                   Q, net_kg, price_eurkg, sd_mat, sd_cycle, sd_scrap,
                   LABOR_RATE, MACHINE_RATES, iters=mc_iter, seed=123)
    p50=float(np.percentile(samples,50)); p80=float(np.percentile(samples,80)); p95=float(np.percentile(samples,95))
    c1,c2,c3=st.columns(3)
    c1.metric("P50", f"€ {p50:.2f}")
    c2.metric("P80", f"€ {p80:.2f}")
    c3.metric("P95", f"€ {p95:.2f}")
    st.plotly_chart(px.histogram(pd.DataFrame({"Kostprijs/stuk":samples}), x="Kostprijs/stuk", nbins=40), use_container_width=True)

# Capaciteit
st.markdown(f"### {T['cap_title']}")
cap_df = capacity_table(st.session_state["routing_df"], Q, hours_per_day, cap_per_process)
if cap_df.empty:
    st.info("Geen routingdata om capaciteit te berekenen.")
else:
    cap_show = cap_df.copy(); cap_show["Util_%"]=(cap_show["Util_pct"]*100).round(1)
    st.dataframe(cap_show[["Proces","Hours_need","Hours_cap","Util_%","Batches","Setup_min","Cycle_min"]], use_container_width=True)
    fig_util = px.bar(cap_df, x="Proces", y="Util_pct", text=(cap_df["Util_pct"]*100).round(1))
    fig_util.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig_util, use_container_width=True)
    bottleneck = cap_df.sort_values("Util_pct", ascending=False).iloc[0]
    st.warning(f"{T['bneck']}: **{bottleneck['Proces']}** – {(bottleneck['Util_pct']*100):.1f}%")

# Make vs Buy
st.markdown(f"### {T['mvb_title']}")
if Q >= moq:
    buy_unit = buy_price + transport_buy
else:
    buy_unit = (buy_price * moq) / Q + transport_buy
capacity_penalty = 0.0
if not cap_df.empty and cap_df["Util_pct"].max() > 1.0:
    overload=float(cap_df["Util_pct"].max()-1.0)
    capacity_penalty = overload * 0.10 * res["total_pc"]
make_unit = res["total_pc"] + capacity_penalty
adv = T["buy"] if buy_unit < make_unit else T["make"]
delta = abs(make_unit - buy_unit)
cc1,cc2,cc3 = st.columns(3)
cc1.metric("Make €/stuk", f"€ {make_unit:.2f}")
cc2.metric("Buy €/stuk", f"€ {buy_unit:.2f}")
cc3.metric("Advies", adv)

# ---------- Export ----------
st.markdown(f"## {T['export']}")
ccsv1, ccsv2 = st.columns(2)
with ccsv1:
    st.download_button(T["dl_route"], st.session_state["routing_df"].to_csv(index=False).encode("utf-8"),
                       f"{project}_routing.csv", "text/csv")
with ccsv2:
    st.download_button(T["dl_bom"], st.session_state["bom_buy_df"].to_csv(index=False).encode("utf-8"),
                       f"{project}_bom.csv", "text/csv")

# PDF
if st.button(T["gen_pdf"]):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 14); c.drawString(30, 800, f"Offerte – {project}")
    c.setFont("Helvetica", 10)
    c.drawString(30, 780, f"Q: {Q}")
    c.drawString(30, 765, f"Materiaal: {materiaal} – € {price_eurkg:.3f}/kg ({price_source})")
    data = [["Post","Bedrag (€)"],
            ["Materiaal", f"{res['mat_pc']:.2f}"],
            ["Conversie", f"{res['conv_total']:.2f}"],
            ["Lean", f"{res['lean_total']:.2f}"],
            ["Inkoopdelen", f"{res['buy_total']:.2f}"],
            ["Totaal", f"{res['total_pc']:.2f}"],
            ["Verkoop (incl. marge+cont.)", f"{(res['total_pc']*(1+PROFIT_PCT+CONTINGENCY_PCT)):.2f}"]]
    table = Table(data, colWidths=[200,130])
    style = TableStyle([("BACKGROUND",(0,0),(-1,0),colors.grey),
                        ("TEXTCOLOR",(0,0),(-1,0),colors.whitesmoke),
                        ("ALIGN",(0,0),(-1,-1),"CENTER"),
                        ("GRID",(0,0),(-1,-1),0.5,colors.black)])
    table.setStyle(style); table.wrapOn(c, 400, 600)
    table.drawOn(c, 30, 700-20*len(data))
    c.save(); buffer.seek(0)
    st.download_button(T["dl_pdf"], buffer.getvalue(), "quote.pdf", "application/pdf")

# Excel
out_buf = io.BytesIO()
with pd.ExcelWriter(out_buf, engine="xlsxwriter") as writer:
    st.session_state["routing_df"].to_excel(writer, index=False, sheet_name="Routing")
    st.session_state["bom_buy_df"].to_excel(writer, index=False, sheet_name="BOM_buy")
    pd.DataFrame([
        {"Post":"Materiaal","Bedrag":res["mat_pc"]},
        {"Post":"Conversie","Bedrag":res["conv_total"]},
        {"Post":"Lean","Bedrag":res["lean_total"]},
        {"Post":"Inkoopdelen","Bedrag":res["buy_total"]},
        {"Post":"Totaal","Bedrag":res["total_pc"]},
        {"Post":"Verkoop (incl. marge+cont.)","Bedrag":res["total_pc"]*(1+PROFIT_PCT+CONTINGENCY_PCT)}
    ]).to_excel(writer, index=False, sheet_name="Summary")
    # Traceability & parameters
    pd.DataFrame([{
        "Materiaal": materiaal,
        "Actuele €/kg": price_eurkg,
        "Bron": price_source,
        "Energy €/kWh": energy_eur_kwh,
        "Storage_days": storage_days,
        "Storage €/day/batch": storage_eur_day_per_batch,
        "Transport_km": transport_km,
        "Transport €/km": transport_eur_km,
        "Rework_pct": rework_pct,
        "Rework_min": rework_min,
        "Project": project, "Q": Q, "Net_kg": net_kg
    }]).to_excel(writer, index=False, sheet_name="Params_Trace")
    # Client input sheet
    pd.DataFrame([
        {"Veld":"Omschrijving_product","Waarde":""},
        {"Veld":"Toleranties","Waarde":""},
        {"Veld":"Materiaal_specificatie","Waarde":materiaal},
        {"Veld":"Aantal_stuks","Waarde":Q},
        {"Veld":"Gewenste_levertijd","Waarde":""},
        {"Veld":"Verpakking","Waarde":""},
        {"Veld":"Incoterms","Waarde":"EXW"},
        {"Veld":"Afwijkende_eisen","Waarde":""},
    ]).to_excel(writer, index=False, sheet_name="ClientInput")
    # Capacity
    cap_x = capacity_table(st.session_state["routing_df"], Q, hours_per_day, cap_per_process)
    if not cap_x.empty:
        cap_x.to_excel(writer, index=False, sheet_name="Capacity")
    # MC sheets
    if mc_on:
        samples = run_mc(st.session_state["routing_df"], st.session_state["bom_buy_df"],
                         Q, net_kg, price_eurkg, sd_mat, sd_cycle, sd_scrap,
                         LABOR_RATE, MACHINE_RATES, iters=mc_iter, seed=123)
        pd.DataFrame({"Kostprijs/stuk": samples}).to_excel(writer, index=False, sheet_name="MC_samples")
        pd.DataFrame([{"P50":float(np.percentile(samples,50)),
                       "P80":float(np.percentile(samples,80)),
                       "P95":float(np.percentile(samples,95))}]).to_excel(writer, index=False, sheet_name="MC_stats")
out_buf.seek(0)
st.download_button(T["dl_xlsx"], out_buf.getvalue(), f"{project}_calc.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown(T["ready"])
