import streamlit as st
import pandas as pd

from data import motores_base
from tabs.especifico import render_especifico_tab
from tabs.resumen import render_resumen_tab
from tabs.analisis import render_analisis_tab

st.set_page_config(layout="wide", page_title="Análisis de Motores", page_icon="🚜")

st.title("Análisis de Motores")

df, df_historico, df_completo, config, params = motores_base()

# === TABS ===
tab_resumen, tab_especifico, tab_analisis = st.tabs(["General", "Específico", "Análisis"])

with tab_resumen:

    render_resumen_tab(df, df_historico, df_completo, config, params)

with tab_especifico:

    render_especifico_tab(df, df_historico, df_completo, config, params)

with tab_analisis:

    render_analisis_tab(df, df_historico, df_completo, config, params)
