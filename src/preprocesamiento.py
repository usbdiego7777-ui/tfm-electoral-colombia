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
    # 2022 se añade con su propio script de agregacion mesa -> municipio
}

# Codigos especiales que NO son votos a un candidato real
CODIGOS_ESPECIALES = {997, 998, 999}  # tarjetas no marcadas, votos nulos, votos en blanco
CODDPTO_EXTERIOR = 9  # voto de colombianos en el exterior - se excluye (sin DIVIPOLA municipal real)


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
        df_ano = extraer_pct_izquierda_municipio(df_crudo, ano)
        resultados.append(df_ano)
        print(f"  {ano}: {len(df_ano)} municipios procesados")

    serie = pd.concat(resultados, ignore_index=True)
    return serie
