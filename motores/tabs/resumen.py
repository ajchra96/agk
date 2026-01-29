import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import data

#from ai import render_ai_chat
from data import enrich_anomalies_with_severity
from data import SEVERITY, SEVERITY_PRIORITY_ORDER_DESC, PARAM_GROUPS

@st.fragment
def render_resumen_tab():

    st.header("Resumen General de Condición - Todos los Equipos")

    # TODO: Vista General de la Flota

    st.subheader("Vista General de la Flota")

    ## Total equipos activos

    fleet_size = len(latest_df)

    st.metric(label="Total equipos activos", value=fleet_size)

    ## Estado actual de la flota

    severity_counts = latest_df["max_priority"].value_counts().reindex(SEVERITY_PRIORITY_ORDER_DESC, fill_value=0)

    fig_donut = go.Figure(go.Pie(
            labels = [SEVERITY[p]["label"] for p in SEVERITY_PRIORITY_ORDER_DESC],
            values = severity_counts.values,
            hole = 0.4,
            marker_colors = [SEVERITY[p]["color"] for p in SEVERITY_PRIORITY_ORDER_DESC],
            textinfo = "label+percent"
    ))
    fig_donut.update_layout(
        title = "Estado actual de la flota",
        showlegend = False
    )

    st.plotly_chart(fig_donut, use_container_width=True)

    # TODO: Anomalías actuales con mayor incidencia por nivel de criticidad

    st.subheader("Anomalías actuales con mayor incidencia por nivel de criticidad")

    ## Ver todas las anomalias actuales

    all_current_enriched = [a for sublist in latest_df["enriched_anomalies"] for a in sublist]

    ## Mostrar resumen de anomalias

    if not all_current_enriched:

        st.success("🎉 ¡No hay anomalías actuales en la flota!")
    
    else:

        df_current_anom = pd.DataFrame(all_current_enriched)
    
        ### Agrupamos por parámetro y severidad máxima

        summary = (
            df_current_anom.groupby("name")
            .agg(
                count=("name", "count"),
                max_priority=("priority", "max")
            )
            .sort_values(["max_priority", "count"], ascending=[False, False])
        )
    
        ### Mostramos un gráfico por nivel de severidad que exista

        for priority in SEVERITY_PRIORITY_ORDER_DESC[:-1]:

            data_sev = summary[summary["max_priority"] == priority]

            if data_sev.empty:
                continue
            
            fig = go.Figure(go.Bar(
                x = data_sev["count"],
                y = data_sev.index,
                orientation = "h",
                marker_color = SEVERITY[priority]["color"],
                text = data_sev["count"],
                textposition = "outside"
            ))
            fig.update_layout(
                title = f"Anomalías {SEVERITY[priority]['name']} ({data_sev['count'].sum()} en total)",
                xaxis_title = "Número de equipos afectados",
                yaxis = dict(autorange="reversed"),
                height = 200 + len(data_sev) * 30,# altura dinámica
                hovermode = "x unified"  
            )
            st.plotly_chart(fig, use_container_width=True)

    # TODO: Resumen Equipos con problemas actuales

    st.subheader("Resumen Equipos con problemas actuales")

    ## Tabla de Equipos con Problemas

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

    
    # TODO: Detalle de Anomalías (Última Toma)

    st.markdown("### Detalle de Anomalías (Última Toma)")

    ## Data con todas las anomalías

    if latest_anomalies:
        num = len(latest_anomalies)

        ## Mensaje resumen

        st.error(f"**{num} {'equipo' if num == 1 else 'equipos'} con anomalías detectadas en la última toma:**")

        ## Detalle por equipo

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
            for group in PARAM_GROUPS:
                violations = by_group.get(group, [])
                if not violations:
                    continue

                st.markdown(f"**Anomalías en {group} ({len(violations)}):**")

                for v in violations:
                    prio = v.get('priority', 0)
                    st.markdown(f"{SEVERITY[prio]['emoji']} {v['mensaje']} ")

            st.markdown("---")

    else:
        st.success("✅ **Todos los equipos están dentro de los límites en su última toma.**")

    # TODO: AI Chat

    total_equipos = df[config.col_equipos].nunique()
