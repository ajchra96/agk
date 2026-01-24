import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

import scipy

from data import get_worst_severity, enrich_anomalies_with_severity, compute_row_metrics, detect_anomalies

def render_analisis_tab(df, df_historico, df_completo, config, params, groups, df_acciones):
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
        yaxis_range=[0, 100],
        hovermode="x unified",
        showlegend=False,
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
        yaxis_range=[0, 100],
        hovermode="x unified",
        showlegend=False,
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
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ────────────────────────────────────────────────────────────────
    # 2. General Analysis: ¿Qué impulsa los patrones actuales?
    # ────────────────────────────────────────────────────────────────
    st.subheader("Análisis General: ¿Qué impulsa los patrones actuales?")

    severity_to_priority = {"Crítico": 3, "Precaución": 2, "Atención": 1}
    emoji_map = {3: "🔴", 2: "🟠", 1: "🟡", 0: "🟢"}
    indicator_emoji = {}
    for p in params:
        col = p[1]
        name = p[0]
        match = df_acciones[df_acciones["Indicador"] == col]
        priority = 0
        if not match.empty:
            sev = match.iloc[0].get("Severidad Típica", "")
            priority = severity_to_priority.get(sev, 0)
        indicator_emoji[name] = emoji_map[priority]

    # Parameter Evolution (Horometer-Based)
    st.markdown("**Evolución de Parámetros vs Horómetro**")
    parametro = st.selectbox(
        "Selecciona un parámetro",
        options=[p[0] for p in params],
        format_func=lambda name: f"{indicator_emoji.get(name, '')} {name}",
        key="hor_param"
    )
    
    # Find limits from params
    selected_param = next((p for p in params if p[0] == parametro), None)
    min_val, max_val = selected_param[2], selected_param[3] if selected_param else (None, None)
    col_name = selected_param[1] if selected_param else parametro

    fig_hor = px.scatter(
        df,
        x=config.col_horometro,
        y=col_name,
        color=config.col_equipos,
        trendline="ols",
        trendline_scope="overall",
        title=f"{parametro} vs Horómetro (tendencia de flota)"
    )
    if min_val is not None:
        fig_hor.add_hline(y=min_val, line_color="orange", line_dash="dash", annotation_text="Mínimo")
    if max_val is not None:
        fig_hor.add_hline(y=max_val, line_color="red", line_dash="dash", annotation_text="Máximo")
    
    if parametro in df_historico.columns:
        hist_mean = df_historico[parametro].mean()
        hist_sd = df_historico[parametro].std()
        fig_hor.add_hline(y=hist_mean, line_color="black", line_dash="dash", annotation_text="Media histórica")
        fig_hor.add_hrect(
            y0=hist_mean - hist_sd,
            y1=hist_mean + hist_sd,
            fillcolor="gray",
            opacity=0.2,
            line_width=0,
            annotation_text="±1 SD histórico"
        )
    
    st.plotly_chart(fig_hor, use_container_width=True)

    # Time-Based Graph (Fecha-Based)
    st.markdown("**Evolución de Parámetros vs Fecha**")
    df[config.col_fecha] = pd.to_datetime(df[config.col_fecha], errors='coerce')
    df_plot = df[[config.col_fecha, col_name, config.col_equipos]].dropna(subset=[config.col_fecha, col_name])
    fig_time = px.scatter(
        df_plot,
        x=config.col_fecha,
        y=col_name,
        color=config.col_equipos,
        trendline="ols",
        trendline_scope="overall",
        title=f"{parametro} vs Fecha (tendencia de flota)"
    )
    if min_val is not None:
        fig_time.add_hline(y=min_val, line_color="orange", line_dash="dash", annotation_text="Mínimo")
    if max_val is not None:
        fig_time.add_hline(y=max_val, line_color="red", line_dash="dash", annotation_text="Máximo")
    
    if parametro in df_historico.columns:
        fig_time.add_hline(y=hist_mean, line_color="black", line_dash="dash", annotation_text="Media histórica")
        fig_time.add_hrect(
            y0=hist_mean - hist_sd,
            y1=hist_mean + hist_sd,
            fillcolor="gray",
            opacity=0.2,
            line_width=0,
            annotation_text="±1 SD histórico"
        )
    
    st.plotly_chart(fig_time, use_container_width=True)

    # Strong Parameter Relationships
    st.markdown("**Relaciones Fuertes entre Parámetros**")
    corr_cols = [p[1] for p in params if p[1] in df.select_dtypes(include=['float64', 'int64']).columns]
    corr_matrix = df[corr_cols].corr().round(3)

    anchor_param = st.selectbox(
        "Selecciona un parámetro para analizar correlaciones",
        options=[p[0] for p in params],
        format_func=lambda name: f"{indicator_emoji.get(name, '')} {name}",
        key="corr_anchor"
    )
    threshold = st.number_input("Umbral de correlación absoluta (recomendado ≥0.7)", min_value=0.0, max_value=1.0, value=0.7, step=0.05, key="corr_thresh")

    if anchor_param:
        anchor_col = next(p[1] for p in params if p[0] == anchor_param)
        correlates = corr_matrix[anchor_col].abs() > threshold
        correlated_df = corr_matrix.loc[correlates, anchor_col].drop(anchor_col, errors='ignore').sort_values(ascending=False)
        if not correlated_df.empty:
            st.write("Correlaciones fuertes:")
            for other_col, corr_val in correlated_df.items():
                other_name = next((p[0] for p in params if p[1] == other_col), other_col)
                sign = "suben juntos" if corr_val > 0 else "uno sube cuando el otro baja"
                st.write(f"- {indicator_emoji.get(other_name, '')} {other_name}: {corr_val:.2f} ({sign})")
        else:
            st.write("No hay correlaciones por encima del umbral seleccionado.")

    # Anomaly Propagation Map (Limited to selected indicator)
    st.markdown("**Mapa de Propagación de Anomalías**")
    import networkx as nx

    if anchor_param:
        G = nx.Graph()
        anchor_col = next(p[1] for p in params if p[0] == anchor_param)
        for other_col in corr_cols:
            if other_col == anchor_col: continue
            corr = corr_matrix[anchor_col][other_col]
            if abs(corr) > threshold:
                other_name = next((p[0] for p in params if p[1] == other_col), other_col)
                G.add_edge(anchor_param, other_name, weight=abs(corr))

        if len(G.edges()) > 0:
            pos = nx.spring_layout(G)
            edge_x, edge_y = [], []
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]

            fig_map = go.Figure()
            fig_map.add_trace(go.Scatter(
                x=edge_x, y=edge_y,
                mode='lines',
                line=dict(width=2, color='gray'),
                hoverinfo='none'
            ))
            for node in G.nodes():
                x, y = pos[node]
                fig_map.add_trace(go.Scatter(
                    x=[x], y=[y],
                    mode='markers+text',
                    text=node,
                    textposition="top center",
                    marker=dict(size=20, color='blue')
                ))
            fig_map.update_layout(
                title=f"Mapa de Propagación para {anchor_param} (correlaciones > umbral)",
                showlegend=False,
                hovermode='closest',
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
            )
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info(f"No hay propagación fuerte para {anchor_param}.")
    else:
        st.info("Selecciona un parámetro para ver el mapa de propagación.")

    # ────────────────────────────────────────────────────────────────
    # 3. Predictive Insights: ¿Qué podría pasar después?
    # ────────────────────────────────────────────────────────────────
    st.subheader("Perspectivas Predictivas: ¿Qué podría pasar después?")

    # User input for N
    N = st.number_input(
        "Número de últimas tomas para proyecciones (default 5, min 3)",
        min_value=3,
        max_value=10,
        value=5,
        step=1,
        key="proj_n"
    )

    # Healthy Subset Warning (Expanded to <3)
    st.markdown("**Advertencia para Equipos No Críticos**")
    non_critical_df = latest_df[latest_df["max_priority"] < 3]
    non_critical_pct = len(non_critical_df) / fleet_size * 100 if fleet_size > 0 else 0
    
    critical_params = [
        p for p in params 
        if df_acciones[(df_acciones["Indicador"] == p[1]) & (df_acciones["Severidad Típica"] == "Crítico")].shape[0] > 0
    ]
    
    at_risk_count = 0
    for _, row in non_critical_df.iterrows():
        eq = row[config.col_equipos]
        eq_hist = df[df[config.col_equipos] == eq].sort_values(config.col_horometro).tail(N)
        if len(eq_hist) < 3: continue
        
        for p in critical_params:
            col = p[1]
            val = row.get(col)
            if pd.isna(val): continue
            limit = p[3] if p[3] else p[2]
            is_min = p[3] is None
            valid_last = eq_hist[[config.col_horometro, col]].dropna()
            if len(valid_last) < 3: continue
            x = valid_last[config.col_horometro]
            y = valid_last[col]
            slope, intercept, r_value, _, _ = scipy.stats.linregress(x, y)
            if abs(slope) < 1e-6: continue
            if (is_min and slope > 0) or (not is_min and slope < 0): continue
            ttl = (limit - val) / slope if not is_min else (val - limit) / -slope
            if 0 < ttl < 10000:
                at_risk_count += 1
                break
    
    at_risk_pct = (at_risk_count / len(non_critical_df) * 100) if len(non_critical_df) > 0 else 0
    st.info(f"De los {non_critical_pct:.0f}% equipos no críticos (incluye atención/precaución), ≈{at_risk_pct:.0f}% podrían escalar a crítico en <10,000h (basado en últimas {N} tomas).")

    # Pre-compute risks with consistent logic
    risks = []
    risk_details = {}  # Store per-eq ttl list for details
    for _, row in latest_df.iterrows():
        eq = row[config.col_equipos]
        anoms = detect_anomalies(row, params)
        enriched = enrich_anomalies_with_severity(anoms, df_acciones)
        if any(a["priority"] == 3 for a in enriched): continue  # Skip if already critical

        eq_hist = df[df[config.col_equipos] == eq].sort_values(config.col_horometro)
        if len(eq_hist) < 3: continue

        eq_hist_last = eq_hist.tail(N)
        if len(eq_hist_last) < 3: 
            eq_hist_last = eq_hist  # Fallback to all

        eq_ttl = []
        for p in critical_params:
            col = p[1]
            if col not in eq_hist_last.columns: continue
            val = row.get(col)
            if pd.isna(val): continue
            limit = p[3] if p[3] is not None else p[2]
            is_min = p[3] is None
            valid_last = eq_hist_last[[config.col_horometro, col]].dropna()
            if len(valid_last) < 3: continue
            x = valid_last[config.col_horometro]
            y = valid_last[col]
            slope, intercept, r_value, _, _ = scipy.stats.linregress(x, y)
            if abs(slope) < 1e-6: continue
            if (is_min and slope > 0) or (not is_min and slope < 0): continue
            ttl = (limit - val) / slope if not is_min else (val - limit) / -slope
            if ttl <= 0 or ttl > 10000: continue
            r2 = r_value ** 2
            if r2 < 0.3: continue  # Skip low confidence fits
            eq_ttl.append((p[0], ttl, col, slope, intercept, r2, valid_last))

        if eq_ttl:
            min_ttl = min([t[1] for t in eq_ttl])
            min_ind = ", ".join([t[0] for t in eq_ttl if t[1] == min_ttl])
            ind_at_risk = ", ".join([t[0] for t in eq_ttl])
            risks.append({
                "Equipo": eq,
                "Horas proyectadas a volverse critico": round(min_ttl, 0),
                "Indicador Causante": min_ind,
                "Indicadores en Riesgo": ind_at_risk
            })
            risk_details[eq] = eq_ttl  # Store for details consistency

    if risks:
        risk_df = pd.DataFrame(risks).sort_values("Horas proyectadas a volverse critico")
        st.warning(f"¡Revisa estos equipos ahora! Podrían alcanzar límites críticos pronto (top 10 mostrados, basado en últimas {N} tomas):")
        st.dataframe(risk_df.head(10))

        selected_eq = st.selectbox("Selecciona un equipo para ver detalles predictivos", risk_df["Equipo"], key="eq_risk_select")
        if selected_eq:
            eq_hist = df[df[config.col_equipos] == selected_eq].sort_values(config.col_horometro)
            row = latest_df[latest_df[config.col_equipos] == selected_eq].iloc[0]
            
            eq_ttl_sorted = sorted(risk_details.get(selected_eq, []), key=lambda x: x[1])  # Use pre-computed, sorted by ttl
            
            st.subheader(f"Proyecciones para {selected_eq}")
            for ind, ttl, col, slope, intercept, r2, valid_last in eq_ttl_sorted:
                conf_note = f" (confianza: {round(r2, 2)} R²)" if r2 < 0.5 else ""
                st.write(f"**{ind}**: ~{round(ttl)} horas a límite (asumiendo tendencia lineal; pendiente: {round(slope * 1000, 2)} por 1000h{conf_note}).")
                
                fig_mini = go.Figure()
                
                # Full history gray
                fig_mini.add_trace(go.Scatter(
                    x=eq_hist[config.col_horometro],
                    y=eq_hist[col],
                    mode='markers',
                    marker=dict(color='gray', opacity=0.5),
                    name='Historia completa'
                ))
                
                # Last N blue
                fig_mini.add_trace(go.Scatter(
                    x=valid_last[config.col_horometro],
                    y=valid_last[col],
                    mode='markers',
                    marker=dict(color='blue'),
                    name=f'Últimas {len(valid_last)} tomas'
                ))
                
                # Reg line on last N
                reg_x = np.linspace(valid_last[config.col_horometro].min(), valid_last[config.col_horometro].max(), 100)
                reg_y = slope * reg_x + intercept
                fig_mini.add_trace(go.Scatter(
                    x=reg_x,
                    y=reg_y,
                    mode='lines',
                    line=dict(color='blue'),
                    name='Tendencia reciente'
                ))
                
                limit_val = next((p[3] if p[3] else p[2] for p in params if p[1] == col), None)
                if limit_val is not None:
                    fig_mini.add_hline(y=limit_val, line_color="red", line_dash="dash", annotation_text="Límite")
                
                # Projected dashed from end
                last_h = eq_hist[config.col_horometro].max()
                proj_x = [last_h, last_h + ttl]
                proj_y = [row[col], limit_val]
                fig_mini.add_trace(go.Scatter(
                    x=proj_x,
                    y=proj_y,
                    mode='lines',
                    line=dict(dash='dash', color='red'),
                    name='Proyección'
                ))
                
                fig_mini.update_layout(title=f"{ind} - {selected_eq}")
                st.plotly_chart(fig_mini, use_container_width=True)
                
                # Recommendation with shoot-up explanation
                correlates = []
                for other_col in corr_cols:
                    if other_col != col and abs(corr_matrix[col][other_col]) > 0.7:
                        correlates.append(next((p2[0] for p2 in params if p2[1] == other_col), other_col))
                
                if abs(slope) > 0.01:  # Adjust threshold based on param scales
                    st.warning(f"Nota: Pendiente pronunciada detectada—posible influencia de factores correlacionados o ruido reciente. Verifica datos históricos.")
                
                if correlates:
                    st.info(f"Recomendación: {ind} correlaciona fuertemente con {', '.join(correlates)}. Considera revisar contaminación/desgaste y avanzar mantenimiento preventivo para evitar aceleración.")
                else:
                    st.info(f"Recomendación: Avanza mantenimiento para evitar que {ind} alcance el límite.")
    else:
        st.success("No hay equipos con proyecciones urgentes de alcanzar límites críticos en los indicadores prioritarios.")
