# ==============================================================================
# agregacion_2022.py
# Agrega los resultados electorales de 2022 (publicados a nivel de MESA por la
# Registraduria, ficheros MMV_NACIONAL_PRESIDENTE_2022_1v.csv / _2v.csv) a
# nivel municipio, y les asigna el codigo DIVIPOLA oficial de 5 digitos.
#
# HALLAZGO IMPORTANTE (documentado tambien en la bitacora privada de la fase 1):
# Los ficheros de 2022 usan columnas DEP/MUN con una codificacion INTERNA de
# la Registraduria que NO corresponde al codigo DIVIPOLA oficial (ej. en estos
# ficheros Antioquia = DEP 01, pero el DIVIPOLA oficial de Antioquia es 05).
# Por eso NO se puede construir el DIVIPOLA concatenando DEP+MUN como se hizo
# con los ficheros 1998-2018. En su lugar, se cruza por NOMBRE de departamento
# y municipio (normalizado) contra la tabla de referencia DIVIPOLA construida
# a partir del fichero de 2018 (que ya usa codigos DIVIPOLA verificados).
#
# Se detectaron ademas ~40 nombres de municipio abreviados/coloquiales en el
# fichero de 2022 que no coinciden textualmente con el nombre oficial DIVIPOLA
# (ej. "CUCUTA" en 2022 vs "SAN JOSE DE CUCUTA" oficial). Estos casos se
# resolvieron a mano, verificando cada uno contra el listado oficial completo
# del departamento correspondiente (ver diccionario CORRECCION_NOMBRES_MUNICIPIO).
# ==============================================================================

import unicodedata
import re
import pandas as pd

DEPNOMBRE_EXTERIOR = "CONSULADOS"  # se excluye, igual que coddpto=9 en 1998-2018

# Candidato de izquierda en 2022: Gustavo Petro, coalicion Pacto Historico.
# OJO: el codigo de CANDIDATO (CAN) cambia entre 1a vuelta ('006') y 2a
# vuelta ('002'), porque se reasigna al quedar solo 2 candidatos. El codigo
# de PARTIDO/coalicion (PAR='1235', Pacto Historico) SI es estable entre
# ambas vueltas, asi que se usa ese como identificador.
PAR_IZQUIERDA_2022 = "1235"

# Codigos especiales en el fichero de 2022 (OJO: son DISTINTOS a los usados
# en los ficheros 1998-2018, que eran 997/998/999). Aqui:
CAN_ESPECIALES_2022 = {"996", "997", "998"}  # blanco, nulos, no marcados

# Nombres de departamento truncados/abreviados en el fichero de 2022
CORRECCION_NOMBRES_DEPARTAMENTO = {
    "NORTE DE SAN": "NORTE DE SANTANDER",
    "VALLE": "VALLE DEL CAUCA",
    "SAN ANDRES": "ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA",
}

# Nombres de municipio abreviados/coloquiales en el fichero de 2022 que no
# coinciden con el nombre oficial DIVIPOLA. Clave: (departamento_normalizado,
# nombre_2022_normalizado_sin_alias_entre_parentesis). Verificado a mano
# contra el listado oficial completo de cada departamento.
CORRECCION_NOMBRES_MUNICIPIO = {
    ("VAUPES", "BUENOS AIRES"): "PACOA",
    ("VAUPES", "MORICHAL"): "PAPUNAHUA",
    ("META", "SAN MARTIN DE LOS LLANOS"): "SAN MARTIN",
    ("META", "VISTA HERMOSA"): "VISTAHERMOSA",
    ("VALLE DEL CAUCA", "BUGA"): "GUADALAJARA DE BUGA",
    ("TOLIMA", "MARIQUITA"): "SAN SEBASTIAN DE MARIQUITA",
    ("SUCRE", "SINCE"): "SAN LUIS DE SINCE",
    ("SUCRE", "TOLU"): "SANTIAGO DE TOLU",
    ("SUCRE", "TOLUVIEJO"): "SAN JOSE DE TOLUVIEJO",
    ("SANTANDER", "EL CARMEN"): "EL CARMEN DE CHUCURI",
    ("NORTE DE SANTANDER", "CUCUTA"): "SAN JOSE DE CUCUTA",
    ("NARINO", "CUASPUD"): "CUASPUD CARLOSAMA",
    ("NARINO", "EL TABLON"): "EL TABLON DE GOMEZ",
    ("NARINO", "TUMACO"): "SAN ANDRES DE TUMACO",
    ("CHOCO", "EL CARMEN"): "EL CARMEN DE ATRATO",
    ("CUNDINAMARCA", "UBATE"): "VILLA DE SAN DIEGO DE UBATE",
    ("CORDOBA", "PURISIMA"): "PURISIMA DE LA CONCEPCION",
    ("CAUCA", "LOPEZ"): "LOPEZ DE MICAY",
    ("CAUCA", "PIENDAMO"): "PIENDAMO TUNIA",
    ("CAUCA", "SOTARA"): "SOTARA PAISPAMBA",
    ("BOYACA", "GUICAN"): "GUICAN DE LA SIERRA",
    ("BOYACA", "VILLA DE LEIVA"): "VILLA DE LEYVA",
    ("BOLIVAR", "CARTAGENA"): "CARTAGENA DE INDIAS",
    ("BOLIVAR", "ARROYO HONDO"): "ARROYOHONDO",
    ("BOLIVAR", "MOMPOS"): "SANTA CRUZ DE MOMPOX",
    ("BOLIVAR", "RIOVIEJO"): "RIO VIEJO",
    ("ANTIOQUIA", "ANTIOQUIA"): "SANTA FE DE ANTIOQUIA",
    ("ANTIOQUIA", "BOLIVAR"): "CIUDAD BOLIVAR",
    ("ANTIOQUIA", "CARMEN DE VIBORAL"): "EL CARMEN DE VIBORAL",
    ("ANTIOQUIA", "DON MATIAS"): "DONMATIAS",
    ("ANTIOQUIA", "PUERTO NARE-LA MAGDALENA"): "PUERTO NARE",
    ("ANTIOQUIA", "SAN ANDRES"): "SAN ANDRES DE CUERQUIA",
    ("ANTIOQUIA", "SAN PEDRO"): "SAN PEDRO DE LOS MILAGROS",
    ("ANTIOQUIA", "SAN VICENTE"): "SAN VICENTE FERRER",
    ("ANTIOQUIA", "SANTUARIO"): "EL SANTUARIO",
    ("ANTIOQUIA", "YONDO-CASABE"): "YONDO",
}


def normalizar_texto(texto: str) -> str:
    """Mayusculas, sin tildes, sin puntos/comas, espacios simples."""
    if pd.isna(texto):
        return texto
    t = str(texto).upper()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[.,]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def quitar_alias_entre_parentesis(texto: str) -> str:
    """
    Elimina el alias entre parentesis de un nombre de municipio (ej.
    'BUENOS AIRES (PACOA)' -> 'BUENOS AIRES'). Tolera parentesis sin cerrar,
    ya que algunos nombres del fichero de 2022 vienen truncados.
    """
    return re.sub(r"\s*\(.*", "", texto).strip()


def construir_tabla_referencia_divipola(ruta_2018: str, encoding: str = "latin1") -> pd.DataFrame:
    """
    Construye la tabla de referencia departamento+municipio -> DIVIPOLA a
    partir del fichero de 2018 (1998-2018 ya usan codigo DIVIPOLA real y
    verificado en la columna codmpio).
    """
    ref = pd.read_csv(ruta_2018, encoding=encoding)
    ref = ref[["coddpto", "departamento", "codmpio", "municipio"]].drop_duplicates()
    ref["divipola"] = ref["codmpio"].astype(int).astype(str).str.zfill(5)
    ref["dep_norm"] = ref["departamento"].apply(normalizar_texto)
    ref["mun_norm"] = ref["municipio"].apply(normalizar_texto)
    return ref[["dep_norm", "mun_norm", "divipola"]]


def asignar_divipola_2022(df22_municipios: pd.DataFrame, tabla_referencia: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza el listado de departamento+municipio del fichero de 2022 contra la
    tabla de referencia DIVIPOLA, en 3 pasadas:
      1. match exacto de nombre normalizado
      2. match quitando alias entre parentesis
      3. correccion manual verificada (CORRECCION_NOMBRES_MUNICIPIO)
    Devuelve el mismo dataframe con la columna 'divipola' añadida.
    Lanza un aviso (no error) si queda algun municipio sin resolver, para que
    se revise antes de continuar.
    """
    df = df22_municipios.copy()
    df["dep_norm"] = df["DEPNOMBRE"].apply(normalizar_texto).replace(CORRECCION_NOMBRES_DEPARTAMENTO)
    df["mun_norm"] = df["MUNNOMBRE"].apply(normalizar_texto)
    df["mun_sin_alias"] = df["mun_norm"].apply(quitar_alias_entre_parentesis)

    # Pasada 1: match exacto
    df = df.merge(tabla_referencia, on=["dep_norm", "mun_norm"], how="left")

    # Pasada 2: match quitando alias entre parentesis (solo para los que fallaron)
    sin_match = df["divipola"].isna()
    ref_sin_alias = tabla_referencia.rename(columns={"mun_norm": "mun_sin_alias", "divipola": "divipola_alt"})
    df = df.merge(ref_sin_alias, on=["dep_norm", "mun_sin_alias"], how="left")
    df.loc[sin_match, "divipola"] = df.loc[sin_match, "divipola_alt"]
    df = df.drop(columns=["divipola_alt"])

    # Pasada 3: correccion manual verificada
    sin_match = df["divipola"].isna()
    for idx in df[sin_match].index:
        clave = (df.at[idx, "dep_norm"], df.at[idx, "mun_sin_alias"])
        nombre_oficial = CORRECCION_NOMBRES_MUNICIPIO.get(clave)
        if nombre_oficial is not None:
            match_ref = tabla_referencia[
                (tabla_referencia["dep_norm"] == clave[0]) & (tabla_referencia["mun_norm"] == nombre_oficial)
            ]
            if len(match_ref) == 1:
                df.at[idx, "divipola"] = match_ref.iloc[0]["divipola"]

    aun_sin_match = df[df["divipola"].isna()]
    if len(aun_sin_match) > 0:
        print("AVISO: quedan municipios sin DIVIPOLA asignado, revisar antes de continuar:")
        print(aun_sin_match[["DEPNOMBRE", "MUNNOMBRE"]].drop_duplicates().to_string())

    return df


def cargar_y_agregar_2022(path: str, ruta_referencia_2018: str, encoding: str = "latin1", sep: str = ";") -> pd.DataFrame:
    """
    Carga un fichero de 2022 a nivel de mesa (primera o segunda vuelta),
    excluye el voto exterior, agrega a nivel municipio, calcula pct_izquierda
    y pct_votos_blanco, y asigna el codigo DIVIPOLA oficial.
    """
    df = pd.read_csv(
        path, encoding=encoding, sep=sep,
        dtype={"CAN": str, "PAR": str, "DEP": str, "MUN": str},
        low_memory=False,
    )
    df = df[df["DEPNOMBRE"] != DEPNOMBRE_EXTERIOR].copy()
    df["VOTOS"] = df["VOTOS"].astype(int)

    # Votos validos = todo lo que no sea blanco/nulo/no-marcado
    df_validos = df[~df["CAN"].isin(CAN_ESPECIALES_2022)]
    agregados = df_validos.groupby(["DEP", "DEPNOMBRE", "MUN", "MUNNOMBRE"], as_index=False).agg(
        votos_validos=("VOTOS", "sum"),
        num_candidatos=("CAN", "nunique"),
    )

    votos_blanco = (
        df[df["CAN"] == "996"]
        .groupby(["DEP", "MUN"], as_index=False)["VOTOS"].sum()
        .rename(columns={"VOTOS": "votos_blanco"})
    )
    votos_nulos = (
        df[df["CAN"] == "997"]
        .groupby(["DEP", "MUN"], as_index=False)["VOTOS"].sum()
        .rename(columns={"VOTOS": "votos_nulos"})
    )
    votos_izquierda = (
        df[df["PAR"] == PAR_IZQUIERDA_2022]
        .groupby(["DEP", "MUN"], as_index=False)["VOTOS"].sum()
        .rename(columns={"VOTOS": "votos_izquierda"})
    )

    agregados = agregados.merge(votos_blanco, on=["DEP", "MUN"], how="left")
    agregados = agregados.merge(votos_nulos, on=["DEP", "MUN"], how="left")
    agregados = agregados.merge(votos_izquierda, on=["DEP", "MUN"], how="left")
    agregados[["votos_blanco", "votos_nulos", "votos_izquierda"]] = agregados[
        ["votos_blanco", "votos_nulos", "votos_izquierda"]
    ].fillna(0)

    agregados["votos_totales_emitidos"] = (
        agregados["votos_validos"] + agregados["votos_blanco"] + agregados["votos_nulos"]
    )
    agregados["pct_votos_blanco"] = agregados["votos_blanco"] / agregados["votos_totales_emitidos"] * 100
    agregados["pct_izquierda"] = agregados["votos_izquierda"] / agregados["votos_validos"] * 100

    # Asignar DIVIPOLA oficial vía crosswalk por nombre
    tabla_referencia = construir_tabla_referencia_divipola(ruta_referencia_2018)
    agregados = asignar_divipola_2022(agregados, tabla_referencia)

    agregados["ano"] = 2022
    columnas = [
        "divipola", "ano", "DEPNOMBRE", "MUNNOMBRE",
        "votos_validos", "votos_izquierda", "pct_izquierda",
        "votos_blanco", "votos_nulos", "votos_totales_emitidos",
        "pct_votos_blanco", "num_candidatos",
    ]
    agregados = agregados.rename(columns={"DEPNOMBRE": "departamento", "MUNNOMBRE": "municipio"})
    columnas = [c.replace("DEPNOMBRE", "departamento").replace("MUNNOMBRE", "municipio") for c in columnas]
    return agregados[columnas]
