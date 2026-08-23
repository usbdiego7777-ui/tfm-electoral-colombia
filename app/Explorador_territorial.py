"""
Enrutador de la app — TFM Electoral Colombia.

Fichero de entrada (el que se pasa a `streamlit run` y el configurado como "Main file
path" en Streamlit Cloud). El contenido de la Página 1 vive en app/pagina1_explorador.py;
aquí solo se hace de "marco": configuración global, texto del panel lateral y la lista de
páginas disponibles.

Al usar st.navigation()/st.Page(), Streamlit deja de detectar automáticamente la carpeta
app/pages/ — la lista de páginas de abajo pasa a ser la única fuente de verdad sobre qué
páginas existen y en qué orden aparecen.
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

# El widget de navegación automático de Streamlit siempre se coloca arriba del todo del
# panel lateral, sin importar el orden del código, así que el menú se construye a mano
# con st.page_link() (con position="hidden" para apagar el widget automático) — así el
# texto de presentación puede ir antes que el menú de páginas.
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
