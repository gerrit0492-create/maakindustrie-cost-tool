# app.py
import io
import re
import json
import base64
from typing import Dict, Tuple, Optional

from datetime import date
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

st.set_page_config(page_title="Maakindustrie Cost Tool – Outokumpu + LME",
                   layout="wide", page_icon="🧮")

# ========================================
# Basis-config
# ========================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (CostTool/1.0; +https://example.local)",
    "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
}

# Materialen (basisprijzen in €/kg); voor RVS/Al wordt dit aangevuld met surcharge/LME
MATERIALS: Dict[str, Dict] = {
    # RVS → Outokumpu alloy surcharge (€/ton) + basis €/kg
    "SS304":            {"base_eurkg": 2.80, "kind": "stainless", "aliases": ["304","1.4301"]},
    "SS316L":           {"base_eurkg": 3.40, "kind": "stainless", "aliases": ["316L","1.4404"]},
    "1.4462_Duplex":    {"base_eurkg": 4.20, "kind": "stainless", "aliases": ["2205","1.4462"]},
    "SuperDuplex_2507": {"base_eurkg": 5.40, "kind": "stainless", "aliases": ["2507","1.4410"]},
    "SS904L":           {"base_eurkg": 6.10, "kind": "stainless", "aliases": ["904L","1.4539"]},

    # Aluminium → LME (€/ton → €/kg) + regiopremie + conversie
    "Al_6082":          {"base_eurkg": 0.00, "kind": "aluminium", "aliases": ["6082"]},
    "Extruded_Al_6060": {"base_eurkg": 0.00, "kind": "aluminium", "aliases": ["6060"]},
    "Cast_Aluminium":   {"base_eurkg": 0.00, "kind": "aluminium", "aliases": ["Cast Al"]},

    # Overig (geen OTK/LME logica) → vaste basis
    "S235JR_steel":     {"base_eurkg": 1.40, "kind": "other"},
    "S355J2_steel":     {"base_eurkg": 1.70, "kind": "other"},
    "C45":              {"base_eurkg": 1.90, "kind": "other"},
    "42CrMo4":          {"base_eurkg": 2.60, "kind": "other"},
    "Cu_ECW":           {"base_eurkg": 8.00, "kind": "other"},
}

OTK_GRADE_KEY = {  # mapping naar surcharge-keys
    "SS304": "304",
    "SS316L": "316L",
    "1.4462_Duplex": "2205",
    "SuperDuplex_2507": "2507",
    "SS904L": "904L",
}

# Tarieven, marges
MACHINE_RATES = {"CNC":85.0,"Laser":110.0,"Lassen":55.0,"Buigen":75.0,"Montage":40.0,"Casting":65.0}
LABOR_RATE = 45.0
PROFIT_PCT = 0.12
CONTINGENCY_PCT = 0.05

# ========================================
# Util
# ========================================
def eurton_to_eurkg(value_eur_per_ton: float) -> float:
    return (value_eur_per_ton or 0.0) / 1000.0

# ========================================
# Scrapers – Outokumpu (€/ton)
# ========================================
def fetch_outokumpu_surcharge_eur_ton(timeout=12) -> Dict[str, float]:
    """
    Best-effort parse van Outokumpu 'Surcharges' pagina.
    Retourneert dict: {'304': 2238.0, '316L': 3693.0, ...} in €/ton als gevonden.
    Site-HTML kan wijzigen; dan valt de app terug op handmatige invoer.
    """
    url = "https://www.outokumpu.com/en/surcharges"
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text(" ", strip=True)

    def grab(pattern: str) -> Optional[float]:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            return None
        raw = m.group(1).strip()
        # "2.238" of "2,238" → "2238"
        raw = raw.replace(".", "").replace(",", "")
        try:
            return float(raw)
        except:
            return None

    patterns = {
        "304":  r"(?:304|1\.4301)[^\d€]{0,40}€\s?([\d\.\,]+)\s*(?:/t|/ton|per ton)",
        "316L": r"(?:316L|1\.4404)[^\d€]{0,40}€\s?([\d\.\,]+)\s*(?:/t|/ton|per ton)",
        "2205": r"(?:2205|1\.4462)[^\d€]{0,40}€\s?([\d\.\,]+)\s*(?:/t|/ton|per ton)",
        "2507": r"(?:2507|1\.4410)[^\d€]{0,40}€\s?([\d\.\,]+)\s*(?:/t|/ton|per ton)",
        "904L": r"(?:904L|1\.4539)[^\d€]{0,40}€\s?([\d\.\,]+)\s*(?:/t|/ton|per ton)",
    }
    out: Dict[str, float] = {}
    for g, pat in patterns.items():
        v = grab(pat)
        if v:
            out[g] = v
    return out

# ========================================
# LME Aluminium (€/ton) – feeds/scraping
# ========================================
def fetch_ecb_usd_eur(timeout=10) -> Optional[float]:
    """USD→EUR koers via exchangerate.host (gratis)."""
    try:
        r = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=EUR",
                         headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return float(data["rates"]["EUR"])
    except Exception:
        return None

def fetch_lme_via_nasdaq(api_key: str, timeout=12) -> Optional[float]:
    """
    Nasdaq Data Link (officiële LME dataset). Haal laatste 'Cash' (USD/ton) en convert naar EUR/ton.
    """
    try:
        url = f"https://data.nasdaq.com/api/v3/datasets/LME/PR_AL.json?api_key={api_key}&rows=1"
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        js = r.json()
        cols = js["dataset"]["column_names"]
        row = js["dataset"]["data"][0]
        rec = dict(zip(cols, row))
        candidates = [k for k in rec.keys() if "cash" in k.lower() and "usd" in k.lower()]
        if not candidates:
            return None
        usd_per_ton = float(rec[candidates[0]])
        fx = fetch_ecb_usd_eur() or 0.92
        return usd_per_ton * fx
    except Exception:
        return None

def fetch_lme_via_tradingeconomics(timeout=12) -> Optional[float]:
    """
    Best-effort parse van TradingEconomics (USD/ton) → ECB FX → EUR/ton.
    """
    try:
        url = "https://tradingeconomics.com/commodity/aluminum"
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        text = r.text
        m = re.search(r'(?i)Aluminum.*?(\d{3,5}(?:\.\d{1,2})?)', text)
        if not m:
            m = re.search(r'data-price="(\d{3,5}(?:\.\d{1,2})?)"', text)
        if not m:
            return None
        usd_per_ton = float(m.group(1))
        fx = fetch_ecb_usd_eur() or 0.92
        return usd_per_ton * fx
    except Exception:
        return None

def fetch_lme_eur_ton(nasdaq_key: Optional[str]) -> Tuple[Optional[float], str]:
    """
    1) Nasdaq Data Link (API key) → EUR/ton
    2) TradingEconomics (scrape) → USD/ton → EUR/ton
    3) None → fallback handmatig
    """
    if nasdaq_key:
        v = fetch_lme_via_nasdaq(nasdaq_key)
        if v:
            return v, "Nasdaq Data Link (LME) → ECB FX"
    v2 = fetch_lme_via_tradingeconomics()
    if v2:
        return v2, "TradingEconomics scrape → ECB FX"
    return None, "Geen LME online bron gevonden (fallback handmatig)"

# ========================================
# Sidebar – Invoer
# ========================================
st.sidebar.header("Invoer")
project = st.sidebar.text_input("Project", "Demo")
Q = st.sidebar.number_input("Aantal stuks (Q)", min_value=1, value=50, step=1)
materiaal = st.sidebar.selectbox("Materiaal", list(MATERIALS.keys()))
net_kg = st.sidebar.number_input("Netto gewicht per stuk (kg)", min_value=0.01, value=2.0)

# RVS – OTK surcharge
st.sidebar.subheader("RVS – Outokumpu alloy surcharge (€/ton)")
otk_mode = st.sidebar.radio("Bron", ["Automatisch (scrape)", "Handmatig"], horizontal=True, key="otk_mode")
manual_otk_eur_ton = st.sidebar.number_input("Handmatig: OTK surcharge (€/ton)", min_value=0.0, value=0.0, step=10.0)

# Aluminium – LME
st.sidebar.subheader("Aluminium – LME (€/ton → €/kg)")
lme_mode = st.sidebar.radio("LME bron", ["Automatisch (Nasdaq/TE)", "Handmatig"], horizontal=True, key="lme_mode")
nasdaq_key = st.sidebar.text_input("Nasdaq Data Link API key (optioneel)", value="", type="password")
manual_lme_eur_ton = st.sidebar.number_input("Handmatig: LME (€/ton)", min_value=0.0, value=2200.0, step=10.0)
region_premium_eurkg = st.sidebar.number_input("Regiopremie (€/kg)", min_value=0.0, value=0.25, step=0.01)
conversion_adder_eurkg = st.sidebar.number_input("Conversie-opslag (€/kg)", min_value=0.0, value=0.40, step=0.01)

# Monte-Carlo & Make-vs-Buy & Capaciteit
st.sidebar.subheader("Monte-Carlo onzekerheid")
mc_on = st.sidebar.checkbox("Monte-Carlo simulatie aan", value=False)
mc_iter = st.sidebar.number_input("Iteraties", 100, 20000, 1000, step=100)
sd_mat = st.sidebar.number_input("σ materiaalprijs (%)", 0.0, 0.5, 0.05, step=0.01)
sd_cycle = st.sidebar.number_input("σ cyclustijd (%)", 0.0, 0.5, 0.08, step=0.01)
sd_scrap = st.sidebar.number_input("σ scrap additief (abs)", 0.0, 0.5, 0.01, step=0.005)

st.sidebar.subheader("Make vs Buy parameters")
buy_price = st.sidebar.number_input("Inkoopprijs/stuk (€)", 0.0, 1e6, 15.0)
moq = st.sidebar.number_input("MOQ", 1, 100000, 250)
transport_buy = st.sidebar.number_input("Transport/handling (€/stuk)", 0.0, 1e6, 0.6)

st.sidebar.subheader("Capaciteit (uren/dag per proces)")
hours_per_day = st.sidebar.number_input("Uren productie per dag", 1.0, 24.0, 8.0, step=0.5)
with st.sidebar.expander("Capaciteit per proces (uren/dag)"):
    cap_per_process = {p: st.number_input(f"{p} (h/dag)", 0.0, 24.0, 8.0, key=f"cap_{p}") for p in MACHINE_RATES.keys()}

# ========================================
# Actuele prijs per kg
# ========================================
def get_stainless_price_eurkg(grade_key: str) -> Tuple[float, str]:
    base = MATERIALS[materiaal]["base_eurkg"]
    surcharge_eurkg = 0.0
    source = "OTK: handmatig (€/ton)"

    if otk_mode == "Automatisch (scrape)":
        try:
            data = fetch_outokumpu_surcharge_eur_ton()
            if data and grade_key in data:
                surcharge_eurkg = eurton_to_eurkg(data[grade_key])
                source = "OTK: scraped (€/ton)"
            else:
                surcharge_eurkg = eurton_to_eurkg(manual_otk_eur_ton)
                source = "OTK: fallback handmatig (€/ton)"
        except Exception:
            surcharge_eurkg = eurton_to_eurkg(manual_otk_eur_ton)
            source = "OTK: fallback handmatig (€/ton)"
    else:
        surcharge_eurkg = eurton_to_eurkg(manual_otk_eur_ton)

    return base + surcharge_eurkg, source

def get_aluminium_price_eurkg() -> Tuple[float, str]:
    lme_eur_ton = None
    src = "LME: handmatig (€/ton)"
    if lme_mode == "Automatisch (Nasdaq/TE)":
        lme_eur_ton, src = fetch_lme_eur_ton(nasdaq_key.strip() or None)
        if lme_eur_ton is None:
            lme_eur_ton = manual_lme_eur_ton
            src = "LME: fallback handmatig (€/ton)"
    else:
        lme_eur_ton = manual_lme_eur_ton

    lme_eurkg = eurton_to_eurkg(lme_eur_ton)
    total = lme_eurkg + float(region_premium_eurkg) + float(conversion_adder_eurkg)
    return total, f"{src} + premie + conversie"

def get_other_price_eurkg() -> Tuple[float, str]:
    return MATERIALS[materiaal]["base_eurkg"], "Vaste basisprijs"

kind = MATERIALS[materiaal]["kind"]
if kind == "stainless":
    gradekey = OTK_GRADE_KEY.get(materiaal, "")
    price_eurkg, price_source = get_stainless_price_eurkg(gradekey)
elif kind == "aluminium":
    price_eurkg, price_source = get_aluminium_price_eurkg()
else:
    price_eurkg, price_source = get_other_price_eurkg()

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Actuele materiaalprijs:** **€ {price_eurkg:.3f}/kg**")
st.sidebar.caption(f"Bron: {price_source}")

# ========================================
# CSV helpers
# ========================================
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

def _coerce_numeric(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
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

# ========================================
# GitHub presets (robuust)
# ========================================
def gh_get_default_branch(owner:str, repo:str, token:Optional[str]=None):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code==404:
        raise FileNotFoundError(f"Repo '{owner}/{repo}' niet gevonden of geen toegang.")
    r.raise_for_status()
    return r.json().get("default_branch","main")

@st.cache_data(ttl=300)
def gh_list_files(owner:str, repo:str, folder:str, branch:Optional[str]=None, token:Optional[str]=None):
    if not branch:
        branch = gh_get_default_branch(owner, repo, token)
    headers = {"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]=f"Bearer {token}"

    def _list(br):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder.strip('/')}"
        r = requests.get(url, params={"ref": br}, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()

    try:
        items = _list(branch)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code==404 and branch!="master":
            items = _list("master")
            branch = "master"
        else:
            raise

    files = [it for it in items
             if isinstance(it, dict) and it.get("type")=="file" and it.get("name","").lower().endswith(".json")]
    return files, branch

@st.cache_data(ttl=300)
def gh_fetch_json(owner:str, repo:str, path:str, branch:Optional[str]=None, token:Optional[str]=None):
    if not branch:
        branch = gh_get_default_branch(owner, repo, token)
    headers = {"Accept":"application/vnd.github+json"}
    if token: headers["Authorization"]=f"Bearer {token}"

    def _fetch(br):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path.strip('/')}"
        r = requests.get(url, params={"ref": br}, headers=headers, timeout=20)
        r.raise_for_status()
        obj = r.json()
        if "content" in obj and obj.get("encoding")=="base64":
            raw = base64.b64decode(obj["content"])
            return json.loads(raw.decode("utf-8")), br
        if "download_url" in obj and obj["download_url"]:
            r2 = requests.get(obj["download_url"], timeout=20); r2.raise_for_status()
            return r2.json(), br
        raise RuntimeError("Onverwachte GitHub API-respons; geen content gevonden.")

    try:
        data, used = _fetch(branch)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code==404 and branch!="master":
            data, used = _fetch("master")
        else:
            raise
    return data

def gh_put_file(owner:str, repo:str, branch:Optional[str], path:str, content_bytes:bytes, message:str, token:str):
    if not token:
        raise PermissionError("Token met 'repo' scope vereist voor schrijven.")
    if not branch:
        branch = gh_get_default_branch(owner, repo, token)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path.strip('/')}"
    headers = {"Accept":"application/vnd.github+json", "Authorization":f"Bearer {token}"}
    b64 = base64.b64encode(content_bytes).decode()
    payload = {"message": message, "content": b64, "branch": branch}
    r = requests.put(url, headers=headers, json=payload, timeout=20)
    if r.status_code==404:
        raise FileNotFoundError("Pad of repo niet gevonden (controleer owner/repo/branch).")
    r.raise_for_status()
    return r.json()

# ========================================
# Routing & BOM – init en UI
# ========================================
if "routing_df" not in st.session_state:
    st.session_state["routing_df"] = routing_template_df()
if "bom_buy_df" not in st.session_state:
    st.session_state["bom_buy_df"] = bom_template_df()

st.markdown("## 📂 Presets & JSON")
colp1, colp2 = st.columns(2)
with colp1:
    if st.button("💾 Save preset (JSON)"):
        preset = {
            "routing": pd.DataFrame(st.session_state["routing_df"]).to_dict(orient="records"),
            "bom_buy": pd.DataFrame(st.session_state["bom_buy_df"]).to_dict(orient="records"),
        }
        js = json.dumps(preset, indent=2)
        st.download_button("⬇️ Download preset.json", js.encode("utf-8"), "preset.json", "application/json")
with colp2:
    uploaded = st.file_uploader("Upload JSON preset", type="json")
    if uploaded:
        try:
            pl = json.load(uploaded)
            if "routing" in pl: st.session_state["routing_df"] = pd.DataFrame(pl["routing"])
            if "bom_buy" in pl: st.session_state["bom_buy_df"] = pd.DataFrame(pl["bom_buy"])
            st.success("Preset geladen.")
        except Exception as e:
            st.error(f"Kon JSON niet laden: {e}")

with st.expander("🔗 GitHub presets laden / aanmaken"):
    owner = st.text_input("GitHub owner", "gerrit0492-create")
    repo = st.text_input("Repository", "maakindustrie-cost-tool")
    folder = st.text_input("Folder", "presets")
    branch_in = st.text_input("Branch (leeg = autodetect)", "")
    token = st.text_input("Token (alleen nodig voor schrijven of private repo)", type="password")
    cols = st.columns(3)
    if cols[0].button("📂 Lijst presets"):
        try:
            files, used_branch = gh_list_files(owner, repo, folder, branch_in or None, token or None)
            st.session_state["gh_filelist"] = files
            st.info(f"Branch gebruikt: {used_branch}")
            if not files:
                st.warning(f"Geen JSON-bestanden in '{folder}'. Maak er één met de knop hieronder.")
            else:
                st.success(f"Gevonden: {[f['name'] for f in files]}")
        except Exception as e:
            st.error(f"GitHub fout: {e}")
    files = st.session_state.get("gh_filelist", [])
    if files:
        names = [f['name'] for f in files]
        sel = st.selectbox("Kies preset", names, key="gh_sel_name")
        if st.button("⬇️ Preset laden"):
            try:
                path = f"{folder}/{sel}"
                data = gh_fetch_json(owner, repo, path, branch_in or None, token or None)
                if "routing" in data: st.session_state["routing_df"] = pd.DataFrame(data["routing"])
                if "bom_buy" in data: st.session_state["bom_buy_df"] = pd.DataFrame(data["bom_buy"])
                st.success(f"Preset '{sel}' geladen.")
            except Exception as e:
                st.error(f"Mislukt: {e}")
    st.markdown("---")
    if st.button("🆕 Push voorbeeldpreset naar repo"):
        try:
            preset = {
                "routing": pd.DataFrame(st.session_state["routing_df"]).to_dict(orient="records"),
                "bom_buy": pd.DataFrame(st.session_state["bom_buy_df"]).to_dict(orient="records"),
            }
            js = json.dumps(preset, indent=2).encode("utf-8")
            _ = gh_put_file(owner, repo, branch_in or None, path=f"{folder.strip('/')}/preset_example.json",
                            content_bytes=js, message="Add preset_example.json via app", token=token or "")
            st.success("Voorbeeldpreset gepusht → klik daarna op '📂 Lijst presets'.")
        except Exception as e:
            st.error(f"Push mislukt: {e}")

# Auto-routing (optioneel)
st.markdown("## 🧩 Auto-routing")
part_type = st.selectbox("Type product", [
    "Gedraaide as / gefreesd deel",
    "Gefreesde beugel (massief)",
    "Lasframe / samenstel",
    "Plaatwerk kast / bracket",
    "Gietstuk behuizing (CNC na-frees)"
])
holes = st.number_input("Aantal gaten", 0, 500, 4)
bends = st.number_input("Aantal zetten (plaatwerk)", 0, 200, 0)
weld_m = st.number_input("Laslengte (m)", 0.0, 1000.0, 0.0, 0.5)
panels = st.number_input("Aantal plaatdelen", 0, 100, 2)

def generate_autorouting(pt: str, holes: int, bends: int, weld_m: float, panels: int):
    rows=[]
    def row(step, proces, cyc, setup, attend, kwh, qa, scrap, par=1, bsize=50, qd=0.5):
        rows.append({
            "Step":step,"Proces":proces,"Qty_per_parent":1.0,"Cycle_min":max(0.1,cyc),"Setup_min":max(0.0,setup),
            "Attend_pct":attend,"kWh_pc":max(0.0,kwh),"QA_min_pc":qa,"Scrap_pct":scrap,
            "Parallel_machines":par,"Batch_size":bsize,"Queue_days":qd
        })
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
        if bends>0:
            row(20,"Buigen", 1.6*bends + 0.2*panels, 15.0, 100, 0.10, 0.2, 0.008)
        row(30,"CNC", 2.5 + 0.25*holes, 10.0, 100, 0.15, 0.4, 0.01)
        row(40,"Montage", 5.0 + 0.25*holes, 8.0, 100, 0.05, 0.8, 0.00)
    elif pt=="Gietstuk behuizing (CNC na-frees)":
        row(10,"Casting", 1.2, 60.0, 50, 0.40, 0.2, 0.03)
        row(20,"CNC", 6.0 + 0.4*holes, 25.0, 100, 0.25, 0.6, 0.015)
        row(30,"Montage", 4.0 + 0.2*holes, 8.0, 100, 0.05, 0.8, 0.00)
    return pd.DataFrame(rows).sort_values("Step").reset_index(drop=True)

if st.button("🔮 Genereer routing"):
    st.session_state["routing_df"] = generate_autorouting(part_type, holes, bends, weld_m, panels)
    st.success("Routing gegenereerd – bewerk hieronder.")

# CSV UI
st.markdown("## 🧩 CSV import/export")
c1,c2=st.columns(2)
with c1: df_to_csv_download(routing_template_df(),"routing_template.csv","⬇️ Routing sjabloon")
with c2: df_to_csv_download(bom_template_df(),"bom_template.csv","⬇️ BOM sjabloon")

imp1,imp2=st.columns(2)
with imp1:
    rout_csv=st.file_uploader("Upload Routing CSV",type="csv",key="r_csv")
    mode_r=st.radio("Import-modus",["Replace","Append"],horizontal=True,key="mode_r")
    if rout_csv:
        df_in=pd.read_csv(rout_csv);df_val,errs=validate_routing_csv(df_in)
        if errs: [st.error(e) for e in errs]
        else:
            if mode_r=="Replace": st.session_state["routing_df"]=df_val
            else: st.session_state["routing_df"]=pd.concat([st.session_state["routing_df"],df_val],ignore_index=True).drop_duplicates().sort_values("Step")
            st.success(f"Routing {mode_r} met {len(df_val)} regels.")
with imp2:
    bom_csv=st.file_uploader("Upload BOM CSV",type="csv",key="b_csv")
    mode_b=st.radio("Import-modus",["Replace","Append"],horizontal=True,key="mode_b")
    if bom_csv:
        df_in=pd.read_csv(bom_csv);df_val,errs=validate_bom_csv(df_in)
        if errs: [st.error(e) for e in errs]
        else:
            if mode_b=="Replace": st.session_state["bom_buy_df"]=df_val
            else: st.session_state["bom_buy_df"]=pd.concat([st.session_state["bom_buy_df"],df_val],ignore_index=True).drop_duplicates()
            st.success(f"BOM {mode_b} met {len(df_val)} regels.")

# Editors
st.markdown("## Routing editor")
routing_view=st.data_editor(st.session_state["routing_df"],key="routing_editor_widget",num_rows="dynamic",use_container_width=True)
st.session_state["routing_df"]=pd.DataFrame(routing_view)

st.markdown("## BOM editor")
bom_view=st.data_editor(st.session_state["bom_buy_df"],key="bom_editor_widget",num_rows="dynamic",use_container_width=True)
st.session_state["bom_buy_df"]=pd.DataFrame(bom_view)

# ========================================
# Kernberekeningen
# ========================================
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

def cost_once(routing_df: pd.DataFrame, bom_df: pd.DataFrame,
              Q: int, net_kg: float, mat_price: float,
              labor_rate: float = LABOR_RATE, machine_rates: Optional[Dict[str,float]] = None) -> Dict[str, float]:
    if machine_rates is None:
        machine_rates = MACHINE_RATES

    # Materiaal
    mat_pc = net_kg * mat_price

    # Conversie
    conv_total = 0.0
    if not routing_df.empty:
        r = propagate_scrap(routing_df, Q)
        for _, row in r.iterrows():
            proc = str(row.get("Proces",""))
            qty_in = float(row.get("Eff_Input_Qty", Q))
            par = max(1, int(row.get("Parallel_machines",1)))
            batch = max(1, int(row.get("Batch_size",50)))
            batches = int(np.ceil(qty_in / batch))

            setup_min = float(row.get("Setup_min",0.0)) * batches
            cycle_min = float(row.get("Cycle_min",0.0)) * qty_in
            qa_min = float(row.get("QA_min_pc",0.0)) * qty_in
            attend = float(row.get("Attend_pct",100.0))/100.0
            kwh = float(row.get("kWh_pc",0.0)) * qty_in

            mach_rate = float(machine_rates.get(proc, labor_rate))
            machine_min = (setup_min + cycle_min) / par
            labor_min = (setup_min + cycle_min + qa_min) * attend
            conv_total += (machine_min/60.0)*mach_rate + (labor_min/60.0)*labor_rate
            conv_total += kwh * 0.20  # simpele energie €0.20/kWh

    # Ingekocht
    buy_total = 0.0
    if not bom_df.empty:
        b = bom_df.copy()
        b["Line"] = b["Qty"] * b["UnitPrice"]
        b["Line"] *= (1.0 + b.get("Scrap_pct",0.0))
        buy_total = float(b["Line"].sum()) * Q

    total_pc = (mat_pc*Q + conv_total + buy_total) / Q
    return {"mat_pc": mat_pc, "conv_total": conv_total, "buy_total": buy_total, "total_pc": total_pc}

res = cost_once(st.session_state["routing_df"], st.session_state["bom_buy_df"],
                Q=Q, net_kg=net_kg, mat_price=price_eurkg)

# Monte-Carlo
def run_mc(routing_df, bom_df, Q, net_kg, mat_mu, sd_mat, sd_cycle, sd_scrap,
           labor_rate, machine_rates, iters=1000, seed=123):
    rng=np.random.default_rng(seed)
    out=[]
    r0 = pd.DataFrame(routing_df)
    b0 = pd.DataFrame(bom_df)
    for _ in range(int(iters)):
        mat_price = max(0.01, rng.normal(mat_mu, sd_mat*mat_mu))
        r = r0.copy()
        if not r.empty:
            if "Cycle_min" in r:
                r["Cycle_min"]=r["Cycle_min"]*(1.0+rng.normal(0.0,sd_cycle,size=len(r)))
                r["Cycle_min"]=r["Cycle_min"].clip(lower=0.05)
            if "Scrap_pct" in r:
                r["Scrap_pct"]=(r["Scrap_pct"]+rng.normal(0.0,sd_scrap,size=len(r))).clip(0.0,0.35)
        rr=cost_once(r,b0,Q,net_kg,mat_price,labor_rate,machine_rates)
        out.append(rr["total_pc"])
    return np.array(out)

# Capaciteit / WIP
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

# ========================================
# Output – KPI’s
# ========================================
st.markdown("## 📊 Kostencalculatie (basis)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Materiaal €/stuk", f"€ {res['mat_pc']:.2f}")
c2.metric("Conversie totaal", f"€ {res['conv_total']:.2f}")
c3.metric("Inkoopdelen totaal", f"€ {res['buy_total']:.2f}")
c4.metric("Kostprijs/stuk", f"€ {res['total_pc']:.2f}")

fig = go.Figure(go.Pie(labels=["Materiaal","Conversie","Inkoopdelen"],
                       values=[res["mat_pc"], res["conv_total"], res["buy_total"]]))
st.plotly_chart(fig, use_container_width=True)

# Monte-Carlo
if mc_on:
    st.markdown("### 🎲 Monte-Carlo simulatie (kostprijs/stuk)")
    samples = run_mc(st.session_state["routing_df"], st.session_state["bom_buy_df"],
                     Q, net_kg, price_eurkg, sd_mat, sd_cycle, sd_scrap,
                     LABOR_RATE, MACHINE_RATES, iters=mc_iter, seed=123)
    p50=float(np.percentile(samples,50)); p80=float(np.percentile(samples,80)); p95=float(np.percentile(samples,95))
    c1,c2,c3=st.columns(3)
    c1.metric("P50 (median)", f"€ {p50:.2f}")
    c2.metric("P80", f"€ {p80:.2f}")
    c3.metric("P95 (risk)", f"€ {p95:.2f}")
    st.plotly_chart(px.histogram(pd.DataFrame({"Kostprijs/stuk":samples}), x="Kostprijs/stuk", nbins=40, marginal="rug"),
                    use_container_width=True)
else:
    samples=None; p50=p80=p95=None

# Capaciteit/WIP
st.markdown("### 🏭 Capaciteit & WIP")
cap_df = capacity_table(st.session_state["routing_df"], Q, hours_per_day, cap_per_process)
if cap_df.empty:
    st.info("Geen routingdata om capaciteit te berekenen.")
else:
    cap_show = cap_df.copy(); cap_show["Util_%"] = (cap_show["Util_pct"]*100).round(1)
    st.dataframe(cap_show[["Proces","Hours_need","Hours_cap","Util_%","Batches","Setup_min","Cycle_min"]], use_container_width=True)
    fig_util = px.bar(cap_df, x="Proces", y="Util_pct", text=(cap_df["Util_pct"]*100).round(1))
    fig_util.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig_util, use_container_width=True)
    bottleneck = cap_df.sort_values("Util_pct", ascending=False).iloc[0]
    st.warning(f"🔧 Bottleneck: **{bottleneck['Proces']}** – benutting ~ {(bottleneck['Util_pct']*100):.1f}%")

# Make vs Buy
st.markdown("### 🔄 Make vs Buy")
if Q >= moq:
    buy_unit = buy_price + transport_buy
else:
    buy_unit = (buy_price * moq) / Q + transport_buy
capacity_penalty = 0.0
if not cap_df.empty and cap_df["Util_pct"].max() > 1.0:
    overload = float(cap_df["Util_pct"].max() - 1.0)
    capacity_penalty = overload * 0.10 * res["total_pc"]
make_unit = res["total_pc"] + capacity_penalty
adv = "BUY" if buy_unit < make_unit else "MAKE"
delta = abs(make_unit - buy_unit)
cc1, cc2, cc3 = st.columns(3)
cc1.metric("Make €/stuk", f"€ {make_unit:.2f}")
cc2.metric("Buy €/stuk", f"€ {buy_unit:.2f}")
cc3.metric("Advies", adv)
if adv=="BUY":
    st.info(f"Inkoop is ~€ {delta:.2f}/stuk voordeliger bij Q={Q} (inclusief MOQ/transport en capaciteitsdruk).")
else:
    st.success(f"Zelf maken is ~€ {delta:.2f}/stuk voordeliger bij Q={Q} (capaciteit meegewogen).")

# ========================================
# Exports
# ========================================
st.markdown("## 📤 Export")
# CSV exports
ccsv1, ccsv2 = st.columns(2)
with ccsv1: df_to_csv_download(pd.DataFrame(st.session_state["routing_df"]), f"{project}_routing.csv", "⬇️ Download Routing CSV")
with ccsv2: df_to_csv_download(pd.DataFrame(st.session_state["bom_buy_df"]), f"{project}_bom.csv", "⬇️ Download BOM CSV")

# PDF
if st.button("📄 Genereer PDF"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 14); c.drawString(30, 800, f"Offerte – {project}")
    c.setFont("Helvetica", 10)
    c.drawString(30, 780, f"Aantal: {Q} stuks")
    c.drawString(30, 765, f"Materiaal: {materiaal} – € {price_eurkg:.3f}/kg ({price_source})")
    data = [["Post","Bedrag (€)"],
            ["Materiaal", f"{res['mat_pc']:.2f}"],
            ["Conversie", f"{res['conv_total']:.2f}"],
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
    st.download_button("⬇️ Download PDF", buffer.getvalue(), "quote.pdf", "application/pdf")

# Excel
out_buf = io.BytesIO()
with pd.ExcelWriter(out_buf, engine="xlsxwriter") as writer:
    pd.DataFrame(st.session_state["routing_df"]).to_excel(writer, index=False, sheet_name="Routing")
    pd.DataFrame(st.session_state["bom_buy_df"]).to_excel(writer, index=False, sheet_name="BOM_buy")
    pd.DataFrame([
        {"Post":"Materiaal","Bedrag":res["mat_pc"]},
        {"Post":"Conversie","Bedrag":res["conv_total"]},
        {"Post":"Inkoopdelen","Bedrag":res["buy_total"]},
        {"Post":"Totaal","Bedrag":res["total_pc"]},
        {"Post":"Verkoop (incl. marge+cont.)","Bedrag":res["total_pc"]*(1+PROFIT_PCT+CONTINGENCY_PCT)}
    ]).to_excel(writer, index=False, sheet_name="Summary")
    if isinstance(mc_on, bool) and mc_on:
        samples_df = pd.DataFrame({"Kostprijs/stuk": run_mc(st.session_state["routing_df"], st.session_state["bom_buy_df"],
                                                            Q, net_kg, price_eurkg, sd_mat, sd_cycle, sd_scrap,
                                                            LABOR_RATE, MACHINE_RATES, iters=mc_iter, seed=123)})
        samples_df.to_excel(writer, index=False, sheet_name="MC_samples")
    cap_x = capacity_table(st.session_state["routing_df"], Q, hours_per_day, cap_per_process)
    if not cap_x.empty:
        cap_x.to_excel(writer, index=False, sheet_name="Capacity")
out_buf.seek(0)
st.download_button("⬇️ Download Excel", out_buf.getvalue(), f"{project}_calc.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("✅ Gereed – dynamische materiaalprijzen (Outokumpu + LME) geïntegreerd met je volledige kostentool.")
