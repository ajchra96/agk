import streamlit as st
import pandas as pd
import plotly.express as px

#from ai import render_ai_chat_esp
from data import get_latest_anomalies
from data import get_worst_severity, enrich_anomalies_with_severity

@st.fragment
def render_especifico_tab(df, df_historico, df_completo, config, params, groups, df_acciones):
    st.header("Análisis de Condición Motores Diesel por Equipo")

    # Get latest anomalies once (shared with resumen tab)
    latest_anomalies = get_latest_anomalies(df, config, params)

    # Prepare equipment list with severity-based emoji + sorting
    equipo_data = []
    all_equipos = sorted(df[config.col_equipos].dropna().unique())

    emoji_map = {3: "🔴", 2: "🟠", 1: "🟡", 0: "🟢"}

    for eq in all_equipos:
        anomalies = latest_anomalies.get(eq, [])
        
        # Get worst severity priority (0 = no issue / green)
        worst_priority = get_worst_severity(anomalies, df_acciones)

        # Map priority → emoji
        emoji = emoji_map.get(worst_priority, "🟢")

        equipo_data.append((emoji, eq, worst_priority))

    # Prepare selectbox data
    display_labels = [f"{emoji} {eq}" for emoji, eq, _ in equipo_data]
    real_equipos   = [eq for _, eq, _ in equipo_data]

    # Selectbox – defaults to the most critical equipment
    selected_idx = st.selectbox(
        label="Equipo",
        options=range(len(real_equipos)),
        format_func=lambda i: display_labels[i],
        index=0,  # first item = worst case
        key="filtro_equipos_especifico"
    )
    selected_equipo = real_equipos[selected_idx]

    df_filtered = df.copy()
    df_filtered = df_filtered[df_filtered[config.col_equipos] == selected_equipo]

    # Get anomalies for this equipment
    anomalies = latest_anomalies.get(selected_equipo, [])
    enriched_anomalies = enrich_anomalies_with_severity(anomalies, df_acciones)

    st.markdown("### Resumen de Condición de la Última Toma")

    if anomalies:
        st.error("⚠️ Anomalías detectadas:")

        # Group by category
        by_group = {}
        for anomaly in enriched_anomalies:
            g = anomaly["grupo"]
            by_group.setdefault(g, []).append(anomaly)

        # Show groups in the original params order
        for group in groups:
            violations = by_group.get(group, [])
            if not violations:
                continue

            st.markdown(f"##### Anomalías en {group} ({len(violations)})")

            for v in violations:
                # Lookup in acciones
                match = df_acciones[
                    (df_acciones["Indicador"] == v["column"]) &
                    (df_acciones["Tipo"].str.upper() == v["tipo"])
                ]

                if not match.empty:
                    row = match.iloc[0]
                    posible_motivo    = row.get("Posible Motivo", "No disponible")
                    accion_recomendada = row.get("Acción Recomendada", "No disponible")
                    severidad_tipica   = row.get("Severidad Típica", "No disponible")
                else:
                    posible_motivo    = "No se encontró motivo específico"
                    accion_recomendada = "No se encontró acción recomendada"
                    severidad_tipica   = "No disponible"

                # Expander per anomaly (keeping your original style)

                emoji = emoji_map.get(v.get("priority", 0), "🟢")

                with st.expander(f"{emoji} {v['mensaje']}", expanded=False):
                    st.markdown(f"**Valor medido:** {v['value']:.2f}")
                    st.markdown("**Posible Motivo:**")
                    st.info(posible_motivo)
                    st.markdown("**Acción Recomendada:**")
                    st.success(accion_recomendada)
                    st.markdown("**Severidad Típica:**")
                    st.markdown(severidad_tipica)

    else:
        st.success(f"✅ Todos los parámetros del equipo **{selected_equipo}** están dentro de los límites.")

    # --- Gráficas ---

    st.markdown("### Gráficos por indicador")

    ## Limpieza de la tabla para graficar

    min_horo = df_filtered[config.col_horometro].min()
    max_horo = df_filtered[config.col_horometro].max()

    df_selected = df_completo[
        (df_completo[config.col_equipos] == selected_equipo) | 
        (df_completo[config.col_equipos] == "Histórico")
    ].sort_values("Horometro")

    df_selected = df_selected[
        (df_selected[config.col_horometro] >= min_horo) &
        (df_selected[config.col_horometro] <= max_horo)
    ]

    ## Plot de las gráficas

    st.markdown("#### - Datos operativos / físicos de la muestra")

    col_1_1, col_1_2, col_1_3, col_1_4 = st.columns(4, gap="small")

    with col_1_1:

        fig_1_1 = px.line(
            df_selected, 
            x= config.col_horometro, 
            y= config.col_cil_1,
            color=config.col_equipos,
            title = "Cilindro 1 (BAR) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_1_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )
        
        fig_1_1.add_hrect(y0=config.cil_min, y1=config.cil_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_1_1.add_hline(y=config.cil_min, line_dash="dash", line_color="red")
        fig_1_1.add_hline(y=config.cil_max, line_dash="dash", line_color="red")
    
        fig_1_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_1_1, use_container_width=True, key="graph_cil_1")

    with col_1_2:

        fig_1_2 = px.line(
            df_selected, 
            x= config.col_horometro, 
            y= config.col_cil_2,
            color=config.col_equipos,
            title = "Cilindro 2 (BAR) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_1_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )
        
        fig_1_2.add_hrect(y0=config.cil_min, y1=config.cil_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_1_2.add_hline(y=config.cil_min, line_dash="dash", line_color="red")
        fig_1_2.add_hline(y=config.cil_max, line_dash="dash", line_color="red")
    
        fig_1_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_1_2, use_container_width=True, key="graph_cil_2")

    with col_1_3:

        fig_1_3 = px.line(
            df_selected, 
            x= config.col_horometro, 
            y= config.col_cil_3,
            color=config.col_equipos,
            title = "Cilindro 3 (BAR) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_1_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )
        
        fig_1_3.add_hrect(y0=config.cil_min, y1=config.cil_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_1_3.add_hline(y=config.cil_min, line_dash="dash", line_color="red")
        fig_1_3.add_hline(y=config.cil_max, line_dash="dash", line_color="red")
    
        fig_1_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_1_3, use_container_width=True, key="graph_cil_3")
    
    with col_1_4:

        fig_1_4 = px.line(
            df_selected, 
            x= config.col_horometro, 
            y= config.col_cil_4,
            color=config.col_equipos,
            title = "Cilindro 4 (BAR) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_1_4.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )
        
        fig_1_4.add_hrect(y0=config.cil_min, y1=config.cil_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_1_4.add_hline(y=config.cil_min, line_dash="dash", line_color="red")
        fig_1_4.add_hline(y=config.cil_max, line_dash="dash", line_color="red")
    
        fig_1_4.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_1_4, use_container_width=True, key="graph_cil_4")
        

    col_2_1, col_2_2 = st.columns(2, gap="small")

    with col_2_1:

        fig_2_1 = px.line(
            df_selected, 
            x= config.col_horometro, 
            y= config.col_p_carter,
            color=config.col_equipos,
            title = "Presión del carter (mmH₂O) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_2_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )
        
        p_carter_min = df_selected[config.col_p_carter].min() 

        fig_2_1.add_hrect(y0=p_carter_min, y1=config.p_carter_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_2_1.add_hline(y=config.p_carter_max, line_dash="dash", line_color="red")
    
        fig_2_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_2_1, use_container_width=True, key="graph_p_carter")

    with col_2_2:
        
        fig_2_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_temp_radiador,
            color = config.col_equipos,
            title="▲ Temperatura Refrigerante en Radiador por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_2_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        temp_rad_max = df_selected[config.col_temp_radiador].max() 

        fig_2_2.add_hrect(y0=config.temp_rad_min, y1 = temp_rad_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_2_2.add_hline(y=config.temp_rad_min, line_dash="dash", line_color="red")
    
        fig_2_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_2_2, use_container_width=True, key="graph_temp_radiador")

    st.markdown("#### - Condición del aceite")

    col_3_1, col_3_2, col_3_3, col_3_4 = st.columns(4, gap="small")

    with col_3_1:

        fig_3_1 = px.line(
            df_selected, 
            x= config.col_horometro, 
            y= config.col_viscosidad,
            color=config.col_equipos,
            title = "Viscosidad por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_3_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )
        
        fig_3_1.add_hrect(y0=config.visc_min, y1=config.visc_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_3_1.add_hline(y=config.visc_min, line_dash="dash", line_color="red")
        fig_3_1.add_hline(y=config.visc_max, line_dash="dash", line_color="red")
    
        fig_3_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_3_1, use_container_width=True, key="graph_viscosidad")
    
    with col_3_2:

        fig_3_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_oxidacion,
            color = config.col_equipos,
            title="Oxidación por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_3_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        oxidacion_min = df_selected[config.col_oxidacion].min() 

        fig_3_2.add_hrect(y0=oxidacion_min, y1 = config.oxidacion_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_3_2.add_hline(y=config.oxidacion_max, line_dash="dash", line_color="red")
    
        fig_3_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_3_2, use_container_width=True, key="graph_oxidacion")
    
    with col_3_3:

        fig_3_3 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_sulfatacion,
            color = config.col_equipos,
            title="Sulfatación por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_3_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        sulfatacion_min = df_selected[config.col_sulfatacion].min() 

        fig_3_3.add_hrect(y0=sulfatacion_min, y1 = config.sulfatacion_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_3_3.add_hline(y=config.sulfatacion_max, line_dash="dash", line_color="red")
    
        fig_3_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_3_3, use_container_width=True, key="graph_sulfatacion")
    
    with col_3_4:

        fig_3_4 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_nitratacion,
            color = config.col_equipos,
            title="Nitratación por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_3_4.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        nitratacion_min = df_selected[config.col_nitratacion].min() 

        fig_3_4.add_hrect(y0=nitratacion_min, y1 = config.nitratacion_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_3_4.add_hline(y=config.nitratacion_max, line_dash="dash", line_color="red")
    
        fig_3_4.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_3_4, use_container_width=True, key="graph_nitratacion")

    col_4_1, col_4_2, col_4_3 = st.columns(3, gap="small")

    with col_4_1:

        fig_4_1 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_tbn,
            color = config.col_equipos,
            title="TBN por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_4_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        hollin_max = df_selected[config.col_tbn].max() 

        fig_4_1.add_hrect(y0=config.tbn_min, y1 = hollin_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_4_1.add_hline(y=config.tbn_min, line_dash="dash", line_color="red")
    
        fig_4_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_4_1, use_container_width=True, key="graph_tbn")
    
    with col_4_2:

        fig_4_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_hollin,
            color = config.col_equipos,
            title="Hollín (%) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_4_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        hollin_min = df_selected[config.col_hollin].min() 

        fig_4_2.add_hrect(y0=hollin_min, y1 = config.hollin_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_4_2.add_hline(y=config.hollin_max, line_dash="dash", line_color="red")
    
        fig_4_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_4_2, use_container_width=True, key="graph_hollin")
    
    with col_4_3:

        fig_4_3 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_pq,
            color = config.col_equipos,
            title="Indice de Particulas Ferrosas (PQ) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_4_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        pq_min = df_selected[config.col_pq].min() 

        fig_4_3.add_hrect(y0=pq_min, y1 = config.pq_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_4_3.add_hline(y=config.pq_max, line_dash="dash", line_color="red")
    
        fig_4_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_4_3, use_container_width=True, key="graph_pq")

    st.markdown("#### - Contaminación (o elementos/propiedades contaminantes)")

    col_5_1, col_5_2, col_5_3 = st.columns(3, gap="small")

    with col_5_1:

        fig_5_1 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_agua,
            color = config.col_equipos,
            title="Agua por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_5_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        agua_min = df_selected[config.col_agua].min() 

        fig_5_1.add_hrect(y0=agua_min, y1 = config.agua_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_5_1.add_hline(y=config.agua_max, line_dash="dash", line_color="red")
    
        fig_5_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_5_1, use_container_width=True, key="graph_agua")

    with col_5_2:

        fig_5_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_diesel,
            color = config.col_equipos,
            title="Diesel por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_5_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        diesel_min = df_selected[config.col_diesel].min() 

        fig_5_2.add_hrect(y0=diesel_min, y1 = config.diesel_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_5_2.add_hline(y=config.diesel_max, line_dash="dash", line_color="red")
    
        fig_5_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_5_2, use_container_width=True, key="graph_diesel")


    with col_5_3:

        fig_5_3 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_silicio,
            color = config.col_equipos,
            title="Silicio por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_5_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        silicio_min = df_selected[config.col_silicio].min() 

        fig_5_3.add_hrect(y0=silicio_min, y1 = config.silicio_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_5_3.add_hline(y=config.silicio_max, line_dash="dash", line_color="red")
    
        fig_5_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_5_3, use_container_width=True, key="graph_silicio")

    col_6_1, col_6_2, col_6_3 = st.columns(3, gap="small")

    with col_6_1:

        fig_6_1 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_b,
            color = config.col_equipos,
            title="Boro (B) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_6_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        b_min = df_selected[config.col_b].min() 

        fig_6_1.add_hrect(y0=b_min, y1 = config.b_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_6_1.add_hline(y=config.b_max, line_dash="dash", line_color="red")
    
        fig_6_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_6_1, use_container_width=True, key="graph_boro")

    with col_6_2:

        fig_6_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_na,
            color = config.col_equipos,
            title="Sodio (Na) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_6_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        na_min = df_selected[config.col_na].min() 

        fig_6_2.add_hrect(y0=na_min, y1 = config.na_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_6_2.add_hline(y=config.na_max, line_dash="dash", line_color="red")
    
        fig_6_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_6_2, use_container_width=True, key="graph_na")


    with col_6_3:

        fig_6_3 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_k,
            color = config.col_equipos,
            title="Potasio (K) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_6_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        k_min = df_selected[config.col_k].min() 

        fig_6_3.add_hrect(y0=k_min, y1 = config.k_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_6_3.add_hline(y=config.k_max, line_dash="dash", line_color="red")
    
        fig_6_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_6_3, use_container_width=True, key="graph_k")

    st.markdown("#### - Elementos de desgaste (wear metals)")

    col_7_1, col_7_2, col_7_3, col_7_4 = st.columns(4, gap="small")

    with col_7_1:

        fig_7_1 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_fe,
            color = config.col_equipos,
            title="Fe por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_7_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        fe_min = df_selected[config.col_fe].min() 

        fig_7_1.add_hrect(y0=fe_min, y1 = config.fe_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_7_1.add_hline(y=config.fe_max, line_dash="dash", line_color="red")
    
        fig_7_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_7_1, use_container_width=True, key="graph_fe")
    
    with col_7_2:

        fig_7_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_cr,
            color = config.col_equipos,
            title="Cr por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_7_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        cr_min = df_selected[config.col_cr].min() 

        fig_7_2.add_hrect(y0=cr_min, y1 = config.cr_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_7_2.add_hline(y=config.cr_max, line_dash="dash", line_color="red")
    
        fig_7_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_7_2, use_container_width=True, key="graph_cr")
    
    with col_7_3:

        fig_7_3 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_pb,
            color = config.col_equipos,
            title="Pb por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_7_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        pb_min = df_selected[config.col_pb].min() 

        fig_7_3.add_hrect(y0=pb_min, y1 = config.pb_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_7_3.add_hline(y=config.pb_max, line_dash="dash", line_color="red")
    
        fig_7_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_7_3, use_container_width=True, key="graph_pb")
    
    with col_7_4:

        fig_7_4 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_cu,
            color = config.col_equipos,
            title="Cu por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_7_4.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        cu_min = df_selected[config.col_cu].min() 

        fig_7_4.add_hrect(y0=cu_min, y1 = config.cu_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_7_4.add_hline(y=config.cu_max, line_dash="dash", line_color="red")
    
        fig_7_4.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_7_4, use_container_width=True, key="graph_cu")
    
    col_8_1, col_8_2, col_8_3, col_8_4 = st.columns(4, gap="small")

    with col_8_1:

        fig_8_1 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_sn,
            color = config.col_equipos,
            title="Sn por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_8_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        sn_min = df_selected[config.col_sn].min() 

        fig_8_1.add_hrect(y0=sn_min, y1 = config.sn_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_8_1.add_hline(y=config.sn_max, line_dash="dash", line_color="red")
    
        fig_8_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_8_1, use_container_width=True, key="graph_sn")
    
    with col_8_2:

        fig_8_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_al,
            color = config.col_equipos,
            title="Al por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_8_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        al_min = df_selected[config.col_al].min() 

        fig_8_2.add_hrect(y0=al_min, y1 = config.al_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_8_2.add_hline(y=config.al_max, line_dash="dash", line_color="red")
    
        fig_8_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_8_2, use_container_width=True, key="graph_al")
    
    with col_8_3:

        fig_8_3 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_ni,
            color = config.col_equipos,
            title="Ni por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_8_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        ni_min = df_selected[config.col_ni].min() 

        fig_8_3.add_hrect(y0=ni_min, y1 = config.ni_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_8_3.add_hline(y=config.ni_max, line_dash="dash", line_color="red")
    
        fig_8_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_8_3, use_container_width=True, key="graph_ni")
    
    with col_8_4:

        fig_8_4 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_ag,
            color = config.col_equipos,
            title="Ag por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_8_4.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        ag_min = df_selected[config.col_ag].min() 

        fig_8_4.add_hrect(y0=ag_min, y1 = config.ag_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_8_4.add_hline(y=config.ag_max, line_dash="dash", line_color="red")
    
        fig_8_4.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_8_4, use_container_width=True, key="graph_ag")

    col_9_1, col_9_2, col_9_3, col_9_4 = st.columns(4, gap="small")

    with col_9_1:

        fig_9_1 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_ti,
            color = config.col_equipos,
            title="Titanio (Ti) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_9_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        ti_min = df_selected[config.col_ti].min() 

        fig_9_1.add_hrect(y0=ti_min, y1 = config.ti_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_9_1.add_hline(y=config.ti_max, line_dash="dash", line_color="red")
    
        fig_9_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_9_1, use_container_width=True, key="graph_ti")
    
    with col_9_2:

        fig_9_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_v,
            color = config.col_equipos,
            title="Vanadio (V) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_9_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        v_min = df_selected[config.col_v].min() 

        fig_9_2.add_hrect(y0=v_min, y1 = config.v_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_9_2.add_hline(y=config.v_max, line_dash="dash", line_color="red")
    
        fig_9_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_9_2, use_container_width=True, key="graph_v")
    
    with col_9_3:

        fig_9_3 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_mn,
            color = config.col_equipos,
            title="Manganeso (mn) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_9_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        mn_min = df_selected[config.col_mn].min() 

        fig_9_3.add_hrect(y0=mn_min, y1 = config.mn_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_9_3.add_hline(y=config.mn_max, line_dash="dash", line_color="red")
    
        fig_9_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_9_3, use_container_width=True, key="graph_mn")
    
    with col_9_4:

        fig_9_4 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_cd,
            color = config.col_equipos,
            title="Cadmio (Cd) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_9_4.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        cd_min = df_selected[config.col_cd].min() 

        fig_9_4.add_hrect(y0=cd_min, y1 = config.cd_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_9_4.add_hline(y=config.cd_max, line_dash="dash", line_color="red")
    
        fig_9_4.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_9_4, use_container_width=True, key="graph_cd")
    
    st.markdown("#### - Elementos aditivos")

    col_10_1, col_10_2, col_10_3 = st.columns(3, gap="small")

    with col_10_1:

        fig_10_1 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_mg,
            color = config.col_equipos,
            title="Magnesium (Mg) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_10_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        mq_max = df_selected[config.col_mg].max() 

        fig_10_1.add_hrect(y0=config.mg_min, y1 = mq_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_10_1.add_hline(y=config.mg_min, line_dash="dash", line_color="red")
    
        fig_10_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_10_1, use_container_width=True, key="graph_mg")
    
    with col_10_2:

        fig_10_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_ca,
            color = config.col_equipos,
            title="Calcium (Ca) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_10_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        ca_max = df_selected[config.col_ca].max() 

        fig_10_2.add_hrect(y0=config.ca_min, y1 = ca_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_10_2.add_hline(y=config.ca_min, line_dash="dash", line_color="red")
    
        fig_10_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_10_2, use_container_width=True, key="graph_ca")
    
    with col_10_3:

        fig_10_3 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_ba,
            color = config.col_equipos,
            title="Barium (Ba) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_10_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        ba_min = df_selected[config.col_ba].min() 

        fig_10_3.add_hrect(y0=ba_min, y1 = config.ba_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_10_3.add_hline(y=config.ba_max, line_dash="dash", line_color="red")
    
        fig_10_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_10_3, use_container_width=True, key="graph_ba")
    
    col_11_1, col_11_2, col_11_3 = st.columns(3, gap="small")

    with col_11_1:

        fig_11_1 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_p,
            color = config.col_equipos,
            title="Phosphorus (P) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_11_1.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        p_max = df_selected[config.col_mg].max() 

        fig_11_1.add_hrect(y0=config.p_min, y1 = p_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_11_1.add_hline(y=config.p_min, line_dash="dash", line_color="red")
    
        fig_11_1.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_11_1, use_container_width=True, key="graph_p")
    
    with col_11_2:

        fig_11_2 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_zn,
            color = config.col_equipos,
            title="Zinc (Zn) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_11_2.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        zn_max = df_selected[config.col_zn].max() 

        fig_11_2.add_hrect(y0=config.zn_min, y1 = zn_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_11_2.add_hline(y=config.zn_min, line_dash="dash", line_color="red")
    
        fig_11_2.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_11_2, use_container_width=True, key="graph_zn")
    
    with col_11_3:

        fig_11_3 = px.line(
            df_selected, 
            x = config.col_horometro, 
            y = config.col_mo,
            color = config.col_equipos,
            title="Molybdenum (Mo) por Horómetro",
            markers=True,
            color_discrete_sequence=["blue"]
        )

        fig_11_3.update_traces(
            selector=dict(name="Histórico"),
            line=dict(dash="dot", color="lightblue"),
            opacity = 0.8
        )

        mo_min = df_selected[config.col_mo].min() 

        fig_11_3.add_hrect(y0=mo_min, y1 = config.mo_max, fillcolor="green", opacity=0.1, line_width=0)
        fig_11_3.add_hline(y=config.mo_max, line_dash="dash", line_color="red")
    
        fig_11_3.update_layout(hovermode="x unified")
    
        st.plotly_chart(fig_11_3, use_container_width=True, key="graph_mo")

    # --- Tabla ---

    st.markdown("### Tabla General")

    ## Añadir estilos para la tabla

    df_filtered_styled = df_filtered.copy()

    df_filtered_styled = (df_filtered_styled.style
        .map(lambda val: 'background-color: #fff8e1' if (val <= config.visc_min or val > config.visc_max) else '', subset=[config.col_viscosidad])
        .map(lambda val: 'background-color: #fff8e1' if val <= config.temp_rad_min else '', subset=[config.col_temp_radiador])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.fe_max else '',subset=[config.col_fe] )
        .map(lambda val: 'background-color: #fff8e1' if (val <= config.cil_min or val > config.cil_max) else '', subset=[config.col_cil_1, config.col_cil_2, config.col_cil_3, config.col_cil_4])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.p_carter_max else '', subset=[config.col_p_carter] )
        .map(lambda val: 'background-color: #fff8e1' if val >= config.cr_max else '', subset=[config.col_cr])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.pb_max else '', subset=[config.col_pb])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.cu_max else '', subset=[config.col_cu])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.sn_max else '', subset=[config.col_sn])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.al_max else '', subset=[config.col_al])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.ni_max else '', subset=[config.col_ni])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.ag_max else '', subset=[config.col_ag])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.silicio_max else '', subset=[config.col_silicio])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.b_max else '', subset=[config.col_b])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.na_max else '', subset=[config.col_na])
        .map(lambda val: 'background-color: #fff8e1' if val <= config.mg_min else '', subset=[config.col_mg])
        .map(lambda val: 'background-color: #fff8e1' if val <= config.ca_min else '', subset=[config.col_ca])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.ba_max else '', subset=[config.col_ba])
        .map(lambda val: 'background-color: #fff8e1' if val <= config.p_min else '', subset=[config.col_p])
        .map(lambda val: 'background-color: #fff8e1' if val <= config.zn_min else '', subset=[config.col_zn])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.mo_max else '', subset=[config.col_mo])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.ti_max else '', subset=[config.col_ti])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.v_max else '', subset=[config.col_v])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.mn_max else '', subset=[config.col_mn])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.cd_max else '', subset=[config.col_cd])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.k_max else '', subset=[config.col_k])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.diesel_max else '', subset=[config.col_diesel])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.agua_max else '', subset=[config.col_agua])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.oxidacion_max else '', subset=[config.col_oxidacion])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.sulfatacion_max else '', subset=[config.col_sulfatacion])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.nitratacion_max else '', subset=[config.col_nitratacion])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.hollin_max else '', subset=[config.col_hollin])
        .map(lambda val: 'background-color: #fff8e1' if val <= config.tbn_min else '', subset=[config.col_tbn])
        .map(lambda val: 'background-color: #fff8e1' if val >= config.pq_max else '', subset=[config.col_pq])
        .format({
            config.col_viscosidad: '{:.2f}',
            config.col_temp_radiador: '{:.2f}',
            config.col_fe: '{:.2f}',
            config.col_p_carter: '{:.2f}',
            config.col_cr: '{:.2f}',
            config.col_pb: '{:.2f}',
            config.col_cu: '{:.2f}',
            config.col_sn: '{:.2f}',
            config.col_al: '{:.2f}',
            config.col_ni: '{:.2f}',
            config.col_ag: '{:.2f}',
            config.col_silicio: '{:.2f}',
            config.col_b: '{:.2f}',
            config.col_na: '{:.2f}',
            config.col_mg: '{:.2f}',
            config.col_ca: '{:.2f}',
            config.col_ba: '{:.2f}',
            config.col_p: '{:.2f}',
            config.col_zn: '{:.2f}',
            config.col_mo: '{:.2f}',
            config.col_ti: '{:.2f}',
            config.col_v: '{:.2f}',
            config.col_mn: '{:.2f}',
            config.col_cd: '{:.2f}',
            config.col_k: '{:.2f}',
            config.col_diesel: '{:.2f}',
            config.col_agua: '{:.2f}',
            config.col_oxidacion: '{:.2f}',
            config.col_sulfatacion: '{:.2f}',
            config.col_nitratacion: '{:.2f}',
            config.col_hollin: '{:.2f}',
            config.col_tbn: '{:.2f}',
            config.col_pq: '{:.2f}',
            config.col_cil_1: '{:.2f}',
            config.col_cil_2: '{:.2f}',
            config.col_cil_3: '{:.2f}',
            config.col_cil_4: '{:.2f}',
            config.col_fecha: '{:%Y-%m-%d}',
        })
    )

    ## Mostrar tabla

    selection = st.dataframe(
        df_filtered_styled,
        use_container_width=True,
        hide_index=True,
        key="tabla_compilado_encuentas",
        selection_mode="single-row",
        on_select="rerun"
    )

    ## AI Chat 

    df_filtered_ai = df_filtered.copy()

    #render_ai_chat_esp(df_filtered=df_filtered_ai,latest_row=latest_row,config=config,params=params,anomalies_by_group=anomalies_by_group,groups_order=groups_order)
