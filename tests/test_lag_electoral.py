# ==============================================================================
# test_lag_electoral.py
# Test de regresion para src/preprocesamiento.py, enfocado en el LAG - el
# punto mas sensible a fugas de datos del proyecto (ya se detecto un bug real
# aqui: encadenar el calculo de dos lags sobre un panel ya filtrado perdia el
# año de referencia). Este test evita que ese error, u otro parecido, vuelva
# a colarse sin que salte una alarma.
#
# Se puede ejecutar de dos formas:
#   - Con pytest:      pytest tests/test_lag_electoral.py -v
#   - Sin pytest:      python tests/test_lag_electoral.py
# No depende de los ficheros de datos reales (usa un panel sintetico minimo),
# para que el test sea rapido, reproducible y no rompa si los datos cambian.
# ==============================================================================

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from preprocesamiento import calcular_variable_lag  # noqa: E402


def construir_panel_sintetico() -> pd.DataFrame:
    """
    Panel minimo con 2 municipios ficticios a lo largo de 2002-2022:
      - 'TEST1': tiene datos en TODOS los años -> debe dar lag exacto, sin imputar
      - 'TEST2': le falta el año 2014 -> su lag de 2018 debe quedar imputado
        (marcado con la bandera), NUNCA silenciosamente en NaN ni con un valor
        inventado sin trazar
    Los valores de pct_izquierda y pct_votos_blanco son arbitrarios, elegidos
    para ser faciles de verificar a ojo (multiplos de 10 y de 1 respectivamente).
    """
    filas = []
    valores_test1 = {2002: 10, 2006: 20, 2010: 30, 2014: 40, 2018: 50, 2022: 60}
    blanco_test1 = {2002: 1, 2006: 2, 2010: 3, 2014: 4, 2018: 5, 2022: 6}

    for ano, val in valores_test1.items():
        filas.append({
            "divipola": "TEST1", "ano": ano, "departamento": "DEPTO_X",
            "municipio": "MUNICIPIO_TEST1",
            "pct_izquierda": val, "pct_votos_blanco": blanco_test1[ano],
            "votos_totales_emitidos": 1000,
        })

    valores_test2 = {2002: 15, 2006: 25, 2010: 35, 2018: 55, 2022: 65}  # sin 2014
    blanco_test2 = {2002: 1.5, 2006: 2.5, 2010: 3.5, 2018: 5.5, 2022: 6.5}
    for ano, val in valores_test2.items():
        filas.append({
            "divipola": "TEST2", "ano": ano, "departamento": "DEPTO_X",
            "municipio": "MUNICIPIO_TEST2",
            "pct_izquierda": val, "pct_votos_blanco": blanco_test2[ano],
            "votos_totales_emitidos": 500,
        })

    # TEST3: votacion baja (100 votos), por debajo del tope de 500 -> debe
    # dar peso proporcional (100/500 = 0.2), no peso pleno
    valores_test3 = {2002: 5, 2006: 8, 2010: 12, 2014: 18, 2018: 22, 2022: 30}
    blanco_test3 = {2002: 0.5, 2006: 0.8, 2010: 1.2, 2014: 1.8, 2018: 2.2, 2022: 3.0}
    for ano, val in valores_test3.items():
        filas.append({
            "divipola": "TEST3", "ano": ano, "departamento": "DEPTO_X",
            "municipio": "MUNICIPIO_TEST3",
            "pct_izquierda": val, "pct_votos_blanco": blanco_test3[ano],
            "votos_totales_emitidos": 100,
        })

    return pd.DataFrame(filas)


def test_lag_coincide_con_el_valor_real_del_ano_anterior():
    """
    Caso central (equivalente al chequeo manual que hicimos con Bogota):
    el lag de un municipio con dato en TODOS los años debe coincidir
    EXACTAMENTE con su propio valor del año inmediatamente anterior, y
    nunca con el de su propio año actual (que es justo el bug que se
    coló en el primer refactor de esta funcion).
    """
    panel = construir_panel_sintetico()
    resultado = calcular_variable_lag(panel)
    t1 = resultado[resultado["divipola"] == "TEST1"].set_index("ano")

    assert t1.loc[2006, "lag_pct_izquierda"] == 10   # valor real de 2002
    assert t1.loc[2010, "lag_pct_izquierda"] == 20   # valor real de 2006
    assert t1.loc[2014, "lag_pct_izquierda"] == 30   # valor real de 2010
    assert t1.loc[2018, "lag_pct_izquierda"] == 40   # valor real de 2014
    assert t1.loc[2022, "lag_pct_izquierda"] == 50   # valor real de 2018

    # Guardia explicita contra el bug ya detectado: el lag NUNCA debe
    # coincidir con el valor del propio año actual (salvo coincidencia
    # numerica improbable, que aqui no se da por diseño de los datos)
    for ano in [2006, 2010, 2014, 2018, 2022]:
        assert t1.loc[ano, "lag_pct_izquierda"] != t1.loc[ano, "pct_izquierda"]


def test_lag_de_votos_blanco_tambien_se_calcula_correctamente():
    """Mismo chequeo que arriba, pero para lag_pct_votos_blanco (la segunda
    correccion metodologica añadida tras revision cruzada)."""
    panel = construir_panel_sintetico()
    resultado = calcular_variable_lag(panel)
    t1 = resultado[resultado["divipola"] == "TEST1"].set_index("ano")

    assert t1.loc[2006, "lag_pct_votos_blanco"] == 1
    assert t1.loc[2010, "lag_pct_votos_blanco"] == 2
    assert t1.loc[2018, "lag_pct_votos_blanco"] == 4
    assert t1.loc[2022, "lag_pct_votos_blanco"] == 5


def test_municipio_sin_dato_en_ano_anterior_queda_imputado_y_marcado():
    """
    TEST2 no tiene fila en 2014, asi que su lag de 2018 no puede calcularse
    por merge directo. Debe quedar IMPUTADO (con la media departamental de
    ese año, aqui solo hay 1 municipio con dato real ese año -TEST1- asi que
    la imputacion debe coincidir con el valor de TEST1 en 2018) y la bandera
    'lag_pct_izquierda_imputado' debe quedar en 1 - nunca en 0 de forma
    silenciosa.
    """
    panel = construir_panel_sintetico()
    resultado = calcular_variable_lag(panel)
    t2 = resultado[resultado["divipola"] == "TEST2"].set_index("ano")

    assert t2.loc[2018, "lag_pct_izquierda_imputado"] == 1
    assert not pd.isna(t2.loc[2018, "lag_pct_izquierda"])  # se imputo, no quedo NaN

    # Los años CON dato real no deben quedar marcados como imputados
    assert t2.loc[2006, "lag_pct_izquierda_imputado"] == 0
    assert t2.loc[2022, "lag_pct_izquierda_imputado"] == 0


def test_peso_muestral_usa_formula_con_tope_500():
    """El peso muestral debe ser min(votos_totales_emitidos/500, 1.0): pleno
    (1.0) para votaciones robustas, proporcional para las muy pequeñas."""
    panel = construir_panel_sintetico()
    resultado = calcular_variable_lag(panel)
    esperado = (resultado["votos_totales_emitidos"] / 500).clip(upper=1.0)
    assert (resultado["peso_muestral"] == esperado).all()

    # TEST1 tiene votos_totales_emitidos=1000 (por encima del tope) -> peso pleno
    t1 = resultado[resultado["divipola"] == "TEST1"]
    assert (t1["peso_muestral"] == 1.0).all()

    # TEST2 tiene votos_totales_emitidos=500 (justo en el tope) -> peso pleno tambien
    t2 = resultado[resultado["divipola"] == "TEST2"]
    assert (t2["peso_muestral"] == 1.0).all()

    # TEST3 tiene votos_totales_emitidos=100 (por debajo del tope) -> peso
    # proporcional (100/500 = 0.2), NUNCA pleno
    t3 = resultado[resultado["divipola"] == "TEST3"]
    assert (t3["peso_muestral"] == 0.2).all()


if __name__ == "__main__":
    tests = [
        test_lag_coincide_con_el_valor_real_del_ano_anterior,
        test_lag_de_votos_blanco_tambien_se_calcula_correctamente,
        test_municipio_sin_dato_en_ano_anterior_queda_imputado_y_marcado,
        test_peso_muestral_usa_formula_con_tope_500,
    ]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print("\nTodos los tests del lag pasaron correctamente.")
