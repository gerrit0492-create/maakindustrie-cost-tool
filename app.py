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

# -----------------------------
# Basisdata
# -----------------------------
materials = {
    "S235JR_steel": {"price": 1.4, "waste": 0.08},
    "S355_steel": {"price": 1.7, "waste": 0.10},
    "SS304": {"price": 3.5, "waste": 0.06},
    "Al_6082": {"price": 4.2, "waste": 0.07},
    "Cu_ECW": {"price": 8.0, "waste": 0.05}
}

# machine- en operatorrates (€/uur)
machine_rates = {"CNC": 85, "Laser": 110, "Lassen": 55, "Buigen": 75, "Montage": 40}
labor_rate = 45.0
overhead_pct = 0.20
profit_pct = 0.12
contingency_pct = 0.05

# -----------------------------
# Sidebar — Invoer
# -----------------------------
st.sidebar.header("🔧 Invoer")
project = st.sidebar.text_input("Projectnaam", "Demo")
Q = st.sidebar.number_input("Aantal stuks (Q)", min_value=1, value=50, step=1)
material = st.sidebar.selectbox("Materiaal", list(materials.keys()))
gewicht = st.sidebar.number_input("Netto gewicht per stuk (kg)", min_value=0.01, value=2.0)

# Learning curve
st.sidebar.subheader("Learning curve (op cyclustijd)")
lc_b = st.sidebar.number_input("b-exponent (negatief)", value=-0.15, step=0.01, format="%.2f")
lc_ref = st.sidebar.number_input("RefQty", min_value=1, value=10, step=1)

# TOU energie
st.sidebar.subheader("Energie (TOU)")
price_day = st.sidebar.number_input("Dagprijs €/kWh", value=0.24, step=0.01)
price_eve = st.sidebar.number_input("Avondprijs €/kWh", value=0.18, step=0.01)
price_night = st.sidebar.number_input("Nachtprijs €/kWh", value=0.12, step=0.01)
tou_day = st.sidebar.slider("Share dag", 0.0, 1.0, 0.6, 0.05)
tou_eve = st.sidebar.slider("Share avond", 0.0, 1.0, 0.3, 0.05)
tou_night = max(0.0, 1.0 - tou_day - tou_eve)
st.sidebar.caption(f"Share nacht wordt automatisch: **{tou_night:.2f}**")

# Processen
st.sidebar.subheader("Processen")
default_sel = ["CNC", "Montage"]
processen = st.sidebar.multiselect("Kies processen", list(machine_rates.keys()), default=default_sel)

# Per-proces parameters
proc_rows = []
for p in processen:
    with st.sidebar.expander(f"⚙️ {p}", expanded=False):
        cycle = st.number_input(f"{p} – cyclustijd (min/stuk)", min_value=0.0,
                                value={"CNC":7.5,"Laser":5.0,"Lassen":8.0,"Buigen":4.0,"Montage":6.0}.get(p,5.0),
                                key=f"cyc_{p}")
        attend = st.slider(f"{p} – operator attend %", 0, 100, 100 if p!="Laser" else 50, key=f"att_{p}")
        kwh_pc = st.number_input(f"{p} – energie (kWh/stuk)", min_value=0.0, value=0.2 if p!="Laser" else 0.5, key=f"kwh_{p}")
        qa_min = st.number_input(f"{p} – QA (min/stuk)", min_value=0.0, value=0.5 if p!="Montage" else 1.0, key=f"qa_{p}")
        scrap = st.number_input(f"{p} – scrap %", min_value=0.0, value=0.02, step=0.01, key=f"scrap_{p}")
        proc_rows.append(dict(
            Proces=p, Cycle_min=cycle, Attend_pct=attend, kWh_pc=kwh_pc, QA_min_pc=qa_min, Scrap_pct=scrap
        ))

proc_df = pd.DataFrame(proc_rows) if proc_rows else pd.DataFrame(
    columns=["Proces","Cycle_min","Attend_pct","kWh_pc","QA_min_pc","Scrap_pct"]
)

# Lean & logistiek
st.sidebar.subheader("Lean / Logistiek")
rework_pct = st.sidebar.number_input("Rework % (op proceskosten)", 0.0, 1.0, 0.05, step=0.01)
transport_min = st.sidebar.number_input("Transport (min/stuk)", 0.0, 60.0, 0.5)
storage_days = st.sidebar.number_input("Opslag (dagen batch)", 0, 365, 30)
inventory_cost_year = st.sidebar.number_input("Voorraadkosten %/jaar", 0.0, 1.0, 0.12, step=0.01)

# Make vs Buy
st.sidebar.subheader("Make vs Buy")
buy_price = st.sidebar.number_input("Inkoopprijs/stuk (€)", 0.0, 1e6, 15.0)
moq = st.sidebar.number_input("MOQ", 1, 100000, 250)
transport_buy = st.sidebar.number_input("Transport/handling (€/stuk)", 0.0, 1e6, 0.6)

# Monte-Carlo
st.sidebar.subheader("Monte-Carlo (onzekerheid)")
mc_on = st.sidebar.checkbox("Monte-Carlo simulatie aan", value=False)
mc_iter = st.sidebar.number_input("Iteraties", 100, 20000, 1000, step=100)
sd_mat = st.sidebar.number_input("σ materiaalprijs (%)", 0.0, 0.5, 0.05, step=0.01)
sd_cycle = st.sidebar.number_input("σ cyclustijd (%)", 0.0, 0.5, 0.08, step=0.01)
sd_scrap = st.sidebar.number_input("σ scrap additief (abs)", 0.0, 0.5, 0.01, step=0.005)

# -----------------------------
# Berekening deterministisch
# -----------------------------
mat = materials[material]
trend_factor = 1.0  # hook voor toekomst
mat_price = mat["price"] * trend_factor
mat_cost_total = (gewicht * mat_price * (1 + mat["waste"])) * Q

# LC factor
def lc_factor(Q, ref, b):
    try:
        return (max(Q, 1) / max(ref, 1)) ** b
    except Exception:
        return 1.0

lc_fac = lc_factor(Q, lc_ref, lc_b)

# Energie mix prijs
eff_kwh_price = (tou_day*price_day + tou_eve*price_eve + tou_night*price_night)

def compute_costs(proc_df, lc_fac):
    if proc_df.empty:
        return dict(
            proc_cost=0.0, labor_cost=0.0, machine_cost=0.0, energy_cost=0.0,
            qa_cost=0.0, scrap_impact=0.0, detail=[]
        )
    rows = []
    labor_total = machine_total = energy_total = qa_total = scrap_total = 0.0
    for _, r in proc_df.iterrows():
        p = r["Proces"]
        rate = machine_rates[p]
        cyc = float(r["Cycle_min"]) * lc_fac
        attend_frac = float(r["Attend_pct"])/100.0
        kwh_pc = float(r["kWh_pc"])
        qa_min = float(r["QA_min_pc"])
        scrap = float(r["Scrap_pct"])

        labor_pc = (cyc/60.0) * labor_rate * attend_frac
        mach_pc = (cyc/60.0) * rate
        energy_pc = kwh_pc * eff_kwh_price
        qa_pc = (qa_min/60.0) * labor_rate
        base_pc = labor_pc + mach_pc + energy_pc + qa_pc
        scrap_imp_pc = (base_pc + (gewicht*mat_price*(1+mat["waste"]))) * scrap / (1 - min(0.9, scrap))  # yield-fout

        rows.append([p, cyc, labor_pc, mach_pc, energy_pc, qa_pc, scrap_imp_pc, base_pc + scrap_imp_pc])
        labor_total += labor_pc * Q
        machine_total += mach_pc * Q
        energy_total += energy_pc * Q
        qa_total += qa_pc * Q
        scrap_total += scrap_imp_pc * Q

    proc_total = labor_total + machine_total + energy_total + qa_total + scrap_total
    return dict(
        proc_cost=proc_total,
        labor_cost=labor_total,
        machine_cost=machine_total,
        energy_cost=energy_total,
        qa_cost=qa_total,
        scrap_impact=scrap_total,
        detail=rows
    )

res = compute_costs(proc_df, lc_fac)

transport_cost = (transport_min/60.0) * labor_rate * Q
storage_cost = (storage_days/365.0) * inventory_cost_year * (res["proc_cost"])  # rente op proc-kosten
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
decision = "MAKE" if sales_total/Q < buy_total/Q else "BUY"

# -----------------------------
# UI – Resultaten
# -----------------------------
st.title("⚙️ Maakindustrie Cost Tool+")
st.caption("Incl. learning curve, TOU-energie, Monte-Carlo, PDF/Excel export")

c1, c2, c3 = st.columns(3)
c1.metric("Verkoopprijs/stuk", f"€ {sales_per_part:,.2f}")
c2.metric("Totale verkoopprijs", f"€ {sales_total:,.2f}")
c3.metric("Advies", decision)

# Tabel kostensplitsing
split_df = pd.DataFrame({
    "Categorie": ["Materiaal","Arbeid","Machine","Energie","QA","Scrap-impact","Transport","Opslag","Rework","Overhead","Contingency","Profit"],
    "Kosten (€)": [
        mat_cost_total, res["labor_cost"], res["machine_cost"], res["energy_cost"], res["qa_cost"],
        res["scrap_impact"], transport_cost, storage_cost, rework_cost, overhead, contingency, profit
    ]
})

left, right = st.columns([0.55,0.45], gap="large")
with left:
    st.subheader("💰 Kostensplitsing")
    st.dataframe(split_df, use_container_width=True, hide_index=True)

with right:
    st.subheader("📊 Visualisaties (Plotly)")
    fig = px.pie(split_df, names="Categorie", values="Kosten (€)", hole=0.35)
    st.plotly_chart(fig, use_container_width=True)
    # materiaal trend (dummy)
    days = np.arange(0, 60, 5)
    trend = materials[material]["price"] * (1 + 0.001*days)
    trend_df = pd.DataFrame({"Datum": pd.date_range(date.today(), periods=len(days), freq="5D"),
                             "€/kg": trend})
    fig2 = px.line(trend_df, x="Datum", y="€/kg", markers=True, title=f"Materiaaltrend: {material}")
    st.plotly_chart(fig2, use_container_width=True)

# Detail per proces
if len(res["detail"]) > 0:
    det_df = pd.DataFrame(res["detail"], columns=["Proces","Cycle_min_eff","Arbeid €/st","Machine €/st","Energie €/st","QA €/st","Scrap-impact €/st","Totaal €/st"])
    st.expander("🔎 Detail per proces (€/stuk)", expanded=False).dataframe(det_df, use_container_width=True, hide_index=True)

# -----------------------------
# Monte-Carlo
# -----------------------------
if mc_on:
    st.subheader("🎲 Monte-Carlo resultaten")
    rng = np.random.default_rng(42)
    # vectorized draws
    mat_mul = rng.normal(1.0, sd_mat, size=mc_iter)
    cyc_mul = rng.normal(1.0, sd_cycle, size=mc_iter)
    scrap_add = np.clip(rng.normal(0.0, sd_scrap, size=mc_iter), -0.49, 0.9)

    mc_vals = []
    for i in range(mc_iter):
        # materiaal
        m_total = (gewicht * mat_price * mat_mul[i] * (1 + materials[material]["waste"])) * Q
        # processen (alle cycli * cyc_mul)
        mod_df = proc_df.copy()
        if not mod_df.empty:
            mod_df["Cycle_min"] = mod_df["Cycle_min"] * (lc_fac * cyc_mul[i])
            mod_df["Scrap_pct"] = np.clip(mod_df["Scrap_pct"] + scrap_add[i], 0.0, 0.9)
        mc_res = compute_costs(mod_df, 1.0)  # lc al verwerkt in Cycle_min
        tr = transport_cost  # deterministisch
        stg = (storage_days/365.0) * inventory_cost_year * (mc_res["proc_cost"])
        rw = rework_pct * mc_res["proc_cost"]
        d = m_total + mc_res["proc_cost"] + tr + stg + rw
        oh = d * overhead_pct
        cg = d * contingency_pct
        ct = d + oh + cg
        pf = ct * profit_pct
        sale = (ct + pf) / Q
        mc_vals.append(sale)

    mc_vals = np.array(mc_vals)
    p50 = float(np.percentile(mc_vals, 50))
    p80 = float(np.percentile(mc_vals, 80))
    p90 = float(np.percentile(mc_vals, 90))
    c1, c2, c3 = st.columns(3)
    c1.metric("P50 €/stuk", f"€ {p50:,.2f}")
    c2.metric("P80 €/stuk", f"€ {p80:,.2f}")
    c3.metric("P90 €/stuk", f"€ {p90:,.2f}")
    hist = pd.DataFrame({"€/stuk": mc_vals})
    figh = px.histogram(hist, x="€/stuk", nbins=40, title="Verdeling verkoopprijs/stuk")
    st.plotly_chart(figh, use_container_width=True)

# -----------------------------
# Export — PDF & Excel
# -----------------------------
def build_pdf(project, Q, material, sales_pp, sales_total, split_df):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    y = H - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Offerte – {project}")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Datum: {date.today().isoformat()}")
    y -= 14
    c.drawString(40, y, f"Aantal: {Q} st  |  Materiaal: {material}")
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"Verkoopprijs/stuk: € {sales_pp:,.2f}")
    y -= 16
    c.drawString(40, y, f"Totaal: € {sales_total:,.2f}")
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
    pdf_buf = build_pdf(project, Q, material, sales_per_part, sales_total, split_df)
    st.download_button("📄 Download offerte (PDF)", data=pdf_buf, file_name=f"Offerte_{project}.pdf", mime="application/pdf")
with exp_col2:
    # Excel export
    xls_buf = io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="xlsxwriter") as xlw:
        split_df.to_excel(xlw, index=False, sheet_name="Cost_Split")
        if len(res["detail"])>0:
            det_df.to_excel(xlw, index=False, sheet_name="Process_Detail")
        meta = pd.DataFrame({
            "Key":["Project","Q","Materiaal","LC_b","LC_ref","TOU_day","TOU_eve","TOU_night","E_price_day","E_price_eve","E_price_night"],
            "Value":[project,Q,material,lc_b,lc_ref,tou_day,tou_eve,tou_night,price_day,price_eve,price_night]
        })
        meta.to_excel(xlw, index=False, sheet_name="Meta")
    xls_buf.seek(0)
    st.download_button("📊 Download Excel", data=xls_buf, file_name=f"Cost_{project}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
