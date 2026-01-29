import streamlit as st
import pandas as pd
from types import SimpleNamespace
import plotly.express as px

# ------------------- Globals (inicialmente None) -------------------
df = None
df_historico = None
df_completo = None
config = None
df_acciones = None
PARAMS = None
PARAM_GROUPS = None
latest_df = None
latest_anomalies = None

# ------------------- Carga de datos base -------------------
def motores_base(uploaded_file):
    if uploaded_file is None:
        return None, None, None, None
    
    config = SimpleNamespace(
        # Columnas
        col_equipos = "Equipo",
        col_fecha = "Fecha",
        col_horometro = "Horometro",
        col_cil_1 = "CIL1",
        col_cil_2 = "CIL2",
        col_cil_3 = "CIL3",
        col_cil_4 = "CIL4",
        col_p_carter = "Blow by Carter",
        col_temp_radiador = "▲ Temp Radiador",
        col_viscosidad = "Viscosidad",
        col_fe = "Fe",
        col_cr = "Cr",
        col_pb = "Pb",
        col_cu = "Cu",
        col_sn = "Sn",
        col_al = "Al",
        col_ni = "Ni",
        col_ag = "Ag",
        col_silicio = "Silicio",
        col_b = "B",
        col_na = "Na",
        col_mg = "Mg",
        col_ca = "Ca",
        col_ba = "Ba",
        col_p = "P",
        col_zn = "Zn",
        col_mo = "Mo",
        col_ti = "Ti",
        col_v = "V",
        col_mn = "Mn",
        col_cd = "Cd",
        col_k = "K",
        col_diesel = "Diesel",
        col_agua = "Agua",
        col_oxidacion = "Oxidación",
        col_sulfatacion = "Sulfatación",
        col_nitratacion = "Nitracion",
        col_hollin = "Hollin",
        col_tbn = "TBN",
        col_pq = "PQ",
        # Límites
        cil_min = 16,
        cil_max = 35,
        p_carter_max = 30,
        temp_rad_min = 7,
        visc_min = 13,
        visc_max = 17,
        fe_max = 70,
        cr_max = 10,
        pb_max = 20,
        cu_max = 25,
        sn_max = 10,
        al_max = 10,
        ni_max = 5,
        ag_max = 2,
        silicio_max = 15,
        b_max = 50,
        na_max = 30,
        mg_min = 10,
        ca_min = 2200,
        ba_max = 2,
        p_min = 800,
        zn_min = 700,
        mo_max = 100,
        ti_max = 2,
        v_max = 1,
        mn_max = 5,
        cd_max = 1,
        k_max = 5,
        diesel_max = 3,
        agua_max = 0.2,
        oxidacion_max = 20,
        sulfatacion_max = 20,
        nitratacion_max = 20,
        hollin_max = 1.8,
        tbn_min = 5,
        pq_max = 50,
    )

    df = pd.read_excel(uploaded_file, sheet_name="DATOS")

    variables = [
        value for key, value in vars(config).items()
        if key.startswith('col_') and key not in ['col_equipos', 'col_horometro', 'col_fecha']
    ]

    df_historico = (
        df.groupby(config.col_horometro, as_index=False)[variables]
        .agg(['mean', 'count'])
        .round(2)
    )
    df_historico.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in df_historico.columns]
    rename_dict = {f"{var}_mean": var for var in variables}
    df_historico = df_historico.rename(columns=rename_dict)
    df_historico = df_historico.sort_values(config.col_horometro)
    df_historico[config.col_equipos] = "Histórico"

    df_completo = pd.concat([df, df_historico], ignore_index=True)

    return df, df_historico, df_completo, config


def acciones_base(uploaded_rules_file):
    if uploaded_rules_file is None:
        return None
    return pd.read_excel(uploaded_rules_file, sheet_name="REGLAS")


# ------------------- Helpers -------------------
@st.cache_data(ttl=3600)
def detect_anomalies(row, params):
    anomalies = []
    for p in params:
        name = p["name"]
        col = p["col"]
        min_val = p["min_val"]
        max_val = p["max_val"]
        group = p["group"]
        value = row.get(col)
        if pd.isna(value):
            continue

        tipo = None
        limite = None
        mensaje = None

        if min_val is not None and max_val is not None:
            if value < min_val:
                tipo = "BAJA"
                limite = min_val
                mensaje = f"por debajo del mínimo ({min_val:.2f})"
            elif value > max_val:
                tipo = "ALTA"
                limite = max_val
                mensaje = f"por encima del máximo ({max_val:.2f})"
        elif min_val is not None and value < min_val:
            tipo = "BAJA"
            limite = min_val
            mensaje = f"por debajo del mínimo ({min_val:.2f})"
        elif max_val is not None and value > max_val:
            tipo = "ALTA"
            limite = max_val
            mensaje = f"por encima del máximo ({max_val:.2f})"

        if tipo is not None:
            full_mensaje = f"{name}: {value:.2f} → {tipo.lower()} {mensaje}"
            anomalies.append({
                "name": name,
                "column": col,
                "value": value,
                "tipo": tipo,
                "limite": limite,
                "mensaje": full_mensaje,
                "grupo": group
            })
    return anomalies


@st.cache_data(ttl=3600)
def get_latest_anomalies(df, config, params):
    latest_idx = df.groupby(config.col_equipos)[config.col_horometro].idxmax()
    latest_df = df.loc[latest_idx]
    result = {}
    for _, row in latest_df.iterrows():
        equipo = row[config.col_equipos]
        anomalies = detect_anomalies(row, params)
        if anomalies:
            result[equipo] = anomalies
    return result


@st.cache_data(ttl=3600)
def enrich_anomalies_with_severity(anomalies, df_acciones):
    enriched = []
    name_to_priority = {info["name"]: info["priority"] for info in SEVERITY.values()}

    for anomaly in anomalies:
        match = df_acciones[
            (df_acciones["Indicador"] == anomaly["column"]) &
            (df_acciones["Tipo"].str.upper() == anomaly["tipo"])
        ]
        severidad = match.iloc[0].get("Severidad Típica", "Sano") if not match.empty else "Sano"
        priority = name_to_priority.get(severidad, 0)

        enriched_anomaly = anomaly.copy()
        enriched_anomaly["severidad"] = severidad
        enriched_anomaly["priority"] = priority
        enriched_anomaly["display_indicator"] = f"{anomaly['name']} ({anomaly['tipo'].capitalize()})"
        enriched.append(enriched_anomaly)

    return enriched


@st.cache_data(ttl=3600)
def get_worst_severity(anomalies, df_acciones):
    if not anomalies:
        return 0
    enriched = enrich_anomalies_with_severity(anomalies, df_acciones)
    return max(a["priority"] for a in enriched) if enriched else 0


def compute_row_metrics(row, params, df_acc):
    anomalies = detect_anomalies(row, params)
    enriched = enrich_anomalies_with_severity(anomalies, df_acc)
    max_priority = max((a["priority"] for a in enriched), default=0)
    anomaly_count = len(enriched)
    return max_priority, anomaly_count, enriched


def create_indicator_chart(df, y_col, title, min_fixed=None, max_fixed=None, use_data_min=False, use_data_max=False):
    fig = px.line(
        df,
        x=config.col_horometro,
        y=y_col,
        color=config.col_equipos,
        title=title,
        markers=True,
        color_discrete_sequence=["blue"],
    )
    fig.update_traces(selector=dict(name="Histórico"), line=dict(dash="dot", color="lightblue"), opacity=0.8)

    y_data = df[y_col].dropna()
    green_y0 = y_data.min() if use_data_min else min_fixed
    green_y1 = y_data.max() if use_data_max else max_fixed
    if green_y0 is not None and green_y1 is not None and green_y0 < green_y1:
        fig.add_hrect(y0=green_y0, y1=green_y1, fillcolor="green", opacity=0.1, line_width=0)

    if min_fixed is not None:
        fig.add_hline(y=min_fixed, line_dash="dash", line_color="red")
    if max_fixed is not None:
        fig.add_hline(y=max_fixed, line_dash="dash", line_color="red")

    fig.update_layout(hovermode="x unified")
    return fig


def style_row(row, params, highlight_color="#fff8e1"):
    styles = [''] * len(row)
    anomalies = detect_anomalies(row, params)  # ← Ahora usa el parámetro params
    for anomaly in anomalies:
        col_idx = row.index.get_loc(anomaly["column"])
        styles[col_idx] = f'background-color: {highlight_color}'
    return styles


# ------------------- Severidad -------------------
SEVERITY = {
    0: {"priority": 0, "name": "Sano", "label": "Sano", "color": "green", "emoji": "🟢"},
    1: {"priority": 1, "name": "Atención", "label": "Atención", "color": "yellow", "emoji": "🟡"},
    2: {"priority": 2, "name": "Precaución", "label": "Precaución", "color": "orange", "emoji": "🟠"},
    3: {"priority": 3, "name": "Crítico", "label": "Crítico", "color": "red", "emoji": "🔴"},
}


# ------------------- Función de carga principal -------------------
def load_data(uploaded_motores, uploaded_reglas):
    global df, df_historico, df_completo, config, df_acciones
    global PARAMS, PARAM_GROUPS, latest_df, latest_anomalies

    if uploaded_motores is None or uploaded_reglas is None:
        return

    # Carga básica
    df, df_historico, df_completo, config = motores_base(uploaded_motores)
    df_acciones = acciones_base(uploaded_reglas)

    # Construcción de PARAMS
    PARAMS = [
        {"name": "CIL1", "col": config.col_cil_1, "min_val": config.cil_min, "max_val": config.cil_max, "group": "Datos operativos / físicos de la muestra"},
        {"name": "CIL2", "col": config.col_cil_2, "min_val": config.cil_min, "max_val": config.cil_max, "group": "Datos operativos / físicos de la muestra"},
        {"name": "CIL3", "col": config.col_cil_3, "min_val": config.cil_min, "max_val": config.cil_max, "group": "Datos operativos / físicos de la muestra"},
        {"name": "CIL4", "col": config.col_cil_4, "min_val": config.cil_min, "max_val": config.cil_max, "group": "Datos operativos / físicos de la muestra"},
        {"name": "Blow by Carter", "col": config.col_p_carter, "min_val": None, "max_val": config.p_carter_max, "group": "Datos operativos / físicos de la muestra"},
        {"name": "▲ Temp Radiador", "col": config.col_temp_radiador, "min_val": config.temp_rad_min, "max_val": None, "group": "Datos operativos / físicos de la muestra"},
        {"name": "Viscosidad", "col": config.col_viscosidad, "min_val": config.visc_min, "max_val": config.visc_max, "group": "Propiedades del aceite"},
        {"name": "Fe", "col": config.col_fe, "min_val": None, "max_val": config.fe_max, "group": "Desgaste"},
        {"name": "Cr", "col": config.col_cr, "min_val": None, "max_val": config.cr_max, "group": "Desgaste"},
        {"name": "Pb", "col": config.col_pb, "min_val": None, "max_val": config.pb_max, "group": "Desgaste"},
        {"name": "Cu", "col": config.col_cu, "min_val": None, "max_val": config.cu_max, "group": "Desgaste"},
        {"name": "Sn", "col": config.col_sn, "min_val": None, "max_val": config.sn_max, "group": "Desgaste"},
        {"name": "Al", "col": config.col_al, "min_val": None, "max_val": config.al_max, "group": "Desgaste"},
        {"name": "Ni", "col": config.col_ni, "min_val": None, "max_val": config.ni_max, "group": "Desgaste"},
        {"name": "Ag", "col": config.col_ag, "min_val": None, "max_val": config.ag_max, "group": "Desgaste"},
        {"name": "Silicio", "col": config.col_silicio, "min_val": None, "max_val": config.silicio_max, "group": "Contaminación"},
        {"name": "B", "col": config.col_b, "min_val": None, "max_val": config.b_max, "group": "Aditivos / Contaminación"},
        {"name": "Na", "col": config.col_na, "min_val": None, "max_val": config.na_max, "group": "Contaminación"},
        {"name": "Mg", "col": config.col_mg, "min_val": config.mg_min, "max_val": None, "group": "Aditivos"},
        {"name": "Ca", "col": config.col_ca, "min_val": config.ca_min, "max_val": None, "group": "Aditivos"},
        {"name": "Ba", "col": config.col_ba, "min_val": None, "max_val": config.ba_max, "group": "Aditivos"},
        {"name": "P", "col": config.col_p, "min_val": config.p_min, "max_val": None, "group": "Aditivos"},
        {"name": "Zn", "col": config.col_zn, "min_val": config.zn_min, "max_val": None, "group": "Aditivos"},
        {"name": "Mo", "col": config.col_mo, "min_val": None, "max_val": config.mo_max, "group": "Aditivos"},
        {"name": "Ti", "col": config.col_ti, "min_val": None, "max_val": config.ti_max, "group": "Desgaste"},
        {"name": "V", "col": config.col_v, "min_val": None, "max_val": config.v_max, "group": "Desgaste"},
        {"name": "Mn", "col": config.col_mn, "min_val": None, "max_val": config.mn_max, "group": "Desgaste"},
        {"name": "Cd", "col": config.col_cd, "min_val": None, "max_val": config.cd_max, "group": "Desgaste"},
        {"name": "K", "col": config.col_k, "min_val": None, "max_val": config.k_max, "group": "Contaminación"},
        {"name": "Diesel", "col": config.col_diesel, "min_val": None, "max_val": config.diesel_max, "group": "Contaminación"},
        {"name": "Agua", "col": config.col_agua, "min_val": None, "max_val": config.agua_max, "group": "Contaminación"},
        {"name": "Oxidación", "col": config.col_oxidacion, "min_val": None, "max_val": config.oxidacion_max, "group": "Degradación del aceite"},
        {"name": "Sulfatación", "col": config.col_sulfatacion, "min_val": None, "max_val": config.sulfatacion_max, "group": "Degradación del aceite"},
        {"name": "Nitración", "col": config.col_nitratacion, "min_val": None, "max_val": config.nitratacion_max, "group": "Degradación del aceite"},
        {"name": "Hollín", "col": config.col_hollin, "min_val": None, "max_val": config.hollin_max, "group": "Contaminación"},
        {"name": "TBN", "col": config.col_tbn, "min_val": config.tbn_min, "max_val": None, "group": "Aditivos"},
        {"name": "PQ", "col": config.col_pq, "min_val": None, "max_val": config.pq_max, "group": "Desgaste"},
    ]

    PARAM_GROUPS = list(dict.fromkeys(p["group"] for p in PARAMS))

    # Última toma por equipo + métricas
    latest_df = (
        df.sort_values(config.col_horometro, ascending=False)
        .groupby(config.col_equipos)
        .head(1)
        .sort_values(config.col_equipos)
        .reset_index(drop=True)
    )

    metrics_list = latest_df.apply(
        lambda row: compute_row_metrics(row, PARAMS, df_acciones),
        axis=1
    )
    latest_df["max_priority"] = [m[0] for m in metrics_list]
    latest_df["anomaly_count"] = [m[1] for m in metrics_list]
    latest_df["enriched_anomalies"] = [m[2] for m in metrics_list]

    # Anomalías de la última toma
    latest_anomalies = get_latest_anomalies(df, config, PARAMS)

    # Asignar a globals
    globals()['latest_df'] = latest_df
    globals()['latest_anomalies'] = latest_anomalies
