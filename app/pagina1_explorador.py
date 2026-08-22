"""
Contenido de la Página 1 — Explorador territorial (tres pestañas):
  - Mapa coroplético interactivo del % de voto de izquierda por municipio y año.
  - Evolución temporal nacional 2006-2022 (hallazgo 1: la curva "V").
  - Relación NBI-voto que cambia de signo por región (hallazgo 2: falacia ecológica).

Este fichero NO es el punto de entrada de la app — lo es app/Explorador_territorial.py,
que actúa como enrutador (st.navigation) y llama a este fichero como una de las tres
páginas. st.set_page_config() y aplicar_estilo() se llaman una sola vez, en el enrutador
— no aquí, para evitar el error de Streamlit por llamar set_page_config más de una vez.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_utils import (
    cargar_dataset_maestro,
    cargar_geometria_municipal,
    COLORES_REGION,
)


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
# Cuerpo de la página
# -----------------------------------------------------------------------
st.title("TFM — Análisis del comportamiento electoral territorial en Colombia")

df_maestro = cargar_dataset_maestro()
geojson_municipios = cargar_geometria_municipal()

# =========================================================================
# Tres pestañas dentro de una sola sección — cada una usa el espacio vertical
# completo, sin competir por altura con las otras dos.
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

            st.caption(
                "**¿Qué es el voto de izquierda?** El bloque Polo Democrático → Colombia "
                "Humana → Pacto Histórico, en primera vuelta presidencial."
            )
            st.markdown("**Cómo leer el mapa**")
            st.markdown(
                "- 🔴 Rojo → mayor % de voto de izquierda\n"
                "- 🔵 Azul → menor % de voto de izquierda\n"
                "- ⬜ Gris → baja confiabilidad electoral (menos de 30 votos); el color no "
                "es representativo\n"
                "- Pasa el cursor sobre un municipio para ver el dato exacto"
            )
            st.markdown(
                "El voto de izquierda se concentra en el Pacífico y el sur; el interior "
                "andino vota menos — un patrón regional que este trabajo explora en las "
                "otras pestañas."
            )
            st.caption(f"{len(df_anio)} municipios con dato en {anio_seleccionado}.")

        with col_mapa:
            df_confiable = df_anio[df_anio["baja_confiabilidad_electoral"] == 0]
            df_baja_confiabilidad = df_anio[df_anio["baja_confiabilidad_electoral"] == 1]

            fig_mapa = go.Figure()

            fig_mapa.add_trace(
                go.Choroplethmap(
                    geojson=geojson_municipios,
                    locations=df_confiable["divipola"],
                    z=df_confiable["pct_izquierda"],
                    featureidkey="properties.divipola",
                    colorscale="RdBu_r",
                    zmin=0,
                    zmax=100,
                    marker_opacity=0.75,
                    marker_line_width=0.5,
                    text=df_confiable["municipio"] + " (" + df_confiable["departamento"] + ")",
                    hovertemplate="%{text}<br>%{z:.1f}% voto izquierda<extra></extra>",
                    colorbar=dict(title="% voto<br>izquierda"),
                )
            )

            if len(df_baja_confiabilidad) > 0:
                fig_mapa.add_trace(
                    go.Choroplethmap(
                        geojson=geojson_municipios,
                        locations=df_baja_confiabilidad["divipola"],
                        z=[0] * len(df_baja_confiabilidad),
                        featureidkey="properties.divipola",
                        colorscale=[[0, "lightgray"], [1, "lightgray"]],
                        showscale=False,
                        marker_opacity=0.75,
                        marker_line_width=0.5,
                        text=df_baja_confiabilidad["municipio"]
                        + " ("
                        + df_baja_confiabilidad["departamento"]
                        + "): baja confiabilidad electoral",
                        hovertemplate="%{text}<extra></extra>",
                    )
                )

            fig_mapa.update_layout(
                map_style="carto-positron-nolabels",
                map_center={"lat": 4.12, "lon": -72.93},
                map_zoom=4.9,
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                height=700,
            )

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
                height=700,
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

            st.caption(
                "**¿Qué es el NBI?** El Índice de Necesidades Básicas Insatisfechas, calculado "
                "por el DANE, mide pobreza estructural — carencias en vivienda, servicios, "
                "educación —, distinta de la pobreza monetaria. Un valor alto indica mayor "
                "privación material del municipio."
            )
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
                        marker=dict(size=5, opacity=0.75, color=color),
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
                height=700,
                legend_title="Región (DANE)",
                margin={"t": 30},
            )

            st.plotly_chart(fig_nbi, use_container_width=True)
