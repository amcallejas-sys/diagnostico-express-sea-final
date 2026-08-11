from typing import Any


CAMPOS_OBLIGATORIOS = [
    "id_documento",
    "nombre_proyecto",
    "region",
    "comuna",
    "tipo_proyecto",
    "subtipo_proyecto",
    "proponente",
    "fecha_resolucion",
    "resultado",
    "debe_ingresar_al_seia",
    "normativa_citada",
    "criterios_sea",
    "resumen_ejecutivo",
    "palabras_clave",
]


def validar_resultado(resultado: dict[str, Any]) -> list[str]:
    """Devuelve una lista de errores simples encontrados en el JSON."""
    errores: list[str] = []

    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in resultado:
            errores.append(f"Falta el campo obligatorio: {campo}")

    if "debe_ingresar_al_seia" in resultado:
        valor = resultado["debe_ingresar_al_seia"]
        if valor not in [True, False, None]:
            errores.append("debe_ingresar_al_seia debe ser true, false o null")

    if "normativa_citada" in resultado and not isinstance(resultado["normativa_citada"], list):
        errores.append("normativa_citada debe ser una lista")

    if "criterios_sea" in resultado and not isinstance(resultado["criterios_sea"], list):
        errores.append("criterios_sea debe ser una lista")

    if "palabras_clave" in resultado and not isinstance(resultado["palabras_clave"], list):
        errores.append("palabras_clave debe ser una lista")

    for indice, criterio in enumerate(resultado.get("criterios_sea", []), start=1):
        if not isinstance(criterio, dict):
            errores.append(f"El criterio {indice} debe ser un objeto JSON")
            continue

        for campo in ["criterio", "explicacion", "fragmento_respaldo", "nivel_confianza"]:
            if campo not in criterio:
                errores.append(f"Falta {campo} en criterio {indice}")

    return errores
