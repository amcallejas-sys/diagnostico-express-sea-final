from __future__ import annotations

import re
import sqlite3
import unicodedata
from typing import Any


ADVERTENCIA_COMPARADOR = (
    "Comparacion referencial basada solo en resoluciones procesadas en la base local. "
    "No constituye pronunciamiento del SEA, no es jurisprudencia vinculante y no reemplaza "
    "una consulta de pertinencia ni un análisis jurídico-técnico profesional."
)


def normalizar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor).strip().lower()
    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def normalizar_region(valor: Any) -> str:
    texto = normalizar_texto(valor)
    texto = re.sub(r"^region\s+(de|del|de la|del la)\s+", "", texto)
    texto = re.sub(r"^region\s+", "", texto)
    return texto.strip()


def texto_no_disponible(valor: Any) -> str:
    if valor is None:
        return "No disponible"
    texto = str(valor).strip()
    if not texto or texto.lower() == "no determinado":
        return "No disponible"
    return texto


def texto_ingreso_seia(valor: Any) -> str:
    if valor == 1 or valor is True:
        return "Si"
    if valor == 0 or valor is False:
        return "No"
    return "No determinado"


def obtener_palabras_clave(conexion: sqlite3.Connection, documento_id: int) -> list[str]:
    filas = conexion.execute(
        """
        SELECT palabra_clave
        FROM palabras_clave
        WHERE documento_id = ?
        ORDER BY palabra_clave
        """,
        (documento_id,),
    ).fetchall()
    return [str(fila["palabra_clave"]) for fila in filas if fila["palabra_clave"]]


def obtener_criterios(conexion: sqlite3.Connection, documento_id: int) -> list[dict[str, Any]]:
    filas = conexion.execute(
        """
        SELECT criterio, explicacion, fragmento_respaldo, nivel_confianza
        FROM criterios
        WHERE documento_id = ?
        ORDER BY id
        """,
        (documento_id,),
    ).fetchall()
    return [dict(fila) for fila in filas]


def obtener_normativa(conexion: sqlite3.Connection, documento_id: int) -> list[str]:
    filas = conexion.execute(
        """
        SELECT normativa
        FROM normativa_citada
        WHERE documento_id = ?
        ORDER BY normativa
        """,
        (documento_id,),
    ).fetchall()
    return [str(fila["normativa"]) for fila in filas if fila["normativa"]]


def obtener_precedentes(conexion: sqlite3.Connection) -> list[dict[str, Any]]:
    filas = conexion.execute(
        """
        SELECT
            d.id,
            d.id_documento,
            d.fecha_resolucion,
            d.resultado,
            d.debe_ingresar_al_seia,
            d.resumen_ejecutivo,
            p.nombre_proyecto,
            p.region,
            p.comuna,
            p.tipo_proyecto,
            p.subtipo_proyecto
        FROM documentos d
        LEFT JOIN proyectos p ON p.documento_id = d.id
        ORDER BY d.id_documento
        """
    ).fetchall()

    precedentes = []
    for fila in filas:
        precedente = dict(fila)
        documento_id = int(precedente["id"])
        precedente["palabras_clave"] = obtener_palabras_clave(conexion, documento_id)
        precedente["criterios"] = obtener_criterios(conexion, documento_id)
        precedente["normativa_citada"] = obtener_normativa(conexion, documento_id)
        precedentes.append(precedente)
    return precedentes


def sector_proyecto(datos_proyecto: dict[str, Any]) -> str:
    sector = datos_proyecto.get("sector")
    if sector:
        return str(sector)
    tipo = datos_proyecto.get("tipo_proyecto")
    return str(tipo) if tipo else ""


def subtipo_proyecto(datos_proyecto: dict[str, Any]) -> str:
    if datos_proyecto.get("sector") == "Energia":
        return str(datos_proyecto.get("subtipo_energia") or "")
    return str(datos_proyecto.get("subtipo_proyecto") or datos_proyecto.get("emplazamiento_inmobiliario") or "")


def palabras_clave_proyecto(datos_proyecto: dict[str, Any], diagnostico: dict[str, Any] | None) -> set[str]:
    palabras = {
        normalizar_texto(sector_proyecto(datos_proyecto)),
        normalizar_texto(subtipo_proyecto(datos_proyecto)),
        normalizar_texto(datos_proyecto.get("tipo_gestion")),
    }
    if diagnostico:
        for literal in diagnostico.get("literales", []):
            palabras.add(normalizar_texto(literal))
    return {palabra for palabra in palabras if palabra}


def literales_proyecto(diagnostico: dict[str, Any] | None) -> set[str]:
    if not diagnostico:
        return set()
    return {normalizar_texto(literal) for literal in diagnostico.get("literales", []) if literal}


def literales_precedente(precedente: dict[str, Any]) -> set[str]:
    textos = []
    for criterio in precedente.get("criterios", []):
        textos.append(str(criterio.get("criterio") or ""))
        textos.append(str(criterio.get("explicacion") or ""))
    unidos = " ".join(textos)
    candidatos = re.findall(r"(?:art\.\s*2\s*letra\s*)?[a-z](?:\.\d+)?\)", normalizar_texto(unidos))
    return {c.strip() for c in candidatos if c.strip()}


def _coincidencia_texto(valor_a: Any, valor_b: Any) -> bool:
    a = normalizar_texto(valor_a)
    b = normalizar_texto(valor_b)
    return bool(a and b and (a == b or a in b or b in a))


def calcular_coincidencia(
    datos_proyecto: dict[str, Any],
    diagnostico: dict[str, Any] | None,
    precedente: dict[str, Any],
) -> dict[str, Any]:
    puntos = 0
    maximo = 0
    coincidencias: list[str] = []
    diferencias: list[str] = []
    no_comparable: list[str] = []

    region_proyecto = datos_proyecto.get("region")
    region_precedente = precedente.get("region")
    if region_proyecto and region_precedente:
        maximo += 30
        if normalizar_region(region_proyecto) == normalizar_region(region_precedente):
            puntos += 30
            coincidencias.append("Coincide en region.")
        else:
            diferencias.append(
                f"La region del precedente es {texto_no_disponible(region_precedente)} y la del proyecto consultado es {texto_no_disponible(region_proyecto)}."
            )
    else:
        no_comparable.append("No fue posible comparar region por falta de informacion.")

    sector_consultado = sector_proyecto(datos_proyecto)
    sector_precedente = precedente.get("tipo_proyecto")
    if sector_consultado and sector_precedente:
        maximo += 25
        if _coincidencia_texto(sector_consultado, sector_precedente):
            puntos += 25
            coincidencias.append("Coincide en sector o tipo de proyecto.")
        else:
            diferencias.append(
                f"El tipo del precedente es {texto_no_disponible(sector_precedente)} y el proyecto consultado corresponde a {texto_no_disponible(sector_consultado)}."
            )
    else:
        no_comparable.append("No fue posible comparar sector o tipo de proyecto.")

    subtipo_consultado = subtipo_proyecto(datos_proyecto)
    subtipo_precedente = precedente.get("subtipo_proyecto")
    if subtipo_consultado and subtipo_precedente and texto_no_disponible(subtipo_precedente) != "No disponible":
        maximo += 20
        if _coincidencia_texto(subtipo_consultado, subtipo_precedente):
            puntos += 20
            coincidencias.append("Coincide en subtipo de proyecto.")
        else:
            diferencias.append(
                f"El subtipo del precedente es {texto_no_disponible(subtipo_precedente)} y el proyecto consultado corresponde a {texto_no_disponible(subtipo_consultado)}."
            )
    else:
        no_comparable.append("No fue posible comparar subtipo de proyecto.")

    palabras_proyecto = palabras_clave_proyecto(datos_proyecto, diagnostico)
    palabras_precedente = {normalizar_texto(p) for p in precedente.get("palabras_clave", []) if p}
    if palabras_proyecto and palabras_precedente:
        maximo += 15
        interseccion = palabras_proyecto.intersection(palabras_precedente)
        if interseccion:
            proporcion = len(interseccion) / max(len(palabras_proyecto), 1)
            puntos_palabras = min(15, round(15 * proporcion))
            puntos += puntos_palabras
            coincidencias.append("Coincide en palabras clave: " + ", ".join(sorted(interseccion)) + ".")
        else:
            diferencias.append("No se identificaron palabras clave coincidentes.")
    else:
        no_comparable.append("No fue posible comparar palabras clave.")

    literales_consultados = literales_proyecto(diagnostico)
    literales_del_precedente = literales_precedente(precedente)
    if literales_consultados and literales_del_precedente:
        maximo += 10
        interseccion = literales_consultados.intersection(literales_del_precedente)
        if interseccion:
            proporcion = len(interseccion) / max(len(literales_consultados), 1)
            puntos_literales = min(10, round(10 * proporcion))
            puntos += puntos_literales
            coincidencias.append("Coincide en literales o criterios: " + ", ".join(sorted(interseccion)) + ".")
        else:
            diferencias.append("No se identificaron literales o criterios coincidentes.")
    else:
        no_comparable.append("No fue posible comparar literales o criterios identificados.")

    if maximo == 0:
        porcentaje = 0
        clasificacion = "Información insuficiente"
    else:
        porcentaje = round(puntos / maximo * 100)
        if maximo < 50:
            clasificacion = "Información insuficiente"
        elif porcentaje >= 75:
            clasificacion = "Alta coincidencia"
        elif porcentaje >= 50:
            clasificacion = "Coincidencia media"
        else:
            clasificacion = "Coincidencia baja"

    no_comparable.append(
        "No fue posible comparar potencia, tension, viviendas, superficie u otros datos tecnicos porque no estan almacenados en campos estructurados de los precedentes."
    )

    return {
        "puntos": puntos,
        "maximo_evaluable": maximo,
        "porcentaje": porcentaje,
        "clasificacion": clasificacion,
        "coincidencias": coincidencias,
        "diferencias": diferencias,
        "no_comparable": no_comparable,
    }


def comparar_precedentes(
    conexion: sqlite3.Connection,
    datos_proyecto: dict[str, Any],
    diagnostico: dict[str, Any] | None,
    incluir_otras_regiones: bool = False,
    limite: int = 5,
) -> dict[str, Any]:
    precedentes = obtener_precedentes(conexion)
    region_consultada = normalizar_region(datos_proyecto.get("region"))
    regionales = [
        p for p in precedentes if region_consultada and normalizar_region(p.get("region")) == region_consultada
    ]

    usar = regionales
    mensaje = ""
    if not regionales:
        mensaje = "No se encontraron precedentes regionales suficientes."
        if incluir_otras_regiones:
            usar = precedentes
    elif incluir_otras_regiones:
        usar = precedentes

    comparados = []
    for precedente in usar:
        comparacion = calcular_coincidencia(datos_proyecto, diagnostico, precedente)
        precedente_comparado = dict(precedente)
        precedente_comparado["comparacion"] = comparacion
        precedente_comparado["referencia_otra_region"] = (
            bool(region_consultada)
            and normalizar_region(precedente.get("region")) != region_consultada
        )
        comparados.append(precedente_comparado)

    comparados.sort(
        key=lambda item: (
            item["comparacion"]["porcentaje"],
            item["comparacion"]["puntos"],
            item["comparacion"]["maximo_evaluable"],
        ),
        reverse=True,
    )

    return {
        "mensaje": mensaje,
        "hay_regionales": bool(regionales),
        "precedentes": comparados[:limite],
        "total_regionales": len(regionales),
        "total_disponibles": len(precedentes),
    }


def matriz_comparativa(datos_proyecto: dict[str, Any], diagnostico: dict[str, Any] | None, precedentes: list[dict[str, Any]]) -> list[dict[str, str]]:
    filas = []
    atributos = [
        ("Región", datos_proyecto.get("region"), "region"),
        ("Comuna", datos_proyecto.get("comuna"), "comuna"),
        ("Sector", sector_proyecto(datos_proyecto), "tipo_proyecto"),
        ("Subtipo", subtipo_proyecto(datos_proyecto), "subtipo_proyecto"),
        ("Literales relevantes", ", ".join(diagnostico.get("literales", [])) if diagnostico else "", None),
        ("Resultado", diagnostico.get("riesgo") if diagnostico else "", "resultado"),
        ("Debe ingresar al SEIA", "No determinado", "debe_ingresar_al_seia"),
    ]
    for nombre, valor_proyecto, clave_precedente in atributos:
        fila = {"Atributo": nombre, "Proyecto consultado": texto_no_disponible(valor_proyecto)}
        for indice, precedente in enumerate(precedentes[:3], start=1):
            if nombre == "Literales relevantes":
                valor = ", ".join(sorted(literales_precedente(precedente)))
            elif clave_precedente == "debe_ingresar_al_seia":
                valor = texto_ingreso_seia(precedente.get(clave_precedente))
            else:
                valor = precedente.get(clave_precedente) if clave_precedente else ""
            fila[f"Precedente {indice}"] = texto_no_disponible(valor)
        filas.append(fila)
    return filas


def interpretar_comparacion(resultado: dict[str, Any]) -> str:
    precedentes = resultado.get("precedentes", [])
    if not precedentes:
        return (
            "INDETERMINADO: la base disponible no contiene antecedentes suficientes para una comparacion confiable. "
            "Derivar a consultor."
        )

    clasificaciones = [p["comparacion"]["clasificacion"] for p in precedentes]
    resultados = {texto_no_disponible(p.get("resultado")) for p in precedentes}
    partes = []
    if resultado.get("hay_regionales"):
        partes.append("Se encontraron precedentes regionales en la base procesada.")
    else:
        partes.append("No se encontraron precedentes regionales suficientes.")

    if any(c == "Alta coincidencia" for c in clasificaciones):
        partes.append("Existen resoluciones comparables con alta coincidencia descriptiva de antecedentes.")
    elif any(c == "Coincidencia media" for c in clasificaciones):
        partes.append("Predominan coincidencias medias o parciales.")
    elif all(c == "Información insuficiente" for c in clasificaciones):
        partes.append("La información comparable es insuficiente.")
    else:
        partes.append("Las coincidencias disponibles son bajas o parciales.")

    if len(resultados) > 1:
        partes.append(
            "Los precedentes comparables presentan resultados distintos. Se requiere revisión profesional del contexto y de las diferencias técnicas entre los proyectos."
        )

    partes.append("Los precedentes no alteran automaticamente el resultado de la rubrica.")
    return " ".join(partes)


def informe_markdown(
    datos_proyecto: dict[str, Any],
    diagnostico: dict[str, Any] | None,
    precedentes: list[dict[str, Any]],
) -> str:
    lineas = [
        "# Informe comparativo preliminar",
        "",
        ADVERTENCIA_COMPARADOR,
        "",
        "## Proyecto consultado",
    ]
    for clave in ["tipo_gestion", "sector", "region", "subtipo_energia", "emplazamiento_inmobiliario"]:
        if datos_proyecto.get(clave):
            lineas.append(f"- {clave}: {datos_proyecto.get(clave)}")
    if diagnostico:
        lineas.extend(["", "## Diagnóstico preliminar", f"- Riesgo: {diagnostico.get('riesgo')}", f"- Conclusión: {diagnostico.get('conclusion')}"])

    lineas.append("")
    lineas.append("## Precedentes comparados")
    for indice, precedente in enumerate(precedentes, start=1):
        comp = precedente["comparacion"]
        lineas.extend(
            [
                f"### {indice}. {texto_no_disponible(precedente.get('nombre_proyecto') or precedente.get('id_documento'))}",
                f"- Región: {texto_no_disponible(precedente.get('region'))}",
                f"- Resultado: {texto_no_disponible(precedente.get('resultado'))}",
                f"- Debe ingresar al SEIA: {texto_ingreso_seia(precedente.get('debe_ingresar_al_seia'))}",
                f"- Nivel de coincidencia de antecedentes: {comp['clasificacion']} ({comp['puntos']}/{comp['maximo_evaluable']})",
                "- Coincidencias: " + ("; ".join(comp["coincidencias"]) if comp["coincidencias"] else "No disponibles"),
                "- Diferencias: " + ("; ".join(comp["diferencias"]) if comp["diferencias"] else "No disponibles"),
                "- Datos no comparables: " + ("; ".join(comp["no_comparable"]) if comp["no_comparable"] else "No disponibles"),
                "",
            ]
        )
    return "\n".join(lineas)
