"""
Página 2 — Predicción y análisis individual.

Selector de municipio y año → carga el dato real ya procesado (tabla_residuos.csv).
2010/2014/2018/2022 tienen residuo; 2006 se maneja explícitamente (no es año de test
de ninguna ventana, no aparece en tabla_residuos.csv — se muestra solo el voto real).
"""

import streamlit as st

from data_utils import (
    cargar_dataset_maestro,
    cargar_tabla_residuos,
    TEXTO_RESIDUOS_BLINDADO,
)

st.set_page_config(page_title="Predicción y análisis individual — TFM Electoral Colombia", layout="wide")

st.title("2. Predicción y análisis individual")
st.caption(
    "Consulta un municipio y un año concretos: voto real, voto que predice su propia "
    "trayectoria histórica, y la diferencia entre ambos."
)

df_maestro = cargar_dataset_maestro()
df_residuos = cargar_tabla_residuos()

# -------------------------------------------------------------------
# Selectores — departamento primero, porque 67 nombres de municipio se
# repiten en más de un departamento (verificado contra el dataset real)
# -------------------------------------------------------------------
col_depto, col_municipio, col_anio = st.columns([1, 1, 1])

with col_depto:
    departamentos = sorted(df_maestro["departamento"].unique())
    departamento_sel = st.selectbox("Departamento", departamentos)

with col_municipio:
    municipios_depto = sorted(
        df_maestro[df_maestro["departamento"] == departamento_sel]["municipio"].unique()
    )
    municipio_sel = st.selectbox("Municipio", municipios_depto)

# divipola único para este departamento+municipio (evita ambigüedad de nombre)
divipola_sel = df_maestro[
    (df_maestro["departamento"] == departamento_sel) & (df_maestro["municipio"] == municipio_sel)
]["divipola"].iloc[0]

with col_anio:
    anios_disponibles = sorted(
        df_maestro[df_maestro["divipola"] == divipola_sel]["ano"].unique()
    )
    anio_sel = st.selectbox(
        "Año",
        anios_disponibles,
        index=len(anios_disponibles) - 1,
    )

st.divider()

# -------------------------------------------------------------------
# Datos del municipio-año seleccionado
# -------------------------------------------------------------------
fila_maestro = df_maestro[
    (df_maestro["divipola"] == divipola_sel) & (df_maestro["ano"] == anio_sel)
]

if fila_maestro.empty:
    st.warning(f"No hay dato electoral para {municipio_sel} ({departamento_sel}) en {anio_sel}.")
    st.stop()

fila_maestro = fila_maestro.iloc[0]
voto_real = fila_maestro["pct_izquierda"]

st.subheader(f"{municipio_sel} ({departamento_sel}) — {anio_sel}")

if fila_maestro.get("valido_para_modelado", 1) == 0:
    st.info(
        "Este municipio-año está marcado como no válido para modelado (0 votos registrados). "
        "Se muestra el dato disponible con esta advertencia."
    )

# Caso 2006 explícito: no es año de test de ninguna ventana, no tiene residuo
if anio_sel == 2006:
    st.metric("Voto real (% izquierda)", f"{voto_real:.1f}%")
    st.info(
        "2006 es el inicio de la serie objetivo y no es año de test de ninguna ventana de "
        "validación — no tiene voto predicho ni residuo asociado. Solo se muestra el voto real."
    )
else:
    fila_residuo = df_residuos[
        (df_residuos["divipola"] == divipola_sel) & (df_residuos["ano"] == anio_sel)
    ]

    if fila_residuo.empty:
        # No debería ocurrir para 2010/2014/2018/2022 salvo el caso conocido de Mapiripana 2022
        st.metric("Voto real (% izquierda)", f"{voto_real:.1f}%")
        st.warning(
            "Este municipio no tiene fila en la tabla de residuos para este año "
            "(caso conocido: Mapiripana, Guainía, ausente en la fuente electoral de 2022)."
        )
    else:
        r = fila_residuo.iloc[0]
        voto_predicho = r["pct_izquierda_predicho"]
        residuo = r["residuo"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Voto real", f"{voto_real:.1f}%")
        col2.metric("Voto predicho por su historia", f"{voto_predicho:.1f}%")
        col3.metric("Residuo", f"{residuo:+.1f} pts")

        # Indicador visual — umbrales verificados contra la distribución real de
        # |residuo| en municipios de confiabilidad normal: <10 (~40% de los casos),
        # 10-25 (~42%), >=25 (~18%).
        residuo_abs = abs(residuo)
        if residuo_abs < 10:
            color, etiqueta = "🟢", "Sigue su tendencia histórica"
        elif residuo_abs < 25:
            color, etiqueta = "🟠", "Se desvía moderadamente de su tendencia"
        else:
            color, etiqueta = "🔴", "Se desvía fuertemente de su tendencia"

        st.markdown(f"### {color} {etiqueta}")

        sentido = "más a la izquierda" if residuo > 0 else "menos a la izquierda"
        st.markdown(
            f"Este municipio votó **{residuo_abs:.1f} puntos {sentido}** de lo que su propia "
            f"historia electoral predice para {anio_sel}."
        )

        if r["baja_confiabilidad_electoral"] == 1:
            st.warning(
                "⚠️ Este municipio tiene baja confiabilidad electoral (menos de 30 votos "
                "emitidos). El residuo mostrado no es representativo — no debe tratarse como "
                "una anomalía real."
            )

        if anio_sel == 2010:
            st.caption(
                "Nota: 2010 corresponde a una ventana de entrenamiento inestable "
                "(n=1 elección + shock Mockus). Este residuo se reporta por completitud, "
                "no se promedia con las ventanas estables."
            )

        st.caption(TEXTO_RESIDUOS_BLINDADO)
