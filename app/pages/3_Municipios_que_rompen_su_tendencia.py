"""
Página 3 — Municipios que rompen su tendencia (2022).

Dos mapas interactivos de residuos (absoluto=contexto, centrado=hallazgo principal, en ese
orden) + top 20 municipios con mayor desviación. Consume tabla_residuos.csv directamente,
nunca recalcula.

Filtrado por baja_confiabilidad_electoral==0 en el cómputo del rango de color y en el
ranking — un micro-electorado no compite por el podio de anomalías (acordado en Fase 4).
"""

import plotly.express as px
import streamlit as st

from data_utils import (
    aplicar_estilo,
    cargar_geometria_municipal,
    cargar_tabla_residuos,
    TEXTO_RESIDUOS_BLINDADO,
)

st.set_page_config(page_title="Municipios que rompen su tendencia — TFM Electoral Colombia", layout="wide")
aplicar_estilo()

st.title("3. Municipios que rompen su tendencia (2022)")
st.caption(
    "Residuos del modelo con lag: la diferencia entre lo que votó cada municipio en 2022 y "
    "lo que predice su propia trayectoria histórica."
)
st.info(TEXTO_RESIDUOS_BLINDADO)

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
# MAPA 1 — Absoluto (contexto)
# =========================================================================
st.header("Mapa 1 — Absoluto (contexto)")

with st.container(border=True):
    fig_absoluto = px.choropleth(
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
    )
    fig_absoluto.update_geos(fitbounds="locations", visible=False)
    fig_absoluto.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=550)

    st.plotly_chart(fig_absoluto, use_container_width=True)
    st.caption(
        "En 2022 hubo una ola nacional hacia la izquierda que el modelo, entrenado con elecciones "
        "anteriores, no podía anticipar en su magnitud: el 76% de los municipios votó por encima "
        "de su tendencia previa. El color absoluto refleja en gran parte ese desplazamiento común."
    )

st.divider()

# =========================================================================
# MAPA 2 — Centrado (hallazgo principal)
# =========================================================================
st.header("Mapa 2 — Centrado (hallazgo principal)")

with st.container(border=True):
    fig_centrado = px.choropleth(
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
    )
    fig_centrado.update_geos(fitbounds="locations", visible=False)
    fig_centrado.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=550)

    st.plotly_chart(fig_centrado, use_container_width=True)
    st.caption(
        "Una vez descontada la ola nacional, el Pacífico y el sur se movieron por encima de la "
        "media nacional y el interior andino por debajo. El patrón territorial de la desviación "
        "coincide con la geografía de la regionalización del voto ya identificada en el EDA: el "
        "mapa no destapa un fenómeno nuevo, lo confirma con granularidad municipal."
    )

st.divider()

# =========================================================================
# TOP 20 municipios con mayor desviación
# =========================================================================
st.header("Los 20 municipios con mayor desviación")

with st.container(border=True):
    st.caption(
        "Ordenados por magnitud del residuo (valor absoluto). Se excluyen los municipios de baja "
        "confiabilidad electoral (menos de 30 votos emitidos) — no compiten por este ranking."
    )

    top20 = (
        df_confiabilidad_normal.reindex(
            df_confiabilidad_normal["residuo"].abs().sort_values(ascending=False).index
        )
        .head(20)[["municipio", "departamento", "residuo", "nbi_total", "per_ocu"]]
        .rename(
            columns={
                "municipio": "Municipio",
                "departamento": "Departamento",
                "residuo": "Residuo (pts)",
                "nbi_total": "NBI total",
                "per_ocu": "Per. ocupada (conflicto, depto.)",
            }
        )
    )
    top20["Residuo (pts)"] = top20["Residuo (pts)"].round(1)
    top20["NBI total"] = top20["NBI total"].round(1)

    st.dataframe(top20, use_container_width=True, hide_index=True)
    st.caption(TEXTO_RESIDUOS_BLINDADO)
