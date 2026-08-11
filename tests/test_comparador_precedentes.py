import sqlite3
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from comparador_precedentes import calcular_coincidencia, normalizar_region


def test_normalizacion_region_con_y_sin_tildes():
    assert normalizar_region("Región del Maule") == "maule"
    assert normalizar_region("Region del Maule") == "maule"
    assert normalizar_region("Maule") == "maule"


def test_coincidencia_mismo_sector():
    datos = {"region": "Maule", "sector": "Energia", "subtipo_energia": "Parque fotovoltaico"}
    precedente = {"region": "Region del Maule", "tipo_proyecto": "energia", "subtipo_proyecto": "solar"}
    resultado = calcular_coincidencia(datos, {"literales": []}, precedente)
    assert any("sector" in texto for texto in resultado["coincidencias"])


def test_diferencia_distinto_subtipo():
    datos = {"region": "Maule", "sector": "Energia", "subtipo_energia": "Almacenamiento BESS"}
    precedente = {"region": "Maule", "tipo_proyecto": "energia", "subtipo_proyecto": "parque fotovoltaico"}
    resultado = calcular_coincidencia(datos, {"literales": []}, precedente)
    assert any("subtipo" in texto.lower() for texto in resultado["diferencias"])


def test_puntaje_con_datos_completos():
    datos = {"region": "Maule", "sector": "Energia", "subtipo_energia": "Parque fotovoltaico"}
    diagnostico = {"literales": ["c)"]}
    precedente = {
        "region": "Region del Maule",
        "tipo_proyecto": "energia",
        "subtipo_proyecto": "parque fotovoltaico",
        "palabras_clave": ["energia", "parque fotovoltaico"],
        "criterios": [{"criterio": "c)", "explicacion": "literal c)"}],
    }
    resultado = calcular_coincidencia(datos, diagnostico, precedente)
    assert resultado["puntos"] > 0
    assert resultado["maximo_evaluable"] == 100


def test_puntaje_con_componentes_no_evaluables():
    datos = {"region": "Maule", "sector": "Energia"}
    precedente = {"region": "Maule", "tipo_proyecto": "energia", "subtipo_proyecto": None}
    resultado = calcular_coincidencia(datos, {"literales": []}, precedente)
    assert resultado["maximo_evaluable"] < 100
    assert resultado["no_comparable"]


def test_informacion_insuficiente():
    resultado = calcular_coincidencia({}, None, {})
    assert resultado["clasificacion"] == "Información insuficiente"
