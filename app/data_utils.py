"""
Carga de datos compartida entre todas las páginas de la app.

Centralizado aquí (en vez de repetido en cada página) porque BASE_DIR se calcula de
forma distinta según la profundidad del fichero que lo importa — este módulo vive
siempre en app/, así que su propio __file__ da una referencia estable sin importar
si lo llama app/Explorador_territorial.py o app/pages/algo.py.

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
    "Andina": "#0B2447",
    "Caribe": "#F1C40F",
    "Pacifica": "#C0392B",
    "Orinoquia": "#27AE60",
    "Amazonia": "#9B2FAE",
    "Insular": "#7F8C8D",
}

# Texto blindado — no reformular en ningún sitio de la app (acordado en Fase 4)
TEXTO_RESIDUOS_BLINDADO = (
    "Los residuos miden la desviación del voto respecto a la trayectoria histórica del "
    "municipio. No son una prueba de irregularidad."
)


def aplicar_estilo():
    """
    Ajustes visuales mínimos, compartidos entre las tres páginas — sin fuentes ni
    animaciones custom, solo espaciado y bordes consistentes. Llamar justo después de
    st.set_page_config() en cada página.

    Nota: sin max-width en .block-container a propósito — con layout="wide" y mapas de
    Colombia (país alto y estrecho), limitar el ancho del contenedor le resta espacio
    horizontal útil al mapa sin necesidad (detectado al probar en pantalla ancha).
    """
    st.markdown(
        """
        <style>
            .block-container { padding-top: 1.3rem; padding-bottom: 3rem; }
            .block-container h1 { font-size: 1.9rem; margin-bottom: 0.3rem; }
            .block-container h2 { font-size: 1.4rem; margin-top: 0.6rem; margin-bottom: 0.4rem; }
            div[data-testid="stMetricValue"] { font-size: 1.7rem; }
            div[data-testid="stSelectbox"] label,
            div[data-testid="stMultiSelect"] label { font-weight: 600; }
            /* Menú lateral más estrecho (sigue visible y desplegado por defecto — no se
               oculta) para devolver espacio horizontal al contenido principal. El ancho
               por defecto de Streamlit (~336px) es más de lo que necesitan tres nombres
               de página cortos. */
            section[data-testid="stSidebar"] { min-width: 280px; max-width: 280px; }
        </style>
        """,
        unsafe_allow_html=True,
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
