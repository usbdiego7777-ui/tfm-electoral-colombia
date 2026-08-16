"""
Carga de datos compartida entre todas las páginas de la app.

Centralizado aquí (en vez de repetido en cada página) porque BASE_DIR se calcula de
forma distinta según la profundidad del fichero que lo importa — este módulo vive
siempre en app/, así que su propio __file__ da una referencia estable sin importar
si lo llama app/streamlit_app.py o app/pages/algo.py.

La app consume, nunca recalcula: todo sale directamente de datos/procesados/ y datos/geo/.
"""

import os
import json

import pandas as pd
import streamlit as st

BASE_DIR = os.environ.get("TFM_BASE_DIR", os.path.dirname(os.path.abspath(__file__)) + "/..")
BASE_DIR = os.path.abspath(BASE_DIR)

RUTA_DATASET_MAESTRO = os.path.join(BASE_DIR, "datos", "procesados", "dataset_maestro_electoral.csv")
RUTA_GEOJSON = os.path.join(BASE_DIR, "datos", "geo", "municipios_colombia_simplificado.geojson")
RUTA_TABLA_RESIDUOS = os.path.join(BASE_DIR, "datos", "procesados", "tabla_residuos.csv")

COLORES_REGION = {
    "Andina": "#4C72B0",
    "Caribe": "#DD8452",
    "Pacifica": "#C44E52",
    "Orinoquia": "#55A868",
    "Amazonia": "#8172B2",
    "Insular": "#937860",
}

# Texto blindado — no reformular en ningún sitio de la app (acordado en Fase 4)
TEXTO_RESIDUOS_BLINDADO = (
    "Los residuos miden la desviación del voto respecto a la trayectoria histórica del "
    "municipio. No son una prueba de irregularidad."
)


@st.cache_data
def cargar_dataset_maestro() -> pd.DataFrame:
    """Carga el dataset maestro electoral ya procesado (Fase 1)."""
    return pd.read_csv(RUTA_DATASET_MAESTRO, dtype={"divipola": str})


@st.cache_data
def cargar_geometria_municipal() -> dict:
    """
    Carga el geojson municipal simplificado (Fase 4) y lo devuelve como dict
    (formato que espera plotly.express.choropleth vía geojson=...).
    """
    with open(RUTA_GEOJSON, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar_tabla_residuos() -> pd.DataFrame:
    """
    Carga la tabla de residuos ya calculada en Fase 4 (municipio-año, solo
    2010/2014/2018/2022 — 2006 no es año de test de ninguna ventana y no aparece aquí).
    """
    return pd.read_csv(RUTA_TABLA_RESIDUOS, dtype={"divipola": str})
