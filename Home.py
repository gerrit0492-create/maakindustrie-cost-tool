import streamlit as st

st.set_page_config(page_title="Maakindustrie Cost Tool", page_icon="🧮", layout="wide")

st.title("🧮 Maakindustrie Cost Tool")
st.write("""
Welkom! Gebruik het navigatiemenu links om te kiezen:
- **Calculatie**: invoer, routing/BOM, berekeningen, Monte-Carlo, capaciteit, export (Excel/CSV/Power BI).
- **Rapport**: genereer een klant-PDF met grafieken en kerncijfers.
""")

st.info("""
**Tip**  
Zorg dat je in **`pages/01_Calculatie.py`** minimaal één berekening draait (Q, materiaal, routing/BOM).  
De **Rapport**-pagina gebruikt die resultaten direct uit `st.session_state`.
""")
