# ==============================================================================
# integrar_nbi.py
# Integra el Indice de Necesidades Basicas Insatisfechas (NBI) municipal al
# panel electoral. Se usan DOS fuentes segun el año de la eleccion (ver
# ESTRATEGIA DE INTEGRACION en el prompt de contexto del proyecto):
#   - NBI Censo 2005 (NBI_total_dpto_30_Jun_2012.xls) para 1998, 2002, 2006, 2010
#   - NBI Censo 2018 (CNPV2018NBI.xlsx)               para 2014, 2018, 2022
#
# HALLAZGO IMPORTANTE (a diferencia del fichero electoral de 2022): en AMBOS
# ficheros de NBI, el codigo DIVIPOLA construido directamente como
# coddpto.zfill(2) + codmun.zfill(3) SI coincide con el DIVIPOLA oficial
# (verificado contra la referencia electoral de 2018, incluyendo casos
# especiales como los municipios de Vaupes con sufijo "(ANM)"/"(CD)" en el
# nombre). Por eso aqui NO hace falta un crosswalk por nombre como en 2022 -
# basta con construir el codigo directamente.
# ==============================================================================

import pandas as pd

FILA_INICIO_DATOS_NBI_2005 = 6   # la hoja 'Municipios' tiene 6 filas de cabecera
FILA_INICIO_DATOS_NBI_2018 = 10  # la hoja 'Municipios' tiene 10 filas de cabecera

COLUMNA_NBI_TOTAL_2005 = 32  # 'Prop de Personas en NBI (%)' bajo el grupo 'Total'
COLUMNA_NBI_TOTAL_2018 = 4   # 'Prop de Personas en NBI (%)' bajo el grupo 'Total'

# Año electoral -> que fuente de NBI usar (ver Estrategia de integracion)
FUENTE_NBI_POR_ANO = {
    1998: "2005", 2002: "2005", 2006: "2005", 2010: "2005",
    2014: "2018", 2018: "2018", 2022: "2018",
}


def cargar_nbi_2005(path: str) -> pd.DataFrame:
    """
    Carga el NBI del Censo 2005 (hoja 'Municipios'). Descarta filas de pie
    de tabla (notas aclaratorias sobre creacion de municipios y limites
    departamentales, sin codigo de municipio real) filtrando por codmun no
    nulo y numerico.
    """
    df = pd.read_excel(path, sheet_name="Municipios", header=None, skiprows=FILA_INICIO_DATOS_NBI_2005)
    df = df[[0, 2, 3, COLUMNA_NBI_TOTAL_2005]].copy()
    df.columns = ["coddpto", "codmun", "municipio_nbi", "nbi_total"]

    # Filtrar filas de pie de tabla: codmun debe ser numerico
    df = df[pd.to_numeric(df["codmun"], errors="coerce").notna()].copy()

    df["divipola"] = (
        df["coddpto"].astype(str).str.zfill(2)
        + df["codmun"].astype(int).astype(str).str.zfill(3)
    )
    df["nbi_total"] = pd.to_numeric(df["nbi_total"], errors="coerce")
    return df[["divipola", "nbi_total"]]


def cargar_nbi_2018(path: str) -> pd.DataFrame:
    """
    Carga el NBI del Censo 2018 (hoja 'Municipios'). Descarta la fila de
    'TOTAL NACIONAL' y las notas de fuente al final, filtrando por codmun
    no nulo y numerico (la fila de total nacional tiene codmun=0, que se
    excluye explicitamente por no ser un municipio real).
    """
    df = pd.read_excel(path, sheet_name="Municipios", header=None, skiprows=FILA_INICIO_DATOS_NBI_2018)
    df = df[[0, 2, 3, COLUMNA_NBI_TOTAL_2018]].copy()
    df.columns = ["coddpto", "codmun", "municipio_nbi", "nbi_total"]

    df = df[pd.to_numeric(df["codmun"], errors="coerce").notna()].copy()
    df = df[df["codmun"] != 0]  # excluir fila de TOTAL NACIONAL (codmun=0)

    df["divipola"] = (
        df["coddpto"].astype(str).str.zfill(2)
        + df["codmun"].astype(int).astype(str).str.zfill(3)
    )
    df["nbi_total"] = pd.to_numeric(df["nbi_total"], errors="coerce")
    return df[["divipola", "nbi_total"]]


def integrar_nbi(panel: pd.DataFrame, ruta_nbi_2005: str, ruta_nbi_2018: str) -> pd.DataFrame:
    """
    Añade la columna 'nbi_total' al panel electoral, usando la fuente de
    NBI correspondiente segun el año de cada fila (ver FUENTE_NBI_POR_ANO).
    Avisa si quedan municipios sin NBI asignado, para revisar en el paso de
    verificacion de calidad (no se imputa aqui a ciegas, a diferencia del
    lag: el NBI ausente probablemente indica un problema de cruce a
    investigar, no una ausencia estructural esperada).
    """
    nbi_2005 = cargar_nbi_2005(ruta_nbi_2005)
    nbi_2018 = cargar_nbi_2018(ruta_nbi_2018)

    resultado = []
    for ano, grupo in panel.groupby("ano"):
        fuente = FUENTE_NBI_POR_ANO.get(ano)
        tabla_nbi = nbi_2005 if fuente == "2005" else nbi_2018
        grupo_con_nbi = grupo.merge(tabla_nbi, on="divipola", how="left")
        grupo_con_nbi["fuente_nbi"] = fuente
        resultado.append(grupo_con_nbi)

    panel_con_nbi = pd.concat(resultado, ignore_index=True)

    n_sin_nbi = panel_con_nbi["nbi_total"].isna().sum()
    if n_sin_nbi > 0:
        print(f"AVISO: {n_sin_nbi} filas sin NBI asignado tras el cruce. Revisar codigos DIVIPOLA no encontrados en la fuente correspondiente.")
        faltantes = panel_con_nbi[panel_con_nbi["nbi_total"].isna()][["divipola", "ano", "municipio"]].drop_duplicates()
        print(faltantes.to_string())

    return panel_con_nbi
