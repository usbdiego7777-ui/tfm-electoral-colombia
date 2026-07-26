# ==============================================================================
# preprocesamiento.py
# Funciones para extraer y consolidar el % de voto de izquierda por municipio
# y año a partir de los ficheros electorales de primera vuelta de la
# Registraduria Nacional (1998-2018). El fichero de 2022 (nivel mesa) se trata
# aparte con un script de agregacion, ya que no esta en el mismo formato.
# ==============================================================================

import pandas as pd

# ------------------------------------------------------------------------
# 1. Diccionario de mapeo: año -> codigo_lista del candidato de izquierda
#    (linea Polo Democratico -> Colombia Humana -> Pacto Historico)
#    1998 no tiene bloque de izquierda consolidado (el Polo se funda en 2005),
#    por lo que ese año no aporta valor de pct_izquierda.
# ------------------------------------------------------------------------
CODIGO_LISTA_IZQUIERDA = {
    2002: 1,   # Luis Eduardo Garzon (Polo) - solo historico/lag
    2006: 4,   # Carlos Gaviria (Polo) - inicio serie objetivo
    2010: 5,   # Gustavo Petro (Polo)
    2014: 1,   # Clara Lopez (Polo)
    2018: 1,   # Gustavo Petro (Colombia Humana)
    # 2022 usa un formato distinto (nivel mesa, columnas CAN/PAR) -> ver
    # agregacion_2022.py. Gustavo Petro (Pacto Historico): CAN='006', PAR='1235'
}

# Codigos especiales que NO son votos a un candidato real
CODIGOS_ESPECIALES = {997, 998, 999}  # tarjetas no marcadas, votos nulos, votos en blanco
CODDPTO_EXTERIOR = 9  # voto de colombianos en el exterior - se excluye (sin DIVIPOLA municipal real)

# Correccion de errores tipograficos REALES detectados en los ficheros
# oficiales de la Registraduria (verificados cruzando contra los otros años
# y contra el NBI, que coinciden entre si). Sin esta correccion, el
# municipio queda con un codigo DIVIPOLA distinto solo en el año afectado,
# rompiendo silenciosamente tanto el cruce con NBI/PER_OCU como el lag
# electoral (el fallback de imputacion lo absorbe sin fallar, pero se
# pierde informacion real que si tenemos disponible).
# Clave: (año, codigo_incorrecto) -> codigo_correcto
CORRECCION_CODIGOS_DIVIPOLA = {
    (2010, 27415): 27425,  # Medio Atrato, Choco: el fichero de 2010 trae 27415;
                           # 2006, 2014, 2018 y ambos NBI usan 27425 (correcto)
}


def cargar_fichero_electoral(path: str, encoding: str = "latin1", sep: str = ",") -> pd.DataFrame:
    """
    Carga un fichero electoral de la Registraduria (1998-2018) y aplica la
    exclusion metodologica acordada: se descarta coddpto == 9 (voto en el
    exterior), porque esos registros no corresponden a ningun municipio real
    de Colombia y no tienen DIVIPOLA, NBI ni PER_OCU asociable.
    """
    df = pd.read_csv(path, encoding=encoding, sep=sep)
    df = df[df["coddpto"] != CODDPTO_EXTERIOR].copy()
    return df


def corregir_codigos_divipola_conocidos(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Aplica las correcciones de CORRECCION_CODIGOS_DIVIPOLA que apliquen a este año."""
    df = df.copy()
    for (ano_afectado, codigo_incorrecto), codigo_correcto in CORRECCION_CODIGOS_DIVIPOLA.items():
        if ano == ano_afectado:
            n_afectadas = (df["codmpio"] == codigo_incorrecto).sum()
            if n_afectadas > 0:
                df.loc[df["codmpio"] == codigo_incorrecto, "codmpio"] = codigo_correcto
                print(f"  Corregido: {n_afectadas} filas de {ano} con codmpio={codigo_incorrecto} -> {codigo_correcto}")
    return df


def extraer_pct_izquierda_municipio(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    """
    Dado el dataframe crudo de un año (ya sin voto exterior), calcula por
    municipio (codigo DIVIPOLA = columna 'codmpio'):
      - votos_validos: suma de votos a candidatos reales (excluye 997/998/999)
      - votos_izquierda: votos al candidato de la linea Polo/CH/Pacto Historico
        (NaN si el año no tiene bloque de izquierda consolidado, ej. 1998)
      - pct_izquierda: % de voto de izquierda sobre votos validos
      - num_candidatos: numero de candidatos reales que compitieron
      - votos_blanco, votos_nulos: para calculos posteriores de participacion

    Devuelve un dataframe con una fila por municipio.
    """
    # Votos a candidatos reales (excluye las 3 categorias especiales)
    df_validos = df[~df["codigo_lista"].isin(CODIGOS_ESPECIALES)]

    agregados = df_validos.groupby(
        ["codmpio", "coddpto", "departamento", "municipio"], as_index=False
    ).agg(
        votos_validos=("votos", "sum"),
        num_candidatos=("codigo_lista", "nunique"),
    )

    # Votos en blanco y nulos (para % de abstencion/participacion en pasos futuros)
    votos_blanco = (
        df[df["codigo_lista"] == 999]
        .groupby("codmpio", as_index=False)["votos"].sum()
        .rename(columns={"votos": "votos_blanco"})
    )
    votos_nulos = (
        df[df["codigo_lista"] == 998]
        .groupby("codmpio", as_index=False)["votos"].sum()
        .rename(columns={"votos": "votos_nulos"})
    )

    agregados = agregados.merge(votos_blanco, on="codmpio", how="left")
    agregados = agregados.merge(votos_nulos, on="codmpio", how="left")
    agregados[["votos_blanco", "votos_nulos"]] = agregados[["votos_blanco", "votos_nulos"]].fillna(0)

    # NOTA METODOLOGICA: la Registraduria no publica el censo electoral
    # historico por municipio en formato descargable (solo un consultor
    # individual por cedula y un tablero de conteo de votos, no de censo).
    # Por eso NO se puede calcular la abstencion real (1 - votantes/censo).
    # Como proxy se usa el % de votos en blanco sobre el total de sufragios
    # emitidos (validos + blanco + nulo). Se documenta como limitacion en
    # la memoria (seccion de Datos / Limitaciones).
    agregados["votos_totales_emitidos"] = (
        agregados["votos_validos"] + agregados["votos_blanco"] + agregados["votos_nulos"]
    )
    agregados["pct_votos_blanco"] = (
        agregados["votos_blanco"] / agregados["votos_totales_emitidos"] * 100
    )

    # Votos al candidato de izquierda (si el año tiene bloque consolidado)
    codigo_izq = CODIGO_LISTA_IZQUIERDA.get(ano)
    if codigo_izq is not None:
        votos_izq = (
            df[df["codigo_lista"] == codigo_izq]
            .groupby("codmpio", as_index=False)["votos"].sum()
            .rename(columns={"votos": "votos_izquierda"})
        )
        agregados = agregados.merge(votos_izq, on="codmpio", how="left")
        agregados["votos_izquierda"] = agregados["votos_izquierda"].fillna(0)
        agregados["pct_izquierda"] = (
            agregados["votos_izquierda"] / agregados["votos_validos"] * 100
        )
    else:
        agregados["votos_izquierda"] = pd.NA
        agregados["pct_izquierda"] = pd.NA

    # DIVIPOLA de 5 digitos como texto (ej. 5001 -> '05001'), clave de cruce oficial
    agregados["divipola"] = agregados["codmpio"].astype(int).astype(str).str.zfill(5)
    agregados["ano"] = ano

    columnas = [
        "divipola", "ano", "coddpto", "departamento", "municipio",
        "votos_validos", "votos_izquierda", "pct_izquierda",
        "votos_blanco", "votos_nulos", "votos_totales_emitidos",
        "pct_votos_blanco", "num_candidatos",
    ]
    return agregados[columnas]


def construir_serie_izquierda(rutas_por_ano: dict, encoding: str = "latin1") -> pd.DataFrame:
    """
    Recorre varios ficheros (uno por año) y devuelve un unico dataframe
    consolidado con una fila por municipio y año.

    rutas_por_ano: dict {ano: ruta_del_fichero}
    """
    resultados = []
    for ano, ruta in sorted(rutas_por_ano.items()):
        df_crudo = cargar_fichero_electoral(ruta, encoding=encoding)
        df_crudo = corregir_codigos_divipola_conocidos(df_crudo, ano)
        df_ano = extraer_pct_izquierda_municipio(df_crudo, ano)
        resultados.append(df_ano)
        print(f"  {ano}: {len(df_ano)} municipios procesados")

    serie = pd.concat(resultados, ignore_index=True)
    return serie


# ------------------------------------------------------------------------
# 2. Variable(s) lag: valor de una columna en la eleccion INMEDIATAMENTE
#    anterior, en el mismo municipio. Se calcula por merge explicito
#    año->año anterior (no por shift posicional), para evitar
#    desalineaciones si un municipio no tiene fila en algun año (ej.
#    municipios nuevos o sin dato ese año). Esto GARANTIZA que nunca se
#    cruza la frontera train/test: el lag de 2022 solo puede venir de
#    2018, nunca de 2022 ni de años futuros.
#
# IMPORTANTE (correccion metodologica, revision cruzada de otros chats del
# proyecto): pct_votos_blanco DEL MISMO AÑO no puede usarse como predictor,
# porque se determina en la misma urna y al mismo tiempo que pct_izquierda
# - no es informacion disponible "antes" del resultado. Se calcula tambien
# su lag (lag_pct_votos_blanco) para usar como predictor; el pct_votos_blanco
# del año en curso queda solo como variable DESCRIPTIVA para el EDA, nunca
# como feature del modelo (ver COLUMNAS_PREDICTORAS / COLUMNAS_DESCRIPTIVAS
# mas abajo).
# ------------------------------------------------------------------------
ANO_ANTERIOR = {
    2006: 2002,
    2010: 2006,
    2014: 2010,
    2018: 2014,
    2022: 2018,
}


def calcular_lag_variable(panel: pd.DataFrame, columna: str, nombre_lag: str = None) -> pd.DataFrame:
    """
    Version generica: calcula el lag de CUALQUIER columna del panel (ej.
    'pct_izquierda' o 'pct_votos_blanco'), devolviendo solo las filas de
    los AÑOS OBJETIVO con una columna nueva 'lag_<columna>' (o el nombre
    que se indique en nombre_lag).
    """
    nombre_lag = nombre_lag or f"lag_{columna}"
    resultados = []
    for ano_objetivo, ano_anterior in ANO_ANTERIOR.items():
        actual = panel[panel["ano"] == ano_objetivo].copy()
        anterior = (
            panel[panel["ano"] == ano_anterior][["divipola", columna]]
            .rename(columns={columna: nombre_lag})
        )
        actual = actual.merge(anterior, on="divipola", how="left")
        resultados.append(actual)
    return pd.concat(resultados, ignore_index=True)


def calcular_variable_lag(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula lag_pct_izquierda Y lag_pct_votos_blanco en un solo paso, e
    imputa los casos sin lag disponible (municipio sin fila en el año
    anterior: municipios muy remotos con 0 votos, o municipios de creacion
    reciente) con la MEDIA DEPARTAMENTAL de ese mismo año objetivo -no con
    cero ni con la media nacional, que distorsionarian mas-. Cada
    imputacion queda marcada con una bandera explicita, nunca oculta.

    OJO: ambos lags se calculan por separado A PARTIR DEL PANEL ORIGINAL
    (que incluye 1998-2022), no de forma encadenada, porque
    calcular_lag_variable() ya filtra su resultado a solo los años
    objetivo - encadenar perderia el año de referencia (ej. 2002) para el
    segundo calculo.
    """
    con_lag_izq = calcular_lag_variable(panel, "pct_izquierda", "lag_pct_izquierda")
    con_lag_blanco = calcular_lag_variable(panel, "pct_votos_blanco", "lag_pct_votos_blanco")

    resultado = con_lag_izq.merge(
        con_lag_blanco[["divipola", "ano", "lag_pct_votos_blanco"]],
        on=["divipola", "ano"], how="left",
    )

    for columna_lag in ["lag_pct_izquierda", "lag_pct_votos_blanco"]:
        col_imputado = f"{columna_lag}_imputado"
        resultado[col_imputado] = resultado[columna_lag].isna().astype(int)
        media_departamental = (
            resultado.groupby(["departamento", "ano"])[columna_lag].transform("mean")
        )
        resultado[columna_lag] = resultado[columna_lag].fillna(media_departamental)
        # Si ni siquiera hay otros municipios del departamento con lag ese año
        # (caso extremo), se deja NaN para que no pase desapercibido en el
        # paso de verificacion de calidad, en vez de forzar un valor.
        n_imputados = resultado[col_imputado].sum()
        n_aun_sin_valor = resultado[columna_lag].isna().sum()
        if n_imputados > 0:
            print(f"AVISO: {n_imputados} filas de '{columna_lag}' imputadas con la media departamental del año (marcadas en '{col_imputado}').")
        if n_aun_sin_valor > 0:
            print(f"AVISO: {n_aun_sin_valor} filas de '{columna_lag}' SIGUEN sin valor tras imputar (ni el departamento tenia dato ese año) - revisar a mano.")

    # Peso muestral sugerido para el modelado (sklearn sample_weight): usar
    # votos_totales_emitidos en vez de excluir municipios de baja votacion.
    # Un municipio con 10 votos totales pesa mucho menos en el ajuste que
    # uno con 50.000, sin descartarlo del analisis de residuos - ahi se
    # debe distinguir explicitamente "residuo alto con votacion robusta" de
    # "residuo extremo con pocos votos" (paso de analisis de residuos, no
    # de preprocesamiento).
    resultado["peso_muestral"] = resultado["votos_totales_emitidos"]

    return resultado


# Columnas que SI pueden usarse como predictoras en el modelo (disponibles
# antes de conocer el resultado de la eleccion objetivo)
COLUMNAS_PREDICTORAS = [
    "lag_pct_izquierda", "lag_pct_izquierda_imputado",
    "lag_pct_votos_blanco", "lag_pct_votos_blanco_imputado",
    "nbi_total",   # NBI municipal (2005 para 1998-2010, 2018 para 2014-2022)
    "per_ocu",     # PER_OCU departamental del MISMO año electoral (ver src/integrar_victimas.py)
]

# Columnas que son descriptivas o de diagnostico, NUNCA features del modelo
# (se determinan en la misma eleccion que se quiere predecir, o son
# variables de identificacion/peso/calidad)
COLUMNAS_DESCRIPTIVAS_NO_PREDICTORAS = [
    "pct_votos_blanco",       # del año EN CURSO - misma urna que el objetivo
    "votos_validos", "votos_izquierda", "votos_blanco", "votos_nulos",
    "votos_totales_emitidos", "num_candidatos",
    "peso_muestral",          # se usa como sample_weight, no como feature
    "fuente_nbi",             # metadato (que censo se uso), no predictor
    "baja_confiabilidad_electoral",  # bandera de calidad, no predictor
    "valido_para_modelado",   # filtro de filas, no predictor (excluir donde =0)
]
