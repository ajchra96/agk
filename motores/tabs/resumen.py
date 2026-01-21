import streamlit as st
import pandas as pd

from ai import render_ai_chat

@st.fragment
def render_resumen_tab(df, df_historico, df_completo, config, params):

    st.header("Resumen General de Condición - Todos los Equipos")

    # --- Detección de anomalías en la última toma ---

    st.markdown("### Resumen de Anomalías (Última Toma)")
    
    # --- Resumen de Condición por Equipo ---

    # Recolectar grupos en el orden en que aparecen por primera vez (global, una sola vez)
    groups_order = []
    for _, _, _, _, group in params:
        if group not in groups_order:
            groups_order.append(group)

    # Lista de equipos ordenada alfabéticamente
    equipment_list = sorted(df[config.col_equipos].dropna().unique())

    # Recolectar solo los equipos que tienen anomalías (con sus mensajes planos)
    anomalies = []  # lista de (equipo, [mensajes])

    for equip in equipment_list:
        equip_df = df[df[config.col_equipos] == equip]
    
        if equip_df.empty:
            continue
    
        # Última toma del equipo
        latest_row = equip_df.sort_values(config.col_horometro).iloc[-1]
    
        # Diccionario para agrupar anomalías por categoría (solo para este equipo)
        anomalies_by_group = {}
    
        # Aplicar checks (igual que antes, pero recolectando mensajes planos)
        for name, col, min_val, max_val, group in params:
            value = latest_row.get(col)
        
            # Saltar si es NaN
            if pd.isna(value):
                continue
        
            message = None
            if min_val is not None and max_val is not None:
                if value <= min_val or value > max_val:
                    tipo = "baja" if value <= min_val else "alta"
                    message = f"**{name}**: {value:.2f} → {tipo} " \
                            f"(límites {min_val:.2f} – {max_val:.2f})"
            elif min_val is not None:
                if value <= min_val:
                    message = f"**{name}**: {value:.2f} → por debajo del mínimo " \
                            f"({min_val:.2f})"
            elif max_val is not None:
                if value > max_val:
                    message = f"**{name}**: {value:.2f} → por encima del máximo " \
                            f"({max_val:.2f})"
        
            if message:
                if group not in anomalies_by_group:
                    anomalies_by_group[group] = []
                anomalies_by_group[group].append(message)
    
        # Solo agregar el equipo si tiene al menos una anomalía
        if anomalies_by_group:
            anomalies.append((equip, anomalies_by_group))

    # Mostrar resumen global y detalle
    if anomalies:
        num = len(anomalies)
        st.error(f"**{num} {'equipo' if num == 1 else 'equipos'} con anomalías detectadas en la última toma:**")
    
        for equipo, anomalies_by_group in anomalies:
            st.markdown(f"**{equipo}**")
        
            for group in groups_order:
                violations = anomalies_by_group.get(group, [])
                if violations:
                    st.markdown(f"**Anomalías en {group}:**")
                    for violation in violations:
                        st.markdown(f"- {violation}")
        
            # Separador visual entre equipos
            st.markdown("---")
    else:
        st.success("✅ **Todos los equipos están dentro de los límites en su última toma.**")

    # --- AI Chat ---

    render_ai_chat(df, config, params)
