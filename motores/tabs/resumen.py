import streamlit as st
import pandas as pd

#from ai import render_ai_chat
from data import get_latest_anomalies

@st.fragment
def render_resumen_tab(df, df_historico, df_completo, config, params, groups):
    st.header("Resumen General de Condición - Todos los Equipos")
    st.markdown("### Resumen de Anomalías (Última Toma)")

    latest_anomalies = get_latest_anomalies(df, config, params)

    if latest_anomalies:
        num = len(latest_anomalies)
        st.error(f"**{num} {'equipo' if num == 1 else 'equipos'} con anomalías detectadas en la última toma:**")

        for equipo in sorted(latest_anomalies.keys()):
            anomalies = latest_anomalies[equipo]
            st.markdown(f"**{equipo}**")

            # Group anomalies by their category
            by_group = {}
            for anomaly in anomalies:
                g = anomaly["grupo"]
                by_group.setdefault(g, []).append(anomaly)

            # Display groups in the original declaration order
            for group in groups:
                violations = by_group.get(group, [])
                if not violations:
                    continue
                st.markdown(f"**Anomalías en {group} ({len(violations)}):**")
                for v in violations:
                    st.markdown(f"- {v['mensaje']}")

            st.markdown("---")

    else:
        st.success("✅ **Todos los equipos están dentro de los límites en su última toma.**")

    # --- AI Chat ---

    #render_ai_chat(df, config, params)
