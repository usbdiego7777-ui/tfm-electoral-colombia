"""
Enrutador de la app — TFM Electoral Colombia.

Este es el fichero de entrada (el que se pasa a `streamlit run` y el configurado como
"Main file path" en Streamlit Cloud). Desde que se usa st.navigation()/st.Page(), este
fichero deja de contener el contenido de la Página 1 directamente — ese contenido vive en
app/pagina1_explorador.py. Aquí solo se hace de "marco": configuración global, texto del
panel lateral (colocado ANTES de declarar la navegación, para que aparezca por encima del
menú de páginas — al contrario que con la carpeta app/pages/ automática, donde el menú
siempre se coloca primero sin poder controlarlo), y la lista de páginas disponibles.

Nota: al llamar a st.navigation(), Streamlit deja de usar la detección automática de la
carpeta app/pages/ — la lista de páginas de abajo es ahora la única fuente de verdad sobre
qué páginas existen y en qué orden aparecen.
"""

import streamlit as st

from data_utils import aplicar_estilo

st.set_page_config(page_title="TFM Electoral Colombia", layout="wide")
aplicar_estilo()

pagina_explorador = st.Page(
    "pagina1_explorador.py",
    title="Explorador territorial",
    icon="🗺️",
    default=True,
)
pagina_prediccion = st.Page(
    "pages/2_Prediccion_y_analisis_individual.py",
    title="Predicción y análisis individual",
    icon="🔍",
)
pagina_residuos = st.Page(
    "pages/3_Rompen_su_tendencia.py",
    title="Rompen su tendencia",
    icon="📍",
)

# Menú lateral construido a mano con st.page_link(), en vez de dejar que
# st.navigation() dibuje su propio widget automático — ese widget se coloca
# siempre arriba del todo del panel lateral sin importar el orden del código
# (limitación conocida de Streamlit, confirmada en discuss.streamlit.io/t/
# st-navigation-menu-is-forced-to-the-top-of-the-sidebar y en el issue
# streamlit/streamlit#11788, todavía abierto a fecha de este commit). Con
# position="hidden" se apaga ese widget automático y se controla el orden
# real: primero el texto, luego el menú.
with st.sidebar:
    st.markdown(
        "*Inercia, pobreza y regionalización del voto de izquierda a nivel municipal "
        "(2006–2022). Herramienta de comprensión del voto territorial para analistas, "
        "investigadores y periodistas de datos.*"
    )
    st.divider()
    st.page_link(pagina_explorador)
    st.page_link(pagina_prediccion)
    st.page_link(pagina_residuos)

pagina_actual = st.navigation(
    [pagina_explorador, pagina_prediccion, pagina_residuos],
    position="hidden",
)
pagina_actual.run()
