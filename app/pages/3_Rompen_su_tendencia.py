"""
Página 3 — Municipios que rompen su tendencia (2022).

Dos mapas interactivos de residuos (absoluto=contexto, centrado=hallazgo principal), cada
uno en su propia pestaña — mismo patrón que la Página 1 — más una tabla del top 20
municipios con mayor desviación, compartida fuera de las pestañas: es material de apoyo
para cualquiera de los dos mapas, no una tercera alternativa entre ellos.

Cada pestaña usa el mismo layout que la Página 1 (columna de texto a la izquierda, mapa a
la derecha) y el mismo tipo de mapa (px.choropleth_map con fondo carto-positron-nolabels),
para que el tamaño y la posición del mapa coincidan visualmente entre páginas.

Filtrado por baja_confiabilidad_electoral==0 en el cómputo del rango de color y en el
ranking — un micro-electorado no compite por el podio de anomalías (acordado en Fase 4).
"""

import plotly.express as px
import streamlit as st

from data_utils import (
    cargar_geometria_municipal,
    cargar_tabla_residuos,
    TEXTO_RESIDUOS_BLINDADO,
)

st.title("3. Municipios que rompen su tendencia (2022)")

df_residuos = cargar_tabla_residuos()
geojson_municipios = cargar_geometria_municipal()

df_2022 = df_residuos[df_residuos["ano"] == 2022].copy()

# Rango de color calculado SOLO con confiabilidad normal (acordado en Fase 4) — los
# micro-electorados no deben estirar ni distorsionar la escala, aunque sigan apareciendo
# en el mapa con su color correspondiente dentro de ese rango.
df_confiabilidad_normal = df_2022[df_2022["baja_confiabilidad_electoral"] == 0]
rango_absoluto = (df_confiabilidad_normal["residuo"].min(), df_confiabilidad_normal["residuo"].max())
rango_centrado = (
    df_confiabilidad_normal["residuo_centrado"].min(),
    df_confiabilidad_normal["residuo_centrado"].max(),
)

# =========================================================================
# Dos pestañas — mismo patrón que la Página 1: un mapa por pestaña
# =========================================================================
tab_absoluto, tab_centrado = st.tabs(
    ["🌎 Mapa 1 — Absoluto (contexto)", "🎯 Mapa 2 — Centrado (hallazgo principal)"]
)

with tab_absoluto:
    with st.container(border=True):
        col_info, col_mapa = st.columns([1, 3])

        with col_info:
            st.caption(
                "Residuos del modelo con lag: la diferencia entre lo que votó cada municipio "
                "en 2022 y lo que predice su propia trayectoria histórica."
            )
            st.info(TEXTO_RESIDUOS_BLINDADO)
            st.markdown("**Cómo leer este mapa**")
            st.markdown(
                "En 2022 hubo una ola nacional hacia la izquierda que el modelo, entrenado "
                "con elecciones anteriores, no podía anticipar en su magnitud: el 76% de los "
                "municipios votó por encima de su tendencia previa. El color absoluto "
                "refleja en gran parte ese desplazamiento común."
            )

        with col_mapa:
            fig_absoluto = px.choropleth_map(
                df_2022,
                geojson=geojson_municipios,
                locations="divipola",
                featureidkey="properties.divipola",
                color="residuo",
                color_continuous_scale="RdBu_r",
                range_color=rango_absoluto,
                color_continuous_midpoint=0,
                hover_name="municipio",
                hover_data={"departamento": True, "residuo": ":.1f", "divipola": False},
                labels={"residuo": "Residuo (pts)"},
                map_style="carto-positron-nolabels",
                center={"lat": 4.12, "lon": -72.93},
                zoom=4.9,
                opacity=0.75,
            )
            fig_absoluto.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=700)

            st.plotly_chart(fig_absoluto, use_container_width=True)

with tab_centrado:
    with st.container(border=True):
        col_info, col_mapa = st.columns([1, 3])

        with col_info:
            st.caption(
                "Residuos del modelo con lag: la diferencia entre lo que votó cada municipio "
                "en 2022 y lo que predice su propia trayectoria histórica."
            )
            st.info(TEXTO_RESIDUOS_BLINDADO)
            st.markdown("**Cómo leer este mapa**")
            st.markdown(
                "Todo el país se movió hacia la izquierda en 2022; este mapa muestra quién "
                "se movió más y quién menos que ese promedio nacional. Una vez descontada "
                "esa ola, el Pacífico y el sur se movieron por encima de la media y el "
                "interior andino por debajo. El patrón territorial de la desviación "
                "coincide con la geografía de la regionalización del voto ya identificada "
                "en el EDA: el mapa no destapa un fenómeno nuevo, lo confirma con "
                "granularidad municipal."
            )

        with col_mapa:
            fig_centrado = px.choropleth_map(
                df_2022,
                geojson=geojson_municipios,
                locations="divipola",
                featureidkey="properties.divipola",
                color="residuo_centrado",
                color_continuous_scale="RdBu_r",
                range_color=rango_centrado,
                color_continuous_midpoint=0,
                hover_name="municipio",
                hover_data={"departamento": True, "residuo_centrado": ":.1f", "divipola": False},
                labels={"residuo_centrado": "Residuo centrado (pts)"},
                map_style="carto-positron-nolabels",
                center={"lat": 4.12, "lon": -72.93},
                zoom=4.9,
                opacity=0.75,
            )
            fig_centrado.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=700)

            st.plotly_chart(fig_centrado, use_container_width=True)

st.divider()

# =========================================================================
# TOP 20 municipios con mayor desviación — compartido, fuera de las pestañas
# (es material de apoyo para cualquiera de los dos mapas, no una tercera
# alternativa entre ellos; aparece una sola vez, no se duplica por pestaña)
# =========================================================================
st.header("Los 20 municipios con mayor desviación")

with st.container(border=True):
    st.caption(
        "Ordenados por magnitud del residuo centrado (valor absoluto, descontada la ola "
        "nacional) — el mismo residuo que usa el mapa del hallazgo principal. Se excluyen los "
        "municipios de baja confiabilidad electoral (menos de 30 votos emitidos) — no compiten "
        "por este ranking. El conflicto armado (per_ocu) no se muestra aquí a propósito: ya "
        "se demostró que no explica estas desviaciones una vez controlado por pobreza y "
        "región (hallazgo 4) — incluirlo junto al ranking sugeriría visualmente una relación "
        "que los datos no sostienen."
    )

    top20 = (
        df_confiabilidad_normal.reindex(
            df_confiabilidad_normal["residuo_centrado"].abs().sort_values(ascending=False).index
        )
        .head(20)[["municipio", "departamento", "residuo_centrado", "nbi_total"]]
        .rename(
            columns={
                "municipio": "Municipio",
                "departamento": "Departamento",
                "residuo_centrado": "Residuo centrado (pts)",
                "nbi_total": "NBI total",
            }
        )
    )
    top20["Residuo centrado (pts)"] = top20["Residuo centrado (pts)"].round(1)
    top20["NBI total"] = top20["NBI total"].round(1)

    st.dataframe(top20, use_container_width=True, hide_index=True)
