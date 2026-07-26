# ==============================================================================
# test_region_dane.py
# Test de regresion para anadir_region_dane() en src/preprocesamiento.py.
# Protege especificamente contra la reaparicion del error ya corregido una
# vez (San Andres clasificado como "Insular" en vez de "Caribe", corregido
# el mismo dia tras verificar con multiples fuentes externas).
#
# Ejecucion: python tests/test_region_dane.py  (no requiere pytest instalado,
# aunque tambien es compatible: pytest tests/test_region_dane.py -v)
# ==============================================================================

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from preprocesamiento import anadir_region_dane, MAPA_REGION_DANE  # noqa: E402


def construir_panel_sintetico_regiones() -> pd.DataFrame:
    """Un municipio ficticio por cada departamento que queremos verificar."""
    divipolas = {
        "05001": "ANTIOQUIA (debe ser Andina)",
        "11001": "BOGOTA (debe ser Andina)",
        "19001": "CAUCA (debe ser Pacifica - confirmado por el usuario con fuentes cruzadas)",
        "52001": "NARINO (debe ser Pacifica - confirmado por el usuario con fuentes cruzadas)",
        "88001": "SAN ANDRES (debe ser Caribe, NO Insular - correccion aplicada)",
        "97001": "VAUPES (debe ser Amazonia, no Orinoquia)",
        "94001": "GUAINIA (debe ser Amazonia, no Orinoquia)",
    }
    return pd.DataFrame({"divipola": list(divipolas.keys())})


def test_cauca_y_narino_son_pacifica():
    """Confirmado explicitamente por el usuario contra multiples fuentes
    (Colombia Travel, Parques Nacionales, Twinkl, Señal Colombia,
    todacolombia.com) - Cauca y Nariño son Region Pacifica."""
    panel = construir_panel_sintetico_regiones()
    resultado = anadir_region_dane(panel)
    resultado = resultado.set_index("divipola")
    assert resultado.loc["19001", "region_dane"] == "Pacifica"  # Cauca
    assert resultado.loc["52001", "region_dane"] == "Pacifica"  # Narino


def test_san_andres_es_caribe_no_insular():
    """
    Guardia explicita contra el bug ya corregido: San Andres se clasifico
    inicialmente como 'Insular' (version del 26/07/2026 del Chat 4), y se
    corrigio a 'Caribe' tras contrastar con multiples fuentes. Este test
    evita que ese error reaparezca sin que salte una alarma.
    """
    panel = construir_panel_sintetico_regiones()
    resultado = anadir_region_dane(panel)
    resultado = resultado.set_index("divipola")
    assert resultado.loc["88001", "region_dane"] == "Caribe"
    assert resultado.loc["88001", "region_dane"] != "Insular"


def test_insular_nunca_aparece_como_valor_real():
    """
    'Insular' existe solo como concepto geografico (Gorgona/Malpelo, sin
    DIVIPOLA municipal propio) - NINGUN codigo de MAPA_REGION_DANE debe
    apuntar a 'Insular', porque no hay observacion electoral real que deba
    caer ahi en este dataset.
    """
    valores_usados = set(MAPA_REGION_DANE.values())
    assert "Insular" not in valores_usados


def test_departamentos_amazonicos_no_orinoquia():
    """Vaupes y Guainia deben ser Amazonia, no Orinoquia (departamentos
    frontera donde algunas fuentes minoritarias discrepan - se usa la
    convencion mayoritaria, confirmada en 3+ fuentes independientes)."""
    panel = construir_panel_sintetico_regiones()
    resultado = anadir_region_dane(panel)
    resultado = resultado.set_index("divipola")
    assert resultado.loc["97001", "region_dane"] == "Amazonia"  # Vaupes
    assert resultado.loc["94001", "region_dane"] == "Amazonia"  # Guainia


def test_codigo_de_departamento_desconocido_falla_explicitamente():
    """Si un codigo de departamento no esta en MAPA_REGION_DANE, la funcion
    debe fallar con un AssertionError claro, NUNCA generar un NaN silencioso."""
    panel = pd.DataFrame({"divipola": ["00999"]})  # codigo inventado, no existe
    fallo_correctamente = False
    try:
        anadir_region_dane(panel)
    except AssertionError:
        fallo_correctamente = True
    assert fallo_correctamente, "anadir_region_dane() deberia fallar con codigo desconocido, no seguir en silencio"


if __name__ == "__main__":
    tests = [
        test_cauca_y_narino_son_pacifica,
        test_san_andres_es_caribe_no_insular,
        test_insular_nunca_aparece_como_valor_real,
        test_departamentos_amazonicos_no_orinoquia,
        test_codigo_de_departamento_desconocido_falla_explicitamente,
    ]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print("\nTodos los tests de region_dane pasaron correctamente.")
