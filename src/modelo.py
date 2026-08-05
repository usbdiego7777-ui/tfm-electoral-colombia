# ==============================================================================
# modelo.py
# Funciones del pipeline de modelizacion (Fase 3): ventana expansiva temporal,
# escalado dentro de cada ventana, ajuste de modelos regresores, y las dos
# metricas que importan para este proyecto (R2 global y correlacion intra-anio
# ponderada).
#
# Decisiones heredadas de la Fase 3 (detalle completo en
# bitacora_fase3_modelizacion_v*.md, documento interno, NO versionado en git):
#
#   - Sin territorio categorico en el modelo predictivo. region_dane y
#     departamento se probaron como controles y empeoran el ajuste en
#     validacion expansiva con este volumen de filas por ventana (decision
#     tomada con evidencia empirica, no solo por diseno de negocio).
#   - La ventana 2006->2010 se reporta aparte, nunca promediada junto a las
#     ventanas estables (2014/2018/2022). Entrenar con una sola eleccion
#     (2006, n=1.117) y predecir 2010 extrapola linealmente fuera de rango:
#     el lag de entrada en test (~19, viene de 2006) esta muy por encima del
#     rango visto en train (~5, viene de 2002), y el modelo predice muy por
#     encima del resultado real de 2010 (~7%, fuga de votos hacia Mockus).
#     No es un problema de las variables ni del territorio - es que un
#     shock de nivel nacional no se puede anticipar con una sola eleccion de
#     historia.
#   - Efecto-anio (Forma 1: dummies de 'ano' en X, con drop_first) SI se usa
#     como control de nivel dentro del train. La Forma 2 (modelar la
#     desviacion respecto a la media nacional del propio anio) se descarto
#     por fuga real: esa media usa el resultado del anio de test, que en
#     produccion no se conoce.
#   - peso_muestral (tope U=500, ya viene en el dataset maestro en escala
#     0-1) se usa como sample_weight en todo ajuste y toda metrica.
#   - Se reporta siempre con y sin lag_pct_izquierda, para medir el aporte
#     real de NBI y per_ocu por encima de la pura inercia electoral.
# ==============================================================================

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV, LassoCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

try:
    from xgboost import XGBRegressor
    XGBOOST_DISPONIBLE = True
except ImportError:
    XGBOOST_DISPONIBLE = False

from sklearn.linear_model import LinearRegression

# Departamentos de interes para el analisis de conflicto armado (Experimentos
# decisivos de Fase 3): Choco, Putumayo, Narino, Caqueta, Norte de Santander,
# Guaviare, Vaupes. Nombres verificados contra los valores reales de
# 'departamento' en el dataset maestro (sin tildes, mayusculas).
ZONA_CONFLICTO_DEPARTAMENTOS = ["CHOCO", "PUTUMAYO", "NARINO", "CAQUETA",
                                 "NORTE DE SANTANDER", "GUAVIARE", "VAUPES"]


# ------------------------------------------------------------------------
# Columnas y ventanas de validacion (ver cabecera del fichero para el porque
# de cada decision)
# ------------------------------------------------------------------------
COLUMNAS_PREDICTORAS_LAG = [
    "lag_pct_izquierda", "lag_pct_izquierda_imputado",
    "lag_pct_votos_blanco", "lag_pct_votos_blanco_imputado",
    "nbi_total", "per_ocu",
]
COLUMNAS_PREDICTORAS_SIN_LAG = ["nbi_total", "per_ocu"]

VENTANA_INESTABLE = 2010          # se reporta aparte, nunca se promedia
VENTANAS_ESTABLES = [2014, 2018, 2022]
TODAS_LAS_VENTANAS = [VENTANA_INESTABLE] + VENTANAS_ESTABLES

ALPHAS_RIDGE = np.logspace(-2, 9, 80)   # rango amplio; verificado en Fase 3
                                         # que con rangos mas cortos RidgeCV
                                         # saturaba en el borde


# ------------------------------------------------------------------------
# Construccion de la ventana expansiva
# ------------------------------------------------------------------------
def construir_ventana(df: pd.DataFrame, ano_test: int, columnas_predictoras: list,
                       efecto_anio: bool = False):
    """
    Construye train/test para la ventana expansiva train=[anios < ano_test],
    test=[ano_test]. Si efecto_anio=True, anade dummies de 'ano' (drop_first)
    calculadas sobre train; el anio de test, al no haber sido visto en train,
    queda con todas las dummies en 0 (esto NO corrige el nivel del anio de
    test, solo limpia ruido de nivel dentro del propio train - ver cabecera).
    """
    train = df[df["ano"] < ano_test].copy()
    test = df[df["ano"] == ano_test].copy()

    def _armar_X(sub):
        X = sub[columnas_predictoras].copy()
        if efecto_anio:
            dummies = pd.get_dummies(sub["ano"], prefix="anio", drop_first=True)
            X = pd.concat([X, dummies], axis=1)
        return X

    X_train = _armar_X(train)
    X_test = _armar_X(test).reindex(columns=X_train.columns, fill_value=0)
    return train, test, X_train, X_test


# ------------------------------------------------------------------------
# Metricas
# ------------------------------------------------------------------------
def correlacion_ponderada(a, b, peso) -> float:
    """
    Correlacion de Pearson ponderada por sample weight. Devuelve NaN de forma
    explicita (sin lanzar RuntimeWarning) cuando una de las dos variables no
    tiene varianza - por ejemplo, el baseline "media train" predice el mismo
    valor para todos los municipios de una eleccion, asi que su varianza es 0
    y la correlacion queda matematicamente indefinida (0/0), no es un error
    de calculo.
    """
    a, b, peso = np.asarray(a, float), np.asarray(b, float), np.asarray(peso, float)
    aw, bw = np.average(a, weights=peso), np.average(b, weights=peso)
    va, vb = np.average((a - aw) ** 2, weights=peso), np.average((b - bw) ** 2, weights=peso)
    TOLERANCIA_VARIANZA_CERO = 1e-10  # el redondeo de coma flotante en el promedio
                                       # ponderado deja varianzas residuales ~1e-16
                                       # aun cuando la variable es constante de verdad
    if va < TOLERANCIA_VARIANZA_CERO or vb < TOLERANCIA_VARIANZA_CERO:
        return np.nan
    cov = np.average((a - aw) * (b - bw), weights=peso)
    return cov / np.sqrt(va * vb)


def evaluar_prediccion(y_real, y_pred, peso) -> dict:
    """
    Las cuatro metricas que reportamos siempre:
      - rmse, mae, r2_global: ponderadas por peso_muestral, en la escala
        habitual de sklearn.
      - corr_intra_anio: correlacion de Pearson ponderada entre predicho y
        real DENTRO del anio de test. Es la metrica clave del proyecto: con
        solo 5 elecciones y saltos de nivel nacional grandes entre ellas, el
        R2 global castiga sobre todo el error de nivel (que fija la
        politica nacional del anio, no el perfil de los municipios). La
        correlacion intra-anio mide si se acierta el patron territorial
        dentro de la eleccion, que es lo que de verdad interesa para el
        diferenciador del proyecto (los residuos).
    """
    rmse = mean_squared_error(y_real, y_pred, sample_weight=peso) ** 0.5
    mae = mean_absolute_error(y_real, y_pred, sample_weight=peso)
    r2 = r2_score(y_real, y_pred, sample_weight=peso)
    corr = correlacion_ponderada(y_pred, y_real, peso)
    return {"rmse": rmse, "mae": mae, "r2_global": r2,
            "corr_intra_anio": corr, "r2_intra_anio": corr ** 2}


# ------------------------------------------------------------------------
# Baselines ingenuos (referencia obligatoria: si el modelo no les gana,
# la inercia manda y eso es un hallazgo, no un fracaso)
# ------------------------------------------------------------------------
def baseline_copiar_lag(df: pd.DataFrame, ano_test: int) -> dict:
    """Predice para cada municipio el resultado de la eleccion anterior (su propio lag)."""
    test = df[df["ano"] == ano_test]
    return evaluar_prediccion(test["pct_izquierda"], test["lag_pct_izquierda"], test["peso_muestral"])


def baseline_media_train(df: pd.DataFrame, ano_test: int) -> dict:
    """Predice la media ponderada del target en train para todos los municipios (nivel puro)."""
    train = df[df["ano"] < ano_test]
    test = df[df["ano"] == ano_test]
    media = np.average(train["pct_izquierda"], weights=train["peso_muestral"])
    pred = np.full(len(test), media)
    return evaluar_prediccion(test["pct_izquierda"], pred, test["peso_muestral"])


# ------------------------------------------------------------------------
# Modelos: Ridge/Lasso (baseline) -> RandomForest/SVR (principales) -> XGBoost (opcional)
# ------------------------------------------------------------------------
def entrenar_evaluar_ridge(df, ano_test, columnas_predictoras, efecto_anio=False,
                            alphas=ALPHAS_RIDGE, cv=5, devolver_modelo=False):
    """RidgeCV: alpha elegido por CV interna en train (nunca toca test)."""
    train, test, X_train, X_test = construir_ventana(df, ano_test, columnas_predictoras, efecto_anio)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    modelo = RidgeCV(alphas=alphas, cv=cv)
    modelo.fit(X_train_s, train["pct_izquierda"], sample_weight=train["peso_muestral"])
    pred = modelo.predict(X_test_s)
    metricas = evaluar_prediccion(test["pct_izquierda"], pred, test["peso_muestral"])
    metricas["alpha_elegido"] = modelo.alpha_
    if devolver_modelo:
        return metricas, modelo, scaler, X_train.columns.tolist()
    return metricas


def entrenar_evaluar_lasso(df, ano_test, columnas_predictoras, efecto_anio=False,
                            cv=5, devolver_modelo=False):
    """LassoCV: alpha elegido por CV interna en train."""
    train, test, X_train, X_test = construir_ventana(df, ano_test, columnas_predictoras, efecto_anio)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    modelo = LassoCV(cv=cv, max_iter=20000)
    modelo.fit(X_train_s, train["pct_izquierda"], sample_weight=train["peso_muestral"])
    pred = modelo.predict(X_test_s)
    metricas = evaluar_prediccion(test["pct_izquierda"], pred, test["peso_muestral"])
    metricas["alpha_elegido"] = modelo.alpha_
    if devolver_modelo:
        return metricas, modelo, scaler, X_train.columns.tolist()
    return metricas


def entrenar_evaluar_random_forest(df, ano_test, columnas_predictoras, efecto_anio=False,
                                    n_estimators=400, max_depth=6, min_samples_leaf=15,
                                    random_state=42, devolver_modelo=False):
    """
    RandomForestRegressor. No necesita escalado (arboles). Hiperparametros
    deliberadamente conservadores (max_depth=6, min_samples_leaf=15): con
    ~1.000-4.500 filas por ventana y solo 6-9 columnas, un bosque profundo
    sobreajusta con facilidad y produce el tipo de metrica sospechosamente
    alta que Santiago penaliza en la evaluacion.
    """
    train, test, X_train, X_test = construir_ventana(df, ano_test, columnas_predictoras, efecto_anio)
    modelo = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth,
                                    min_samples_leaf=min_samples_leaf,
                                    random_state=random_state, n_jobs=-1)
    modelo.fit(X_train, train["pct_izquierda"], sample_weight=train["peso_muestral"])
    pred = modelo.predict(X_test)
    metricas = evaluar_prediccion(test["pct_izquierda"], pred, test["peso_muestral"])
    if devolver_modelo:
        return metricas, modelo, X_train.columns.tolist()
    return metricas


def entrenar_evaluar_svr(df, ano_test, columnas_predictoras, efecto_anio=False,
                          C=1.0, epsilon=1.0, kernel="rbf", devolver_modelo=False):
    """SVR con kernel RBF. Requiere escalado (igual que Ridge/Lasso)."""
    train, test, X_train, X_test = construir_ventana(df, ano_test, columnas_predictoras, efecto_anio)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    modelo = SVR(C=C, epsilon=epsilon, kernel=kernel)
    modelo.fit(X_train_s, train["pct_izquierda"], sample_weight=train["peso_muestral"])
    pred = modelo.predict(X_test_s)
    metricas = evaluar_prediccion(test["pct_izquierda"], pred, test["peso_muestral"])
    if devolver_modelo:
        return metricas, modelo, scaler, X_train.columns.tolist()
    return metricas


def entrenar_evaluar_xgboost(df, ano_test, columnas_predictoras, efecto_anio=False,
                              n_estimators=300, max_depth=3, learning_rate=0.05,
                              random_state=42, devolver_modelo=False):
    """XGBoost, opcional segun el stack acordado. Hiperparametros conservadores por el mismo motivo que RF."""
    if not XGBOOST_DISPONIBLE:
        raise ImportError("xgboost no esta instalado en este entorno. pip install xgboost.")
    train, test, X_train, X_test = construir_ventana(df, ano_test, columnas_predictoras, efecto_anio)
    modelo = XGBRegressor(n_estimators=n_estimators, max_depth=max_depth,
                           learning_rate=learning_rate, random_state=random_state,
                           n_jobs=-1, verbosity=0)
    modelo.fit(X_train, train["pct_izquierda"], sample_weight=train["peso_muestral"])
    pred = modelo.predict(X_test)
    metricas = evaluar_prediccion(test["pct_izquierda"], pred, test["peso_muestral"])
    if devolver_modelo:
        return metricas, modelo, X_train.columns.tolist()
    return metricas


# ------------------------------------------------------------------------
# Orquestacion: tabla resumen de una variante a lo largo de las ventanas
# ------------------------------------------------------------------------
def resumen_variante(nombre_variante: str, funcion_entrenar, df: pd.DataFrame,
                      columnas_predictoras: list, efecto_anio: bool = False,
                      ventanas: list = TODAS_LAS_VENTANAS, **kwargs_extra) -> pd.DataFrame:
    """
    Ejecuta funcion_entrenar (una de las entrenar_evaluar_*) en cada ventana y
    devuelve una tabla larga (una fila por ventana) con las metricas y el
    nombre de la variante, para poder concatenar variantes y comparar.
    """
    filas = []
    for ano in ventanas:
        metricas = funcion_entrenar(df, ano, columnas_predictoras, efecto_anio=efecto_anio, **kwargs_extra)
        fila = {"variante": nombre_variante, "ano_test": ano, "ventana_estable": ano != VENTANA_INESTABLE}
        fila.update(metricas)
        filas.append(fila)
    return pd.DataFrame(filas)


def promedio_ventanas_estables(tabla_resumen: pd.DataFrame, columnas_metricas=None) -> pd.Series:
    """
    Promedia SOLO sobre VENTANAS_ESTABLES (2014/2018/2022) - la ventana 2010
    nunca se promedia junto a las demas (ver cabecera del fichero).
    """
    if columnas_metricas is None:
        columnas_metricas = ["rmse", "mae", "r2_global", "corr_intra_anio", "r2_intra_anio"]
    sub = tabla_resumen[tabla_resumen["ventana_estable"]]
    return sub[columnas_metricas].mean()


# ------------------------------------------------------------------------
# Analisis explicativo (in-sample, cross-seccional) - distinto del pipeline
# predictivo de arriba. Se usa para las preguntas de "cuanto explica X mas
# alla de Y", no para predecir fuera de muestra. Sin regularizar (LinearRegression
# simple): aqui interesa el R2/coeficiente insesgado dentro del propio anio,
# no la capacidad de generalizar a anios futuros.
# ------------------------------------------------------------------------
def r2_ponderado(X, y, peso) -> float:
    """R2 (ponderado) de una regresion lineal simple ajustada y evaluada sobre los MISMOS datos (in-sample)."""
    reg = LinearRegression().fit(X, y, sample_weight=peso)
    pred = reg.predict(X)
    return r2_score(y, pred, sample_weight=peso)


def correlacion_parcial_ponderada(target, control_df, variable_extra, peso):
    """
    Correlacion parcial ponderada de variable_extra con target, controlando por
    las columnas de control_df. Metodo de residualizacion: se regresa target
    contra los controles (residuo 1) y variable_extra contra los mismos
    controles (residuo 2); la correlacion ponderada entre ambos residuos es la
    correlacion parcial. Devuelve (correlacion, residuo_target, residuo_variable_extra)
    para poder reusar los residuos en analisis posteriores (p.ej. comparar
    grupos sobre el residuo del target ya controlado).
    """
    Xc = control_df.values if hasattr(control_df, "values") else np.asarray(control_df)
    target = np.asarray(target, float)
    variable_extra = np.asarray(variable_extra, float)

    reg_t = LinearRegression().fit(Xc, target, sample_weight=peso)
    resid_t = target - reg_t.predict(Xc)

    reg_e = LinearRegression().fit(Xc, variable_extra, sample_weight=peso)
    resid_e = variable_extra - reg_e.predict(Xc)

    corr = correlacion_ponderada(resid_t, resid_e, peso)
    return corr, resid_t, resid_e


# ------------------------------------------------------------------------
# Fase 4 - Tabla de residuos (municipios que rompen su tendencia)
# ------------------------------------------------------------------------

COLUMNAS_TABLA_RESIDUOS = [
    "divipola", "municipio", "departamento", "region_dane", "ano",
    "pct_izquierda", "pct_izquierda_predicho", "residuo",
    "lag_pct_izquierda", "nbi_total", "per_ocu",
    "baja_confiabilidad_electoral", "peso_muestral", "votos_totales_emitidos",
    "ventana_estable",
]

COLUMNAS_CONTEXTO_RESIDUO = [
    "divipola", "municipio", "departamento", "region_dane", "ano",
    "pct_izquierda", "lag_pct_izquierda", "nbi_total", "per_ocu",
    "baja_confiabilidad_electoral", "peso_muestral", "votos_totales_emitidos",
]


def calcular_tabla_residuos(df: pd.DataFrame, columnas_predictoras: list,
                             ventanas: list = None) -> pd.DataFrame:
    """
    Calcula la tabla de residuos out-of-sample: para cada anio de `ventanas`
    (por defecto TODAS_LAS_VENTANAS = [2010, 2014, 2018, 2022]), entrena UN
    MODELO NUEVO exclusivamente con anios estrictamente anteriores (ventana
    expansiva, via entrenar_evaluar_ridge -> construir_ventana) y predice
    SOLO ese anio de test con ESE modelo.

    DECISION DE DISENO, verificada por el chat maestro y el chat de
    validacion antes de escribir esta funcion (ver bitacora Fase 4 S9): el
    residuo de cada anio-municipio tiene que salir del modelo entrenado sin
    ese anio, nunca de un modelo unico entrenado con la ventana mas amplia y
    aplicado a los 4 anios. Si se hiciera con un solo modelo, los residuos de
    2014 y 2018 saldrian in-sample (el modelo ya vio esos anios al
    entrenar), pareceerian razonables sin serlo, y romperian la regla
    out-of-sample de forma silenciosa - sin ningun error visible. Por eso
    esta funcion NUNCA entrena un modelo fuera del bucle: cada iteracion
    llama a entrenar_evaluar_ridge() de cero, con su propio StandardScaler
    ajustado solo con el train de esa ventana (verificado: cada llamada a
    entrenar_evaluar_ridge crea un StandardScaler() nuevo, nunca reutiliza
    uno global - ver esa funcion mas arriba en este mismo modulo).

    2006 nunca aparece en la tabla resultante: no es anio de test de ninguna
    ventana (es el anio con el que arranca el entrenamiento de la ventana
    2010), asi que no tiene residuo out-of-sample posible - si apareciera,
    seria la senal de un error de construccion (residuo in-sample colado).

    2010 SI aparece, pero con ventana_estable=False: la ventana que lo
    predice se entrena con una sola eleccion (2006), lo que la hace
    estructuralmente debil (Fase 3: R2~=-26 en esa ventana, colapso por el
    shock Mockus) - no es que 2010 sea un anio "malo" en si, es que el
    modelo que lo predice no tiene suficiente historia para ser fiable. Se
    marca, no se descarta, para que quien use la tabla decida con
    conocimiento de causa si lo incluye o no en cada analisis.

    Devuelve una tabla con las columnas de COLUMNAS_TABLA_RESIDUOS, mas dos
    columnas auxiliares (anio_train_min, anio_train_max) que documentan,
    fila a fila, el rango de anios de entrenamiento del modelo que genero
    ese residuo - pensadas para la verificacion out-of-sample explicita
    (ver notebook 04, verificacion 3).
    """
    if ventanas is None:
        ventanas = TODAS_LAS_VENTANAS

    bloques = []
    for ano_test in ventanas:
        # Entrena un modelo NUEVO, exclusivamente con anios < ano_test.
        # Cada llamada crea su propio scaler y su propio RidgeCV - no hay
        # reutilizacion de modelo ni de scaler entre iteraciones.
        _, modelo, scaler, columnas_modelo = entrenar_evaluar_ridge(
            df, ano_test, columnas_predictoras, efecto_anio=True, devolver_modelo=True
        )

        # Reconstruye la misma ventana para obtener train/test con todas las
        # columnas de contexto (entrenar_evaluar_ridge solo devuelve metricas
        # + modelo, no las filas de test con sus columnas descriptivas).
        train, test, X_train, X_test = construir_ventana(
            df, ano_test, columnas_predictoras, efecto_anio=True
        )
        X_test = X_test.reindex(columns=columnas_modelo, fill_value=0)
        X_test_s = scaler.transform(X_test)
        pred = modelo.predict(X_test_s)

        bloque = test[COLUMNAS_CONTEXTO_RESIDUO].copy()
        bloque["pct_izquierda_predicho"] = pred
        bloque["residuo"] = bloque["pct_izquierda"] - bloque["pct_izquierda_predicho"]
        bloque["ventana_estable"] = ano_test != VENTANA_INESTABLE
        # Columnas auxiliares para la verificacion out-of-sample explicita
        # (verificacion 3 del notebook 04): documentan que el modelo que
        # genero ESTE bloque de residuos se entreno solo con estos anios.
        bloque["anio_train_min"] = int(train["ano"].min())
        bloque["anio_train_max"] = int(train["ano"].max())
        bloques.append(bloque)

    tabla = pd.concat(bloques, ignore_index=True)
    tabla = tabla[COLUMNAS_TABLA_RESIDUOS + ["anio_train_min", "anio_train_max"]]

    # residuo_centrado: separa la ola nacional del anio (desplazamiento comun,
    # que el modelo basado en el pasado no puede anticipar - p.ej. el ascenso
    # de Petro en 2022) de la desviacion territorial especifica (quien se
    # mueve MAS que esa ola). Verificado con datos reales (chat de
    # validacion, Fase 4): en 2022 el residuo absoluto medio es +12.6 puntos
    # y 75.6% de los municipios son positivos - casi todo el pais sube por
    # el efecto nacional, el mismo "error de nivel" ya documentado en Fase 3.
    # Al centrar, el reparto pasa a 41.5% por encima / 58.5% por debajo de la
    # media, que es el patron territorial limpio.
    #
    # La media de referencia se calcula SOLO sobre el subconjunto fiable
    # (ventana_estable=True, baja_confiabilidad_electoral=0), para que ni la
    # ventana 2010 ni los micro-electorados distorsionen la referencia. Para
    # 2010 (ventana_estable=False) el resultado es NaN de forma deliberada -
    # no tiene sentido centrar un residuo ya marcado como no fiable contra
    # una media calculada excluyendolo a el mismo.
    referencia = tabla[tabla["ventana_estable"] & (tabla["baja_confiabilidad_electoral"] == 0)]
    media_residuo_por_anio = referencia.groupby("ano")["residuo"].mean()
    tabla["residuo_centrado"] = tabla["residuo"] - tabla["ano"].map(media_residuo_por_anio)

    return tabla
