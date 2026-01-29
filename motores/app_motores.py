import streamlit as st

from tabs.especifico import render_especifico_tab
from tabs.resumen import render_resumen_tab
from tabs.analisis import render_analisis_tab

st.set_page_config(layout="wide", page_title="Análisis de Motores", page_icon="🚜")

st.title("Análisis de Motores")

####

st.sidebar.header("Carga de archivos")

uploaded_motores = st.sidebar.file_uploader(
    "Archivo de datos de motores (motores_base.xlsx)",
    type=["xlsx", "xls"],
    help="Debe contener la hoja 'DATOS'"
)

uploaded_reglas = st.sidebar.file_uploader(
    "Archivo de reglas (Reglas.xlsx)",
    type=["xlsx", "xls"],
    help="Debe contener la hoja 'REGLAS'"
)

data.load_data(uploaded_motores, uploaded_reglas)

# === TABS ===
tab_resumen, tab_especifico, tab_analisis = st.tabs(["General", "Específico", "Análisis"])

with tab_resumen:

    render_resumen_tab()

with tab_especifico:

    render_especifico_tab()

with tab_analisis:

    render_analisis_tab()
