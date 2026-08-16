"""
Esqueleto mínimo de la app Streamlit — TFM Electoral Colombia.

Objetivo de esta primera versión: confirmar que el despliegue en Streamlit Cloud
funciona, que los datos (geometría + dataset maestro) caben en memoria del plan
gratuito, y que el enlace abre correctamente sin instalar nada.

NO es la app final de tres páginas — eso viene después, una vez confirmado esto.
"""

import os
import json

import pandas as pd
import geopandas as gpd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------
# Configuración — sin rutas locales hardcodeadas
# -----------------------------------------------------------------------
BASE_DIR = os.environ.get("TFM_BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUTA_DATASET_MAESTRO = os.path.join(BASE_DIR, "datos", "procesados", "dataset_maestro_electoral.csv")
RUTA_GEOJSON = os.path.join(BASE_DIR, "datos", "geo", "municipios_colombia_simplificado.geojson")

st.set_page_config(page_title="TFM Electoral Colombia — esqueleto", layout="wide")


# -----------------------------------------------------------------------
# Carga de datos cacheada — obligatoria desde la primera versión funcional
# -----------------------------------------------------------------------
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
        geojson = json.load(f)
    return geojson


# -----------------------------------------------------------------------
# Cuerpo de la app
# -----------------------------------------------------------------------
st.title("TFM — Análisis del comportamiento electoral territorial en Colombia")
st.caption(
    "Esqueleto de despliegue — mapa único de % de voto de izquierda por municipio. "
    "Página completa (evolución temporal, relación NBI-voto, predicción y residuos) "
    "se construye a partir de esta base ya confirmada como desplegable."
)

df_maestro = cargar_dataset_maestro()
geojson_municipios = cargar_geometria_municipal()

anios_disponibles = sorted(df_maestro["ano"].unique())
anio_seleccionado = st.selectbox(
    "Año",
    anios_disponibles,
    index=anios_disponibles.index(2022) if 2022 in anios_disponibles else len(anios_disponibles) - 1,
)

df_anio = df_maestro[df_maestro["ano"] == anio_seleccionado].copy()

fig = px.choropleth(
    df_anio,
    geojson=geojson_municipios,
    locations="divipola",
    featureidkey="properties.divipola",
    color="pct_izquierda",
    color_continuous_scale="RdBu_r",
    range_color=(0, 100),
    hover_name="municipio",
    hover_data={"departamento": True, "pct_izquierda": ":.1f", "divipola": False},
    labels={"pct_izquierda": "% voto izquierda"},
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=650)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    f"{len(df_anio)} municipios con dato en {anio_seleccionado}. "
    "Dataset maestro y geometría cargados directamente desde datos/ (sin recalcular nada)."
)
