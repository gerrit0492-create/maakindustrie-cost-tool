import os, sys
print(">>> sys.path:", sys.path)
print(">>> files in root:", os.listdir("."))
print(">>> files in utils:", os.listdir("utils"))
import io, streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from utils.shared import *

st.set_page_config(page_title="Rapport", page_icon="📄", layout="wide")
st.title("Klant-rapport (PDF)")

# Vereiste data uit calculatie
missing=[k for k in ["project","Q","mat","netkg","price","price_src","res"] if k not in st.session_state]
if missing:
    st.warning("Eerst een berekening uitvoeren op de pagina **Calculatie**.")
    st.stop()

project=st.session_state["project"]; Q=st.session_state["Q"]; mat=st.session_state["mat"]
price=st.session_state["price"]; src=st.session_state["price_src"]; res=st.session_state["res"]
mc_samples=st.session_state.get("mc_samples"); cap_df=st.session_state.get("cap_df")

# Optionele projectie
proj_on = st.checkbox("Projectie (12 mnd)", False)
mchg = st.number_input("Mutatie %/mnd (alleen materiaal)", -0.5, 0.5, 0.0, 0.01)
proj_df=None
if proj_on:
    d=[price]
    for _ in range(12): d.append(d[-1]*(1+mchg))
    proj_df=pd.DataFrame({"Month":range(13),"€/kg":d})
    st.session_state["proj_df"]=proj_df
else:
    st.session_state["proj_df"]=None

# Voorbeeld grafieken op scherm
st.plotly_chart(go.Figure(go.Pie(labels=["Materiaal","Conversie","Lean","Inkoop"],
                                 values=[res['mat_pc'],res['conv_total'],res['lean_total'],res['buy_total']])),
                use_container_width=True)
if cap_df is not None and not cap_df.empty:
    fig=px.bar(cap_df,x="Proces",y="Util_pct",text=(cap_df["Util_pct"]*100).round(1)); fig.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
if proj_df is not None:
    st.plotly_chart(px.line(proj_df, x="Month", y="€/kg"), use_container_width=True)
if mc_samples is not None and len(mc_samples)>0:
    st.plotly_chart(px.histogram(pd.DataFrame({"UnitCost":mc_samples}), x="UnitCost", nbins=40), use_container_width=True)

# ---- PDF export met grafieken (via kaleido) ----
def fig_to_png_bytes(fig)->bytes:
    return fig.to_image(format="png", width=900, height=600, scale=1)  # kaleido

def build_figs():
    figs={}
    pie=go.Figure(go.Pie(labels=["Materiaal","Conversie","Lean","Inkoop"],
                         values=[res['mat_pc'],res['conv_total'],res['lean_total'],res['buy_total']]))
    pie.update_layout(title="Kostensamenstelling")
    figs["pie"]=pie
    if cap_df is not None and not cap_df.empty:
        cap=px.bar(cap_df,x="Proces",y="Util_pct",text=(cap_df["Util_pct"]*100).round(1))
        cap.update_layout(title="Capaciteitsbenutting", yaxis_tickformat=".0%")
        figs["cap"]=cap
    if st.session_state.get("proj_df") is not None:
        figs["proj"]=px.line(st.session_state["proj_df"], x="Month", y="€/kg", title="Materiaalprijs projectie (12 mnd)")
    if mc_samples is not None and len(mc_samples)>0:
        figs["mc"]=px.histogram(pd.DataFrame({"UnitCost":mc_samples}), x="UnitCost", nbins=40, title="Monte-Carlo – kostprijs/stuk")
    return figs

if st.button("⬇️ Genereer PDF"):
    figs=build_figs()
    pdf=io.BytesIO(); c=canvas.Canvas(pdf, pagesize=A4); W,H=A4

    # Voorblad
    c.setFont("Helvetica-Bold", 16); c.drawString(36, H-48, f"Offerte – {project}")
    c.setFont("Helvetica",10)
    c.drawString(36, H-68, f"Q: {Q}")
    c.drawString(36, H-82, f"Materiaal: {mat} – € {price:.3f}/kg ({src})")
    table_data=[
        ["Post","€"],
        ["Materiaal", f"{res['mat_pc']:.2f}"],
        ["Conversie", f"{res['conv_total']:.2f}"],
        ["Lean", f"{res['lean_total']:.2f}"],
        ["Inkoop", f"{res['buy_total']:.2f}"],
        ["Totaal", f"{res['total_pc']:.2f}"],
        ["Verkoop (marge+cont.)", f"{(res['total_pc']*(1+PROFIT+CONT)):.2f}"],
    ]
    t=Table(table_data, colWidths=[260,120])
    t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.5,colors.black),
                           ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
                           ("ALIGN",(1,1),(1,-1),"RIGHT")]))
    tw,th=t.wrapOn(c, W-72, H-200); t.drawOn(c, 36, H-140-th)
    c.showPage()

    # Grafiekenpagina's
    for key,title in [("pie","Kostensamenstelling"),("proj","Prijsprojectie"),
                      ("cap","Capaciteit"),("mc","Monte-Carlo")]:
        if key in figs:
            try:
                img=io.BytesIO(fig_to_png_bytes(figs[key]))
                margin=36; img_w, img_h = 520, 360
                x=(W-img_w)/2; y=(H-img_h)/2 - 20
                c.setFont("Helvetica-Bold", 14); c.drawString(margin, H - margin - 10, title)
                c.drawImage(img, x, y, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
                c.showPage()
            except Exception as e:
                c.setFont("Helvetica", 12); c.drawString(36, H-72, f"Kon {title} niet renderen (kaleido vereist)."); c.showPage()

    c.save(); pdf.seek(0)
    st.download_button("⬇️ Download PDF", pdf.getvalue(), f"{project}_rapport.pdf", "application/pdf")
