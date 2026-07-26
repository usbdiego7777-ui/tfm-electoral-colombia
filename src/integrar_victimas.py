# ==============================================================================
# integrar_victimas.py
# Integra la variable PER_OCU (personas victimizadas por ocurrencia del hecho,
# UARIV) al panel electoral, como covariable DEPARTAMENTAL de intensidad del
# conflicto armado (cada municipio hereda el valor de su departamento, ya que
# la fuente oficial no tiene granularidad municipal).
#
# DECISION METODOLOGICA (confirmada con el usuario, revisada por el chat
# principal del proyecto): PER_OCU se incorpora del MISMO año electoral, NO
# rezagado. A diferencia de pct_votos_blanco (informacion de la urna del
# propio año, por eso SI se rezaga), PER_OCU es una caracteristica
# estructural del territorio (intensidad del conflicto), un dato publico
# disponible con anterioridad a la celebracion de las elecciones - no es
# informacion generada por la votacion en si. Rezagarlo introduciria ademas
# perdida de precision innecesaria (ej. usar el conflicto de 2018 para
# explicar el voto de 2022).
# ==============================================================================

import pandas as pd

COD_DEPTO_SIN_DEFINIR = 0  # registros sin departamento asignable - se excluyen


def cargar_victimas(path: str) -> pd.DataFrame:
    """
    Carga VICTIMAS_FILTRADO_V2.csv (ya corregido y agregado por
    src/filtrar_victimas.py: 1 fila por año x departamento, sin el
    problema de doble conteo de los cortes mensuales apilados). Excluye
    'SIN DEFINIR' (COD_ESTADO_DEPTO=0), que no es un departamento real y no
    puede heredarse a ningun municipio.
    """
    df = pd.read_csv(path)
    df = df[df["COD_ESTADO_DEPTO"] != COD_DEPTO_SIN_DEFINIR].copy()
    df["coddpto_str"] = df["COD_ESTADO_DEPTO"].astype(str).str.zfill(2)
    return df[["VIGENCIA", "coddpto_str", "ESTADO_DEPTO", "PER_OCU"]]


def integrar_victimas(panel: pd.DataFrame, ruta_victimas: str) -> pd.DataFrame:
    """
    Añade 'per_ocu' al panel electoral: PER_OCU del MISMO año que la
    eleccion, para el departamento al que pertenece cada municipio (los 2
    primeros digitos del codigo DIVIPOLA). Avisa si queda algun municipio
    sin PER_OCU asignado (departamento sin dato ese año), para revisar en
    el paso de verificacion de calidad.
    """
    victimas = cargar_victimas(ruta_victimas)

    panel = panel.copy()
    panel["coddpto_str"] = panel["divipola"].str[:2]

    panel_con_victimas = panel.merge(
        victimas[["VIGENCIA", "coddpto_str", "PER_OCU"]],
        left_on=["ano", "coddpto_str"], right_on=["VIGENCIA", "coddpto_str"],
        how="left",
    )
    panel_con_victimas = panel_con_victimas.rename(columns={"PER_OCU": "per_ocu"}).drop(columns=["VIGENCIA"])

    # IMPORTANTE: la ausencia de una fila (departamento, año) en
    # VICTIMAS_FILTRADO_V2.csv NO es un hueco de datos - el fichero se
    # construye con un groupby().sum() sobre el microdato de la UARIV, que
    # solo genera una fila si hubo AL MENOS un registro ese año. Un
    # departamento-año ausente significa CERO victimas registradas ese año,
    # no un dato faltante. Verificado con San Andres (departamento pequeño e
    # insular, con varios años en cero incluso en su historial 1998-2019):
    # no tiene ninguna fila desde 2020, consistente con cero victimizacion
    # registrada, no con un problema de cobertura de la fuente.
    n_sin_fila = panel_con_victimas["per_ocu"].isna().sum()
    if n_sin_fila > 0:
        print(f"NOTA: {n_sin_fila} filas sin registro en VICTIMAS_FILTRADO_V2.csv - se interpretan como 0 victimas (ausencia de registro en la fuente UARIV para ese departamento-año), no como dato faltante:")
        sin_fila = panel_con_victimas[panel_con_victimas["per_ocu"].isna()][["divipola", "ano", "departamento"]].drop_duplicates()
        print(sin_fila.to_string())
        panel_con_victimas["per_ocu"] = panel_con_victimas["per_ocu"].fillna(0)

    # 'coddpto_str' es un helper interno solo para el merge por codigo de
    # departamento - nunca debe filtrarse al dataset final (se detecto que
    # se colaba en la version anterior de este pipeline, corregido aqui en
    # el origen para que la limpieza no dependa de un paso manual externo).
    panel_con_victimas = panel_con_victimas.drop(columns=["coddpto_str"])

    return panel_con_victimas
