import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

def render_analisis_tab(df, df_historico, df_completo, config, params):
    st.header("Análisis Avanzado")

    # === 1. Heatmap de correlaciones ===
    st.subheader("Matriz de Correlaciones")
    st.markdown("""
    Muestra las correlaciones (Pearson) entre todos los parámetros numéricos.  
    Valores cercanos a ±1 indican relaciones fuertes.
    """)

    # Columnas numéricas relevantes (excluye Horometro y Fecha si quieres)
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    # Opcional: filtrar solo las columnas de interés para que no sea demasiado grande
    key_params = ["Viscosidad", "▲ Temp Radiador", "Fe", "Cr", "Pb", "Cu", "Sn", "Al",
                  "Silicio", "Na", "Hollin", "Oxidación", "Sulfatación", "Nitración",
                  "TBN", "P", "Zn", "Blow by Carter"]  # ajusta según tus columnas reales
    corr_cols = [col for col in key_params if col in numeric_cols]

    corr_matrix = df[corr_cols].corr().round(3)

    fig_heatmap = px.imshow(
        corr_matrix,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1,
        title="Correlación entre parámetros clave"
    )
    fig_heatmap.update_layout(height=700)
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # === 2. Tendencias con regresión ===
    st.subheader("Tendencias vs Horómetro con Regresión")
    col1, col2 = st.columns(2)
    with col1:
        parametro = st.selectbox("Parámetro", corr_cols)
    with col2:
        modo = st.radio("Modo de visualización", ["Todos los equipos", "Por equipo separado"])

    if modo == "Todos los equipos":
        fig_trend = px.scatter(
            df,
            x="Horometro",
            y=parametro,
            color="Equipo",
            trendline="ols",          # regresión lineal
            trendline_scope="overall",# línea global
            title=f"{parametro} vs Horómetro (tendencia global)"
        )
    else:
        fig_trend = px.scatter(
            df,
            x="Horometro",
            y=parametro,
            color="Equipo",
            trendline="ols",
            trendline_scope="trace",  # una línea por equipo
            title=f"{parametro} vs Horómetro (tendencia por equipo)"
        )

    # Añadir línea del promedio histórico
    if parametro in df_historico.columns:
        fig_trend.add_scatter(
            x=df_historico["Horometro"],
            y=df_historico[parametro],
            mode="lines",
            name="Promedio histórico",
            line=dict(dash="dash", color="black", width=3)
        )

    st.plotly_chart(fig_trend, use_container_width=True)

    # === 3. Tasa de desgaste (solo para metales de desgaste) ===
    st.subheader("Tasa de Desgaste (ppm por 1000 horas)")
    wear_metals = ["Fe", "Cr", "Pb", "Cu", "Al"]  # ajusta según tus datos
    wear_metals = [m for m in wear_metals if m in df.columns]

    if wear_metals:
        rates = []
        for equipo in df["Equipo"].unique():
            df_eq = df[df["Equipo"] == equipo].sort_values("Horometro")
            if len(df_eq) < 2:
                continue
            for metal in wear_metals:
                # Regresión simple: pendiente * 1000 para tasa por 1000 h
                slope = np.polyfit(df_eq["Horometro"], df_eq[metal], 1)[0] * 1000
                rates.append({
                    "Equipo": equipo,
                    "Metal": metal,
                    "Tasa (ppm/1000 h)": round(slope, 2)
                })
        df_rates = pd.DataFrame(rates)
        if not df_rates.empty:
            st.dataframe(df_rates.pivot(index="Equipo", columns="Metal", values="Tasa (ppm/1000 h)").round(2))

    # === 4. Opcional: PCA rápido (avanzado pero útil) ===
    if st.checkbox("Mostrar Análisis de Componentes Principales (PCA)"):
        from sklearn.preprocessing import StandardScaler
        from sklearn.decomposition import PCA

        X = df[corr_cols].dropna()
        X_scaled = StandardScaler().fit_transform(X)
        pca = PCA(n_components=3)
        components = pca.fit_transform(X_scaled)

        fig_pca = px.scatter_3d(
            x=components[:,0],
            y=components[:,1],
            z=components[:,2],
            color=df.loc[X.index, "Equipo"],
            size=df.loc[X.index, "Fe"],  # ejemplo: tamaño por Fe
            hover_data={"Horometro": df.loc[X.index, "Horometro"]},
            title="PCA – 3 componentes principales"
        )
        st.plotly_chart(fig_pca, use_container_width=True)

        st.write("Varianza explicada:", pca.explained_variance_ratio_.round(3))
