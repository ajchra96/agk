import streamlit as st
import pandas as pd
import plotly.graph_objects as go

#from ai import render_ai_chat
from data import get_latest_anomalies, enrich_anomalies_with_severity, compute_row_metrics

@st.fragment
def render_resumen_tab(df, df_historico, df_completo, config, params, groups, df_acciones):
    st.header("Resumen General de Condición - Todos los Equipos")

    #--------------Detalle General----------------------------#

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

    st.subheader("Vista General de la Flota")
    
    st.metric(label="Total equipos activos", value=fleet_size)

    severity_counts = latest_df["max_priority"].value_counts().reindex([0, 1, 2, 3], fill_value=0)
    fig_donut = go.Figure(go.Pie(
            labels=["Sano", "Atención", "Precaución", "Crítico"],
            values=severity_counts.values,
            hole=0.4,
            marker_colors=["green", "yellow", "orange", "red"],
            textinfo="label+percent"
    ))
    fig_donut.update_layout(title="Estado actual de la flota")
    st.plotly_chart(fig_donut, use_container_width=True)

    # ----- Problemas más prevalentes actuales -----
    st.subheader("Anomalías actuales con mayor incidencia por nivel de criticidad")
    all_current_enriched = [a for sublist in latest_df["enriched_anomalies"] for a in sublist]

    if not all_current_enriched:
        st.success("🎉 ¡No hay anomalías actuales en la flota!")
    else:
        df_current_anom = pd.DataFrame(all_current_enriched)
    
        color_map = {3: "red", 2: "orange", 1: "yellow", 0: "green"}
        severity_names = {3: "Críticas", 2: "Precaución", 1: "Atención"}
    
        # Agrupamos por parámetro y severidad máxima
        summary = (
            df_current_anom.groupby("name")
            .agg(
                count=("name", "count"),
                max_priority=("priority", "max")
            )
            .sort_values(["max_priority", "count"], ascending=[False, False])
        )
    
        # Mostramos un gráfico por nivel de severidad que exista
        for priority in [3, 2, 1]:
            data_sev = summary[summary["max_priority"] == priority]
            if data_sev.empty:
                continue
            
            fig = go.Figure(go.Bar(
                x=data_sev["count"],
                y=data_sev.index,
                orientation="h",
                marker_color=color_map[priority],
                text=data_sev["count"],
                textposition="outside"
            ))
            fig.update_layout(
                title=f"Anomalías {severity_names[priority]} ({data_sev['count'].sum()} en total)",
                xaxis_title="Número de equipos afectados",
                yaxis=dict(autorange="reversed"),
                height=200 + len(data_sev) * 30,# altura dinámica
                hovermode="x unified"  
            )
            st.plotly_chart(fig, use_container_width=True)

    # ----- Top offenders -----
    st.subheader("Resumen Equipos con problemas actuales")
    offenders = latest_df[latest_df["max_priority"] > 0].copy()
    if not offenders.empty:
        def top_groups(enriched):
            if not enriched:
                return "-"
            df_g = pd.DataFrame(enriched)
            return ", ".join(df_g["grupo"].value_counts().head(2).index)

        offenders["top_grupos"] = offenders["enriched_anomalies"].apply(top_groups)

        display_cols = [
            config.col_equipos,
            "max_priority",
            "anomaly_count",
            "top_grupos",
            config.col_horometro,
            config.col_fecha
        ]
        offenders_display = offenders[display_cols].sort_values(
            ["max_priority", "anomaly_count"], ascending=False
        ).rename(columns={
            config.col_equipos: "Equipo",
            "max_priority": "Severidad máxima",
            "anomaly_count": "Nº anomalías",
            "top_grupos": "Grupos principales",
            config.col_horometro: "Horómetro",
            config.col_fecha: "Última fecha"
        })
        st.dataframe(offenders_display, use_container_width=True)
    else:
        st.success("¡No hay equipos con anomalías actuales!")
        
    #-------------------Resumen especifico------------------------#
    
    st.markdown("### Resumen de Anomalías (Última Toma)")

    emoji_map = {3: "🔴", 2: "🟠", 1: "🟡", 0: "🟢"}

    latest_anomalies = get_latest_anomalies(df, config, params)

    if latest_anomalies:
        num = len(latest_anomalies)
        st.error(f"**{num} {'equipo' if num == 1 else 'equipos'} con anomalías detectadas en la última toma:**")

        for equipo in sorted(latest_anomalies.keys()):
            anomalies = latest_anomalies[equipo]

            enriched_anomalies = enrich_anomalies_with_severity(anomalies, df_acciones)

            st.markdown(f"**{equipo}**")

            # Group anomalies by their category
            by_group = {}
            for anomaly in enriched_anomalies:
                g = anomaly["grupo"]
                by_group.setdefault(g, []).append(anomaly)

            # Display groups in the original declaration order
            for group in groups:
                violations = by_group.get(group, [])
                if not violations:
                    continue

                st.markdown(f"**Anomalías en {group} ({len(violations)}):**")

                for v in violations:
                    st.markdown(f"{emoji_map.get(v.get('priority', 0), '🟢')} {v['mensaje']} ")

            st.markdown("---")

    else:
        st.success("✅ **Todos los equipos están dentro de los límites en su última toma.**")

    # --- AI Chat ---

    #render_ai_chat(df, config, params)
