import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

def render_analisis_tab(df, df_historico, df_completo, config, params):
    st.header("Análisis Avanzado")

    #----------------- Tendencias históricas--------------#

    # ---------- Latest per equipment ----------
    latest_idx = df.groupby(config.col_equipos)[config.col_horometro].idxmax()
    latest_df = df.loc[latest_idx].sort_values(config.col_equipos).reset_index(drop=True)

    # Compute current metrics
    metrics_list = latest_df.apply(
        lambda row: compute_row_metrics(row, params, df_acciones),
        axis=1
    )
    latest_df["max_priority"] = [m[0] for m in metrics_list]
    latest_df["anomaly_count"] = [m[1] for m in metrics_list]
    latest_df["enriched_anomalies"] = [m[2] for m in metrics_list]

    fleet_size = len(latest_df)
    healthy_percent = (latest_df["max_priority"] == 0).sum() / fleet_size * 100 if fleet_size > 0 else 0

    # ----- Tendencias históricas -----
    st.subheader("📈 Tendencias históricas")

    @st.cache_data(ttl=3600)
    def add_max_priority_to_full_df(_df):
        _df = _df.copy()
        def row_max_p(r):
            anomalies = detect_anomalies(r, params)
            enriched = enrich_anomalies_with_severity(anomalies, df_acciones)
            return max((a["priority"] for a in enriched), default=0)
        _df["max_priority"] = _df.apply(row_max_p, axis=1)
        return _df

    df_with_priority = add_max_priority_to_full_df(df)

    # Monthly snapshots
    df_with_priority[config.col_fecha] = pd.to_datetime(df_with_priority[config.col_fecha])
    fecha_periods = df_with_priority[config.col_fecha].dt.to_period('M')
    min_period = fecha_periods.min()
    max_period = fecha_periods.max()

    monthly_dates = pd.date_range(
        min_period.start_time,
        max_period.end_time,
        freq="M"
    )

    trend_rows = []

    # Anomalías por grupo (conteo y %)
    group_trend_counts = {g: [] for g in groups}
    group_trend_pct = {g: [] for g in groups}

    # Anomalías por indicador, separadas por severidad
    all_indicators = [p[0] for p in params]
    indicator_trend_counts_by_sev = {
        3: {ind: [] for ind in all_indicators},
        2: {ind: [] for ind in all_indicators},
        1: {ind: [] for ind in all_indicators}
    }
    indicator_trend_pct_by_sev = {
        3: {ind: [] for ind in all_indicators},
        2: {ind: [] for ind in all_indicators},
        1: {ind: [] for ind in all_indicators}
    }

    for month_end in monthly_dates:
        snapshot = df_with_priority[df_with_priority[config.col_fecha] <= month_end]
        if snapshot.empty:
            trend_rows.append({
                "date": month_end,
                "fleet_size": 0,
                **{f"pct_{i}": 0 for i in range(4)},
                **{f"count_{i}": 0 for i in range(4)}
            })
            for g in groups:
                group_trend_counts[g].append(0)
                group_trend_pct[g].append(0)
            for prio in [3, 2, 1]:
                for ind in all_indicators:
                    indicator_trend_counts_by_sev[prio][ind].append(0)
                    indicator_trend_pct_by_sev[prio][ind].append(0)
            continue

        latest_snapshot = snapshot.loc[snapshot.groupby(config.col_equipos)[config.col_horometro].idxmax()]

        # Severidad (% de equipos)
        sev_counts = latest_snapshot["max_priority"].value_counts().reindex([0,1,2,3], fill_value=0)
        fleet_month = len(latest_snapshot)
        raw_pct = sev_counts / fleet_month * 100 if fleet_month > 0 else pd.Series([0]*4, index=[0,1,2,3])
        pct = raw_pct.round(1)
        if pct.sum() > 0:
            difference = 100 - pct.sum()
            if difference != 0:
                max_idx = pct.idxmax()
                pct[max_idx] += difference

        trend_rows.append({
            "date": month_end,
            "fleet_size": fleet_month,
            **{f"pct_{i}": pct[i] for i in range(4)},
            **{f"count_{i}": sev_counts[i] for i in range(4)}
        })

        # Anomalías
        snapshot_anomalies = []
        for _, row in latest_snapshot.iterrows():
            anom = detect_anomalies(row, params)
            enriched = enrich_anomalies_with_severity(anom, df_acciones)
            snapshot_anomalies.extend(enriched)

        total_anomalies_month = len(snapshot_anomalies)

        if snapshot_anomalies:
            df_snap_anom = pd.DataFrame(snapshot_anomalies)

            # Por grupo
            group_counts = df_snap_anom["grupo"].value_counts()
            for g in groups:
                count = group_counts.get(g, 0)
                group_trend_counts[g].append(count)
                pct_val = (count / total_anomalies_month * 100) if total_anomalies_month > 0 else 0
                group_trend_pct[g].append(pct_val)

            # NUEVO: Totals por severidad para este mes
            total_per_sev = {3: 0, 2: 0, 1: 0}
            sev_counts_month = df_snap_anom["priority"].value_counts()
            for prio in [3, 2, 1]:
                total_per_sev[prio] = sev_counts_month.get(prio, 0)

            # Por indicador y severidad
            grouped = df_snap_anom.groupby(["name", "priority"]).size().unstack(fill_value=0)
            for prio in [3, 2, 1]:
                total_this_sev = total_per_sev[prio]
                for ind in all_indicators:
                    count = grouped[prio].get(ind, 0) if prio in grouped.columns else 0
                    indicator_trend_counts_by_sev[prio][ind].append(count)
                    pct_val = (count / total_this_sev * 100) if total_anomalies_month > 0 else 0
                    indicator_trend_pct_by_sev[prio][ind].append(pct_val)
        else:
            for g in groups:
                group_trend_counts[g].append(0)
                group_trend_pct[g].append(0)
            for prio in [3, 2, 1]:
                for ind in all_indicators:
                    indicator_trend_counts_by_sev[prio][ind].append(0)
                    indicator_trend_pct_by_sev[prio][ind].append(0)

    df_trend = pd.DataFrame(trend_rows)

    # Gráfico 1: % de la flota por severidad
    fig_trend_pct = go.Figure()
    for i, name, color in zip(range(4), ["Sano", "Atención", "Precaución", "Crítico"], ["green", "yellow", "orange", "red"]):
        fig_trend_pct.add_trace(go.Scatter(
            x=df_trend["date"],
            y=df_trend[f"pct_{i}"],
            name=name,
            stackgroup="one",
            fillcolor=color,
            line=dict(color=color),
            hovertemplate=f"{name}: %{{y:.1f}}% (%{{customdata}} equipos)<extra></extra>",
            customdata=df_trend[f"count_{i}"]
        ))
    fig_trend_pct.update_layout(
        title="% de la flota por nivel de severidad (mensual)",
        yaxis_title="% de equipos",
        yaxis_range=[0, 100]
    )
    st.plotly_chart(fig_trend_pct, use_container_width=True)

    # Gráfico 2: % de anomalías por grupo
    fig_group_trend = go.Figure()
    for g in groups:
        fig_group_trend.add_trace(go.Scatter(
            x=df_trend["date"],
            y=group_trend_pct[g],
            name=g,
            stackgroup="one",
            mode="lines",
            hovertemplate=f"{g}: %{{y:.1f}}% (%{{customdata}} anomalías)<extra></extra>",
            customdata=group_trend_counts[g]
        ))
    fig_group_trend.update_layout(
        title="% de anomalías por grupo (mensual)",
        yaxis_title="% del total de anomalías",
        yaxis_range=[0, 100]
    )
    st.plotly_chart(fig_group_trend, use_container_width=True)

    # Gráfico 3: % de anomalías por indicador, separado por severidad
    st.subheader("📈 Evolución de anomalías por indicador (mensual, por severidad)")

    severity_info = {
        3: {"name": "Críticas", "color": "red"},
        2: {"name": "Precaución", "color": "orange"},
        1: {"name": "Atención", "color": "yellow"}
    }

    for prio in [3, 2, 1]:  # Crítico primero
        info = severity_info[prio]
        active_ind = [ind for ind in all_indicators if sum(indicator_trend_counts_by_sev[prio][ind]) > 0]

        if active_ind:
            fig = go.Figure()
            for ind in active_ind:
                fig.add_trace(go.Scatter(
                    x=df_trend["date"],
                    y=indicator_trend_pct_by_sev[prio][ind],
                    name=ind,
                    stackgroup="one",
                    mode="lines",
                    hovertemplate=f"{ind}: %{{y:.1f}}% (%{{customdata}} anomalías)<extra></extra>",
                    customdata=indicator_trend_counts_by_sev[prio][ind]
                ))

            fig.update_layout(
                title=f"% de anomalías {info['name']} por indicador (mensual)",
                yaxis_title="% del total de anomalías",
                yaxis_range=[0, 100],
                legend_title="Indicador",
                height=500 if len(active_ind) > 10 else 400,
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

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
