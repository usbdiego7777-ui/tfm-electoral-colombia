"""
App Streamlit — TFM Electoral Colombia.

Página 1 — Explorador del voto territorial:
  1. Mapa coroplético interactivo del % de voto de izquierda por municipio y año.
  2. Evolución temporal nacional 2006-2022 (hallazgo 1: la curva "V").
  3. Relación NBI-voto que cambia de signo por región (hallazgo 2: falacia ecológica).

La app consume, nunca recalcula: todo sale directamente de datos/procesados/ y datos/geo/.
"""

import os
import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------
# Configuración — sin rutas locales hardcodeadas
# -----------------------------------------------------------------------
BASE_DIR = os.environ.get("TFM_BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUTA_DATASET_MAESTRO = os.path.join(BASE_DIR, "datos", "procesados", "dataset_maestro_electoral.csv")
RUTA_GEOJSON = os.path.join(BASE_DIR, "datos", "geo", "municipios_colombia_simplificado.geojson")

st.set_page_config(page_title="TFM Electoral Colombia", layout="wide")

COLORES_REGION = {
    "Andina": "#4C72B0",
    "Caribe": "#DD8452",
    "Pacifica": "#C44E52",
    "Orinoquia": "#55A868",
    "Amazonia": "#8172B2",
    "Insular": "#937860",
}


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


@st.cache_data
def calcular_evolucion_nacional(df: pd.DataFrame) -> pd.DataFrame:
    """
    % de voto de izquierda nacional por año, ponderado por votos_validos.
    Reproduce la curva "V" ya documentada en Fase 2 (22.6/9.3/16.2/25.7/41.2).
    """
    filas = []
    for anio in sorted(df["ano"].unique()):
        sub = df[df["ano"] == anio]
        pct_ponderado = (sub["pct_izquierda"] * sub["votos_validos"]).sum() / sub["votos_validos"].sum()
        filas.append({"ano": anio, "pct_izquierda_nacional": pct_ponderado})
    return pd.DataFrame(filas)


# -----------------------------------------------------------------------
# Cuerpo de la app
# -----------------------------------------------------------------------
st.title("TFM — Análisis del comportamiento electoral territorial en Colombia")
st.caption(
    "Inercia, pobreza y regionalización del voto de izquierda a nivel municipal (2006–2022). "
    "Herramienta de comprensión del voto territorial para analistas, investigadores y "
    "periodistas de datos."
)

df_maestro = cargar_dataset_maestro()
geojson_municipios = cargar_geometria_municipal()

# =========================================================================
# SECCIÓN 1 — Mapa coroplético por año
# =========================================================================
st.header("1. El voto de izquierda por municipio")

anios_disponibles = sorted(df_maestro["ano"].unique())
anio_seleccionado = st.selectbox(
    "Año",
    anios_disponibles,
    index=anios_disponibles.index(2022) if 2022 in anios_disponibles else len(anios_disponibles) - 1,
)

df_anio = df_maestro[df_maestro["ano"] == anio_seleccionado].copy()

fig_mapa = px.choropleth(
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
fig_mapa.update_geos(fitbounds="locations", visible=False)
fig_mapa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=600)

st.plotly_chart(fig_mapa, use_container_width=True)
st.caption(f"{len(df_anio)} municipios con dato en {anio_seleccionado}.")

st.divider()

# =========================================================================
# SECCIÓN 2 — Evolución temporal nacional (hallazgo 1: la curva "V")
# =========================================================================
st.header("2. Evolución nacional del voto de izquierda")

df_evolucion = calcular_evolucion_nacional(df_maestro[df_maestro["ano"] >= 2006])

fig_evolucion = go.Figure()
fig_evolucion.add_trace(
    go.Scatter(
        x=df_evolucion["ano"],
        y=df_evolucion["pct_izquierda_nacional"],
        mode="lines+markers+text",
        text=[f"{v:.1f}%" for v in df_evolucion["pct_izquierda_nacional"]],
        textposition="top center",
        line=dict(width=3),
        marker=dict(size=10),
    )
)
fig_evolucion.update_layout(
    xaxis_title="Año",
    yaxis_title="% voto izquierda (ponderado por votos_validos)",
    xaxis=dict(tickmode="array", tickvals=df_evolucion["ano"]),
    height=420,
    margin={"t": 30},
)

st.plotly_chart(fig_evolucion, use_container_width=True)
st.markdown(
    "**Hallazgo 1 — la inercia electoral es el predictor dominante.** El voto municipal se "
    "explica sobre todo por cómo votó ese municipio en la elección anterior. La curva nacional "
    "muestra una caída fuerte en 2010, seguida de un ascenso sostenido hasta el 41,2% de 2022, "
    "coincidiendo con el ascenso político de Petro."
)

st.divider()

# =========================================================================
# SECCIÓN 3 — Relación NBI-voto que cambia de signo por región (hallazgo 2)
# =========================================================================
st.header("3. La relación entre pobreza (NBI) y voto de izquierda — heterogénea por región")

df_modelado = df_maestro[df_maestro["valido_para_modelado"] == 1].copy()

regiones_disponibles = sorted(df_modelado["region_dane"].dropna().unique())
regiones_seleccionadas = st.multiselect(
    "Filtrar por región (DANE)",
    regiones_disponibles,
    default=regiones_disponibles,
)

df_nbi = df_modelado[df_modelado["region_dane"].isin(regiones_seleccionadas)]

fig_nbi = go.Figure()
for region in regiones_seleccionadas:
    sub = df_nbi[df_nbi["region_dane"] == region]
    color = COLORES_REGION.get(region, "#333333")
    fig_nbi.add_trace(
        go.Scatter(
            x=sub["nbi_total"],
            y=sub["pct_izquierda"],
            mode="markers",
            name=region,
            marker=dict(size=5, opacity=0.45, color=color),
            legendgroup=region,
        )
    )
    # Línea de tendencia manual (ajuste lineal simple, sin dependencias nuevas)
    if len(sub) >= 5:
        coeficientes = np.polyfit(sub["nbi_total"], sub["pct_izquierda"], 1)
        x_linea = np.linspace(sub["nbi_total"].min(), sub["nbi_total"].max(), 50)
        y_linea = np.polyval(coeficientes, x_linea)
        fig_nbi.add_trace(
            go.Scatter(
                x=x_linea,
                y=y_linea,
                mode="lines",
                line=dict(width=3, color=color),
                showlegend=False,
                legendgroup=region,
                hoverinfo="skip",
            )
        )

fig_nbi.update_layout(
    xaxis_title="NBI total (% población con necesidades básicas insatisfechas)",
    yaxis_title="% voto izquierda",
    height=520,
    legend_title="Región (DANE)",
    margin={"t": 30},
)

st.plotly_chart(fig_nbi, use_container_width=True)

with st.expander("Correlación NBI-voto por región (valores exactos)"):
    tabla_corr = (
        df_nbi.groupby("region_dane")
        .apply(lambda g: g["nbi_total"].corr(g["pct_izquierda"]))
        .reset_index(name="correlacion")
        .sort_values("correlacion")
    )
    st.dataframe(tabla_corr, use_container_width=True, hide_index=True)

st.markdown(
    "**Hallazgo 2 — falacia ecológica.** La correlación global entre pobreza y voto de "
    "izquierda es casi nula (~0,03), pero es el promedio de dos señales reales que se cancelan: "
    "**negativa** en la región Andina y Caribe, y **positiva** en la periferia (Orinoquía, "
    "frontera). Un mismo nivel de NBI puede acompañar más voto de izquierda en una región y "
    "menos en otra — por eso la relación nacional no dice casi nada por sí sola."
)
