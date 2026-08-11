from dataclasses import dataclass
from typing import Any


PESO_RIESGO = {"BAJO": 1, "MEDIO": 2, "ALTO": 3, "INDETERMINADO": 4}
PESO_VISUAL = {"BAJO": 1, "MEDIO": 2, "INDETERMINADO": 3, "ALTO": 4}


@dataclass
class Hallazgo:
    riesgo: str
    literal: str
    criterio: str
    explicacion: str


def _normalizar(texto: str) -> str:
    return texto.strip().lower()


def _agregar(hallazgos: list[Hallazgo], riesgo: str, literal: str, criterio: str, explicacion: str) -> None:
    hallazgos.append(Hallazgo(riesgo=riesgo, literal=literal, criterio=criterio, explicacion=explicacion))


def _evaluar_potencia_generacion(hallazgos: list[Hallazgo], potencia: float | None, etiqueta: str) -> None:
    if potencia is None:
        _agregar(hallazgos, "BAJO", "c)", "Potencia no informada", "No se informo potencia; revisar si corresponde para el proyecto nuevo.")
    elif potencia >= 3:
        _agregar(hallazgos, "ALTO", "c)", f"{etiqueta} mayor o igual a 3 MW", "La potencia nominal informada iguala o supera el umbral de 3 MW.")
    elif 2.95 <= potencia < 3:
        diferencia = 3 - potencia
        _agregar(
            hallazgos,
            "BAJO",
            "c)",
            f"{etiqueta} bajo umbral de 3 MW, con advertencia",
            (
                f"La potencia informada es {potencia:g} MW, por debajo del umbral de 3 MW. "
                f"Se advierte que, si el proyecto aumentare su potencia en {diferencia:.2f} MW o mas, "
                "igualaria o superaria el limite de 3 MW y deberia revisarse nuevamente la pertinencia de ingreso al SEIA."
            ),
        )
    else:
        _agregar(hallazgos, "BAJO", "c)", f"{etiqueta} bajo umbral de 3 MW", "La potencia informada esta bajo la franja cercana al umbral de 3 MW.")


def _no_sabe(datos: dict[str, Any], campo_respuesta: str) -> bool:
    return datos.get(campo_respuesta) == "No sabe"


def _riesgo_final(hallazgos: list[Hallazgo]) -> str:
    if not hallazgos:
        return "BAJO"
    riesgos = {h.riesgo for h in hallazgos}
    if "ALTO" in riesgos:
        return "ALTO"
    if "INDETERMINADO" in riesgos:
        return "INDETERMINADO"
    if "MEDIO" in riesgos:
        return "MEDIO"
    return "BAJO"


def _evaluar_localizacion(datos: dict[str, Any], hallazgos: list[Hallazgo]) -> None:
    if _no_sabe(datos, "respuesta_area_protegida"):
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "p)",
            "Falta verificar area bajo proteccion oficial",
            (
                "No se puede determinar si el proyecto se emplaza en area protegida o bajo proteccion oficial. "
                "Derivar a consultor para revisar cartografia oficial y restricciones territoriales."
            ),
        )
    elif datos.get("en_area_protegida"):
        _agregar(
            hallazgos,
            "ALTO",
            "p)",
            "Area bajo proteccion oficial",
            (
                "El proyecto se declara dentro de un area protegida o bajo proteccion oficial. "
                "Esto no determina por si solo el ingreso al SEIA; se debe derivar a consultor para revisar "
                "magnitud de las obras, localizacion exacta, objeto de proteccion y posible afectacion del area."
            ),
        )
    else:
        _agregar(
            hallazgos,
            "BAJO",
            "p)",
            "Area bajo proteccion oficial descartada preliminarmente",
            "No se declaro emplazamiento dentro de un area protegida o bajo proteccion oficial.",
        )

    if _no_sabe(datos, "respuesta_humedal"):
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "s)",
            "Falta verificar humedal urbano",
            (
                "No se puede determinar si el proyecto esta dentro de un humedal urbano. "
                "Derivar a consultor para revisar cartografia oficial y posible alteracion del humedal."
            ),
        )
    elif datos.get("en_humedal"):
        _agregar(
            hallazgos,
            "ALTO",
            "s)",
            "Proyecto dentro de humedal urbano",
            (
                "El proyecto se declara dentro de humedal urbano. Esto no determina por si solo el ingreso al SEIA; "
                "se debe derivar a consultor para revisar magnitud de las obras, manejo de residuos, escorrentias, "
                "descargas, medidas de control y posible alteracion fisica, quimica o ecosistemica del humedal."
            ),
        )
    else:
        _agregar(
            hallazgos,
            "BAJO",
            "s)",
            "Humedal urbano descartado preliminarmente",
            "No se declaro emplazamiento dentro de humedal urbano.",
        )


def _evaluar_cambios_consideracion_con_rca(datos: dict[str, Any], hallazgos: list[Hallazgo]) -> None:
    if datos.get("tipo_gestion") != "Modificacion con RCA":
        return

    if _no_sabe(datos, "respuesta_area_fuera_influencia_rca"):
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "Art. 2 letra g.1)",
            "Sin antecedente sobre area de influencia de la RCA",
            (
                "No se puede determinar si las partes, obras o acciones se emplazan dentro "
                "o fuera del area de influencia evaluada. Derivar a consultor para revisar RCA, planos y area de influencia."
            ),
        )
    elif datos.get("area_fuera_influencia_rca"):
        _agregar(
            hallazgos,
            "MEDIO",
            "Art. 2 letra g.1)",
            "Nueva area fuera del area de influencia evaluada",
            (
                "La ubicacion solo se considera relevante para esta pregunta si las partes, obras "
                "o acciones se emplazan fuera del area de influencia evaluada en la RCA."
            ),
        )
    else:
        _agregar(
            hallazgos,
            "BAJO",
            "Art. 2 letra g.1)",
            "Sin nueva area fuera del area de influencia evaluada",
            (
                "No se declaro que la modificacion incorpore partes, obras o acciones fuera "
                "del area de influencia evaluada en la RCA."
            ),
        )

    _agregar(
        hallazgos,
        "BAJO",
        "Art. 2 letra g.2)",
        "g.2 descartado preliminarmente para modificacion con RCA",
        (
            "Segun la regla de trabajo del MVP para proyectos con RCA en la Region del Maule, "
            "este criterio se informa como no configurado en el diagnostico preliminar."
        ),
    )

    if _no_sabe(datos, "respuesta_modifica_impactos_evaluados"):
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "Art. 2 letra g.3)",
            "Sin antecedente sobre cambios en impactos evaluados",
            (
                "No se puede determinar si cambia la extension, magnitud o duracion de impactos ambientales evaluados. "
                "Derivar a consultor para comparar la modificacion con la RCA y sus antecedentes tecnicos."
            ),
        )
    elif datos.get("modifica_impactos_evaluados"):
        _agregar(
            hallazgos,
            "MEDIO",
            "Art. 2 letra g.3)",
            "Posible cambio en impactos evaluados",
            "Se declaro que la modificacion podria cambiar la extension, magnitud o duracion de impactos ambientales evaluados.",
        )
    else:
        _agregar(
            hallazgos,
            "BAJO",
            "Art. 2 letra g.3)",
            "Sin cambio declarado en impactos evaluados",
            "No se declaro cambio en extension, magnitud o duracion de impactos ambientales evaluados.",
        )

    if _no_sabe(datos, "respuesta_modifica_medidas_rca"):
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "Art. 2 letra g.4)",
            "Sin antecedente sobre medidas de la RCA",
            (
                "No se puede determinar si la modificacion altera medidas de mitigacion, reparacion o compensacion. "
                "Derivar a consultor para revisar compromisos, medidas y condiciones de la RCA."
            ),
        )
    elif datos.get("modifica_medidas_rca"):
        _agregar(
            hallazgos,
            "MEDIO",
            "Art. 2 letra g.4)",
            "Posible cambio en medidas de la RCA",
            "Se declaro modificacion de medidas de mitigacion, reparacion o compensacion establecidas en la RCA.",
        )
    else:
        _agregar(
            hallazgos,
            "BAJO",
            "Art. 2 letra g.4)",
            "Sin cambio declarado en medidas de la RCA",
            "No se declaro modificacion de medidas de mitigacion, reparacion o compensacion de la RCA.",
        )

    if datos.get("modifica_pas"):
        _agregar(
            hallazgos,
            "MEDIO",
            "PAS",
            "Modificacion de PAS",
            "La modificacion de permisos ambientales sectoriales requiere revision tecnica especifica y su relacion con la RCA.",
        )

    if datos.get("otra_modificacion"):
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "Otro",
            "Otra modificacion no clasificada",
            "El MVP no cuenta con una regla suficiente para esta modificacion. Requiere revision tecnica manual.",
        )


def _evaluar_obras_electricas_nuevas(datos: dict[str, Any], hallazgos: list[Hallazgo]) -> None:
    respuesta = datos.get("respuesta_nueva_infraestructura")
    obras = datos.get("obras_electricas_nuevas") or []

    if respuesta == "No sabe":
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "b.1) / b.2)",
            "Falta definir obras electricas de conexion o evacuacion",
            (
                "No se informo si el proyecto requiere una nueva linea, celda, paño, subestacion, "
                "seccionamiento, punto de conexion u otra obra electrica nueva. Derivar a consultor."
            ),
        )
        return

    if respuesta != "Si":
        _agregar(
            hallazgos,
            "BAJO",
            "b.1) / b.2)",
            "Sin nuevas obras electricas de conexion o evacuacion",
            "Se declara que el proyecto usara infraestructura existente, sin nuevas obras electricas de conexion o evacuacion.",
        )
        return

    if not obras:
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "b.1) / b.2)",
            "Falta precisar tipo de obra electrica nueva",
            "Se declaro que existen obras electricas nuevas, pero no se preciso si corresponden a linea, subestacion, seccionamiento, punto de conexion u otra obra.",
        )
        return

    if "Nueva linea o tramo electrico" in obras:
        tension_obra = datos.get("tension_obra_electrica_kv")
        if tension_obra is None:
            _agregar(
                hallazgos,
                "INDETERMINADO",
                "b.1)",
                "Falta tension de nueva linea o tramo",
                "Se declaro una nueva linea o tramo electrico, pero falta informar su tension. Derivar a consultor.",
            )
        elif tension_obra > 23:
            _agregar(
                hallazgos,
                "ALTO",
                "b.1)",
                "Nueva linea o tramo en alta tension",
                f"La nueva linea o tramo considera {tension_obra:g} kV, superior a 23 kV.",
            )
        else:
            _agregar(
                hallazgos,
                "BAJO",
                "b.1)",
                "Nueva linea o tramo bajo umbral de alta tension",
                (
                    f"La nueva linea o tramo considera {tension_obra:g} kV. "
                    "Al no superar 23 kV, preliminarmente no configura la tipologia de linea de alta tension por literal b.1)."
                ),
            )

    if "Nueva subestacion electrica" in obras:
        funcion_obra = _normalizar(datos.get("funcion_subestacion_obra", ""))
        if funcion_obra in ("", "no sabe", "no aplica"):
            _agregar(
                hallazgos,
                "INDETERMINADO",
                "b.2)",
                "Falta funcion de nueva subestacion",
                "Se declaro una nueva subestacion electrica, pero falta indicar si es de distribucion, seccionamiento, mixta o transporte.",
            )
        elif "transporte" in funcion_obra:
            _agregar(hallazgos, "ALTO", "b.2)", "Nueva subestacion de transporte", "La funcion declarada se asocia a transporte electrico.")
        elif "seccionamiento" in funcion_obra:
            _agregar(hallazgos, "MEDIO", "b.2)", "Nueva subestacion de seccionamiento", "La funcion declarada corresponde a seccionamiento y requiere revision tecnica del alcance de obras.")
        elif "mixta" in funcion_obra:
            _agregar(hallazgos, "MEDIO", "b.2)", "Nueva subestacion mixta", "La subestacion combina funciones de seccionamiento y distribucion.")
        else:
            _agregar(hallazgos, "BAJO", "b.2)", "Nueva subestacion de distribucion", "La funcion declarada es distribucion.")

    if "Ampliacion de subestacion existente: celda, paño o equipos" in obras:
        _agregar(
            hallazgos,
            "MEDIO",
            "b.2)",
            "Ampliacion de subestacion existente",
            "La incorporacion de celda, paño o equipos requiere revisar alcance de obras, conexion e impactos asociados.",
        )

    if "Seccionamiento" in obras:
        _agregar(
            hallazgos,
            "MEDIO",
            "b.1) / b.2)",
            "Seccionamiento electrico",
            "El seccionamiento requiere revisar obras asociadas, paños, subestacion, caminos, area de influencia e impactos.",
        )

    if "Nuevo o cambio de punto de conexion al SEN" in obras:
        _agregar(
            hallazgos,
            "MEDIO",
            "b.1)",
            "Nuevo o cambio de punto de conexion al SEN",
            "El punto de conexion al SEN requiere revisar obras electricas asociadas, tension, trazado y permisos aplicables.",
        )

    if "Otra obra electrica" in obras:
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "b.1) / b.2)",
            "Otra obra electrica no clasificada",
            "El MVP no cuenta con una regla suficiente para clasificar esta obra electrica. Requiere revision tecnica manual.",
        )


def _evaluar_energia(datos: dict[str, Any], hallazgos: list[Hallazgo]) -> None:
    subtipo = _normalizar(datos.get("subtipo_energia", ""))
    tipo_gestion = datos.get("tipo_gestion")
    potencia = datos.get("potencia_mw")
    tension = datos.get("tension_kv")
    tension_linea_modificada = datos.get("tension_linea_modificada_kv")
    longitud_linea = datos.get("longitud_linea_km")
    nueva_infra = datos.get("nueva_infraestructura")
    cambia_trazado = datos.get("cambia_trazado") or datos.get("modifica_trazado_linea")
    funcion_subestacion = _normalizar(datos.get("funcion_subestacion", ""))

    if subtipo == "almacenamiento bess":
        _agregar(
            hallazgos,
            "BAJO",
            "c)",
            "BESS puro no es central generadora",
            "La rubrica indica que un BESS puro no configura por si solo el literal c).",
        )
        if tipo_gestion == "Modificacion con RCA":
            componentes_bess = any(
                [
                    datos.get("agrega_bess"),
                    datos.get("modifica_linea_evacuacion"),
                    datos.get("modifica_trazado_linea"),
                    datos.get("cambia_punto_conexion"),
                    datos.get("modifica_pas"),
                    datos.get("otra_modificacion"),
                ]
            )
            if not componentes_bess:
                _agregar(
                    hallazgos,
                    "INDETERMINADO",
                    "Información insuficiente",
                    "Falta precisar componentes de la modificacion BESS",
                    "Se debe indicar si la modificacion instala BESS, modifica linea, cambia punto de conexion, modifica PAS u otro componente.",
                )

            if datos.get("agrega_bess"):
                _agregar(
                    hallazgos,
                    "BAJO",
                    "c)",
                    "Instalacion de BESS sin generacion primaria",
                    "La instalacion de BESS se analiza como almacenamiento y no como central generadora por si sola.",
                )

            if datos.get("modifica_linea_evacuacion") or datos.get("modifica_trazado_linea"):
                if tension_linea_modificada is None:
                    _agregar(
                        hallazgos,
                        "INDETERMINADO",
                        "b.1)",
                        "Falta tension de linea asociada a la modificacion",
                        "Se declaro modificacion de linea, pero falta informar su tension para revisar el literal b.1).",
                    )
                elif tension_linea_modificada > 23:
                    _agregar(
                        hallazgos,
                        "ALTO",
                        "b.1)",
                        "Linea asociada a la modificacion en alta tension",
                        f"La linea asociada a la modificacion considera {tension_linea_modificada:g} kV, superior a 23 kV.",
                    )
                else:
                    _agregar(
                        hallazgos,
                        "BAJO",
                        "b.1)",
                        "Linea asociada a la modificacion bajo umbral de alta tension",
                        (
                            f"La linea asociada a la modificacion considera {tension_linea_modificada:g} kV. "
                            "Al no superar 23 kV, preliminarmente no configura la tipologia de linea de alta tension por literal b.1). "
                            "Si cambia area de emplazamiento, impactos o medidas, eso debe revisarse en el Art. 2 letra g)."
                        ),
                    )

            if datos.get("cambia_punto_conexion"):
                if tension_linea_modificada is not None and tension_linea_modificada > 23:
                    _agregar(
                        hallazgos,
                        "ALTO",
                        "b.1)",
                        "Cambio de punto de conexion con alta tension",
                        "El cambio de punto de conexion considera tension superior a 23 kV.",
                    )
                else:
                    _agregar(
                        hallazgos,
                        "MEDIO",
                        "b.1)",
                        "Cambio de punto de conexion",
                        "El cambio de punto de conexion requiere revisar obras electricas asociadas y su relacion con la RCA.",
                    )
        else:
            _evaluar_obras_electricas_nuevas(datos, hallazgos)

    elif subtipo == "parque fotovoltaico":
        modifica_potencia_parque = datos.get("modifica_potencia_parque")
        potencia_rca = datos.get("potencia_rca_mw")
        potencia_propuesta = datos.get("potencia_propuesta_mw")

        if (
            tipo_gestion == "Modificacion con RCA"
            and modifica_potencia_parque
            and (potencia_rca is None or potencia_propuesta is None)
        ):
            _agregar(
                hallazgos,
                "INDETERMINADO",
                "c)",
                "Falta comparar potencia RCA y potencia propuesta",
                (
                    "Se declaro cambio en numero de paneles o tecnologia, pero falta informar la potencia aprobada "
                    "en la RCA o la potencia propuesta. Derivar a consultor o completar ambos datos para evaluar el literal c)."
                ),
            )
        elif tipo_gestion == "Modificacion con RCA" and modifica_potencia_parque and potencia_propuesta > potencia_rca:
            diferencia = potencia_propuesta - potencia_rca
            _agregar(
                hallazgos,
                "MEDIO",
                "c)",
                "Aumento de potencia respecto de la RCA",
                (
                    f"La modificacion aumenta la potencia desde {potencia_rca:g} MW a {potencia_propuesta:g} MW "
                    f"(+{diferencia:g} MW). Corresponde revisar si este aumento modifica la generacion aprobada "
                    "y si se relaciona con cambios en impactos evaluados."
                ),
            )
        elif tipo_gestion == "Modificacion con RCA" and modifica_potencia_parque and potencia_propuesta <= potencia_rca:
            diferencia = potencia_propuesta - potencia_rca
            criterio = "Disminucion de potencia respecto de la RCA" if diferencia < 0 else "Potencia se mantiene respecto de la RCA"
            explicacion = (
                f"La potencia propuesta es {potencia_propuesta:g} MW frente a {potencia_rca:g} MW aprobados en la RCA. "
                "Aunque se modifique tecnologia o numero de paneles, no se declara aumento de potencia; "
                "preliminarmente no se configura cambio por literal c) por este factor."
            )
            _agregar(hallazgos, "BAJO", "c)", criterio, explicacion)
        elif tipo_gestion == "Modificacion con RCA" and not modifica_potencia_parque:
            _agregar(
                hallazgos,
                "BAJO",
                "c)",
                "Tipologia base sin modificacion de generacion",
                (
                    "El literal c) se reconoce como tipologia base de la RCA del parque fotovoltaico. "
                    "Sin embargo, la modificacion consultada no declara cambio en numero de paneles, "
                    "capacidad ni potencia, por lo que no se configura un cambio por literal c) en esta modificacion."
                ),
            )
        else:
            _evaluar_potencia_generacion(hallazgos, potencia, "Potencia")

        if tipo_gestion != "Modificacion con RCA":
            _evaluar_obras_electricas_nuevas(datos, hallazgos)

        if tipo_gestion == "Modificacion con RCA":
            if datos.get("agrega_bess"):
                if datos.get("area_fuera_influencia_rca"):
                    _agregar(
                        hallazgos,
                        "MEDIO",
                        "Art. 2 letra g.1)",
                        "BESS en nueva area",
                        "La incorporacion de BESS requiere revisar g.1) si sus obras quedan fuera del area de influencia evaluada.",
                    )
                else:
                    _agregar(
                        hallazgos,
                        "BAJO",
                        "c)",
                        "Incorporacion de BESS sin generacion primaria",
                        "La rubrica trata el BESS puro como almacenamiento, no como central generadora por si solo.",
                    )

            if datos.get("cambia_punto_conexion"):
                if tension_linea_modificada is not None and tension_linea_modificada > 23:
                    _agregar(
                        hallazgos,
                        "ALTO",
                        "b.1)",
                        "Cambio de punto de conexion con alta tension",
                        "El cambio de conexion al SEN considera tension superior a 23 kV.",
                    )
                else:
                    _agregar(
                        hallazgos,
                        "MEDIO",
                        "b.1)",
                        "Cambio de punto de conexion",
                        "Aunque no se informe alta tension, el cambio de punto de conexion debe revisarse por posible infraestructura electrica asociada.",
                    )

            if datos.get("modifica_linea_evacuacion"):
                if tension_linea_modificada is not None and tension_linea_modificada > 23:
                    _agregar(
                        hallazgos,
                        "ALTO",
                        "b.1)",
                        "Modificacion o nueva linea en alta tension",
                        "La linea de evacuacion nueva o modificada supera 23 kV.",
                    )
                else:
                    _agregar(
                        hallazgos,
                        "MEDIO",
                        "b.1)",
                        "Modificacion o nueva linea de evacuacion",
                        "La modificacion de linea de evacuacion requiere revisar trazado, tension, estructuras y faja.",
                    )

    elif subtipo == "central generadora":
        _evaluar_potencia_generacion(hallazgos, potencia, "Central")

    elif subtipo == "linea de transmision":
        if tipo_gestion == "Modificacion con RCA":
            agrega_linea = datos.get("agrega_linea_transmision")
            seccionamiento = datos.get("seccionamiento_linea")
            modifica_conductores = datos.get("modifica_conductores_linea")
            modifica_trazado = datos.get("modifica_trazado_linea")
            tension_rca = datos.get("tension_linea_rca_kv")
            tension_propuesta = datos.get("tension_linea_propuesta_kv")

            if not (agrega_linea or seccionamiento or modifica_conductores or modifica_trazado):
                _agregar(
                    hallazgos,
                    "BAJO",
                    "b.1)",
                    "Tipologia base sin modificacion tecnica de linea",
                    (
                        "La linea de transmision puede ser parte de la RCA base, pero no se declaro nueva linea, "
                        "seccionamiento, cambio de conductores, cambio de trazado ni faja para esta modificacion."
                    ),
                )

            if agrega_linea:
                if tension_propuesta is None:
                    _agregar(
                        hallazgos,
                        "INDETERMINADO",
                        "b.1)",
                        "Falta tension de nueva linea o tramo",
                        "Se declaro nueva linea o tramo, pero falta informar su tension. Derivar a consultor.",
                    )
                elif tension_propuesta > 23:
                    _agregar(
                        hallazgos,
                        "ALTO",
                        "b.1)",
                        "Nueva linea o tramo en alta tension",
                        f"La nueva linea o tramo considera {tension_propuesta:g} kV, superior a 23 kV.",
                    )
                else:
                    _agregar(
                        hallazgos,
                        "MEDIO",
                        "b.1)",
                        "Nueva linea o tramo en media/baja tension",
                        (
                            f"La nueva linea o tramo considera {tension_propuesta:g} kV. "
                            "Aunque no supera 23 kV, requiere revisar obras, trazado, faja y area de influencia."
                        ),
                    )

            if seccionamiento:
                _agregar(
                    hallazgos,
                    "MEDIO",
                    "b.1)",
                    "Seccionamiento de linea",
                    (
                        "El seccionamiento no se evalua solo por tension. Requiere revisar obras asociadas, "
                        "paños, subestacion, caminos, area de influencia e impactos de la modificacion."
                    ),
                )

            if modifica_conductores or modifica_trazado:
                if tension_rca is None or tension_propuesta is None:
                    _agregar(
                        hallazgos,
                        "INDETERMINADO",
                        "b.1)",
                        "Falta comparar tension RCA y tension propuesta",
                        (
                            "Se declaro modificacion de conductores, trazado, estructuras o faja, pero falta comparar "
                            "la tension aprobada en la RCA con la tension propuesta. Derivar a consultor."
                        ),
                    )
                elif tension_propuesta > tension_rca:
                    diferencia = tension_propuesta - tension_rca
                    _agregar(
                        hallazgos,
                        "MEDIO",
                        "b.1)",
                        "Aumento de tension respecto de la RCA",
                        (
                            f"La tension aumenta desde {tension_rca:g} kV a {tension_propuesta:g} kV "
                            f"(+{diferencia:g} kV). Corresponde revisar si modifica la tipologia base o los impactos evaluados."
                        ),
                    )
                else:
                    _agregar(
                        hallazgos,
                        "BAJO",
                        "b.1)",
                        "Tension se mantiene o disminuye respecto de la RCA",
                        (
                            f"La tension propuesta es {tension_propuesta:g} kV frente a {tension_rca:g} kV aprobados. "
                            "Preliminarmente no hay aumento de tension por este factor; igualmente revisar g.1), g.3) y g.4) si cambia trazado, faja u obras."
                        ),
                    )

        elif tipo_gestion == "Modificacion sin RCA" and datos.get("agrega_linea_transmision"):
            tension_nueva = datos.get("tension_linea_propuesta_kv")
            if tension_nueva is None or longitud_linea is None:
                _agregar(
                    hallazgos,
                    "INDETERMINADO",
                    "b.1)",
                    "Falta caracterizar nueva linea o tramo",
                    "Se declaro una nueva linea o tramo, pero falta informar tension y longitud para revisar el literal b.1).",
                )
            elif tension_nueva > 23 and longitud_linea > 2:
                _agregar(
                    hallazgos,
                    "ALTO",
                    "b.1)",
                    "Nueva linea de alta tension mayor a 2 km",
                    f"La nueva linea o tramo considera {tension_nueva:g} kV y {longitud_linea:g} km.",
                )
            elif tension_nueva > 23:
                _agregar(
                    hallazgos,
                    "BAJO",
                    "b.1)",
                    "Nueva linea de alta tension bajo umbral de longitud",
                    (
                        f"La nueva linea o tramo considera {tension_nueva:g} kV, pero su longitud informada es "
                        f"{longitud_linea:g} km, por lo que no supera el umbral de 2 km usado por el MVP para b.1)."
                    ),
                )
            else:
                _agregar(
                    hallazgos,
                    "BAJO",
                    "b.1)",
                    "Nueva linea bajo umbral de alta tension",
                    f"La nueva linea o tramo considera {tension_nueva:g} kV y no supera 23 kV.",
                )
        elif tipo_gestion == "Modificacion sin RCA" and datos.get("modifica_conductores_linea") and not cambia_trazado:
            _agregar(
                hallazgos,
                "BAJO",
                "b.1)",
                "Cambio de conductor en linea existente",
                (
                    "Se declaro cambio de conductor o capacidad en una linea existente, sin cambio de trazado, "
                    "estructuras ni faja. La tension de la linea existente no activa por si sola una nueva "
                    "tipologia b.1) en este diagnostico preliminar."
                ),
            )
        elif tipo_gestion == "Proyecto nuevo" and tension is not None and longitud_linea is not None and tension > 23 and longitud_linea > 2:
            _agregar(
                hallazgos,
                "ALTO",
                "b.1)",
                "Linea nueva de alta tension mayor a 2 km",
                f"La linea nueva considera {tension:g} kV y {longitud_linea:g} km.",
            )
        elif tipo_gestion == "Proyecto nuevo" and tension is not None and tension > 23:
            _agregar(
                hallazgos,
                "BAJO",
                "b.1)",
                "Linea nueva bajo umbral de longitud b.1)",
                (
                    f"La linea nueva considera {tension:g} kV, pero no se informo una longitud mayor a 2 km. "
                    "Preliminarmente no configura b.1) por este factor en el MVP."
                ),
            )
        elif tension is not None and tension >= 15 and cambia_trazado:
            _agregar(hallazgos, "MEDIO", "b.1)", "Ajustes de trazado en media tension", "La tension es media, pero hay ajustes de trazado o estructuras.")
        else:
            _agregar(hallazgos, "BAJO", "b.1)", "Linea de distribucion o ajuste menor", "No se informa tension mayor a 23 kV ni nuevo trazado relevante.")

        if cambia_trazado and tension is not None and tension > 23:
            _agregar(hallazgos, "ALTO", "b.1)", "Nuevo trazado o faja", "Nuevo trazado, estructuras o faja elevan el riesgo.")
        if tipo_gestion == "Modificacion sin RCA" and datos.get("otra_modificacion"):
            descripcion = datos.get("descripcion_otra_modificacion") or "No se describio la otra modificacion."
            _agregar(
                hallazgos,
                "INDETERMINADO",
                "Otro",
                "Otra modificacion de linea no clasificada",
                f"Descripcion entregada: {descripcion} Requiere revision tecnica porque el MVP no cuenta con una regla especifica para este cambio.",
            )

    elif subtipo == "subestacion electrica":
        if "transporte" in funcion_subestacion:
            _agregar(hallazgos, "ALTO", "b.2)", "Subestacion de transporte", "La funcion declarada se asocia a tension de transporte.")
        elif "seccionamiento" in funcion_subestacion:
            _agregar(
                hallazgos,
                "MEDIO",
                "b.2)",
                "Subestacion de seccionamiento",
                "La funcion declarada corresponde a seccionamiento y requiere revisar obras, conexion y relacion con el sistema electrico.",
            )
        elif "mixta" in funcion_subestacion:
            _agregar(hallazgos, "MEDIO", "b.2)", "Funcion mixta", "La subestacion combina seccionamiento y distribucion.")
        else:
            _agregar(hallazgos, "BAJO", "b.2)", "Subestacion de distribucion", "La funcion declarada es reducir tension hacia distribucion.")


def _evaluar_inmobiliario(datos: dict[str, Any], hallazgos: list[Hallazgo]) -> None:
    viviendas = datos.get("numero_viviendas")
    superficie = datos.get("superficie_ha")
    tipo_inmobiliario = datos.get("tipo_inmobiliario") or "Viviendas o loteo habitacional"
    subtipo_equipamiento = datos.get("subtipo_equipamiento") or "No aplica"
    antiguedad_proyecto = datos.get("antiguedad_proyecto")
    tiene_ipt = datos.get("tiene_ipt")
    emplazamiento = datos.get("emplazamiento_inmobiliario")
    zona_saturada = datos.get("zona_saturada")
    respuesta_zona_saturada = datos.get("respuesta_zona_saturada")
    comuna = datos.get("comuna_proyecto")
    es_urbano = emplazamiento in ["Area urbana", "Area urbana y rural", "Area con IPT vigente"]
    es_extension_o_rural = emplazamiento in ["Area de extension urbana", "Sector rural", "Area urbana y rural"]
    es_rural = emplazamiento in ["Sector rural", "Area urbana y rural"]

    if emplazamiento == "No sabe":
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "g) / h.1)",
            "Falta determinar emplazamiento inmobiliario",
            "No se puede definir si corresponde analizar g) por sector rural o h.1 por area con IPT vigente.",
        )
    elif es_rural:
        _agregar(
            hallazgos,
            "MEDIO",
            "g)",
            "Proyecto inmobiliario en sector rural",
            "Al emplazarse en sector rural, el analisis preliminar debe concentrarse en la tipologia g).",
        )

    if es_urbano:
        _agregar(
            hallazgos,
            "BAJO",
            "h.1)",
            "Proyecto en area urbana",
            "Al emplazarse en area urbana, el analisis preliminar se orienta a h.1 y sus umbrales.",
        )

    evaluar_h1 = es_urbano

    if es_extension_o_rural:
        if (
            datos.get("respuesta_sistema_agua_potable") == "No sabe"
            or datos.get("respuesta_sistema_aguas_servidas") == "No sabe"
        ):
            _agregar(
                hallazgos,
                "INDETERMINADO",
                "h.1.1)",
                "Falta revisar sistemas sanitarios propios",
                (
                    "Para area de extension urbana o sector rural, falta determinar si el proyecto requiere "
                    "sistemas propios de produccion/distribucion de agua potable o de recoleccion, tratamiento "
                    "y disposicion de aguas servidas."
                ),
            )
        elif datos.get("sistema_agua_potable") or datos.get("sistema_aguas_servidas"):
            _agregar(
                hallazgos,
                "ALTO",
                "h.1.1)",
                "Sistemas sanitarios propios en extension urbana o rural",
                (
                    "El proyecto se emplaza en area de extension urbana o rural y declara requerir sistemas propios "
                    "de agua potable o aguas servidas."
                ),
            )
        else:
            _agregar(
                hallazgos,
                "BAJO",
                "h.1.1)",
                "Sin sistemas sanitarios propios declarados",
                "No se declaro requerimiento de sistemas propios de agua potable ni aguas servidas para h.1.1).",
            )
    elif emplazamiento in ["Area urbana", "Area con IPT vigente"]:
        _agregar(
            hallazgos,
            "BAJO",
            "h.1.1)",
            "h.1.1 no aplica preliminarmente por emplazamiento urbano",
            (
                "El proyecto se declara emplazado en area urbana. h.1.1) se refiere a proyectos en area de "
                "extension urbana o sector rural que requieren sistemas propios de agua potable o aguas servidas; "
                "por tanto, se descarta preliminarmente en el MVP."
            ),
        )

    respuesta_vialidad_publica = datos.get("respuesta_incorpora_vialidad_publica") or "No"
    es_cementerio = tipo_inmobiliario == "Equipamiento" and subtipo_equipamiento in ["Cementerio", "Cementerio o mausoleo"]

    if respuesta_vialidad_publica == "No sabe":
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "h.1.2)",
            "Falta revisar apertura de vias publicas",
            (
                "No se informo si el proyecto considera apertura o incorporacion de nuevas vias/calles "
                "al dominio nacional de uso publico. Si existe apertura de calles, revisar CIP y clasificacion vial."
            ),
        )
    elif respuesta_vialidad_publica != "Si":
        if es_cementerio:
            _agregar(
                hallazgos,
                "BAJO",
                "h.1.2)",
                "h.1.2 no aplica preliminarmente por ausencia de apertura vial",
                (
                    "Para el cementerio consultado no se declaro apertura o incorporacion de nuevas vias/calles "
                    "al dominio nacional de uso publico. Por tanto, h.1.2) se descarta preliminarmente en el MVP."
                ),
            )
        else:
            _agregar(
                hallazgos,
                "BAJO",
                "h.1.2)",
                "Sin apertura de nuevas vias publicas declarada",
                "No se declaro apertura o incorporacion de nuevas vias/calles al uso publico.",
            )
    elif datos.get("respuesta_vias_expresas_troncales") == "No sabe":
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "h.1.2)",
            "Falta revisar vias expresas o troncales",
            (
                "Se declaro apertura o incorporacion de nuevas vias/calles al uso publico, pero no se informo "
                "si corresponden a vias expresas o troncales. "
                "Este antecedente puede revisarse en el Certificado de Informaciones Previas."
            ),
        )
    elif datos.get("vias_expresas_troncales"):
        _agregar(
            hallazgos,
            "ALTO",
            "h.1.2)",
            "Incorpora vias expresas o troncales",
            "Se declaro incorporacion al uso publico de vias expresas o troncales.",
        )
    elif datos.get("respuesta_vias_expresas_troncales") == "No":
        _agregar(
            hallazgos,
            "BAJO",
            "h.1.2)",
            "Apertura vial sin vias expresas o troncales declaradas",
            "Se declaro apertura o incorporacion de vias/calles al uso publico, pero no vias expresas o troncales.",
        )

    es_cementerio_o_mausoleo = (
        tipo_inmobiliario == "Cementerio o mausoleo existente"
        or (tipo_inmobiliario == "Equipamiento" and subtipo_equipamiento in ["Cementerio", "Cementerio o mausoleo"])
    )

    if es_cementerio_o_mausoleo:
        if datos.get("tipo_gestion") == "Modificacion sin RCA" and antiguedad_proyecto == "No sabe":
            _agregar(
                hallazgos,
                "INDETERMINADO",
                "h.1) / fecha de operacion",
                "Falta fecha de inicio de operacion",
                (
                    "No se informo si el proyecto existente opera desde antes del 03-04-1997. "
                    "Este antecedente permite orientar el analisis hacia las obras o modificaciones posteriores a la entrada en vigencia del RSEIA."
                ),
            )
            return

        if datos.get("respuesta_aumenta_estacionamientos") == "No sabe" or datos.get("respuesta_aumenta_carga_ocupacion") == "No sabe":
            _agregar(
                hallazgos,
                "INDETERMINADO",
                "h.1.4)",
                "Falta revisar estacionamientos o carga de ocupacion",
                (
                    "Para analizar h.1.4) en equipamiento existente, el MVP necesita saber si la modificacion "
                    "aumenta estacionamientos o carga de ocupacion. Si no se sabe, derivar a consultor."
                ),
            )
            return

        if datos.get("aumenta_estacionamientos") or datos.get("aumenta_carga_ocupacion"):
            _agregar(
                hallazgos,
                "MEDIO",
                "h.1.4)",
                "Equipamiento existente con aumento de estacionamientos o carga",
                (
                    "Se declaro aumento de estacionamientos o carga de ocupacion para h.1.4). "
                    "El MVP no cuenta aun con umbrales estructurados para este subtipo, por lo que requiere revision tecnica."
                ),
            )
            return

        explicacion_antiguedad = ""
        if antiguedad_proyecto in [
            "Anterior al 03-04-1997",
            "Anterior a la entrada en vigencia del RSEIA (03 de abril 1997)",
        ]:
            explicacion_antiguedad = (
                " El proyecto existente se declaro anterior a la entrada en vigencia del RSEIA "
                "(03 de abril 1997); el analisis preliminar se concentra en las obras o modificaciones posteriores a esa fecha."
            )
        _agregar(
            hallazgos,
            "BAJO",
            "h.1.4)",
            "Mejoramiento de cementerio o mausoleo existente sin aumento de uso",
            (
                "No se declaro aumento de viviendas, estacionamientos ni carga de ocupacion. "
                "Para el MVP, h.1.4) se descarta preliminarmente por no aumentar estacionamientos ni carga de ocupacion, "
                "y el mejoramiento acotado de estructura existente no se evalua por umbrales habitacionales h.1.3)."
                + explicacion_antiguedad
            ),
        )
        return

    if tipo_inmobiliario in ["Equipamiento", "Equipamiento, comercio o servicios"]:
        if datos.get("respuesta_aumenta_estacionamientos") == "No sabe" or datos.get("respuesta_aumenta_carga_ocupacion") == "No sabe":
            _agregar(
                hallazgos,
                "INDETERMINADO",
                "h.1.4)",
                "Falta revisar estacionamientos o carga de ocupacion",
                "Para analizar h.1.4) en equipamiento, faltan antecedentes para determinar si aumenta estacionamientos o carga de ocupacion.",
            )
            return
        if datos.get("aumenta_estacionamientos") or datos.get("aumenta_carga_ocupacion"):
            _agregar(
                hallazgos,
                "MEDIO",
                "h.1.4)",
                "Equipamiento con aumento de estacionamientos o carga",
                (
                    f"Subtipo declarado: {subtipo_equipamiento}. Se declaro aumento de estacionamientos o carga para h.1.4). "
                    "pero no cuenta aun con umbrales especificos estructurados para este subtipo."
                ),
            )
        else:
            _agregar(
                hallazgos,
                "BAJO",
                "h.1.4)",
                "Equipamiento sin aumento declarado para h.1.4)",
                f"Subtipo declarado: {subtipo_equipamiento}. No se declaro aumento de estacionamientos ni carga de ocupacion.",
            )
        return

    if tipo_inmobiliario == "Otro proyecto inmobiliario":
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "h.1) / g)",
            "Tipo inmobiliario no clasificado",
            "El MVP no cuenta con una regla suficiente para este tipo de proyecto inmobiliario. Derivar a consultor.",
        )
        return

    if evaluar_h1 and respuesta_zona_saturada == "No sabe":
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "h.1.3)",
            "Falta verificar zona latente o saturada",
            (
                "No se puede determinar si la comuna esta en zona latente o saturada. "
                "Este antecedente puede ser relevante para aplicar los umbrales h.1.3)."
            ),
        )
        return

    datos_h13_faltantes = []
    if evaluar_h1 and zona_saturada and viviendas is None:
        datos_h13_faltantes.append("numero de viviendas")
    if evaluar_h1 and zona_saturada and superficie is None:
        datos_h13_faltantes.append("superficie del proyecto")

    if datos_h13_faltantes:
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "h.1.3)",
            "Faltan antecedentes para evaluar h.1.3)",
            (
                "No se informo " + ", ".join(datos_h13_faltantes) + ". Para revisar correctamente h.1.3), "
                "el MVP requiere contrastar viviendas y superficie; dejar 0 se interpreta como dato no disponible."
            ),
        )
        return

    if evaluar_h1 and zona_saturada and viviendas is not None and viviendas >= 300:
        _agregar(
            hallazgos,
            "ALTO",
            "h.1.3)",
            "300 o mas viviendas en zona latente/saturada",
            f"Se supera el umbral habitacional relevante. Comuna considerada: {comuna or 'no informada'}.",
        )
    elif evaluar_h1 and viviendas is not None and 295 <= viviendas < 300:
        unidades_para_umbral = 300 - viviendas
        _agregar(
            hallazgos,
            "BAJO",
            "h.1.3)",
            "Viviendas bajo umbral de 300, con advertencia",
            (
                f"El proyecto considera {viviendas:g} viviendas, por debajo del umbral de 300. "
                f"Se advierte que, si el proyecto aumentare la cantidad de viviendas en {unidades_para_umbral:g} "
                "o mas unidades, igualaria o superaria el limite de 300 viviendas y deberia revisarse nuevamente "
                "la pertinencia de ingreso al SEIA."
            ),
        )
    elif evaluar_h1 and viviendas is not None:
        _agregar(
            hallazgos,
            "BAJO",
            "h.1.3)",
            "Viviendas bajo umbral de 300",
            f"El proyecto considera {viviendas:g} viviendas, por debajo de la franja cercana al umbral de 300.",
        )

    if evaluar_h1 and zona_saturada and superficie is not None and superficie >= 7:
        _agregar(
            hallazgos,
            "ALTO",
            "h.1.3)",
            "Superficie mayor o igual a 7 ha",
            f"La superficie supera el umbral en zona latente o saturada. Comuna considerada: {comuna or 'no informada'}.",
        )
    elif evaluar_h1 and superficie is not None and superficie >= 6.8:
        _agregar(
            hallazgos,
            "BAJO",
            "h.1.3)",
            "Superficie bajo umbral de 7 ha, con advertencia",
            (
                f"La superficie informada es {superficie:g} ha. Aunque esta bajo el umbral de 7 ha, "
                "queda en una franja cercana que conviene revisar si el proyecto aumenta su superficie."
            ),
        )
    elif evaluar_h1 and superficie is not None:
        _agregar(
            hallazgos,
            "BAJO",
            "h.1.3)",
            "Superficie bajo franja cercana al umbral de 7 ha",
            f"La superficie informada es {superficie:g} ha, bajo la franja de alerta preliminar de 6,8 ha.",
        )


def _evaluar_modificacion_inmobiliaria(datos: dict[str, Any], hallazgos: list[Hallazgo]) -> None:
    modifica_viviendas = datos.get("modifica_viviendas_inmobiliario")
    modifica_superficie = datos.get("modifica_superficie_inmobiliario")
    emplazamiento = datos.get("emplazamiento_inmobiliario")

    if emplazamiento == "Sector rural":
        literal_inmobiliario = "g)"
        contexto = "sector rural"
    elif emplazamiento in ["Area urbana", "Area con IPT vigente"]:
        literal_inmobiliario = "h.1)"
        contexto = "area urbana"
    elif emplazamiento == "Area urbana y rural":
        literal_inmobiliario = "g) / h.1)"
        contexto = "area urbana y rural"
    else:
        literal_inmobiliario = "g) / h.1)"
        contexto = "emplazamiento no determinado"
        _agregar(
            hallazgos,
            "INDETERMINADO",
            literal_inmobiliario,
            "Falta determinar emplazamiento inmobiliario",
            "No se puede definir si la modificacion debe analizarse por g) o por h.1). Derivar a consultor.",
        )

    if not (modifica_viviendas or modifica_superficie):
        _agregar(
            hallazgos,
            "BAJO",
            literal_inmobiliario,
            "Tipologia base sin modificacion de magnitud inmobiliaria",
            (
                f"La RCA del proyecto puede tener una tipologia inmobiliaria base asociada a {contexto}, "
                "pero no se declaro cambio en viviendas ni superficie urbanizada para esta modificacion."
            ),
        )
        return

    viviendas_rca = datos.get("viviendas_rca")
    viviendas_propuestas = datos.get("viviendas_propuestas")
    if modifica_viviendas:
        if viviendas_rca is None or viviendas_propuestas is None:
            _agregar(
                hallazgos,
                "INDETERMINADO",
                literal_inmobiliario,
                "Falta comparar viviendas RCA y viviendas propuestas",
                "Se declaro cambio en viviendas, pero falta informar viviendas aprobadas en la RCA o viviendas propuestas.",
            )
        elif viviendas_propuestas > viviendas_rca:
            diferencia = viviendas_propuestas - viviendas_rca
            _agregar(
                hallazgos,
                "MEDIO",
                literal_inmobiliario,
                "Aumento de viviendas respecto de la RCA",
                (
                    f"La modificacion aumenta de {viviendas_rca:g} a {viviendas_propuestas:g} viviendas "
                    f"(+{diferencia:g}). Esto debe revisarse junto con el Art. 2 letra g.3)."
                ),
            )
        else:
            _agregar(
                hallazgos,
                "BAJO",
                literal_inmobiliario,
                "Viviendas se mantienen o disminuyen respecto de la RCA",
                (
                    f"La modificacion propone {viviendas_propuestas:g} viviendas frente a {viviendas_rca:g} "
                    "aprobadas en la RCA; preliminarmente no hay aumento de magnitud por este factor."
                ),
            )

    superficie_rca = datos.get("superficie_rca_ha")
    superficie_propuesta = datos.get("superficie_propuesta_ha")
    if modifica_superficie:
        if superficie_rca is None or superficie_propuesta is None:
            _agregar(
                hallazgos,
                "INDETERMINADO",
                literal_inmobiliario,
                "Falta comparar superficie RCA y superficie propuesta",
                "Se declaro cambio de superficie, pero falta informar superficie aprobada en la RCA o superficie propuesta.",
            )
        elif superficie_propuesta > superficie_rca:
            diferencia = superficie_propuesta - superficie_rca
            _agregar(
                hallazgos,
                "MEDIO",
                literal_inmobiliario,
                "Aumento de superficie respecto de la RCA",
                (
                    f"La modificacion aumenta de {superficie_rca:g} ha a {superficie_propuesta:g} ha "
                    f"(+{diferencia:g} ha). Esto debe revisarse junto con area de influencia e impactos evaluados."
                ),
            )
        else:
            _agregar(
                hallazgos,
                "BAJO",
                literal_inmobiliario,
                "Superficie se mantiene o disminuye respecto de la RCA",
                (
                    f"La modificacion propone {superficie_propuesta:g} ha frente a {superficie_rca:g} ha "
                    "aprobadas en la RCA; preliminarmente no hay aumento de magnitud por este factor."
                ),
            )


def evaluar_diagnostico(datos: dict[str, Any]) -> dict[str, Any]:
    """Evalua un diagnostico preliminar segun las rubricas del MVP."""
    hallazgos: list[Hallazgo] = []
    datos_faltantes: list[str] = []

    if datos.get("sector") == "Energia":
        if datos.get("respuesta_area_protegida") == "No sabe":
            datos_faltantes.append("verificar area protegida o bajo proteccion oficial")
        if datos.get("respuesta_humedal") == "No sabe":
            datos_faltantes.append("verificar humedal urbano")
        if (
            datos.get("tipo_gestion") != "Modificacion con RCA"
            and datos.get("potencia_mw") is None
            and datos.get("subtipo_energia") in ["Parque fotovoltaico", "Central generadora"]
        ):
            datos_faltantes.append("potencia MW")
        if (
            datos.get("tipo_gestion") != "Modificacion con RCA"
            and datos.get("subtipo_energia") in ["Almacenamiento BESS", "Parque fotovoltaico"]
            and datos.get("respuesta_nueva_infraestructura") == "No sabe"
        ):
            datos_faltantes.append("definir si requiere obras electricas nuevas de conexion o evacuacion")
        if (
            datos.get("tipo_gestion") != "Modificacion con RCA"
            and datos.get("subtipo_energia") in ["Almacenamiento BESS", "Parque fotovoltaico"]
            and datos.get("respuesta_nueva_infraestructura") == "Si"
            and not datos.get("obras_electricas_nuevas")
        ):
            datos_faltantes.append("precisar que obras electricas nuevas requiere el proyecto")
        if (
            datos.get("tipo_gestion") != "Modificacion con RCA"
            and "Nueva linea o tramo electrico" in (datos.get("obras_electricas_nuevas") or [])
            and datos.get("tension_obra_electrica_kv") is None
        ):
            datos_faltantes.append("tension de nueva linea o tramo electrico")
        if (
            datos.get("tipo_gestion") != "Modificacion con RCA"
            and "Nueva subestacion electrica" in (datos.get("obras_electricas_nuevas") or [])
            and datos.get("funcion_subestacion_obra") in (None, "", "No sabe", "No aplica")
        ):
            datos_faltantes.append("funcion de nueva subestacion electrica")
        if (
            datos.get("tipo_gestion") == "Modificacion con RCA"
            and datos.get("subtipo_energia") == "Almacenamiento BESS"
            and not (
                datos.get("agrega_bess")
                or datos.get("modifica_linea_evacuacion")
                or datos.get("modifica_trazado_linea")
                or datos.get("cambia_punto_conexion")
                or datos.get("modifica_pas")
                or datos.get("otra_modificacion")
            )
        ):
            datos_faltantes.append("precisar componentes de la modificacion BESS")
        if (
            datos.get("tipo_gestion") == "Modificacion con RCA"
            and datos.get("subtipo_energia") == "Almacenamiento BESS"
            and (
                datos.get("modifica_linea_evacuacion")
                or datos.get("modifica_trazado_linea")
                or datos.get("cambia_punto_conexion")
            )
            and datos.get("tension_linea_modificada_kv") is None
        ):
            datos_faltantes.append("tension de linea asociada a la modificacion BESS")
        if (
            datos.get("tipo_gestion") == "Modificacion con RCA"
            and datos.get("subtipo_energia") == "Parque fotovoltaico"
            and datos.get("modifica_potencia_parque")
            and (datos.get("potencia_rca_mw") is None or datos.get("potencia_propuesta_mw") is None)
        ):
            datos_faltantes.append("potencia aprobada en RCA y potencia propuesta")
        if (
            datos.get("tipo_gestion") == "Modificacion con RCA"
            and datos.get("subtipo_energia") == "Parque fotovoltaico"
            and (datos.get("cambia_punto_conexion") or datos.get("modifica_linea_evacuacion"))
            and datos.get("tension_linea_modificada_kv") is None
        ):
            datos_faltantes.append("tension de nueva/modificada linea o conexion")
        if (
            datos.get("tipo_gestion") == "Modificacion con RCA"
            and datos.get("subtipo_energia") == "Linea de transmision"
            and datos.get("agrega_linea_transmision")
            and datos.get("tension_linea_propuesta_kv") is None
        ):
            datos_faltantes.append("tension de nueva linea o tramo")
        if (
            datos.get("tipo_gestion") == "Modificacion con RCA"
            and datos.get("subtipo_energia") == "Linea de transmision"
            and (datos.get("modifica_conductores_linea") or datos.get("modifica_trazado_linea"))
            and (datos.get("tension_linea_rca_kv") is None or datos.get("tension_linea_propuesta_kv") is None)
        ):
            datos_faltantes.append("tension aprobada en RCA y tension propuesta")
        if (
            datos.get("tipo_gestion") == "Proyecto nuevo"
            and datos.get("tension_kv") is None
            and datos.get("subtipo_energia") == "Linea de transmision"
        ):
            datos_faltantes.append("tension de nueva linea")
        if (
            datos.get("tipo_gestion") == "Proyecto nuevo"
            and datos.get("longitud_linea_km") is None
            and datos.get("subtipo_energia") == "Linea de transmision"
        ):
            datos_faltantes.append("longitud de nueva linea")
        if (
            datos.get("tipo_gestion") == "Modificacion sin RCA"
            and datos.get("subtipo_energia") == "Linea de transmision"
            and datos.get("agrega_linea_transmision")
            and datos.get("tension_linea_propuesta_kv") is None
        ):
            datos_faltantes.append("tension de nueva linea o tramo")
        if (
            datos.get("tipo_gestion") == "Modificacion sin RCA"
            and datos.get("subtipo_energia") == "Linea de transmision"
            and datos.get("agrega_linea_transmision")
            and datos.get("longitud_linea_km") is None
        ):
            datos_faltantes.append("longitud de nueva linea o tramo")
        if (
            datos.get("tipo_gestion") == "Modificacion sin RCA"
            and datos.get("subtipo_energia") == "Linea de transmision"
            and datos.get("otra_modificacion")
            and not datos.get("descripcion_otra_modificacion")
        ):
            datos_faltantes.append("descripcion de otra modificacion de linea")
        _evaluar_energia(datos, hallazgos)
    else:
        if datos.get("respuesta_area_protegida") == "No sabe":
            datos_faltantes.append("verificar area protegida o bajo proteccion oficial")
        if datos.get("respuesta_humedal") == "No sabe":
            datos_faltantes.append("verificar humedal urbano")
        if datos.get("tipo_gestion") == "Modificacion con RCA":
            if datos.get("emplazamiento_inmobiliario") == "No sabe":
                datos_faltantes.append("ubicacion territorial inmobiliaria: area urbana, sector rural o ambas")
            if (
                datos.get("emplazamiento_inmobiliario") in ["Area de extension urbana", "Sector rural", "Area urbana y rural"]
                and (
                    datos.get("respuesta_sistema_agua_potable") == "No sabe"
                    or datos.get("respuesta_sistema_aguas_servidas") == "No sabe"
                )
            ):
                datos_faltantes.append("sistemas propios de agua potable o aguas servidas para h.1.1)")
            if datos.get("respuesta_incorpora_vialidad_publica") == "No sabe":
                datos_faltantes.append("definir si considera apertura o incorporacion de vias publicas para h.1.2)")
            if (
                datos.get("respuesta_incorpora_vialidad_publica") == "Si"
                and datos.get("respuesta_vias_expresas_troncales") == "No sabe"
            ):
                datos_faltantes.append("incorporacion de vias expresas o troncales para h.1.2)")
            if datos.get("modifica_viviendas_inmobiliario") and (
                datos.get("viviendas_rca") is None or datos.get("viviendas_propuestas") is None
            ):
                datos_faltantes.append("viviendas aprobadas en RCA y viviendas propuestas")
            if datos.get("modifica_superficie_inmobiliario") and (
                datos.get("superficie_rca_ha") is None or datos.get("superficie_propuesta_ha") is None
            ):
                datos_faltantes.append("superficie aprobada en RCA y superficie propuesta")
            _evaluar_modificacion_inmobiliaria(datos, hallazgos)
        else:
            if datos.get("emplazamiento_inmobiliario") == "No sabe":
                datos_faltantes.append("ubicacion territorial inmobiliaria: area urbana, sector rural o ambas")
            if (
                datos.get("emplazamiento_inmobiliario") in ["Area de extension urbana", "Sector rural", "Area urbana y rural"]
                and (
                    datos.get("respuesta_sistema_agua_potable") == "No sabe"
                    or datos.get("respuesta_sistema_aguas_servidas") == "No sabe"
                )
            ):
                datos_faltantes.append("sistemas propios de agua potable o aguas servidas para h.1.1)")
            if datos.get("respuesta_incorpora_vialidad_publica") == "No sabe":
                datos_faltantes.append("definir si considera apertura o incorporacion de vias publicas para h.1.2)")
            if (
                datos.get("respuesta_incorpora_vialidad_publica") == "Si"
                and datos.get("respuesta_vias_expresas_troncales") == "No sabe"
            ):
                datos_faltantes.append("incorporacion de vias expresas o troncales para h.1.2)")
            if (
                datos.get("emplazamiento_inmobiliario") in ["Area urbana", "Area urbana y rural", "Area con IPT vigente"]
                and datos.get("respuesta_zona_saturada") == "No sabe"
            ):
                datos_faltantes.append("seleccionar comuna para verificar PDA o zona saturada en area urbana")
            tipo_inmobiliario_actual = datos.get("tipo_inmobiliario") or "Viviendas o loteo habitacional"
            if (
                datos.get("emplazamiento_inmobiliario") in ["Area urbana", "Area urbana y rural", "Area con IPT vigente"]
                and datos.get("zona_saturada")
                and tipo_inmobiliario_actual == "Viviendas o loteo habitacional"
                and datos.get("numero_viviendas") is None
            ):
                datos_faltantes.append("numero de viviendas para evaluar h.1.3)")
            if (
                datos.get("emplazamiento_inmobiliario") in ["Area urbana", "Area urbana y rural", "Area con IPT vigente"]
                and datos.get("zona_saturada")
                and tipo_inmobiliario_actual == "Viviendas o loteo habitacional"
                and datos.get("superficie_ha") is None
            ):
                datos_faltantes.append("superficie del proyecto para evaluar h.1.3)")
            if (
                datos.get("tipo_gestion") == "Modificacion sin RCA"
                and (
                    tipo_inmobiliario_actual == "Cementerio o mausoleo existente"
                    or (
                        tipo_inmobiliario_actual == "Equipamiento"
                        and datos.get("subtipo_equipamiento") in ["Cementerio", "Cementerio o mausoleo"]
                    )
                )
                and datos.get("antiguedad_proyecto") == "No sabe"
            ):
                datos_faltantes.append("inicio de operacion del proyecto existente")
            _evaluar_inmobiliario(datos, hallazgos)

    _evaluar_cambios_consideracion_con_rca(datos, hallazgos)
    _evaluar_localizacion(datos, hallazgos)

    if datos_faltantes and not any(h.riesgo == "INDETERMINADO" for h in hallazgos):
        _agregar(
            hallazgos,
            "INDETERMINADO",
            "Información insuficiente",
            "Datos faltantes relevantes",
            (
                "Existen antecedentes indispensables para evaluar uno o mas criterios relevantes: "
                + ", ".join(datos_faltantes)
                + ". Requiere revisión de consultor."
            ),
        )

    riesgo = _riesgo_final(hallazgos)
    hallazgos_ordenados = sorted(hallazgos, key=lambda h: PESO_VISUAL[h.riesgo], reverse=True)
    hallazgos_indeterminados = [h for h in hallazgos if h.riesgo == "INDETERMINADO"]
    if datos_faltantes:
        suficiencia_antecedentes = "INCOMPLETOS"
        detalle_suficiencia = "Faltan antecedentes relevantes para aplicar completamente la rubrica: " + ", ".join(datos_faltantes) + "."
    elif hallazgos_indeterminados:
        suficiencia_antecedentes = "PARCIALMENTE SUFICIENTES"
        criterios_pendientes = ", ".join(h.criterio for h in hallazgos_indeterminados)
        detalle_suficiencia = (
            "Con la informacion ingresada, el MVP puede aplicar las reglas existentes y detectar los factores "
            "evaluables. Sin embargo, queda pendiente revisar informacion especifica asociada a: "
            + criterios_pendientes
            + ". Derivar ese punto a revision tecnica."
        )
    else:
        suficiencia_antecedentes = "SUFICIENTES PARA EL MVP"
        detalle_suficiencia = (
            "Con las respuestas ingresadas, el formulario contiene los antecedentes minimos "
            "para aplicar las reglas actualmente implementadas en este MVP."
        )

    alto_por_localizacion_sensible = any(
        h.riesgo == "ALTO" and h.literal in ["p)", "s)"] for h in hallazgos
    )

    if riesgo == "ALTO":
        if alto_por_localizacion_sensible:
            conclusion = (
                "Existe un factor de localizacion sensible asociado a humedal urbano o area bajo proteccion oficial. "
                "No implica ingreso automatico al SEIA: debe derivarse a consultor para revisar caso a caso la magnitud "
                "de las obras, sus caracteristicas y su posible afectacion."
            )
        else:
            conclusion = "Existen factores que pueden configurar ingreso obligatorio o requieren revision tecnica prioritaria."
    elif riesgo == "MEDIO":
        if datos_faltantes:
            conclusion = (
                "Hay antecedentes incompletos que impiden cerrar uno o mas criterios. "
                "Revisa la lista de datos faltantes antes de ejecutar o decidir."
            )
        else:
            conclusion = (
                "Hay factores en zona gris o de alerta media que conviene revisar. "
                "La rubrica no identifico datos faltantes indispensables en el formulario."
            )
    elif riesgo == "INDETERMINADO":
        conclusion = "No hay una regla suficiente en el MVP para estimar el riesgo de una o mas modificaciones declaradas."
    else:
        conclusion = "Con los datos ingresados, no se observan factores criticos evidentes segun la rubrica inicial."

    return {
        "riesgo": riesgo,
        "conclusion": conclusion,
        "hallazgos": [h.__dict__ for h in hallazgos_ordenados],
        "literales": sorted({h.literal for h in hallazgos if h.literal}),
        "datos_faltantes": datos_faltantes,
        "suficiencia_antecedentes": suficiencia_antecedentes,
        "detalle_suficiencia": detalle_suficiencia,
        "advertencia": (
            "Diagnostico preliminar basado en rubricas internas y precedentes revisados. "
            "No reemplaza una consulta de pertinencia ni un analisis juridico-tecnico profesional."
        ),
    }
