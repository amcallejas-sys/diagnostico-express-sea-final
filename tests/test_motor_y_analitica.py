import sqlite3
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from analitica_datos import aplicar_filtros, calcular_indicadores, obtener_registros
from base_datos import crear_tablas
from motor_rubrica import evaluar_diagnostico
from zonas_maule import COMUNAS_MAULE, obtener_pda_maule_por_comuna


def test_diagnostico_indeterminado_con_dato_indispensable_faltante():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Parque fotovoltaico",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "INDETERMINADO"
    assert "potencia MW" in resultado["datos_faltantes"]
    assert resultado["suficiencia_antecedentes"] == "INCOMPLETOS"


def test_humedal_no_no_exige_distancia():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Almacenamiento BESS",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "nueva_infraestructura": False,
        "respuesta_nueva_infraestructura": "No",
    }
    resultado = evaluar_diagnostico(datos)
    assert "antecedentes tecnicos por cercania menor a 500 m de humedal urbano" not in resultado["datos_faltantes"]
    assert any(h["literal"] == "s)" and h["riesgo"] == "BAJO" for h in resultado["hallazgos"])


def test_bess_no_sabe_obras_electricas_queda_indeterminado():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Almacenamiento BESS",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "nueva_infraestructura": False,
        "respuesta_nueva_infraestructura": "No sabe",
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "INDETERMINADO"
    assert "definir si requiere obras electricas nuevas de conexion o evacuacion" in resultado["datos_faltantes"]


def test_parque_fotovoltaico_294_mw_queda_bajo():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Parque fotovoltaico",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "potencia_mw": 2.94,
        "respuesta_nueva_infraestructura": "No",
        "nueva_infraestructura": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Potencia bajo umbral de 3 MW" for h in resultado["hallazgos"])


def test_parque_fotovoltaico_295_mw_queda_bajo_con_advertencia():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Parque fotovoltaico",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "potencia_mw": 2.95,
        "respuesta_nueva_infraestructura": "No",
        "nueva_infraestructura": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Potencia bajo umbral de 3 MW, con advertencia" for h in resultado["hallazgos"])


def test_parque_fotovoltaico_3_mw_queda_alto():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Parque fotovoltaico",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "potencia_mw": 3.0,
        "respuesta_nueva_infraestructura": "No",
        "nueva_infraestructura": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "ALTO"
    assert any(h["criterio"] == "Potencia mayor o igual a 3 MW" for h in resultado["hallazgos"])


def test_bess_si_obras_electricas_sin_precisar_queda_indeterminado():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Almacenamiento BESS",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "nueva_infraestructura": True,
        "respuesta_nueva_infraestructura": "Si",
        "obras_electricas_nuevas": [],
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "INDETERMINADO"
    assert "precisar que obras electricas nuevas requiere el proyecto" in resultado["datos_faltantes"]


def test_bess_linea_nueva_alta_tension_activa_b1_alto():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Almacenamiento BESS",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "nueva_infraestructura": True,
        "respuesta_nueva_infraestructura": "Si",
        "obras_electricas_nuevas": ["Nueva linea o tramo electrico"],
        "tension_obra_electrica_kv": 66,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "ALTO"
    assert any(h["criterio"] == "Nueva linea o tramo en alta tension" for h in resultado["hallazgos"])


def test_bess_linea_nueva_media_tension_queda_bajo_en_proyecto_nuevo():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Almacenamiento BESS",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "nueva_infraestructura": True,
        "respuesta_nueva_infraestructura": "Si",
        "obras_electricas_nuevas": ["Nueva linea o tramo electrico"],
        "tension_obra_electrica_kv": 23,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert resultado["suficiencia_antecedentes"] == "SUFICIENTES PARA EL MVP"
    assert any(h["criterio"] == "Nueva linea o tramo bajo umbral de alta tension" for h in resultado["hallazgos"])


def test_modificacion_bess_con_linea_media_tension_permite_multiples_componentes():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Modificacion con RCA",
        "subtipo_energia": "Almacenamiento BESS",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "agrega_bess": True,
        "modifica_linea_evacuacion": True,
        "modifica_trazado_linea": True,
        "cambia_punto_conexion": False,
        "modifica_pas": False,
        "otra_modificacion": False,
        "tension_linea_modificada_kv": 23,
        "respuesta_area_fuera_influencia_rca": "No",
        "area_fuera_influencia_rca": False,
        "respuesta_modifica_impactos_evaluados": "No",
        "modifica_impactos_evaluados": False,
        "respuesta_modifica_medidas_rca": "No",
        "modifica_medidas_rca": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["suficiencia_antecedentes"] == "SUFICIENTES PARA EL MVP"
    assert any(h["criterio"] == "Instalacion de BESS sin generacion primaria" for h in resultado["hallazgos"])
    assert any(h["criterio"] == "Linea asociada a la modificacion bajo umbral de alta tension" for h in resultado["hallazgos"])
    assert not any(h["criterio"] == "Linea asociada a la modificacion en alta tension" for h in resultado["hallazgos"])


def test_modificacion_sin_rca_linea_cambio_conductor_media_tension_queda_bajo():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Modificacion sin RCA",
        "subtipo_energia": "Linea de transmision",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "tension_kv": 23,
        "modifica_conductores_linea": True,
        "cambia_trazado": False,
        "otra_modificacion": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Cambio de conductor en linea existente" for h in resultado["hallazgos"])


def test_modificacion_sin_rca_linea_cambio_conductor_alta_tension_existente_no_queda_alto():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Modificacion sin RCA",
        "subtipo_energia": "Linea de transmision",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "tension_kv": 66,
        "modifica_conductores_linea": True,
        "modifica_trazado_linea": False,
        "otra_modificacion": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Cambio de conductor en linea existente" for h in resultado["hallazgos"])
    assert not any(h["criterio"] == "Linea de alta tension" for h in resultado["hallazgos"])


def test_modificacion_sin_rca_linea_nueva_alta_tension_menor_2_km_no_queda_alto():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Modificacion sin RCA",
        "subtipo_energia": "Linea de transmision",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "agrega_linea_transmision": True,
        "tension_linea_propuesta_kv": 66,
        "longitud_linea_km": 2,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Nueva linea de alta tension bajo umbral de longitud" for h in resultado["hallazgos"])


def test_modificacion_sin_rca_linea_nueva_alta_tension_mayor_2_km_queda_alto():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Modificacion sin RCA",
        "subtipo_energia": "Linea de transmision",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "agrega_linea_transmision": True,
        "tension_linea_propuesta_kv": 66,
        "longitud_linea_km": 2.1,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "ALTO"
    assert any(h["criterio"] == "Nueva linea de alta tension mayor a 2 km" for h in resultado["hallazgos"])


def test_modificacion_sin_rca_linea_otra_modificacion_descrita_queda_indeterminada():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Modificacion sin RCA",
        "subtipo_energia": "Linea de transmision",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "tension_kv": 23,
        "modifica_conductores_linea": False,
        "cambia_trazado": False,
        "otra_modificacion": True,
        "descripcion_otra_modificacion": "Cambio de aisladores.",
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "INDETERMINADO"
    assert any(h["criterio"] == "Otra modificacion de linea no clasificada" for h in resultado["hallazgos"])


def test_inmobiliario_zona_saturada_no_sabe_queda_indeterminado():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "respuesta_zona_saturada": "No sabe",
        "zona_saturada": False,
        "numero_viviendas": 299,
        "superficie_ha": 6.2,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "INDETERMINADO"
    assert "seleccionar comuna para verificar PDA o zona saturada en area urbana" in resultado["datos_faltantes"]


def test_detecta_pda_maule_por_comuna_curico():
    assert "Curico" in COMUNAS_MAULE
    assert "No sabe / No indicada" in COMUNAS_MAULE
    assert obtener_pda_maule_por_comuna("Curicó", "Región del Maule") is not None
    assert obtener_pda_maule_por_comuna("Curico", "Region del Maule") is not None
    assert obtener_pda_maule_por_comuna("Curico", "Region Metropolitana") is None


def test_inmobiliario_curico_con_pda_detectado_aplica_zona_saturada():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Curico",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "numero_viviendas": 264,
        "superficie_ha": 1.3,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Viviendas bajo umbral de 300" for h in resultado["hallazgos"])


def test_inmobiliario_295_viviendas_queda_bajo_con_advertencia():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Curico",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "numero_viviendas": 295,
        "superficie_ha": 1.3,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Viviendas bajo umbral de 300, con advertencia" for h in resultado["hallazgos"])


def test_inmobiliario_superficie_62_no_es_cercana_al_umbral():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "tipo_inmobiliario": "Viviendas o loteo habitacional",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Talca",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "numero_viviendas": 264,
        "superficie_ha": 6.2,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Superficie bajo franja cercana al umbral de 7 ha" for h in resultado["hallazgos"])
    assert not any(h["criterio"] == "Superficie cercana al umbral de 7 ha" for h in resultado["hallazgos"])


def test_inmobiliario_superficie_68_queda_bajo_con_advertencia():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "tipo_inmobiliario": "Viviendas o loteo habitacional",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Talca",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "numero_viviendas": 264,
        "superficie_ha": 6.8,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Superficie bajo umbral de 7 ha, con advertencia" for h in resultado["hallazgos"])


def test_inmobiliario_zona_saturada_sin_superficie_queda_indeterminado():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Talca",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "numero_viviendas": 299,
        "superficie_ha": None,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "INDETERMINADO"
    assert "superficie del proyecto para evaluar h.1.3)" in resultado["datos_faltantes"]
    assert any(h["criterio"] == "Faltan antecedentes para evaluar h.1.3)" for h in resultado["hallazgos"])


def test_inmobiliario_zona_saturada_sin_viviendas_queda_indeterminado():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Talca",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "numero_viviendas": None,
        "superficie_ha": 1.5,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "INDETERMINADO"
    assert "numero de viviendas para evaluar h.1.3)" in resultado["datos_faltantes"]
    assert any(h["criterio"] == "Faltan antecedentes para evaluar h.1.3)" for h in resultado["hallazgos"])


def test_inmobiliario_area_urbana_y_rural_activa_g_y_h1():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana y rural",
        "tiene_ipt": True,
        "comuna_proyecto": "Curico",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "numero_viviendas": 100,
        "superficie_ha": 1.0,
    }
    resultado = evaluar_diagnostico(datos)
    assert "g)" in resultado["literales"]
    assert "h.1)" in resultado["literales"]


def test_inmobiliario_rural_con_sistema_propio_activa_h11():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "tipo_inmobiliario": "Viviendas o loteo habitacional",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Sector rural",
        "respuesta_sistema_agua_potable": "Si",
        "respuesta_sistema_aguas_servidas": "No",
        "sistema_agua_potable": True,
        "sistema_aguas_servidas": False,
        "respuesta_vias_expresas_troncales": "No",
        "vias_expresas_troncales": False,
        "numero_viviendas": 10,
        "superficie_ha": 1.0,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "ALTO"
    assert any(h["criterio"] == "Sistemas sanitarios propios en extension urbana o rural" for h in resultado["hallazgos"])


def test_inmobiliario_con_vias_expresas_troncales_activa_h12():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "tipo_inmobiliario": "Equipamiento",
        "subtipo_equipamiento": "Centro comercial",
        "respuesta_aumenta_estacionamientos": "No",
        "respuesta_aumenta_carga_ocupacion": "No",
        "aumenta_estacionamientos": False,
        "aumenta_carga_ocupacion": False,
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "respuesta_incorpora_vialidad_publica": "Si",
        "incorpora_vialidad_publica": True,
        "respuesta_vias_expresas_troncales": "Si",
        "vias_expresas_troncales": True,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "ALTO"
    assert any(h["criterio"] == "Incorpora vias expresas o troncales" for h in resultado["hallazgos"])


def test_inmobiliario_area_urbana_descarta_h11():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "tipo_inmobiliario": "Equipamiento",
        "subtipo_equipamiento": "Cementerio",
        "respuesta_aumenta_estacionamientos": "No",
        "respuesta_aumenta_carga_ocupacion": "No",
        "aumenta_estacionamientos": False,
        "aumenta_carga_ocupacion": False,
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "respuesta_incorpora_vialidad_publica": "No",
        "incorpora_vialidad_publica": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert any(
        h["criterio"] == "h.1.1 no aplica preliminarmente por emplazamiento urbano"
        for h in resultado["hallazgos"]
    )


def test_inmobiliario_extension_urbana_sistemas_no_sabe_queda_indeterminado():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "tipo_inmobiliario": "Viviendas o loteo habitacional",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area de extension urbana",
        "respuesta_sistema_agua_potable": "No sabe",
        "respuesta_sistema_aguas_servidas": "No",
        "sistema_agua_potable": False,
        "sistema_aguas_servidas": False,
        "respuesta_incorpora_vialidad_publica": "No",
        "incorpora_vialidad_publica": False,
        "respuesta_vias_expresas_troncales": "No",
        "vias_expresas_troncales": False,
        "numero_viviendas": 10,
        "superficie_ha": 1.0,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "INDETERMINADO"
    assert "sistemas propios de agua potable o aguas servidas para h.1.1)" in resultado["datos_faltantes"]
    assert any(h["criterio"] == "Falta revisar sistemas sanitarios propios" for h in resultado["hallazgos"])


def test_cementerio_mausoleo_existente_no_exige_viviendas_ni_superficie():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Modificacion sin RCA",
        "tipo_inmobiliario": "Equipamiento",
        "subtipo_equipamiento": "Cementerio",
        "antiguedad_proyecto": "Anterior a la entrada en vigencia del RSEIA (03 de abril 1997)",
        "respuesta_aumenta_estacionamientos": "No",
        "respuesta_aumenta_carga_ocupacion": "No",
        "aumenta_estacionamientos": False,
        "aumenta_carga_ocupacion": False,
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Talca",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "respuesta_incorpora_vialidad_publica": "No",
        "incorpora_vialidad_publica": False,
        "numero_viviendas": None,
        "superficie_ha": None,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert "numero de viviendas para evaluar h.1.3)" not in resultado["datos_faltantes"]
    assert "superficie del proyecto para evaluar h.1.3)" not in resultado["datos_faltantes"]
    assert any(h["criterio"] == "Mejoramiento de cementerio o mausoleo existente sin aumento de uso" for h in resultado["hallazgos"])
    assert "h.1.4)" in resultado["literales"]
    assert "incorporacion de vias expresas o troncales para h.1.2)" not in resultado["datos_faltantes"]
    assert any(h["criterio"] == "h.1.2 no aplica preliminarmente por ausencia de apertura vial" for h in resultado["hallazgos"])


def test_cementerio_mausoleo_sin_fecha_operacion_queda_indeterminado():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Modificacion sin RCA",
        "tipo_inmobiliario": "Equipamiento",
        "subtipo_equipamiento": "Cementerio",
        "antiguedad_proyecto": "No sabe",
        "respuesta_aumenta_estacionamientos": "No",
        "respuesta_aumenta_carga_ocupacion": "No",
        "aumenta_estacionamientos": False,
        "aumenta_carga_ocupacion": False,
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Talca",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "respuesta_incorpora_vialidad_publica": "No",
        "incorpora_vialidad_publica": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "INDETERMINADO"
    assert "inicio de operacion del proyecto existente" in resultado["datos_faltantes"]


def test_modificacion_inmobiliaria_otra_modificacion_mas_humedal_queda_alto():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Modificacion con RCA",
        "tipo_inmobiliario": "Viviendas o loteo habitacional",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "Si",
        "en_humedal": True,
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Talca",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "otra_modificacion": True,
        "modifica_viviendas_inmobiliario": False,
        "modifica_superficie_inmobiliario": False,
        "respuesta_area_fuera_influencia_rca": "No",
        "area_fuera_influencia_rca": False,
        "respuesta_modifica_impactos_evaluados": "No",
        "modifica_impactos_evaluados": False,
        "respuesta_modifica_medidas_rca": "No",
        "modifica_medidas_rca": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "ALTO"
    assert resultado["suficiencia_antecedentes"] == "PARCIALMENTE SUFICIENTES"
    assert "queda pendiente revisar informacion especifica" in resultado["detalle_suficiencia"]
    assert "No implica ingreso automatico al SEIA" in resultado["conclusion"]
    assert "derivarse a consultor" in resultado["conclusion"]
    assert any(h["criterio"] == "Otra modificacion no clasificada" for h in resultado["hallazgos"])
    assert any(h["criterio"] == "Proyecto dentro de humedal urbano" for h in resultado["hallazgos"])
    assert resultado["hallazgos"][0]["riesgo"] == "ALTO"


def test_equipamiento_centro_salud_sin_aumento_de_uso_queda_bajo():
    datos = {
        "sector": "Inmobiliario",
        "tipo_gestion": "Proyecto nuevo",
        "tipo_inmobiliario": "Equipamiento",
        "subtipo_equipamiento": "Centro de salud",
        "respuesta_aumenta_estacionamientos": "No",
        "respuesta_aumenta_carga_ocupacion": "No",
        "aumenta_estacionamientos": False,
        "aumenta_carga_ocupacion": False,
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
        "emplazamiento_inmobiliario": "Area urbana",
        "tiene_ipt": True,
        "comuna_proyecto": "Talca",
        "respuesta_zona_saturada": "Si",
        "zona_saturada": True,
        "respuesta_incorpora_vialidad_publica": "No",
        "incorpora_vialidad_publica": False,
    }
    resultado = evaluar_diagnostico(datos)
    assert resultado["riesgo"] == "BAJO"
    assert any(h["criterio"] == "Equipamiento sin aumento declarado para h.1.4)" for h in resultado["hallazgos"])
    assert "h.1.4)" in resultado["literales"]


def test_subestacion_seccionamiento_disponible_en_motor():
    datos = {
        "sector": "Energia",
        "tipo_gestion": "Proyecto nuevo",
        "subtipo_energia": "Subestacion electrica",
        "funcion_subestacion": "Seccionamiento",
        "respuesta_area_protegida": "No",
        "respuesta_humedal": "No",
    }
    resultado = evaluar_diagnostico(datos)
    assert any(h["criterio"] == "Subestacion de seccionamiento" for h in resultado["hallazgos"])


def _crear_base_temporal():
    conexion = sqlite3.connect(":memory:")
    conexion.row_factory = sqlite3.Row
    crear_tablas(conexion)
    cursor = conexion.execute(
        """
        INSERT INTO documentos (
            id_documento, archivo_json, fecha_resolucion, resultado,
            debe_ingresar_al_seia, resumen_ejecutivo
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("DOC-1", "doc1.json", "2025-01-15", "No debe ingresar", 0, "Resumen"),
    )
    documento_id = cursor.lastrowid
    conexion.execute(
        """
        INSERT INTO proyectos (
            documento_id, nombre_proyecto, region, comuna, tipo_proyecto,
            subtipo_proyecto, proponente
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            documento_id,
            "Proyecto de prueba",
            "Region del Maule",
            "Talca",
            "energia",
            "parque fotovoltaico",
            "Titular",
        ),
    )
    conexion.commit()
    return conexion


def test_consultas_analiticas_con_sqlite_temporal():
    conexion = _crear_base_temporal()
    datos = obtener_registros(conexion)
    assert len(datos) == 1
    indicadores = calcular_indicadores(datos)
    assert indicadores["total_resoluciones"] == 1
    assert indicadores["resoluciones_energia"] == 1
    filtrados = aplicar_filtros(datos, region="Region del Maule")
    assert len(filtrados) == 1
