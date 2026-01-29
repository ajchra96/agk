import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

#from ai import render_ai_chat_esp
from data import create_indicator_chart, get_worst_severity, enrich_anomalies_with_severity, compute_row_metrics, style_row
from data import latest_anomalies
from data import SEVERITY, SEVERITY_PRIORITY_ORDER_ASC, PARAMS, PARAM_GROUPS
from data import df, df_completo, config, df_acciones

@st.fragment
def render_especifico_tab():

    st.header("Análisis de Condición Motores Diesel por Equipo")

    # TODO: Filtro

    ## Prepare equipment list with severity-based emoji + sorting

    equipo_data = []
    all_equipos = sorted(df[config.col_equipos].dropna().unique())

    for eq in all_equipos:
        anomalies = latest_anomalies.get(eq, [])
        
        # Get worst severity priority (0 = no issue / green)
        worst_priority = get_worst_severity(anomalies, df_acciones)

        # Use centralised emoji from SEVERITY
        emoji = SEVERITY[worst_priority]["emoji"]

        equipo_data.append((worst_priority, emoji, eq))  # priority first for sorting

    ## Prepare selectbox data (now ordered worst → best)
    display_labels = [f"{emoji} {eq}" for _, emoji, eq in equipo_data]
    real_equipos   = [eq for _, _, eq in equipo_data]

    ## Selectbox – defaults to the most critical equipment (now index=0 is truly the worst)

    selected_idx = st.selectbox(
        label = "Equipo",
        options = range(len(real_equipos)),
        format_func = lambda i: display_labels[i],
        index = 0,
        key = "filtro_equipos_especifico"
    )
    selected_equipo = real_equipos[selected_idx]

    ## Resultado de la data filtrada

    df_filtered = df.copy()
    df_filtered = df_filtered[df_filtered[config.col_equipos] == selected_equipo]

    # TODO: Resumen de Condición de la Última Toma

    st.markdown("### Resumen de Condición de la Última Toma")

    ## Get anomalies for this equipment

    anomalies = latest_anomalies.get(selected_equipo, [])
    enriched_anomalies = enrich_anomalies_with_severity(anomalies, df_acciones)

    if anomalies:

        ## Mensaje si hay errores

        st.error("⚠️ Anomalías detectadas:")

        ## Group by category
        by_group = {}
        for anomaly in enriched_anomalies:
            g = anomaly["grupo"]
            by_group.setdefault(g, []).append(anomaly)

        ## Show groups in the original params order
        for group in PARAM_GROUPS:
            violations = by_group.get(group, [])
            if not violations:
                continue

            st.markdown(f"##### Anomalías en {group} ({len(violations)})")

            for v in violations:
                ## Lookup in acciones
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

                ## Mostrar mensaje
                prio = v.get("priority", 0)
                emoji = SEVERITY[prio]["emoji"]

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

    # TODO: Evolución estado del equipo

    st.markdown("### Evolución estado del equipo")

    ## Hisotrico de salud del equipo

    equip_df = df[df[config.col_equipos] == selected_equipo].sort_values(config.col_horometro).reset_index(drop=True)

    metrics_eq = equip_df.apply(
        lambda row: compute_row_metrics(row, PARAMS, df_acciones),
        axis=1
    )
    equip_df["max_priority"] = [m[0] for m in metrics_eq]
    equip_df["anomaly_count"] = [m[1] for m in metrics_eq]
    equip_df["enriched"] = [m[2] for m in metrics_eq]

    ## Grapgh 1: Evolucioón historica de salud

    fig_main = go.Figure()

    ### Stepped lines
    for i in range(len(equip_df) - 1):
        p = equip_df.iloc[i]["max_priority"]
        fig_main.add_trace(go.Scatter(
            x = [equip_df.iloc[i][config.col_horometro], equip_df.iloc[i+1][config.col_horometro]],
            y = [p, p],
            mode = "lines",
            line = dict(color=SEVERITY[p]["color"], width=6),
            showlegend = False
        ))
    fig_main.add_trace(go.Scatter(
        x = equip_df[config.col_horometro],
        y = equip_df["max_priority"],
        mode = "markers+text",
        marker = dict(color=[SEVERITY[p]["color"] for p in equip_df["max_priority"]], size=12),
        text = [SEVERITY[p]["label"] for p in equip_df["max_priority"]],
        textposition = "top center",
        showlegend = False
    ))
    fig_main.update_layout(
        title = f"Evolución de severidad máxima – {selected_equipo}",
        xaxis_title = "Horómetro",
        yaxis = dict(
            tickvals=SEVERITY_PRIORITY_ORDER_ASC,
            ticktext=[SEVERITY[p]["label"] for p in SEVERITY_PRIORITY_ORDER_ASC]
        ),
        showlegend = False
    )
    st.plotly_chart(fig_main, use_container_width=True)

    ## Grapgh 2: Cuenta por tipo de anomalía

    stacked_data = []

    for _, row in equip_df.iterrows():
        enriched = row["enriched"]
        if enriched:
            df_g = pd.DataFrame(enriched)
            counts = df_g["severidad"].value_counts()
            for severidad_name, c in counts.items():
                stacked_data.append({"horometro": row[config.col_horometro], "severidad": severidad_name, "count": c})

    if stacked_data:
        df_stacked = pd.DataFrame(stacked_data)

        # Color map by severity name (Crítico, Precaución, Atención)

        color_map_severidad = {
            SEVERITY[p]["name"]: SEVERITY[p]["color"]
            for p in SEVERITY if p > 0
        }

        fig_stacked = px.bar(
            df_stacked,
            x = "horometro",
            y = "count",
            color = "severidad",
            title = "Total de Anomalías por nivel de severidad",
            barmode = "stack",
            color_discrete_map = color_map_severidad,
            category_orders = {"severidad": [SEVERITY[p]["name"] for p in SEVERITY_PRIORITY_ORDER_ASC if p > 0]}
        )
        fig_stacked.update_traces(
            hovertemplate = "Nivel: %{fullData.name}<br>Nº anomalías: %{y}<br>Horómetro: %{x}<extra></extra>"
        )
        fig_stacked.update_layout(
            xaxis_title = "Horómetro",
            yaxis_title = "Total de Anomalías",
            showlegend = False
        )
        
        st.plotly_chart(fig_stacked, use_container_width=True)

    # TODO: Gráficos por indicador

    st.markdown("### Gráficos por indicador")

    ## Preparación de df_selected

    min_horo = df_filtered[config.col_horometro].min()
    max_horo = df_filtered[config.col_horometro].max()

    df_selected = df_completo[
        (df_completo[config.col_equipos] == selected_equipo) |
        (df_completo[config.col_equipos] == "Histórico")
    ].sort_values(config.col_horometro)

    df_selected = df_selected[
        (df_selected[config.col_horometro] >= min_horo) &
        (df_selected[config.col_horometro] <= max_horo)
    ]

    ## ==== Datos operativos / físicos ====
    st.markdown("#### - Datos operativos / físicos de la muestra")

    cols1 = st.columns(4, gap="small")
    cols2 = st.columns(2, gap="small")

    plots_operativos = [
        {"container": cols1[0], "y": config.col_cil_1, "title": "Cilindro 1 (BAR) por Horómetro", "st_key": "graph_cil_1", "min_fixed": config.cil_min, "max_fixed": config.cil_max},
        {"container": cols1[1], "y": config.col_cil_2, "title": "Cilindro 2 (BAR) por Horómetro", "st_key": "graph_cil_2", "min_fixed": config.cil_min, "max_fixed": config.cil_max},
        {"container": cols1[2], "y": config.col_cil_3, "title": "Cilindro 3 (BAR) por Horómetro", "st_key": "graph_cil_3", "min_fixed": config.cil_min, "max_fixed": config.cil_max},
        {"container": cols1[3], "y": config.col_cil_4, "title": "Cilindro 4 (BAR) por Horómetro", "st_key": "graph_cil_4", "min_fixed": config.cil_min, "max_fixed": config.cil_max},
        {"container": cols2[0], "y": config.col_p_carter, "title": "Presión del carter (mmH₂O) por Horómetro", "st_key": "graph_p_carter", "use_data_min": True, "max_fixed": config.p_carter_max},
        {"container": cols2[1], "y": config.col_temp_radiador, "title": "▲ Temperatura Refrigerante en Radiador por Horómetro", "st_key": "graph_temp_radiador", "min_fixed": config.temp_rad_min, "use_data_max": True},
    ]

    for p in plots_operativos:
        with p["container"]:
            chart_params = {
                "min_fixed": p.get("min_fixed"),
                "max_fixed": p.get("max_fixed"),
                "use_data_min": p.get("use_data_min", False),
                "use_data_max": p.get("use_data_max", False),
            }
            fig = create_indicator_chart(
                df_selected,
                p["y"],
                p["title"],
                **chart_params
            )
            st.plotly_chart(fig, use_container_width=True, key=p["st_key"])

    ## ==== Condición del aceite ====
    st.markdown("#### - Condición del aceite")

    cols3 = st.columns(4, gap="small")
    cols4 = st.columns(3, gap="small")

    plots_aceite = [
        {"container": cols3[0], "y": config.col_viscosidad, "title": "Viscosidad por Horómetro", "st_key": "graph_viscosidad", "min_fixed": config.visc_min, "max_fixed": config.visc_max},
        {"container": cols3[1], "y": config.col_oxidacion, "title": "Oxidación por Horómetro", "st_key": "graph_oxidacion", "use_data_min": True, "max_fixed": config.oxidacion_max},
        {"container": cols3[2], "y": config.col_sulfatacion, "title": "Sulfatación por Horómetro", "st_key": "graph_sulfatacion", "use_data_min": True, "max_fixed": config.sulfatacion_max},
        {"container": cols3[3], "y": config.col_nitratacion, "title": "Nitratación por Horómetro", "st_key": "graph_nitratacion", "use_data_min": True, "max_fixed": config.nitratacion_max},
        {"container": cols4[0], "y": config.col_tbn, "title": "TBN por Horómetro", "st_key": "graph_tbn", "min_fixed": config.tbn_min, "use_data_max": True},
        {"container": cols4[1], "y": config.col_hollin, "title": "Hollín (%) por Horómetro", "st_key": "graph_hollin", "use_data_min": True, "max_fixed": config.hollin_max},
        {"container": cols4[2], "y": config.col_pq, "title": "Indice de Particulas Ferrosas (PQ) por Horómetro", "st_key": "graph_pq", "use_data_min": True, "max_fixed": config.pq_max},
    ]

    for p in plots_aceite:
        with p["container"]:
            chart_params = {
                "min_fixed": p.get("min_fixed"),
                "max_fixed": p.get("max_fixed"),
                "use_data_min": p.get("use_data_min", False),
                "use_data_max": p.get("use_data_max", False),
            }
            fig = create_indicator_chart(
                df_selected,
                p["y"],
                p["title"],
                **chart_params
            )
            st.plotly_chart(fig, use_container_width=True, key=p["st_key"])

    ##  ==== Contaminación ====
    st.markdown("#### - Contaminación (o elementos/propiedades contaminantes)")

    cols5 = st.columns(3, gap="small")
    cols6 = st.columns(3, gap="small")

    plots_contaminacion = [
        {"container": cols5[0], "y": config.col_agua, "title": "Agua por Horómetro", "st_key": "graph_agua", "use_data_min": True, "max_fixed": config.agua_max},
        {"container": cols5[1], "y": config.col_diesel, "title": "Diesel por Horómetro", "st_key": "graph_diesel", "use_data_min": True, "max_fixed": config.diesel_max},
        {"container": cols5[2], "y": config.col_silicio, "title": "Silicio por Horómetro", "st_key": "graph_silicio", "use_data_min": True, "max_fixed": config.silicio_max},
        {"container": cols6[0], "y": config.col_b, "title": "Boro (B) por Horómetro", "st_key": "graph_boro", "use_data_min": True, "max_fixed": config.b_max},
        {"container": cols6[1], "y": config.col_na, "title": "Sodio (Na) por Horómetro", "st_key": "graph_na", "use_data_min": True, "max_fixed": config.na_max},
        {"container": cols6[2], "y": config.col_k, "title": "Potasio (K) por Horómetro", "st_key": "graph_k", "use_data_min": True, "max_fixed": config.k_max},
    ]

    for p in plots_contaminacion:
        with p["container"]:
            chart_params = {
                "min_fixed": p.get("min_fixed"),
                "max_fixed": p.get("max_fixed"),
                "use_data_min": p.get("use_data_min", False),
                "use_data_max": p.get("use_data_max", False),
            }
            fig = create_indicator_chart(
                df_selected,
                p["y"],
                p["title"],
                **chart_params
            )
            st.plotly_chart(fig, use_container_width=True, key=p["st_key"])

    ## ==== Elementos de desgaste (wear metals) ====
    st.markdown("#### - Elementos de desgaste (wear metals)")

    cols7 = st.columns(4, gap="small")
    cols8 = st.columns(4, gap="small")
    cols9 = st.columns(4, gap="small")

    plots_desgaste = [
        {"container": cols7[0], "y": config.col_fe, "title": "Fe por Horómetro", "st_key": "graph_fe", "use_data_min": True, "max_fixed": config.fe_max},
        {"container": cols7[1], "y": config.col_cr, "title": "Cr por Horómetro", "st_key": "graph_cr", "use_data_min": True, "max_fixed": config.cr_max},
        {"container": cols7[2], "y": config.col_pb, "title": "Pb por Horómetro", "st_key": "graph_pb", "use_data_min": True, "max_fixed": config.pb_max},
        {"container": cols7[3], "y": config.col_cu, "title": "Cu por Horómetro", "st_key": "graph_cu", "use_data_min": True, "max_fixed": config.cu_max},
        {"container": cols8[0], "y": config.col_sn, "title": "Sn por Horómetro", "st_key": "graph_sn", "use_data_min": True, "max_fixed": config.sn_max},
        {"container": cols8[1], "y": config.col_al, "title": "Al por Horómetro", "st_key": "graph_al", "use_data_min": True, "max_fixed": config.al_max},
        {"container": cols8[2], "y": config.col_ni, "title": "Ni por Horómetro", "st_key": "graph_ni", "use_data_min": True, "max_fixed": config.ni_max},
        {"container": cols8[3], "y": config.col_ag, "title": "Ag por Horómetro", "st_key": "graph_ag", "use_data_min": True, "max_fixed": config.ag_max},
        {"container": cols9[0], "y": config.col_ti, "title": "Titanio (Ti) por Horómetro", "st_key": "graph_ti", "use_data_min": True, "max_fixed": config.ti_max},
        {"container": cols9[1], "y": config.col_v, "title": "Vanadio (V) por Horómetro", "st_key": "graph_v", "use_data_min": True, "max_fixed": config.v_max},
        {"container": cols9[2], "y": config.col_mn, "title": "Manganeso (mn) por Horómetro", "st_key": "graph_mn", "use_data_min": True, "max_fixed": config.mn_max},
        {"container": cols9[3], "y": config.col_cd, "title": "Cadmio (Cd) por Horómetro", "st_key": "graph_cd", "use_data_min": True, "max_fixed": config.cd_max},
    ]

    for p in plots_desgaste:
        with p["container"]:
            chart_params = {
                "min_fixed": p.get("min_fixed"),
                "max_fixed": p.get("max_fixed"),
                "use_data_min": p.get("use_data_min", False),
                "use_data_max": p.get("use_data_max", False),
            }
            fig = create_indicator_chart(
                df_selected,
                p["y"],
                p["title"],
                **chart_params
            )
            st.plotly_chart(fig, use_container_width=True, key=p["st_key"])

    ## ==== Elementos aditivos ====
    st.markdown("#### - Elementos aditivos")

    cols10 = st.columns(3, gap="small")
    cols11 = st.columns(3, gap="small")

    plots_aditivos = [
        {"container": cols10[0], "y": config.col_mg, "title": "Magnesium (Mg) por Horómetro", "st_key": "graph_mg", "min_fixed": config.mg_min, "use_data_max": True},
        {"container": cols10[1], "y": config.col_ca, "title": "Calcium (Ca) por Horómetro", "st_key": "graph_ca", "min_fixed": config.ca_min, "use_data_max": True},
        {"container": cols10[2], "y": config.col_ba, "title": "Barium (Ba) por Horómetro", "st_key": "graph_ba", "use_data_min": True, "max_fixed": config.ba_max},
        {"container": cols11[0], "y": config.col_p, "title": "Phosphorus (P) por Horómetro", "st_key": "graph_p", "min_fixed": config.p_min, "use_data_max": True},
        {"container": cols11[1], "y": config.col_zn, "title": "Zinc (Zn) por Horómetro", "st_key": "graph_zn", "min_fixed": config.zn_min, "use_data_max": True},
        {"container": cols11[2], "y": config.col_mo, "title": "Molybdenum (Mo) por Horómetro", "st_key": "graph_mo", "use_data_min": True, "max_fixed": config.mo_max},
    ]

    for p in plots_aditivos:
        with p["container"]:
            chart_params = {
                "min_fixed": p.get("min_fixed"),
                "max_fixed": p.get("max_fixed"),
                "use_data_min": p.get("use_data_min", False),
                "use_data_max": p.get("use_data_max", False),
            }
            fig = create_indicator_chart(
                df_selected,
                p["y"],
                p["title"],
                **chart_params
            )
            st.plotly_chart(fig, use_container_width=True, key=p["st_key"])

    # TODO: Tabla 

    st.markdown("### Tabla General")

    ## Añadir estilos y formato para la tabla

    df_filtered_styled = df_filtered.copy()
    df_filtered_styled = df_filtered_styled.sort_values(config.col_horometro, ascending=False).reset_index(drop=True)

    numeric_cols = [p["col"] for p in PARAMS]

    format_dict = {col: '{:.2f}' for col in numeric_cols}
    format_dict[config.col_fecha] = '{:%Y-%m-%d}'

    df_filtered_styled = (df_filtered_styled.style
        .apply(style_row, params=PARAMS, axis=1)
        .format(format_dict)
    )

    ## Mostrar tabla

    st.dataframe(
        df_filtered_styled,
        use_container_width=True,
        hide_index=True,
        key="tabla_compilado_encuentas",
        selection_mode="single-row",
        on_select="rerun"
    )

    # TODO: AI Chat 

    df_filtered_ai = df_filtered.copy()
    latest_row = df_filtered_ai.iloc[-1]

    #render_ai_chat_esp(df_filtered=df_filtered_ai,latest_row=latest_row,config=config,params=params,anomalies_by_group=anomalies_by_group,groups_order=groups_order)
