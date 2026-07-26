# ==============================================================================
# verificar_calidad_y_finalizar.py
# Ultimo paso de la fase de preprocesamiento: verificacion de calidad del
# dataset maestro (duplicados, nulos, consistencia de nombres, rangos) y
# guardado del fichero final en datos/procesados/.
#
# Se ejecuta DESPUES de: construir_serie_izquierda + cargar_y_agregar_2022
# (electoral) -> calcular_variable_lag (lag) -> integrar_nbi -> integrar_victimas
# ==============================================================================

import pandas as pd


def construir_tabla_nombres_canonicos(ruta_2018: str, encoding: str = "latin1") -> pd.DataFrame:
    """
    Construye la tabla de nombres canonicos (divipola -> departamento,
    municipio) directamente desde el fichero electoral de 2018, que ya se
    usa como referencia DIVIPOLA en el resto del proyecto (ver
    src/agregacion_2022.py). Se genera en memoria a partir del fichero
    fuente versionado en datos/raw/ - NUNCA depende de un CSV auxiliar
    suelto sin versionar (correccion de un vacio de reproducibilidad
    detectado al construir el notebook 01_preprocesamiento.ipynb: la
    version anterior de esta funcion leia un 'nombres_canonicos.csv' que
    nunca llego a subirse al repositorio).
    """
    ref = pd.read_csv(ruta_2018, encoding=encoding)
    ref = ref[["codmpio", "departamento", "municipio"]].drop_duplicates(subset="codmpio")
    ref["divipola"] = ref["codmpio"].astype(int).astype(str).str.zfill(5)
    return ref[["divipola", "departamento", "municipio"]]


def estandarizar_nombres(panel: pd.DataFrame, ruta_referencia_2018: str) -> pd.DataFrame:
    """
    Reemplaza 'departamento' y 'municipio' del panel por el nombre CANONICO
    (tomado del fichero de 2018, ya usado como referencia de DIVIPOLA en
    otras partes del proyecto), para TODOS los años.

    ruta_referencia_2018: ruta al fichero electoral CRUDO de 2018 (el mismo
    que se usa en src/agregacion_2022.py como referencia), NO a un CSV
    auxiliar pre-construido - la tabla canonica se genera en memoria con
    construir_tabla_nombres_canonicos(), para que el pipeline completo sea
    reproducible desde los ficheros fuente de datos/raw/ sin depender de
    ningun artefacto intermedio sin versionar.

    HALLAZGO que motiva esta funcion: se detectaron 232 codigos DIVIPOLA
    cuyo nombre de departamento y/o municipio varia segun el año (ej. "VALLE"
    en el fichero de 2022 vs "VALLE DEL CAUCA" en el resto; "BOGOTA D.C." vs
    "BOGOTA DC"; variaciones de tildes entre fuentes). El CODIGO ya era
    consistente (los cruces de datos son correctos, se hacen por divipola,
    nunca por nombre) - el problema es puramente de presentacion, pero es
    real: sin esta estandarizacion, cualquier groupby o mapa por nombre de
    departamento/municipio en el EDA o en Streamlit separaria erroneamente
    un mismo territorio en dos categorias distintas.
    """
    ref = construir_tabla_nombres_canonicos(ruta_referencia_2018)
    ref = ref.rename(columns={"departamento": "departamento_canonico", "municipio": "municipio_canonico"})

    panel = panel.merge(ref, on="divipola", how="left")
    n_sin_nombre_canonico = panel["departamento_canonico"].isna().sum()
    if n_sin_nombre_canonico > 0:
        print(f"AVISO: {n_sin_nombre_canonico} filas sin nombre canonico (divipola no encontrado en la referencia de 2018) - revisar a mano.")

    # Donde SI hay nombre canonico, se reemplaza; donde no (caso raro), se
    # conserva el nombre original de esa fila en vez de dejarlo en blanco.
    panel["departamento"] = panel["departamento_canonico"].fillna(panel["departamento"])
    panel["municipio"] = panel["municipio_canonico"].fillna(panel["municipio"])
    panel = panel.drop(columns=["departamento_canonico", "municipio_canonico"])
    return panel


def marcar_confiabilidad_electoral(panel: pd.DataFrame, umbral_votos: int = 30) -> pd.DataFrame:
    """
    Añade 'baja_confiabilidad_electoral' (1 si votos_totales_emitidos <
    umbral_votos, 0 en caso contrario). NO excluye filas - solo marca, para
    que el modelado (ponderacion) y el analisis de residuos (interpretacion)
    usen la señal con criterio, en vez de que la decision quede escondida
    aqui. Umbral acordado con el usuario: 30 votos totales emitidos.

    OJO: se compara contra 'votos_totales_emitidos' (el conteo real de
    votos), NO contra 'peso_muestral' - esta ultima esta normalizada con
    tope en [0, 1] (ver formula peso_muestral = min(votos/500, 1.0)), asi
    que comparaciones directas contra un umbral en escala de votos (30)
    darian TODAS las filas como baja confiabilidad si se comparara mal.
    """
    panel = panel.copy()
    panel["baja_confiabilidad_electoral"] = (panel["votos_totales_emitidos"] < umbral_votos).astype(int)
    n_marcados = panel["baja_confiabilidad_electoral"].sum()
    print(f"{n_marcados} filas marcadas con baja_confiabilidad_electoral=1 (menos de {umbral_votos} votos totales emitidos).")
    return panel


def marcar_valido_para_modelado(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Añade 'valido_para_modelado' (0 solo cuando pct_izquierda es NaN por
    ausencia total de votos validos ese año - ej. La Guadalupe, Guainia,
    2006, con 0 votos totales). Estas filas NO tienen un valor de variable
    objetivo definido (0/0), asi que no pueden entrar al entrenamiento del
    modelo, aunque SI se conservan en el dataset maestro (no se borran) para
    no perder trazabilidad. El chat de modelizacion debe filtrar por esta
    columna antes de construir X/y.
    """
    panel = panel.copy()
    panel["valido_para_modelado"] = panel["pct_izquierda"].notna().astype(int)
    n_invalidos = (panel["valido_para_modelado"] == 0).sum()
    if n_invalidos > 0:
        print(f"AVISO: {n_invalidos} fila(s) marcada(s) como valido_para_modelado=0 (pct_izquierda indefinido, 0 votos validos ese año):")
        print(panel[panel["valido_para_modelado"] == 0][["divipola", "ano", "departamento", "municipio"]].to_string())
    return panel


def verificar_calidad(panel: pd.DataFrame) -> None:
    """Imprime un resumen de verificacion de calidad. No modifica el panel."""
    print("=" * 70)
    print("VERIFICACION DE CALIDAD DEL DATASET MAESTRO")
    print("=" * 70)

    print(f"\nFilas totales: {len(panel)}")
    print(f"Duplicados (divipola+ano): {panel.duplicated(subset=['divipola', 'ano']).sum()}")

    print("\nFilas por año:")
    print(panel.groupby("ano").size())

    print("\nNulos por columna (excepto los ya tratados con bandera explicita):")
    nulos = panel.isna().sum()
    print(nulos[nulos > 0] if nulos.sum() > 0 else "  (ninguno)")

    print("\nRangos de variables clave:")
    for col in ["pct_izquierda", "lag_pct_izquierda", "pct_votos_blanco", "lag_pct_votos_blanco", "nbi_total"]:
        print(f"  {col}: [{panel[col].min():.2f}, {panel[col].max():.2f}]")
    print(f"  per_ocu: [{panel['per_ocu'].min():.0f}, {panel['per_ocu'].max():.0f}]")

    print("\nConsistencia de nombres por codigo DIVIPOLA (tras estandarizar):")
    inconsist = panel.groupby("divipola")[["departamento", "municipio"]].nunique()
    n_inconsistentes = (inconsist["departamento"] > 1).sum() + (inconsist["municipio"] > 1).sum()
    print(f"  Codigos con nombre inconsistente entre años: {n_inconsistentes}")

    print("\nBanderas de calidad:")
    print(f"  baja_confiabilidad_electoral=1: {panel['baja_confiabilidad_electoral'].sum()} filas")
    print(f"  lag_pct_izquierda_imputado=1: {panel['lag_pct_izquierda_imputado'].sum()} filas")
    print(f"  lag_pct_votos_blanco_imputado=1: {panel['lag_pct_votos_blanco_imputado'].sum()} filas")
    print(f"  valido_para_modelado=0: {(panel['valido_para_modelado'] == 0).sum()} filas")
    print("=" * 70)
