import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import date

st.set_page_config(page_title="Maakindustrie Cost Tool", layout="wide")

# -----------------------------
# Data (materialen & rates)
# -----------------------------
materials = {
    "S235JR_steel": {"price": 1.4, "waste": 0.08},
    "S355_steel": {"price": 1.7, "waste": 0.10},
    "SS304": {"price": 3.5, "waste": 0.06},
    "Al_6082": {"price": 4.2, "waste": 0.07},
    "Cu_ECW": {"price": 8.0, "waste": 0.05}
}

machine_rates = {
    "CNC": 85,
    "Laser": 110,
    "Lassen": 55,
    "Buigen": 75,
    "Montage": 40
}

labor_rate = 45
energy_rate = 0.20
overhead_pct = 0.20
profit_pct = 0.12
contingency_pct = 0.05

# -----------------------------
# Sidebar inputs
# -----------------------------
st.sidebar.header("🔧 Invoer")
Q = st.sidebar.number_input("Aantal stuks", min_value=1, value=50)
material = st.sidebar.selectbox("Materiaal", list(materials.keys()))
gewicht = st.sidebar.number_input("Netto gewicht per stuk (kg)", min_value=0.1, value=2.0)

processen = st.sidebar.multiselect(
    "Processen",
    ["CNC", "Laser", "Lassen", "Buigen", "Montage"],
    default=["CNC", "Montage"]
)

scrap_pct = st.sidebar.slider("Scrap %", 0.0, 0.2, 0.02, step=0.01)
rework_pct = st.sidebar.slider("Rework %", 0.0, 0.2, 0.05, step=0.01)
transport_min = st.sidebar.number_input("Transport (min/stuk)", 0.0, 5.0, 0.5)
storage_days = st.sidebar.number_input("Opslag (dagen batch)", 0, 180, 30)

st.sidebar.subheader("Make vs Buy")
buy_price = st.sidebar.number_input("Inkoopprijs/stuk (€)", 0.0, 1000.0, 15.0)
moq = st.sidebar.number_input("MOQ (stuks)", 1, 5000, 250)
transport_buy = st.sidebar.number_input("Transport (€/stuk)", 0.0, 50.0, 0.6)

# -----------------------------
# Berekening
# -----------------------------
mat_info = materials[material]
mat_cost = (gewicht * mat_info["price"] * (1 + mat_info["waste"] + scrap_pct)) * Q

proc_costs = {}
for p in processen:
    rate = machine_rates[p]
    cycle_time_min = {"CNC": 7.5, "Laser": 5.0, "Lassen": 8.0, "Buigen": 4.0, "Montage": 6.0}[p]
    cost = (cycle_time_min/60) * rate * Q
    proc_costs[p] = cost

rework_cost = rework_pct * sum(proc_costs.values())
transport_cost = (transport_min/60) * labor_rate * Q
storage_cost = (storage_days/365) * 0.12 * sum(proc_costs.values())  # 12% jaar

direct_cost = mat_cost + sum(proc_costs.values()) + rework_cost + transport_cost + storage_cost
overhead = direct_cost * overhead_pct
contingency = direct_cost * contingency_pct
cost_total = direct_cost + overhead + contingency
profit = cost_total * profit_pct
sales_total = cost_total + profit
sales_per_part = sales_total / Q

# Make vs Buy
buy_total = (buy_price + transport_buy) * max(Q, moq)
make_total = sales_total
decision = "MAKE" if make_total/Q < buy_total/Q else "BUY"

# -----------------------------
# Output
# -----------------------------
st.title("⚙️ Maakindustrie Cost Tool")
st.markdown(f"### Project calculatie voor **{Q} stuks {material}**")

col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Kostensplitsing")
    df = pd.DataFrame({
        "Categorie": ["Materiaal", "Processen", "Rework", "Transport", "Opslag", "Overhead", "Contingency", "Profit"],
        "Kosten (€)": [mat_cost, sum(proc_costs.values()), rework_cost, transport_cost, storage_cost, overhead, contingency, profit]
    })
    st.dataframe(df, use_container_width=True)
    st.metric("Totale kostprijs", f"€ {sales_total:,.2f}")
    st.metric("Verkoopprijs/stuk", f"€ {sales_per_part:,.2f}")

with col2:
    st.subheader("📊 Visualisatie")
    fig, ax = plt.subplots()
    ax.pie(df["Kosten (€)"], labels=df["Categorie"], autopct="%1.1f%%")
    st.pyplot(fig)

st.markdown('---')
st.subheader("🤝 Make vs Buy analyse")
col3, col4 = st.columns(2)
with col3:
    st.metric("MAKE €/stuk", f"€ {make_total/Q:,.2f}")
with col4:
    st.metric("BUY €/stuk", f"€ {buy_total/Q:,.2f}")
st.success(f"Advies: **{decision}**")

# -----------------------------
# Materiaal prijs trend (dummy 2 mnd)
# -----------------------------
st.markdown('---')
st.subheader("📈 Materiaalprijs trend (2 maanden)")
days = np.arange(0, 60, 5)
trend = mat_info['price'] * (1 + 0.001*days)
dates = pd.date_range(date.today(), periods=len(days), freq='5D')
fig2, ax2 = plt.subplots()
ax2.plot(dates, trend, marker='o')
ax2.set_ylabel("€/kg")
ax2.set_title(f"Prijs trend {material}")
st.pyplot(fig2)
