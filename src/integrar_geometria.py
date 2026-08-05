# ==============================================================================
# integrar_geometria.py
# Prepara la geometria municipal (Marco Geoestadistico Nacional - MGN, DANE) para
# el mapa coropletico de residuos de la Fase 4. Dos pasos, en este orden:
#   1. Disolver por DIVIPOLA los municipios que llegan fragmentados en varias
#      filas de poligono en el shapefile original.
#   2. Simplificar la geometria para que el fichero sea manejable en git y en
#      Streamlit Cloud (plan gratuito), sin perder fidelidad visual a escala
#      nacional.
#
# FUENTE: DANE, Marco Geoestadistico Nacional (MGN), version 2018, capa
# Municipio (MGN_MPIO_POLITICO). Descarga manual desde geoportal.dane.gov.co
# (geovisor interactivo, sin URL de descarga directa) - no automatizable desde
# este pipeline. Datos abiertos del Estado colombiano, uso libre (mismo
# tratamiento de licencia que el resto de fuentes DANE del proyecto: NBI 2005,
# NBI 2018, IPM). Se eligio deliberadamente la version 2018 del MGN, no la mas
# reciente disponible en el geoportal, para mantener la misma vintage de
# codigos DIVIPOLA que ya usa el resto del proyecto como referencia (el
# fichero electoral de 2018 y CNPV2018NBI.xlsx) y minimizar el riesgo de que
# algun municipio tenga un codigo distinto entre fuentes.
#
# HALLAZGO DE VERIFICACION (antes de construir nada de esto): los 1.122
# codigos DIVIPOLA unicos del shapefile MGN 2018 casan 1:1, sin excepciones,
# contra los 1.122 municipios unicos de dataset_maestro_electoral.csv. Cero
# codigos huerfanos en ningun sentido - confirma ademas la cifra de 1.122
# municipios que ya se conocia de la fuente NBI 2005.
#
# HALLAZGO SOBRE LA GEOMETRIA CRUDA: 9 municipios (todos costeros o
# insulares - Cartagena, Buenaventura, Tumaco, San Andres, Providencia,
# Ocaña, Hatonuevo, Ubala, Hatillo de Loba) llegan repartidos en mas de una
# fila de poligono en el shapefile original (Cartagena, el caso extremo, en
# 50 filas). Sin corregir esto, un merge directo contra el dataset electoral
# multiplicaria filas para esos 9 municipios. Se corrige con dissolve() por
# divipola antes de cualquier otro uso.
# ==============================================================================

import geopandas as gpd

# Tolerancia de simplificacion (grados, ~110m en el ecuador con tol=0.001).
# Se probaron 0.0005 / 0.001 / 0.003 / 0.005: a escala nacional el resultado
# es visualmente indistinguible del original incluso en 0.003, y los
# municipios muy pequeños (San Andres, Providencia) no se destruyen ni
# pierden area apreciable. Se elige 0.003 como compromiso entre peso de
# fichero (~4MB, comodo para git y Streamlit Cloud) y fidelidad visual.
TOLERANCIA_SIMPLIFICACION = 0.003

COLUMNAS_ATRIBUTO = ["divipola", "DPTO_CCDGO", "MPIO_CCDGO", "MPIO_CNMBR", "DPTO_CNMBR"]


def cargar_y_preparar_geometria(ruta_shapefile: str, tolerancia: float = TOLERANCIA_SIMPLIFICACION) -> gpd.GeoDataFrame:
    """
    Carga el shapefile MGN_MPIO_POLITICO, construye el codigo DIVIPOLA
    (MPIO_CCNCT ya viene como string de 5 digitos con ceros a la izquierda,
    pero se fuerza zfill(5) explicitamente por seguridad, siguiendo el mismo
    principio que el resto del proyecto: nunca asumir formato, verificarlo),
    disuelve los municipios fragmentados en una sola geometria por codigo, y
    simplifica para reducir peso. Devuelve un GeoDataFrame de 1.122 filas
    (una por municipio), CRS EPSG:4326 (WGS84, el que esperan folium/plotly
    para mapas web).
    """
    gdf = gpd.read_file(ruta_shapefile)
    gdf["divipola"] = gdf["MPIO_CCNCT"].astype(str).str.zfill(5)

    gdf_disuelto = gdf[COLUMNAS_ATRIBUTO + ["geometry"]].dissolve(by="divipola", as_index=False, aggfunc="first")

    n_invalidas_antes = (~gdf_disuelto.geometry.is_valid).sum()
    if n_invalidas_antes > 0:
        print(f"AVISO: {n_invalidas_antes} geometrias invalidas tras el dissolve, antes de simplificar.")

    gdf_disuelto["geometry"] = gdf_disuelto.geometry.simplify(tolerancia, preserve_topology=True)

    n_invalidas_despues = (~gdf_disuelto.geometry.is_valid).sum()
    n_vacias = gdf_disuelto.geometry.is_empty.sum()
    if n_invalidas_despues > 0 or n_vacias > 0:
        print(f"AVISO: tras simplificar quedan {n_invalidas_despues} geometrias invalidas y {n_vacias} vacias - revisar tolerancia.")

    return gdf_disuelto


def verificar_cruce_con_dataset(gdf: gpd.GeoDataFrame, ruta_dataset_maestro: str) -> None:
    """
    Verifica el cruce por DIVIPOLA entre la geometria y el dataset maestro
    electoral en ambos sentidos (huerfanos en cada lado), siguiendo la regla
    de oro del proyecto: ninguna cifra ni cruce se da por bueno sin
    verificarlo contra los datos reales. No modifica nada, solo informa.
    """
    import pandas as pd

    df = pd.read_csv(ruta_dataset_maestro, dtype={"divipola": str})
    df["divipola"] = df["divipola"].str.zfill(5)

    codigos_dataset = set(df["divipola"].unique())
    codigos_geo = set(gdf["divipola"].unique())

    en_dataset_no_geo = codigos_dataset - codigos_geo
    en_geo_no_dataset = codigos_geo - codigos_dataset

    print(f"Municipios en dataset maestro: {len(codigos_dataset)}")
    print(f"Municipios en geometria:       {len(codigos_geo)}")
    print(f"En dataset pero sin geometria:  {len(en_dataset_no_geo)}")
    print(f"En geometria pero sin dataset:  {len(en_geo_no_dataset)}")

    if en_dataset_no_geo:
        print("AVISO - divipola en dataset sin geometria asociada:")
        print(df[df["divipola"].isin(en_dataset_no_geo)][["divipola", "departamento", "municipio"]].drop_duplicates().to_string())
    if en_geo_no_dataset:
        print("AVISO - divipola en geometria sin fila en el dataset:")
        print(gdf[gdf["divipola"].isin(en_geo_no_dataset)][["divipola", "MPIO_CNMBR", "DPTO_CNMBR"]].drop_duplicates().to_string())
