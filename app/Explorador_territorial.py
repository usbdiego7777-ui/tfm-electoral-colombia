"""
App Streamlit — TFM Electoral Colombia. Punto de entrada = Página 1.

Página 1 — Explorador del voto territorial (tres pestañas dentro de una sola sección):
  - Mapa coroplético interactivo del % de voto de izquierda por municipio y año.
  - Evolución temporal nacional 2006-2022 (hallazgo 1: la curva "V").
  - Relación NBI-voto que cambia de signo por región (hallazgo 2: falacia ecológica).

Las Páginas 2 y 3 viven en app/pages/ (navegación automática de Streamlit, menú lateral).
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_utils import (
    aplicar_estilo,
    cargar_dataset_maestro,
    cargar_geometria_municipal,
    COLORES_REGION,
)

st.set_page_config(page_title="TFM Electoral Colombia", layout="wide")
aplicar_estilo()


@st.cache_data
def calcular_evolucion_nacional(df):
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
st.markdown(
    "*Inercia, pobreza y regionalización del voto de izquierda a nivel municipal (2006–2022). "
    "Herramienta de comprensión del voto territorial para analistas, investigadores y "
    "periodistas de datos.*"
)

df_maestro = cargar_dataset_maestro()
geojson_municipios = cargar_geometria_municipal()

# =========================================================================
# Tres pestañas dentro de una sola sección — cada una usa el espacio vertical
# completo, sin competir por altura con las otras dos (a diferencia del layout
# anterior de tres bloques apilados con scroll).
# =========================================================================
tab_mapa, tab_evolucion, tab_nbi = st.tabs(
    ["🗺️ Mapa por municipio", "📈 Evolución nacional", "📊 Relación NBI-voto"]
)

# -------------------------------------------------------------------------
# Pestaña 1 — Mapa coroplético por año
# -------------------------------------------------------------------------
with tab_mapa:
    with st.container(border=True):
        col_info, col_mapa = st.columns([1, 3])

        with col_info:
            anios_disponibles = sorted(df_maestro["ano"].unique())
            anio_seleccionado = st.selectbox(
                "Año",
                anios_disponibles,
                index=anios_disponibles.index(2022) if 2022 in anios_disponibles else len(anios_disponibles) - 1,
            )

            df_anio = df_maestro[df_maestro["ano"] == anio_seleccionado].copy()

            st.markdown("**Cómo leer el mapa**")
            st.markdown(
                "- 🔴 Rojo → mayor % de voto de izquierda\n"
                "- 🔵 Azul → menor % de voto de izquierda\n"
                "- Pasa el cursor sobre un municipio para ver el dato exacto"
            )
            st.caption(f"{len(df_anio)} municipios con dato en {anio_seleccionado}.")

        with col_mapa:
            fig_mapa = px.choropleth_map(
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
                map_style="carto-positron-nolabels",
                center={"lat": 4.12, "lon": -72.93},
                zoom=4.9,
                opacity=0.75,
            )
            fig_mapa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=710)

            st.plotly_chart(fig_mapa, use_container_width=True)

# -------------------------------------------------------------------------
# Pestaña 2 — Evolución temporal nacional (hallazgo 1: la curva "V")
# -------------------------------------------------------------------------
with tab_evolucion:
    with st.container(border=True):
        col_info, col_evolucion = st.columns([1, 3])

        df_evolucion = calcular_evolucion_nacional(df_maestro[df_maestro["ano"] >= 2006])

        with col_info:
            st.markdown(
                "**Hallazgo 1 — la inercia electoral es el predictor dominante.** El voto "
                "municipal se explica sobre todo por cómo votó ese municipio en la elección "
                "anterior. La curva nacional muestra una caída fuerte en 2010, seguida de un "
                "ascenso sostenido hasta el 41,2% de 2022, coincidiendo con el ascenso "
                "político de Petro."
            )

        with col_evolucion:
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
                height=710,
                margin={"t": 30},
            )

            st.plotly_chart(fig_evolucion, use_container_width=True)

# -------------------------------------------------------------------------
# Pestaña 3 — Relación NBI-voto que cambia de signo por región (hallazgo 2)
# -------------------------------------------------------------------------
with tab_nbi:
    with st.container(border=True):
        df_modelado = df_maestro[df_maestro["valido_para_modelado"] == 1].copy()
        regiones_disponibles = sorted(df_modelado["region_dane"].dropna().unique())

        col_info, col_chart = st.columns([1, 3])

        with col_info:
            regiones_seleccionadas = st.multiselect(
                "Filtrar por región (DANE)",
                regiones_disponibles,
                default=regiones_disponibles,
            )

            df_nbi = df_modelado[df_modelado["region_dane"].isin(regiones_seleccionadas)]

            st.markdown(
                "**Hallazgo 2 — falacia ecológica.** La correlación global entre pobreza y "
                "voto de izquierda es casi nula (~0,03), pero es el promedio de dos señales "
                "reales que se cancelan: **negativa** en la región Andina y Caribe, y "
                "**positiva** en la periferia (Orinoquía, frontera). Un mismo nivel de NBI "
                "puede acompañar más voto de izquierda en una región y menos en otra — por "
                "eso la relación nacional no dice casi nada por sí sola."
            )
            with st.expander("Correlación exacta por región"):
                tabla_corr = (
                    df_nbi.groupby("region_dane")
                    .apply(lambda g: g["nbi_total"].corr(g["pct_izquierda"]), include_groups=False)
                    .reset_index(name="correlacion")
                    .sort_values("correlacion")
                )
                st.dataframe(tabla_corr, use_container_width=True, hide_index=True)

        with col_chart:
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
                height=710,
                legend_title="Región (DANE)",
                margin={"t": 30},
            )

            st.plotly_chart(fig_nbi, use_container_width=True)
