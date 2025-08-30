0001 import io
0002 import json
0003 import base64
0004 import requests
0005 from math import ceil
0006 from datetime import date
0007 import numpy as np
0008 import pandas as pd
0009 import streamlit as st
0010 import plotly.express as px
0011 import plotly.graph_objects as go
0012 from reportlab.lib.pagesizes import A4
0013 from reportlab.lib import colors
0014 from reportlab.pdfgen import canvas
0015 from reportlab.platypus import Table, TableStyle
0016 
0017 st.set_page_config(page_title="Maakindustrie Cost Tool+",
0018                    layout="wide",
0019                    page_icon="⚙️")
0020 
0021 # =============================
0022 # i18n
0023 # =============================
0024 TXT = {
0025     "app_title":{"nl":"Maakindustrie Cost Tool+","en":"Manufacturing Cost Tool+"},
0026     "app_caption":{"nl":"BOM routing, Auto-routing, Presets, Forecast, WIP/Capaciteit, CO₂, Monte-Carlo, PDF/Excel",
0027                    "en":"BOM routing, Auto-routing, Presets, Forecast, WIP/Capacity, CO₂, Monte Carlo, PDF/Excel"},
0028     "lang":{"nl":"Taal / Language","en":"Language / Taal"},
0029     "sidebar_input":{"nl":"🔧 Invoer","en":"🔧 Inputs"},
0030     "project":{"nl":"Projectnaam","en":"Project name"},
0031     "qty":{"nl":"Aantal stuks (Q)","en":"Quantity (Q)"},
0032     "material":{"nl":"Materiaal","en":"Material"},
0033     "net_weight":{"nl":"Netto gewicht per stuk (kg)","en":"Net weight per part (kg)"},
0034     "learning_curve":{"nl":"Learning curve (op cyclustijd)","en":"Learning curve (on cycle time)"},
0035     "lc_b":{"nl":"b-exponent (negatief)","en":"b-exponent (negative)"},
0036     "lc_ref":{"nl":"RefQty","en":"RefQty"},
0037     "tou":{"nl":"Energie (TOU)","en":"Energy (TOU)"},
0038     "price_day":{"nl":"Dagprijs €/kWh","en":"Day price €/kWh"},
0039     "price_eve":{"nl":"Avondprijs €/kWh","en":"Evening price €/kWh"},
0040     "price_night":{"nl":"Nachtprijs €/kWh","en":"Night price €/kWh"},
0041     "share_day":{"nl":"Share dag","en":"Share day"},
0042     "share_eve":{"nl":"Share avond","en":"Share evening"},
0043     "plant_hdr":{"nl":"Fabriek / Capaciteit","en":"Plant / Capacity"},
0044     "hours_per_day":{"nl":"Uren productie per dag","en":"Production hours per day"},
0045     "cap_per_process":{"nl":"Capaciteit per proces (uren/dag)","en":"Capacity per process (hours/day)"},
0046     "lean_hdr":{"nl":"Lean / Logistiek","en":"Lean / Logistics"},
0047     "rework_pct":{"nl":"Rework % (op proceskosten)","en":"Rework % (on process costs)"},
0048     "transport_min":{"nl":"Transport (min/stuk)","en":"Transport (min/part)"},
0049     "storage_days":{"nl":"Opslag (dagen batch)","en":"Storage (days per batch)"},
0050     "inventory_rate":{"nl":"Voorraadkosten %/jaar","en":"Inventory cost %/year"},
0051     "mvb_hdr":{"nl":"Make vs Buy","en":"Make vs Buy"},
0052     "buy_price":{"nl":"Inkoopprijs/stuk (€)","en":"Purchase price/part (€)"},
0053     "moq":{"nl":"MOQ","en":"MOQ"},
0054     "buy_transport":{"nl":"Transport/handling (€/stuk)","en":"Transport/handling (€/part)"},
0055     "mc_hdr":{"nl":"Monte-Carlo (onzekerheid)","en":"Monte Carlo (uncertainty)"},
0056     "mc_enable":{"nl":"Monte-Carlo simulatie aan","en":"Enable Monte Carlo simulation"},
0057     "mc_iter":{"nl":"Iteraties","en":"Iterations"},
0058     "sd_mat":{"nl":"σ materiaalprijs (%)","en":"σ material price (%)"},
0059     "sd_cycle":{"nl":"σ cyclustijd (%)","en":"σ cycle time (%)"},
0060     "sd_scrap":{"nl":"σ scrap additief (abs)","en":"σ scrap additive (abs)"},
0061     "forecast_hdr":{"nl":"Materiaal prijs forecast","en":"Material price forecast"},
0062     "horizon":{"nl":"Horizon (maanden)","en":"Horizon (months)"},
0063     "method":{"nl":"Methode","en":"Method"},
0064     "drift_abs":{"nl":"Drift (€/kg per maand)","en":"Drift (€/kg per month)"},
0065     "drift_pct":{"nl":"Drift (% per maand)","en":"Drift (% per month)"},
0066     "sigma_pct":{"nl":"Onzekerheid σ (%/mnd)","en":"Uncertainty σ (%/month)"},
0067     "use_fc":{"nl":"Gebruik voorspelde prijs in kostprijs","en":"Use forecasted price in costing"},
0068     "month_t":{"nl":"Gebruik maand t=","en":"Use month t="},
0069     "routing_hdr":{"nl":"🧭 Routing (BOM-stappen)","en":"🧭 Routing (BOM steps)"},
0070     "routing_cap":{"nl":"Definieer bewerkingen in volgorde. Setup over batch; scrap propageert.",
0071                    "en":"Define operations in order. Setup over batch; scrap propagates."},
0072     "bom_buy_hdr":{"nl":"🧾 BOM – Ingekochte onderdelen","en":"🧾 BOM – Purchased components"},
0073     "bom_buy_cap":{"nl":"Inkoopregels per eindproduct; scrapt mee in routing.",
0074                    "en":"Purchase items per finished unit; scrap cascades in routing."},
0075     "client_hdr":{"nl":"👤 Klantinformatie","en":"👤 Client information"},
0076     "client_cap":{"nl":"Komt op PDF/Excel; vul in voor complete offerte.",
0077                   "en":"Goes on PDF/Excel; fill for a complete quote."},
0078     "verkoop_stuk":{"nl":"Verkoopprijs/stuk","en":"Sales price/part"},
0079     "verkoop_totaal":{"nl":"Totale verkoopprijs","en":"Total sales price"},
0080     "advies":{"nl":"Advies","en":"Recommendation"},
0081     "used_price":{"nl":"Gebruikte materiaalprijs","en":"Material price used"},
0082     "month":{"nl":"maand","en":"month"}
0083 }
0084 
0085 def tr(key, lang="nl", **fmt):
0086     s = TXT.get(key, {}).get(lang, key)
0087     return s.format(**fmt) if fmt else s
0088 
0089 # =============================
0090 # Materialen incl. CO₂
0091 # =============================
0092 materials = {
0093     "S235JR_steel":{"price":1.40,"waste":0.08,"k_cycle":1.00,"tool_wear_eur_pc":0.02,"co2e_kgkg":1.9},
0094     "S355J2_steel":{"price":1.70,"waste":0.08,"k_cycle":1.05,"tool_wear_eur_pc":0.03,"co2e_kgkg":2.0},
0095     "C45":{"price":1.90,"waste":0.06,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":2.0},
0096     "42CrMo4":{"price":2.60,"waste":0.06,"k_cycle":1.20,"tool_wear_eur_pc":0.07,"co2e_kgkg":2.3},
0097     "SS304":{"price":3.50,"waste":0.06,"k_cycle":1.15,"tool_wear_eur_pc":0.06,"co2e_kgkg":6.5},
0098     "SS316L":{"price":4.20,"waste":0.06,"k_cycle":1.20,"tool_wear_eur_pc":0.08,"co2e_kgkg":6.8},
0099     "SS904L":{"price":8.50,"waste":0.06,"k_cycle":1.25,"tool_wear_eur_pc":0.10,"co2e_kgkg":8.5},
0100     "1.4462_Duplex":{"price":5.50,"waste":0.07,"k_cycle":1.30,"tool_wear_eur_pc":0.12,"co2e_kgkg":7.5},
0101     "SuperDuplex_2507":{"price":7.50,"waste":0.07,"k_cycle":1.45,"tool_wear_eur_pc":0.18,"co2e_kgkg":10.5},
0102     "Al_6082":{"price":4.20,"waste":0.07,"k_cycle":0.80,"tool_wear_eur_pc":0.01,"co2e_kgkg":8.0},
0103     "Cast_Aluminium":{"price":3.20,"waste":0.07,"k_cycle":0.90,"tool_wear_eur_pc":0.02,"co2e_kgkg":8.5},
0104     "Cu_ECW":{"price":8.00,"waste":0.05,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":3.5},
0105     "Cast_Steel_GS45":{"price":1.60,"waste":0.05,"yield":0.80,"conv_cost":0.80,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":2.1},
0106     "Cast_Iron_GG25":{"price":1.20,"waste":0.05,"yield":0.85,"conv_cost":0.60,"k_cycle":1.05,"tool_wear_eur_pc":0.04,"co2e_kgkg":1.8},
0107     "Cast_AlSi10Mg":{"price":3.00,"waste":0.05,"yield":0.75,"conv_cost":1.00,"k_cycle":0.90,"tool_wear_eur_pc":0.02,"co2e_kgkg":8.5},
0108     "Forged_C45":{"price":1.90,"waste":0.04,"yield":0.90,"conv_cost":1.20,"k_cycle":1.20,"tool_wear_eur_pc":0.06,"co2e_kgkg":2.2},
0109     "Forged_42CrMo4":{"price":2.80,"waste":0.04,"yield":0.92,"conv_cost":1.40,"k_cycle":1.30,"tool_wear_eur_pc":0.08,"co2e_kgkg":2.5},
0110     "Forged_1.4462":{"price":6.00,"waste":0.04,"yield":0.88,"conv_cost":1.60,"k_cycle":1.40,"tool_wear_eur_pc":0.12,"co2e_kgkg":8.0},
0111     "Extruded_Al_6060":{"price":3.50,"waste":0.03,"yield":0.95,"conv_cost":0.50,"k_cycle":0.85,"tool_wear_eur_pc":0.01,"co2e_kgkg":7.5},
0112     "Extruded_Cu":{"price":7.50,"waste":0.03,"yield":0.92,"conv_cost":0.70,"k_cycle":1.10,"tool_wear_eur_pc":0.05,"co2e_kgkg":3.5},
0113 }
0114 
0115 # Tarieven (€/uur)
0116 machine_rates = {
0117     "CNC":85.0,
0118     "Laser":110.0,
0119     "Lassen":55.0,
0120     "Buigen":75.0,
0121     "Montage":40.0,
0122     "Casting":65.0
0123 }
0124 labor_rate = 45.0
0125 overhead_pct = 0.20
0126 profit_pct = 0.12
0127 contingency_pct = 0.05
0128 co2_per_kwh = 0.35  # kg CO2/kWh
0129 
0130 # Placeholder defaults (overschreven door sidebar)
0131 project = "Demo"
0132 Q = 1
0133 material = "S235JR_steel"
0134 gewicht = 1.0
0135 
0136 # Learning curve defaults
0137 lc_b = -0.15
0138 lc_ref = 10
0139 
0140 # Energieprijzen defaults
0141 price_day = 0.24
0142 price_eve = 0.18
0143 price_night = 0.12
0144 tou_day = 0.6
0145 tou_eve = 0.3
0146 tou_night = 0.1
0147 
0148 # Capaciteit defaults
0149 hours_per_day = 8.0
0150 cap_per_process = {p: 8.0 for p in machine_rates.keys()}
0151 
0152 # Lean defaults
0153 rework_pct = 0.05
0154 transport_min = 0.5
0155 storage_days = 30
0156 inventory_cost_year = 0.12
0157 
0158 # Make-vs-buy defaults
0159 buy_price = 15.0
0160 moq = 250
0161 transport_buy = 0.6
0162 
0163 # Monte-Carlo defaults
0164 mc_on = False
0165 mc_iter = 1000
0166 sd_mat = 0.05
0167 sd_cycle = 0.08
0168 sd_scrap = 0.01
0169 
0170 # Forecast defaults
0171 forecast_horizon = 12
0172 forecast_method = "Drift (€/mnd)"
0173 drift_abs = 0.00
0174 drift_pct = 0.00
0175 sigma_pct = 1.5
0176 use_forecast_for_cost = False
0177 quote_month_offset = 0
0178 
0179 # Client info defaults
0180 client_info = {
0181     "Company": "",
0182     "Contact": "",
0183     "Email": "",
0184     "Phone": "",
0185     "RFQ": "",
0186     "Incoterms": "EXW",
0187     "Currency": "EUR",
0188     "PaymentTerms": "30 dagen netto",
0189     "DeliveryAddress": "",
0190     "RequiredDelivery": "",
0191     "QuoteValidity": "60 dagen",
0192     "NDA": "No"
0193 }
0194 
0195 # =============================
0196 # Start van de app UI
0197 # =============================
0198 # Sidebar inputs volgen hierna
0199 
0200 # =============================
0201 # Sidebar – Invoer
0202 # =============================
0203 lang_choice = st.sidebar.selectbox(
0204     TXT["lang"]["nl"],
0205     options=["nl","en"],
0206     index=0,
0207     format_func=lambda x: "Nederlands" if x=="nl" else "English"
0208 )
0209 
0210 st.title(tr("app_title", lang_choice))
0211 st.caption(tr("app_caption", lang_choice))
0212 
0213 st.sidebar.header(tr("sidebar_input", lang_choice))
0214 project = st.sidebar.text_input(tr("project", lang_choice), "Demo")
0215 Q = st.sidebar.number_input(tr("qty", lang_choice), min_value=1, value=50, step=1)
0216 material = st.sidebar.selectbox(tr("material", lang_choice), list(materials.keys()))
0217 gewicht = st.sidebar.number_input(tr("net_weight", lang_choice), min_value=0.01, value=2.0)
0218 
0219 st.sidebar.subheader(tr("learning_curve", lang_choice))
0220 lc_b = st.sidebar.number_input(tr("lc_b", lang_choice), value=-0.15, step=0.01, format="%.2f")
0221 lc_ref = st.sidebar.number_input(tr("lc_ref", lang_choice), min_value=1, value=10, step=1)
0222 
0223 st.sidebar.subheader(tr("tou", lang_choice))
0224 price_day = st.sidebar.number_input(tr("price_day", lang_choice), value=0.24, step=0.01)
0225 price_eve = st.sidebar.number_input(tr("price_eve", lang_choice), value=0.18, step=0.01)
0226 price_night = st.sidebar.number_input(tr("price_night", lang_choice), value=0.12, step=0.01)
0227 tou_day = st.sidebar.slider(tr("share_day", lang_choice), 0.0, 1.0, 0.60, 0.05)
0228 tou_eve = st.sidebar.slider(tr("share_eve", lang_choice), 0.0, 1.0, 0.30, 0.05)
0229 tou_night = max(0.0, 1.0 - tou_day - tou_eve)
0230 st.sidebar.caption(f"Night share: {tou_night:.2f}")
0231 
0232 st.sidebar.subheader(tr("plant_hdr", lang_choice))
0233 hours_per_day = st.sidebar.number_input(tr("hours_per_day", lang_choice), 1.0, 24.0, 8.0, step=0.5)
0234 with st.sidebar.expander(tr("cap_per_process", lang_choice), expanded=False):
0235     cap_per_process = {
0236         p: st.number_input(f"{p} (h/dag)", 0.0, 24.0, 8.0, key=f"cap_{p}")
0237         for p in machine_rates.keys()
0238     }
0239 
0240 st.sidebar.subheader(tr("lean_hdr", lang_choice))
0241 rework_pct = st.sidebar.number_input(tr("rework_pct", lang_choice), 0.0, 1.0, 0.05, step=0.01)
0242 transport_min = st.sidebar.number_input(tr("transport_min", lang_choice), 0.0, 60.0, 0.5)
0243 storage_days = st.sidebar.number_input(tr("storage_days", lang_choice), 0, 365, 30)
0244 inventory_cost_year = st.sidebar.number_input(tr("inventory_rate", lang_choice), 0.0, 1.0, 0.12, step=0.01)
0245 
0246 st.sidebar.subheader(tr("mvb_hdr", lang_choice))
0247 buy_price = st.sidebar.number_input(tr("buy_price", lang_choice), 0.0, 1e6, 15.0)
0248 moq = st.sidebar.number_input(tr("moq", lang_choice), 1, 100000, 250)
0249 transport_buy = st.sidebar.number_input(tr("buy_transport", lang_choice), 0.0, 1e6, 0.6)
0250 
0251 st.sidebar.subheader(tr("mc_hdr", lang_choice))
0252 mc_on = st.sidebar.checkbox(tr("mc_enable", lang_choice), value=False)
0253 mc_iter = st.sidebar.number_input(tr("mc_iter", lang_choice), 100, 20000, 1000, step=100)
0254 sd_mat = st.sidebar.number_input(tr("sd_mat", lang_choice), 0.0, 0.5, 0.05, step=0.01)
0255 sd_cycle = st.sidebar.number_input(tr("sd_cycle", lang_choice), 0.0, 0.5, 0.08, step=0.01)
0256 sd_scrap = st.sidebar.number_input(tr("sd_scrap", lang_choice), 0.0, 0.5, 0.01, step=0.005)
0257 
0258 st.sidebar.subheader(tr("forecast_hdr", lang_choice))
0259 forecast_horizon = st.sidebar.slider(tr("horizon", lang_choice), 1, 12, 12)
0260 forecast_method = st.sidebar.selectbox(tr("method", lang_choice), ["Drift (€/mnd)","Drift (%/mnd) + onzekerheid"])
0261 drift_abs = st.sidebar.number_input(tr("drift_abs", lang_choice), value=0.00, step=0.05, format="%.2f")
0262 drift_pct = st.sidebar.number_input(tr("drift_pct", lang_choice), value=0.00, step=0.01, format="%.2f")
0263 sigma_pct = st.sidebar.number_input(tr("sigma_pct", lang_choice), value=1.50, step=0.25, format="%.2f")
0264 use_forecast_for_cost = st.sidebar.checkbox(tr("use_fc", lang_choice), value=False)
0265 quote_month_offset = st.sidebar.slider(tr("month_t", lang_choice), 0, forecast_horizon, 0)
0266 
0267 # =============================
0268 # Helpers
0269 # =============================
0270 def lc_factor(Q, ref, b):
0271     try:
0272         return (max(Q,1)/max(ref,1))**b
0273     except:
0274         return 1.0
0275 
0276 def forecast_series(p0, months, method, drift_abs, drift_pct, sigma_pct, seed=42):
0277     idx = pd.date_range(date.today(), periods=months+1, freq="MS")
0278     if method=="Drift (€/mnd)":
0279         vals=[max(0.01,p0+i*drift_abs) for i in range(months+1)]
0280         return pd.DataFrame({"Datum":idx,"€/kg":vals})
0281     rng=np.random.default_rng(seed)
0282     vals=[p0]; low=[p0]; high=[p0]
0283     for _ in range(months):
0284         mu=1+drift_pct/100; shock=rng.normal(0.0, sigma_pct/100.0)
0285         nxt=max(0.01, vals[-1]*(mu+shock)); vals.append(nxt)
0286         trend=vals[-2]*mu
0287         low.append(max(0.01, trend*(1-2*sigma_pct/100)))
0288         high.append(trend*(1+2*sigma_pct/100))
0289     return pd.DataFrame({"Datum":idx,"€/kg":vals,"Low":low,"High":high})
0290 
0291 # ---- GitHub helpers (presets uit repo laden) ----
0292 @st.cache_data(ttl=300)
0293 def gh_list_files(owner:str, repo:str, folder:str, branch:str="main", token:str|None=None):
0294     url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder}"
0295     params = {"ref": branch}
0296     headers = {"Accept": "application/vnd.github+json"}
0297     if token:
0298         headers["Authorization"] = f"Bearer {token}"
0299     r = requests.get(url, params=params, headers=headers, timeout=20)
0300     r.raise_for_status()
0301     items = r.json()
0302     return [
0303         it for it in items
0304         if isinstance(it, dict) and it.get("type")=="file" and it.get("name","").lower().endswith(".json")
0305     ]
0306 
0307 @st.cache_data(ttl=300)
0308 def gh_fetch_json(owner:str, repo:str, path:str, branch:str="main", token:str|None=None):
0309     url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
0310     params = {"ref": branch}
0311     headers = {"Accept": "application/vnd.github+json"}
0312     if token:
0313         headers["Authorization"] = f"Bearer {token}"
0314     r = requests.get(url, params=params, headers=headers, timeout=20)
0315     r.raise_for_status()
0316     obj = r.json()
0317     if "content" in obj and obj.get("encoding")=="base64":
0318         raw = base64.b64decode(obj["content"])
0319         return json.loads(raw.decode("utf-8"))
0320     if "download_url" in obj and obj["download_url"]:
0321         r2 = requests.get(obj["download_url"], timeout=20)
0322         r2.raise_for_status()
0323         return r2.json()
0324     raise RuntimeError("Onverwachte GitHub API-respons; geen content gevonden.")
0325 
0326 # =============================
0327 # Forecast bouwen
0328 # =============================
0329 mat = materials[material]
0330 p0 = mat["price"]
0331 df_fc = forecast_series(p0, forecast_horizon, forecast_method, drift_abs, drift_pct, sigma_pct)
0332 
0333 st.markdown("---")
0334 st.subheader(f"📈 {tr('forecast_hdr', lang_choice)} – {material} ({forecast_horizon} mnd)")
0335 if "Low" in df_fc.columns:
0336     fig_fc = px.line(
0337         df_fc, x="Datum", y=["€/kg","Low","High"], markers=True,
0338         labels={"value":"€/kg","variable":"Serie"}
0339     )
0340 else:
0341     fig_fc = px.line(df_fc, x="Datum", y="€/kg", markers=True, labels={"€/kg":"€/kg"})
0342 st.plotly_chart(fig_fc, use_container_width=True)
0343 
0344 if use_forecast_for_cost:
0345     try:
0346         mat_price_used = float(df_fc.loc[df_fc.index[quote_month_offset], "€/kg"])
0347     except Exception:
0348         mat_price_used = p0
0349     used_note = f"{tr('use_fc', lang_choice)} → € {mat_price_used:.2f}/kg ({tr('month', lang_choice)} t={quote_month_offset})"
0350 else:
0351     mat_price_used = p0
0352     used_note = f"Prijs basis: € {mat_price_used:.2f}/kg (t=0)"
0353 
0354 # =============================
0355 # Klantinformatie
0356 # =============================
0357 st.markdown(f"## {tr('client_hdr', lang_choice)}")
0358 st.caption(tr("client_cap", lang_choice))
0359 with st.form("client_form"):
0360     c1, c2 = st.columns(2)
0361     with c1:
0362         client_company = st.text_input("Bedrijf / Company", "")
0363         client_contact = st.text_input("Contactpersoon / Contact", "")
0364         client_email = st.text_input("E-mail", "")
0365         client_phone = st.text_input("Telefoon / Phone", "")
0366         rfq_ref = st.text_input("RFQ / Referentie", "")
0367         incoterms = st.text_input("Incoterms (bijv. EXW, DAP)", "EXW")
0368     with c2:
0369         currency = st.text_input("Valuta / Currency", "EUR")
0370         pay_terms = st.text_input("Betalingscondities / Payment terms", "30 dagen netto")
0371         delivery_addr = st.text_area("Leveradres / Delivery address", "")
0372         req_delivery = st.text_input("Gewenste leverdatum / Required delivery", "")
0373         quote_valid = st.text_input("Offertegeldigheid / Quote validity", "60 dagen")
0374         nda_flag = st.checkbox("NDA van toepassing / NDA applies", value=False)
0375     submitted = st.form_submit_button("Opslaan / Save")
0376 
0377 client_info = {
0378     "Company": client_company if 'client_company' in locals() else "",
0379     "Contact": client_contact if 'client_contact' in locals() else "",
0380     "Email": client_email if 'client_email' in locals() else "",
0381     "Phone": client_phone if 'client_phone' in locals() else "",
0382     "RFQ": rfq_ref if 'rfq_ref' in locals() else "",
0383     "Incoterms": incoterms if 'incoterms' in locals() else "",
0384     "Currency": currency if 'currency' in locals() else "EUR",
0385     "PaymentTerms": pay_terms if 'pay_terms' in locals() else "",
0386     "DeliveryAddress": delivery_addr if 'delivery_addr' in locals() else "",
0387     "RequiredDelivery": req_delivery if 'req_delivery' in locals() else "",
0388     "QuoteValidity": quote_valid if 'quote_valid' in locals() else "",
0389     "NDA": "Yes" if ('nda_flag' in locals() and nda_flag) else "No",
0390 }
0391 
0392 # =============================
0393 # 🧩 Product specificatie & Auto-routing
0394 # =============================
0395 st.markdown("## 🧩 Product specificatie & Auto-routing")
0396 st.caption("Kies producttype en kenmerken → ‘Genereer routing’ → daarna kun je handmatig bijstellen.")
0397 
0398 part_type = st.selectbox(
0399     "Type product",
0400     [
0401         "Gedraaide as / gefreesd deel",
0402         "Gefreesde beugel (massief)",
0403        "Lasframe / samenstel",
0404         "Plaatwerk kast / bracket",
0405         "Gietstuk behuizing (CNC na-frees)",
0406         "Gesmede flens (CNC na-bewerking)"
0407     ]
0408 )
0409 
0410 colA, colB, colC = st.columns(3)
0411 with colA:
0412     tol_class = st.selectbox("Tolerantieklasse", ["Normaal", "Nauwkeurig", "Zeer nauwkeurig"], index=0)
0413     surface = st.selectbox("Oppervlakteruwheid", ["Standaard", "Fijn", "Zeer fijn"], index=0)
0414 with colB:
0415     holes = st.number_input("Aantal gaten (boren/tappen)", min_value=0, value=4, step=1)
0416     bends = st.number_input("Aantal zetten (alleen voor plaatwerk)", min_value=0, value=0, step=1)
0417 with colC:
0418     weld_m = st.number_input("Laslengte totaal (meter)", min_value=0.0, value=0.0, step=0.5)
0419     panels = st.number_input("Aantal plaatdelen (plaatwerk/samenstel)", min_value=0, value=2, step=1)
0420 
0421 tol_k = {"Normaal": 1.00, "Nauwkeurig": 1.20, "Zeer nauwkeurig": 1.45}[tol_class]
0422 surf_k = {"Standaard": 1.00, "Fijn": 1.15, "Zeer fijn": 1.30}[surface]
0423 
0424 def _base_scrap(pt):
0425     return {
0426         "Gedraaide as / gefreesd deel": 0.02,
0427         "Gefreesde beugel (massief)": 0.025,
0428         "Lasframe / samenstel": 0.015,
0429         "Plaatwerk kast / bracket": 0.02,
0430         "Gietstuk behuizing (CNC na-frees)": 0.03,
0431         "Gesmede flens (CNC na-bewerking)": 0.02
0432     }[pt]
0433 
0434 def generate_autorouting(pt: str, Q: int, gross_kg_pc: float, holes: int, bends: int, weld_m: float, panels: int,
0435                          tol_k: float, surf_k: float):
0436     rows = []
0437     scrap_default = _base_scrap(pt)
0438     def row(step, proces, qpp, cyc, setup, attend, kwh, qa, scrap, par=1, bsize=50, qd=0.5):
0439         rows.append({
0440             "Step": step, "Proces": proces, "Qty_per_parent": qpp, "Cycle_min": max(0.1, cyc),
0441             "Setup_min": max(0.0, setup), "Attend_pct": attend, "kWh_pc": max(0.0, kwh),
0442             "QA_min_pc": max(0.0, qa), "Scrap_pct": max(0.0, min(0.9, scrap)),
0443             "Parallel_machines": max(1, int(par)), "Batch_size": max(1, int(bsize)), "Queue_days": max(0.0, qd)
0444         })
0445 
0446     if pt == "Gedraaide as / gefreesd deel":
0447         cyc_cnc = (8.0 * tol_k * surf_k) + 0.4*holes + 2.0*(gross_kg_pc**0.5)
0448         row(10, "CNC", 1.0, cyc_cnc, 25.0, 100, 0.20, 0.5, scrap_default, par=1, bsize=50, qd=0.4)
0449         row(20, "Montage", 1.0, 4.0 + 0.3*holes, 10.0, 100, 0.05, 0.8, 0.0, par=1, bsize=100, qd=0.2)
0450 
0451     elif pt == "Gefreesde beugel (massief)":
0452         cyc_cnc = (10.0 * tol_k * surf_k) + 0.5*holes + 3.0*(gross_kg_pc**0.6)
0453         row(10, "CNC", 1.0, cyc_cnc, 30.0, 100, 0.25, 0.6, scrap_default, par=1, bsize=40, qd=0.5)
0454         row(20, "Montage", 1.0, 5.0 + 0.3*holes, 10.0, 100, 0.05, 1.0, 0.0, par=1, bsize=80, qd=0.3)
0455 
0456     elif pt == "Lasframe / samenstel":
0457         cut_time = 3.0 + 0.8 * panels
0458         row(10, "Laser", panels, cut_time, 20.0, 50, 0.50, 0.3, scrap_default*0.5, par=1, bsize=80, qd=0.5)
0459         weld_time = 6.0 + 6.0*weld_m + 0.5*panels
0460         row(20, "Lassen", 1.0, weld_time, 20.0, 100, 0.35, 0.5, scrap_default, par=1, bsize=30, qd=0.8)
0461         cnc_time = 4.0*tol_k + 0.3*holes + 1.5*(gross_kg_pc**0.4)
0462         row(30, "CNC", 1.0, cnc_time, 15.0, 100, 0.20, 0.5, 0.01, par=1, bsize=40, qd=0.4)
0463         row(40, "Montage", 1.0, 6.0 + 0.3*holes, 10.0, 100, 0.05, 1.0, 0.0, par=1, bsize=60, qd=0.3)
0464 
0465     elif pt == "Plaatwerk kast / bracket":
0466         laser_time = 3.0 + 0.6 * panels
0467         row(10, "Laser", panels, laser_time, 20.0, 50, 0.50, 0.3, scrap_default*0.6, par=1, bsize=100, qd=0.5)
0468         if bends > 0:
0469             bend_time = 1.6*bends + 0.2*panels
0470             row(20, "Buigen", 1.0, bend_time, 15.0, 100, 0.10, 0.2, scrap_default*0.4, par=1, bsize=80, qd=0.3)
0471         cnc_time = 2.5*tol_k + 0.25*holes
0472         row(30, "CNC", 1.0, cnc_time, 10.0, 100, 0.15, 0.4, 0.01, par=1, bsize=60, qd=0.3)
0473         row(40, "Montage", 1.0, 5.0 + 0.25*holes, 8.0, 100, 0.05, 0.8, 0.0, par=1, bsize=80, qd=0.2)
0474 
0475     elif pt == "Gietstuk behuizing (CNC na-frees)":
0476         cast_cyc = 1.2 + 0.4*(gross_kg_pc**0.7)
0477         row(10, "Casting", 1.0, cast_cyc, 60.0, 50, 0.40, 0.2, scrap_default, par=1, bsize=60, qd=1.0)
0478         cnc_time = 6.0*tol_k*surf_k + 0.4*holes + 1.5*(gross_kg_pc**0.5)
0479         row(20, "CNC", 1.0, cnc_time, 25.0, 100, 0.25, 0.6, 0.015, par=1, bsize=40, qd=0.6)
0480         row(30, "Montage", 1.0, 4.0 + 0.2*holes, 8.0, 100, 0.05, 0.8, 0.0, par=1, bsize=80, qd=0.2)
0481 
0482     elif pt == "Gesmede flens (CNC na-bewerking)":
0483         cnc_time = 5.0*tol_k + 0.2*holes + 1.0*(gross_kg_pc**0.5)
0484         row(10, "CNC", 1.0, cnc_time, 20.0, 100, 0.20, 0.5, scrap_default, par=1, bsize=60, qd=0.4)
0485         row(20, "Montage", 1.0, 3.5 + 0.2*holes, 8.0, 100, 0.05, 0.8, 0.0, par=1, bsize=100, qd=0.2)
0486 
0487     return pd.DataFrame(rows).sort_values("Step").reset_index(drop=True)
0488 
0489 if st.button("🔮 Genereer routing"):
0490     yfac = float(materials[material].get("yield", 1.0))
0491     bruto_kg_pc = gewicht / yfac
0492     gen_df = generate_autorouting(part_type, Q, bruto_kg_pc, holes, bends, weld_m, panels, tol_k, surf_k)
0493     st.session_state["routing_editor"] = gen_df
0494     st.success("Routing gegenereerd – bewerk ‘m hieronder naar wens.")
0495     st.rerun()
0496 
0497 # =============================
0498 # Presets & JSON (incl. GitHub loader)
0499 # =============================
0500 st.markdown("## 📂 Presets & JSON")
0501 st.caption("Bewaar of laad routing/BOM configuraties")
0502 
0503 preset_col1, preset_col2 = st.columns(2)
0504 with preset_col1:
0505     if st.button("💾 Save preset (JSON)"):
0506         preset = {
0507             "routing": st.session_state.get("routing_editor", pd.DataFrame()).to_dict(orient="records"),
0508             "bom_buy": st.session_state.get("bom_buy_editor", pd.DataFrame()).to_dict(orient="records"),
0509         }
0510         js = json.dumps(preset, indent=2)
0511         b64 = base64.b64encode(js.encode()).decode()
0512         href = f'<a href="data:application/json;base64,{b64}" download="preset.json">Download preset.json</a>'
0513         st.markdown(href, unsafe_allow_html=True)
0514 
0515 with preset_col2:
0516     uploaded = st.file_uploader("Upload JSON preset", type="json")
0517     if uploaded:
0518         try:
0519             pl = json.load(uploaded)
0520             if "routing" in pl:
0521                 st.session_state["routing_editor"] = pd.DataFrame(pl["routing"])
0522             if "bom_buy" in pl:
0523                 st.session_state["bom_buy_editor"] = pd.DataFrame(pl["bom_buy"])
0524             st.success("Preset geladen vanaf upload.")
0525             st.rerun()
0526         except Exception as e:
0527             st.error(f"Kon JSON niet laden: {e}")
0528 
0529 with st.expander("🔗 GitHub presets laden"):
0530     owner = st.text_input("GitHub owner", "gerrit0492-create")
0531     repo = st.text_input("Repository", "maakindustrie-cost-tool")
0532     folder = st.text_input("Folder", "presets")
0533     branch = st.text_input("Branch", "main")
0534     token = st.text_input("Token (optioneel)", type="password")
0535     if st.button("📂 Lijst presets"):
0536         try:
0537             files = gh_list_files(owner, repo, folder, branch, token or None)
0538             st.session_state["gh_filelist"] = files
0539             st.success(f"Gevonden: {[f['name'] for f in files]}")
0540         except Exception as e:
0541             st.error(f"GitHub error: {e}")
0542 
0543     files = st.session_state.get("gh_filelist", [])
0544     if files:
0545         names = [f['name'] for f in files]
0546         sel = st.selectbox("Kies preset", names, key="gh_sel_name")
0547         load_btn = st.button("Preset laden uit GitHub")
0548         if load_btn:
0549             try:
0550                 path = f"{folder}/{sel}".strip("/ ")
0551                 data = gh_fetch_json(owner, repo, path, branch, token or None)
0552                 if "routing" in data:
0553                     st.session_state["routing_editor"] = pd.DataFrame(data["routing"])
0554                 if "bom_buy" in data:
0555                     st.session_state["bom_buy_editor"] = pd.DataFrame(data["bom_buy"])
0556                 st.success(f"Preset '{sel}' geladen uit GitHub.")
0557                 st.rerun()
0558             except Exception as e:
0559                 st.error(f"Mislukt: {e}")
0560 
0561 # =============================
0562 # ROUTING (BOM-stappen)
0563 # =============================
0564 st.markdown(f"## {tr('routing_hdr', lang_choice)}")
0565 st.caption(tr("routing_cap", lang_choice))
0566 
0567 process_choices = list(machine_rates.keys())
0568 default_routing = pd.DataFrame([
0569     {"Step":10,"Proces":"Casting","Qty_per_parent":1.0,"Cycle_min":2.0,"Setup_min":60.0,"Attend_pct":50,
0570      "kWh_pc":0.4,"QA_min_pc":0.2,"Scrap_pct":0.03,"Parallel_machines":1,"Batch_size":50,"Queue_days":1.0},
0571     {"Step":20,"Proces":"CNC","Qty_per_parent":1.0,"Cycle_min":7.5,"Setup_min":30.0,"Attend_pct":100,
0572      "kWh_pc":0.2,"QA_min_pc":0.5,"Scrap_pct":0.02,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.5},
0573     {"Step":30,"Proces":"Montage","Qty_per_parent":1.0,"Cycle_min":6.0,"Setup_min":10.0,"Attend_pct":100,
0574      "kWh_pc":0.1,"QA_min_pc":1.0,"Scrap_pct":0.00,"Parallel_machines":1,"Batch_size":50,"Queue_days":0.2},
0575 ])
0576 routing = st.data_editor(
0577     default_routing,
0578     key="routing_editor",
0579     num_rows="dynamic",
0580     use_container_width=True,
0581     column_config={
0582         "Proces": st.column_config.SelectboxColumn(options=process_choices, required=True),
0583         "Step": st.column_config.NumberColumn(),
0584         "Qty_per_parent": st.column_config.NumberColumn(),
0585         "Cycle_min": st.column_config.NumberColumn(),
0586         "Setup_min": st.column_config.NumberColumn(),
0587         "Attend_pct": st.column_config.NumberColumn(),
0588         "kWh_pc": st.column_config.NumberColumn(),
0589         "QA_min_pc": st.column_config.NumberColumn(),
0590         "Scrap_pct": st.column_config.NumberColumn(),
0591         "Parallel_machines": st.column_config.NumberColumn(),
0592         "Batch_size": st.column_config.NumberColumn(),
0593         "Queue_days": st.column_config.NumberColumn()
0594     }
0595 )
0596 
0597 st.markdown("---")
0598 st.write("Pas routingstappen aan of genereer via presets.")
0599 
0600 # =============================
0601 # Routing presets knoppen
0602 # =============================
0603 preset_col3, preset_col4 = st.columns(2)
0604 with preset_col3:
0605     if st.button("⭐ Typisch lasframe"):
0606         st.session_state["routing_editor"] = generate_autorouting(
0607             "Lasframe / samenstel", Q, gewicht, holes, bends, weld_m, panels, tol_k, surf_k
0608         )
0609         st.rerun()
0610 with preset_col4:
0611     if st.button("⭐ Plaatwerk kast"):
0612         st.session_state["routing_editor"] = generate_autorouting(
0613             "Plaatwerk kast / bracket", Q, gewicht, holes, bends, weld_m, panels, tol_k, surf_k
0614         )
0615         st.rerun()
0616 
0617 preset_col5, preset_col6 = st.columns(2)
0618 with preset_col5:
0619     if st.button("⭐ Gietstuk behuizing"):
0620         st.session_state["routing_editor"] = generate_autorouting(
0621             "Gietstuk behuizing (CNC na-frees)", Q, gewicht, holes, bends, weld_m, panels, tol_k, surf_k
0622         )
0623         st.rerun()
0624 with preset_col6:
0625     if st.button("⭐ Gesmede flens"):
0626         st.session_state["routing_editor"] = generate_autorouting(
0627             "Gesmede flens (CNC na-bewerking)", Q, gewicht, holes, bends, weld_m, panels, tol_k, surf_k
0628         )
0629         st.rerun()
0630 
0631 uploaded = st.file_uploader("Upload routing JSON", type="json", key="routing_upload")
0632 if uploaded:
0633     try:
0634         pl = json.load(uploaded)
0635         st.session_state["routing_editor"] = pd.DataFrame(pl)
0636         st.success("Routing preset geladen.")
0637         st.rerun()
0638     except Exception as e:
0639         st.error(f"Kon routing niet laden: {e}")
0640 
0641 # =============================
0642 # BOM – Ingekochte onderdelen
0643 # =============================
0644 st.markdown(f"## {tr('bom_buy_hdr', lang_choice)}")
0645 st.caption(tr("bom_buy_cap", lang_choice))
0646 
0647 default_bom = pd.DataFrame([
0648     {"Part":"Handgreep","Qty":2,"UnitPrice":3.5,"Scrap_pct":0.01},
0649     {"Part":"Schroef M8","Qty":8,"UnitPrice":0.1,"Scrap_pct":0.02}
0650 ])
0651 bom_buy = st.data_editor(
0652     default_bom,
0653     key="bom_buy_editor",
0654     num_rows="dynamic",
0655     use_container_width=True,
0656     column_config={
0657         "Part": st.column_config.TextColumn(required=True),
0658         "Qty": st.column_config.NumberColumn(),
0659         "UnitPrice": st.column_config.NumberColumn(),
0660         "Scrap_pct": st.column_config.NumberColumn()
0661     }
0662 )
0663 
0664 # =============================
0665 # Placeholder voor calculatie
0666 # =============================
0667 st.markdown("---")
0668 st.subheader("📊 Kostencalculatie (basis placeholders, nog uit te breiden)")
0669 
0670 st.write(f"Project: **{project}** – {Q} stuks van {material}")
0671 st.write(f"Gebruikte materiaalprijs: {mat_price_used:.2f} €/kg")
0672 
0673 # voorbeeld calculatie
0674 base_mat_cost = gewicht * mat_price_used
0675 conv_cost = sum(routing["Cycle_min"]) * (labor_rate/60)
0676 buy_cost = (bom_buy["Qty"]*bom_buy["UnitPrice"]).sum()
0677 
0678 total_cost = base_mat_cost + conv_cost + buy_cost
0679 sales_price = total_cost * (1+profit_pct+contingency_pct)
0680 
0681 st.metric("Totale kostprijs/stuk", f"€ {total_cost:.2f}")
0682 st.metric("Verkoopprijs/stuk (incl. marge)", f"€ {sales_price:.2f}")
0683 
0684 st.markdown("### Breakdown")
0685 st.write({
0686     "Materiaal": base_mat_cost,
0687     "Conversie": conv_cost,
0688     "Inkoopdelen": buy_cost,
0689     "Marge/Contingency": sales_price-total_cost
0690 })
0691 
0692 # grafiek
0693 fig = go.Figure(go.Pie(labels=["Materiaal","Conversie","Inkoopdelen","Marge"],
0694                        values=[base_mat_cost, conv_cost, buy_cost, sales_price-total_cost]))
0695 st.plotly_chart(fig, use_container_width=True)
0696 
0697 st.caption("⚠️ Deze calculatie is een vereenvoudigd voorbeeld. Volledige cost breakdown kan worden uitgebreid.")
0698 
0699 st.markdown("---")
0700 # =============================
0701 # Export naar PDF en Excel
0702 # =============================
0703 st.subheader("📤 Export opties")
0704 exp_col1, exp_col2 = st.columns(2)
0705 
0706 with exp_col1:
0707     if st.button("📄 Genereer PDF"):
0708         buffer = io.BytesIO()
0709         c = canvas.Canvas(buffer, pagesize=A4)
0710         c.setFont("Helvetica-Bold", 14)
0711         c.drawString(30, 800, f"Offerte – {project}")
0712         c.setFont("Helvetica", 10)
0713         c.drawString(30, 780, f"Aantal: {Q} stuks")
0714         c.drawString(30, 765, f"Materiaal: {material} – {mat_price_used:.2f} €/kg")
0715 
0716         data = [["Post","Bedrag (€)"],
0717                 ["Materiaal", f"{base_mat_cost:.2f}"],
0718                 ["Conversie", f"{conv_cost:.2f}"],
0719                 ["Inkoopdelen", f"{buy_cost:.2f}"],
0720                 ["Totaal", f"{total_cost:.2f}"],
0721                 ["Verkoop (incl. marge)", f"{sales_price:.2f}"]]
0722         table = Table(data, colWidths=[200,100])
0723         style = TableStyle([("BACKGROUND",(0,0),(-1,0),colors.grey),
0724                             ("TEXTCOLOR",(0,0),(-1,0),colors.whitesmoke),
0725                             ("ALIGN",(0,0),(-1,-1),"CENTER"),
0726                             ("GRID",(0,0),(-1,-1),0.5,colors.black)])
0727         table.setStyle(style)
0728         table.wrapOn(c, 400, 600)
0729         table.drawOn(c, 30, 700-20*len(data))
0730 
0731         c.save()
0732         buffer.seek(0)
0733         b64 = base64.b64encode(buffer.read()).decode()
0734         href = f'<a href="data:application/pdf;base64,{b64}" download="quote.pdf">Download PDF</a>'
0735         st.markdown(href, unsafe_allow_html=True)
0736 
0737 with exp_col2:
0738     out_buf = io.BytesIO()
0739     with pd.ExcelWriter(out_buf, engine="xlsxwriter") as writer:
0740         # Routing sheet
0741         st.session_state.get("routing_editor", routing).to_excel(writer, index=False, sheet_name="Routing")
0742         # BOM sheet
0743         st.session_state.get("bom_buy_editor", bom_buy).to_excel(writer, index=False, sheet_name="BOM_buy")
0744         # Summary
0745         pd.DataFrame([
0746             {"Post":"Materiaal","Bedrag":base_mat_cost},
0747             {"Post":"Conversie","Bedrag":conv_cost},
0748             {"Post":"Inkoopdelen","Bedrag":buy_cost},
0749             {"Post":"Totaal","Bedrag":total_cost},
0750             {"Post":"Verkoop (incl. marge)","Bedrag":sales_price}
0751         ]).to_excel(writer, index=False, sheet_name="Summary")
0752     out_buf.seek(0)
0753     st.download_button("📊 Download Excel",
0754                        data=out_buf,
0755                        file_name=f"{project}_calc.xlsx",
0756                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
0757 
0758 # =============================
0759 # Einde app
0760 # =============================
0761 st.markdown("✅ Klaar – dit is de huidige versie van de Maakindustrie Cost Tool+.")
