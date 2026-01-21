import streamlit as st
import pandas as pd
from types import SimpleNamespace

def motores_base():
    #---------File Upload-------------#
    uploaded_file = st.file_uploader(
        "Sube el archivo de datos de motores (anteriormente 'motores_base.xlsx')",
        type=["xlsx", "xls"],
        key="motores_data_upload"
    )
    
    if uploaded_file is None:
        st.info("Por favor, sube el archivo Excel con los datos para continuar.")
        st.stop()
    
    #---------Constantes-------------#
    config = SimpleNamespace(
        ## Columnas
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
        col_nitratacion= "Nitracion",
        col_hollin = "Hollin",
        col_tbn = "TBN",
        col_pq = "PQ",
        ## Limites
        cil_min = 16,
        cil_max = 35,
        p_carter_max = 30,
        temp_rad_min=7,
        visc_min=13,
        visc_max=17,
        fe_max=70,
        cr_max = 10,
        pb_max = 20,
        cu_max = 25, #rev
        sn_max = 10, #rev
        al_max = 10,
        ni_max = 5, #rev
        ag_max = 2, #rev
        silicio_max = 15, #rev
        b_max = 50, #rev
        na_max = 30, #rev
        mg_min = 10, #rev
        ca_min = 2200, #rev
        ba_max = 2, #rev
        p_min = 800, #rev
        zn_min = 700, #rev
        mo_max = 100, #rev
        ti_max = 2, #rev
        v_max = 1, #rev
        mn_max = 5, #rev
        cd_max = 1, #rev
        k_max = 5,#rev
        diesel_max = 3, #rev
        agua_max = 0.2, #rev
        oxidacion_max = 20,
        sulfatacion_max = 20,
        nitratacion_max = 20,#rev
        hollin_max = 1.8,
        tbn_min = 5, #rev
        pq_max = 50, #rev
    )
    
    #---------Data Original-------------#
    ## Lectura
    df = pd.read_excel(uploaded_file, sheet_name="DATOS")
    
    #---------Data Promedios-------------#
    ## Variables
    variables = [
        value for key, value in vars(config).items()
        if key.startswith('col_') and key not in ['col_equipos', 'col_horometro', 'col_fecha']
    ]
    
    ## df_historico
    df_historico = (
        df.groupby(config.col_horometro, as_index=False)[variables]
            .agg(['mean', 'count']) # promedio + cantidad de mediciones en esa hora exacta
            .round(2)
    )
    
    ## Flatten multiindex columns
    df_historico.columns = [
        f"{col[0]}_{col[1]}" if col[1] else col[0]
        for col in df_historico.columns
    ]
    
    # Renombramos automáticamente todas las columnas _mean para que coincidan con el nombre original
    rename_dict = {f"{var}_mean": var for var in variables}
    df_historico = df_historico.rename(columns=rename_dict)
    df_historico = df_historico.sort_values(config.col_horometro)
    df_historico[config.col_equipos] = "Histórico"
    
    #---------Tabla unida historico + promedios-------------#
    df_completo = pd.concat([df, df_historico], ignore_index=True)
    
    #---------Parametros agrupados-------------#
    params = [
            ("CIL1", config.col_cil_1, config.cil_min, config.cil_max, "Datos operativos / físicos de la muestra"),
            ("CIL2", config.col_cil_2, config.cil_min, config.cil_max, "Datos operativos / físicos de la muestra"),
            ("CIL3", config.col_cil_3, config.cil_min, config.cil_max, "Datos operativos / físicos de la muestra"),
            ("CIL4", config.col_cil_4, config.cil_min, config.cil_max, "Datos operativos / físicos de la muestra"),
            ("Presión Carter", config.col_p_carter, None, config.p_carter_max, "Datos operativos / físicos de la muestra"),
            ("▲ Temperatura Radiador", config.col_temp_radiador, config.temp_rad_min, None, "Datos operativos / físicos de la muestra"),
            ("Viscosidad", config.col_viscosidad, config.visc_min, config.visc_max, "Condición del aceite"),
            ("Fe (Hierro)", config.col_fe, None, config.fe_max, "Elementos de desgaste (wear metals)"),
            ("Cr (Cromo)", config.col_cr, None, config.cr_max, "Elementos de desgaste (wear metals)"),
            ("Pb (Plomo)", config.col_pb, None, config.pb_max, "Elementos de desgaste (wear metals)"),
            ("Cu (Cobre)", config.col_cu, None, config.cu_max, "Elementos de desgaste (wear metals)"),
            ("Sn (Estaño)", config.col_sn, None, config.sn_max, "Elementos de desgaste (wear metals)"),
            ("Al (Aluminio)", config.col_al, None, config.al_max, "Elementos de desgaste (wear metals)"),
            ("Ni (Níquel)", config.col_ni, None, config.ni_max, "Elementos de desgaste (wear metals)"),
            ("Ag (Plata)", config.col_ag, None, config.ag_max, "Elementos de desgaste (wear metals)"),
            ("Silicio", config.col_silicio, None, config.silicio_max, "Contaminación (o elementos/propiedades contaminantes)"),
            ("B (Boro)", config.col_b, None, config.b_max, "Contaminación (o elementos/propiedades contaminantes)"),
            ("Na (Sodio)", config.col_na, None, config.na_max, "Contaminación (o elementos/propiedades contaminantes)"),
            ("Mg (Magnesio)", config.col_mg, config.mg_min, None, "Elementos aditivos"),
            ("Ca (Calcio)", config.col_ca, config.ca_min, None, "Elementos aditivos"),
            ("Ba (Bario)", config.col_ba, None, config.ba_max, "Elementos aditivos"),
            ("P (Fósforo)", config.col_p, config.p_min, None, "Elementos aditivos"),
            ("Zn (Zinc)", config.col_zn, config.zn_min, None, "Elementos aditivos"),
            ("Mo (Molibdeno)", config.col_mo, None, config.mo_max, "Elementos aditivos"),
            ("Ti (Titanio)", config.col_ti, None, config.ti_max, "Elementos de desgaste (wear metals)"),
            ("V (Vanadio)", config.col_v, None, config.v_max, "Elementos de desgaste (wear metals)"),
            ("Mn (Manganeso)", config.col_mn, None, config.mn_max, "Elementos de desgaste (wear metals)"),
            ("Cd (Cadmio)", config.col_cd, None, config.cd_max, "Elementos de desgaste (wear metals)"),
            ("K (Potasio)", config.col_k, None, config.k_max, "Contaminación (o elementos/propiedades contaminantes)"),
            ("Diesel (%)", config.col_diesel, None, config.diesel_max, "Contaminación (o elementos/propiedades contaminantes)"),
            ("Agua (%)", config.col_agua, None, config.agua_max, "Contaminación (o elementos/propiedades contaminantes)"),
            ("Oxidación", config.col_oxidacion, None, config.oxidacion_max, "Condición del aceite"),
            ("Sulfatación", config.col_sulfatacion, None, config.sulfatacion_max, "Condición del aceite"),
            ("Nitración", config.col_nitratacion, None, config.nitratacion_max, "Condición del aceite"),
            ("Hollín (%)", config.col_hollin, None, config.hollin_max, "Condición del aceite"),
            ("TBN", config.col_tbn, config.tbn_min, None, "Condición del aceite"),
            ("PQ", config.col_pq, None, config.pq_max, "Condición del aceite"),
        ]
    
    return df, df_historico, df_completo, config, params

def acciones_base():
    #---------File Upload-------------#
    uploaded_rules = st.file_uploader(
        "Sube el archivo de reglas (anteriormente 'Reglas.xlsx')",
        type=["xlsx", "xls"],
        key="reglas_upload"
    )
    
    if uploaded_rules is None:
        st.info("Por favor, sube el archivo Excel con las reglas para continuar.")
        st.stop()
    
    df_acc = pd.read_excel(uploaded_rules, sheet_name="REGLAS")
    return df_acc
