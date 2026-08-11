import sqlite3

import pandas as pd
import streamlit as st

from analitica_datos import (
    aplicar_filtros,
    calcular_indicadores,
    calidad_datos,
    conteo_por_columna,
    conteo_temporal,
    obtener_registros,
    opciones_anio,
    opciones_filtro,
    preparar_tabla_descarga,
)
from busqueda_precedentes import buscar_precedentes, obtener_criterios_precedente
from comparador_precedentes import (
    ADVERTENCIA_COMPARADOR,
    comparar_precedentes,
    informe_markdown,
    interpretar_comparacion,
    matriz_comparativa,
    texto_ingreso_seia as texto_ingreso_comparador,
    texto_no_disponible,
)
from config import RUTA_BASE_DATOS
from motor_rubrica import evaluar_diagnostico
from zonas_maule import COMUNAS_MAULE, obtener_pda_maule_por_comuna


st.set_page_config(page_title="Diagnóstico Express SEA", layout="wide")


def conectar() -> sqlite3.Connection:
    conexion = sqlite3.connect(RUTA_BASE_DATOS)
    conexion.row_factory = sqlite3.Row
    return conexion


def obtener_opciones(conexion: sqlite3.Connection, columna: str) -> list[str]:
    filas = conexion.execute(
        f"""
        SELECT DISTINCT {columna} AS valor
        FROM proyectos
        WHERE {columna} IS NOT NULL
          AND TRIM({columna}) != ''
          AND LOWER({columna}) != 'no determinado'
        ORDER BY {columna}
        """
    ).fetchall()
    return [fila["valor"] for fila in filas]


def buscar_documentos(
    conexion: sqlite3.Connection,
    tipo_proyecto: str,
    region: str,
    palabra_clave: str,
) -> list[sqlite3.Row]:
    condiciones: list[str] = []
    parametros: list[str] = []

    if tipo_proyecto:
        condiciones.append("p.tipo_proyecto = ?")
        parametros.append(tipo_proyecto)

    if region:
        condiciones.append("p.region = ?")
        parametros.append(region)

    if palabra_clave:
        condiciones.append(
            """
            EXISTS (
                SELECT 1
                FROM palabras_clave pc
                WHERE pc.documento_id = d.id
                  AND LOWER(pc.palabra_clave) LIKE LOWER(?)
            )
            """
        )
        parametros.append(f"%{palabra_clave}%")

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    consulta = f"""
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
            p.subtipo_proyecto,
            p.proponente
        FROM documentos d
        LEFT JOIN proyectos p ON p.documento_id = d.id
        {where}
        ORDER BY d.id_documento
    """
    return conexion.execute(consulta, parametros).fetchall()


def obtener_criterios(conexion: sqlite3.Connection, documento_id: int) -> list[sqlite3.Row]:
    return conexion.execute(
        """
        SELECT criterio, explicacion, fragmento_respaldo, nivel_confianza
        FROM criterios
        WHERE documento_id = ?
        ORDER BY id
        """,
        (documento_id,),
    ).fetchall()


def texto_ingreso_seia(valor: int | None) -> str:
    if valor == 1:
        return "Si"
    if valor == 0:
        return "No"
    return "No determinado"


def respuesta_si_no_no_sabe(etiqueta: str, ayuda: str | None = None) -> str:
    return st.selectbox(etiqueta, ["No", "Si", "No sabe"], help=ayuda)


def mostrar_precedente(conexion: sqlite3.Connection, precedente: dict) -> None:
    titulo = precedente.get("nombre_proyecto") or precedente.get("id_documento")
    if titulo == "no determinado":
        titulo = precedente.get("id_documento")

    with st.expander(titulo):
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Region", precedente.get("region") or "No determinado")
        col_b.metric("Tipo", precedente.get("tipo_proyecto") or "No determinado")
        col_c.metric("Ingresa al SEIA", texto_ingreso_seia(precedente.get("debe_ingresar_al_seia")))

        st.write("**Resultado SEA**")
        st.write(precedente.get("resultado") or "No determinado")

        st.write("**Resumen**")
        st.write(precedente.get("resumen_ejecutivo") or "Sin resumen.")

        criterios = obtener_criterios_precedente(conexion, precedente["id"])
        if criterios:
            st.write("**Criterios extraidos**")
            for criterio in criterios[:3]:
                st.markdown(f"**{criterio.get('criterio') or 'Criterio no determinado'}**")
                st.write(criterio.get("explicacion") or "Sin explicacion.")
                if criterio.get("fragmento_respaldo"):
                    st.markdown(f"> {criterio['fragmento_respaldo']}")


def render_analitica(conexion: sqlite3.Connection | None) -> None:
    st.subheader("Analítica de datos")
    st.caption(
        "La analítica refleja únicamente las resoluciones cargadas y procesadas en esta base local. "
        "No representa necesariamente el universo total de resoluciones del SEA."
    )

    if conexion is None:
        st.warning("Todavía no existe la base SQLite. Ejecuta primero el flujo de carga de resoluciones.")
        return

    datos = obtener_registros(conexion)
    if datos.empty:
        st.info("La base existe, pero no contiene registros para analizar.")
        return

    st.write("**Filtros**")
    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
    with col_f1:
        filtro_region = st.selectbox("Región", opciones_filtro(datos, "region"))
    with col_f2:
        filtro_comuna = st.selectbox("Comuna", opciones_filtro(datos, "comuna"))
    with col_f3:
        filtro_tipo = st.selectbox("Sector o tipo", opciones_filtro(datos, "tipo_proyecto"))
    with col_f4:
        filtro_subtipo = st.selectbox("Subtipo", opciones_filtro(datos, "subtipo_proyecto"))
    with col_f5:
        filtro_anio = st.selectbox("Año", opciones_anio(datos))

    filtrados = aplicar_filtros(datos, filtro_region, filtro_comuna, filtro_tipo, filtro_subtipo, filtro_anio)
    if filtrados.empty:
        st.info("No hay registros para los filtros seleccionados.")
        return

    indicadores = calcular_indicadores(filtrados)
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    col_m1.metric("Resoluciones procesadas", indicadores["total_resoluciones"])
    col_m2.metric("Regiones representadas", indicadores["regiones_representadas"])
    col_m3.metric("Comunas representadas", indicadores["comunas_representadas"])
    col_m4.metric("Resoluciones energía", indicadores["resoluciones_energia"])
    col_m5.metric("Resoluciones inmobiliarias", indicadores["resoluciones_inmobiliarias"])

    st.write("**Ingreso al SEIA**")
    col_i1, col_i2, col_i3 = st.columns(3)
    for columna, etiqueta in zip([col_i1, col_i2, col_i3], ["Si", "No", "No determinado"]):
        info = indicadores["ingreso_seia"][etiqueta]
        columna.metric(
            etiqueta,
            f"{info['conteo']} ({info['porcentaje']:.1f}%)",
            help=f"Denominador: {info['denominador']} resoluciones filtradas.",
        )

    col_d1, col_d2 = st.columns(2)
    col_d1.metric("Sin región determinada", indicadores["sin_region"])
    col_d2.metric("Sin tipo de proyecto determinado", indicadores["sin_tipo_proyecto"])

    st.divider()
    st.write("**Gráficos**")
    graf_1, graf_2 = st.columns(2)
    with graf_1:
        st.write("Resoluciones por región")
        st.bar_chart(conteo_por_columna(filtrados, "region"), x="region", y="cantidad")
    with graf_2:
        st.write("Resoluciones por sector")
        st.bar_chart(conteo_por_columna(filtrados, "tipo_proyecto"), x="tipo_proyecto", y="cantidad")

    graf_3, graf_4 = st.columns(2)
    with graf_3:
        st.write("Resoluciones por resultado de ingreso al SEIA")
        st.bar_chart(
            conteo_por_columna(filtrados, "debe_ingresar_al_seia_texto"),
            x="debe_ingresar_al_seia_texto",
            y="cantidad",
        )
    with graf_4:
        st.write("Principales subtipos de proyecto")
        st.bar_chart(conteo_por_columna(filtrados, "subtipo_proyecto", limite=10), x="subtipo_proyecto", y="cantidad")

    temporal = conteo_temporal(filtrados)
    if temporal.empty:
        st.info("No hay fechas válidas suficientes para mostrar evolución temporal.")
    else:
        st.write("Evolución anual de resoluciones")
        st.bar_chart(temporal, x="anio_resolucion", y="cantidad")

    st.write("**Tabla filtrada**")
    tabla = preparar_tabla_descarga(filtrados)
    st.dataframe(tabla, use_container_width=True)
    st.download_button(
        "Descargar CSV filtrado",
        data=tabla.to_csv(index=False).encode("utf-8-sig"),
        file_name="analitica_resoluciones_filtradas.csv",
        mime="text/csv",
    )

    with st.expander("Calidad y cobertura de los datos"):
        st.dataframe(calidad_datos(filtrados), use_container_width=True)
        st.warning(
            "La analítica muestra solo las resoluciones cargadas y procesadas. "
            "La base puede estar incompleta y no debe interpretarse como muestra representativa de todo el SEA."
        )


def render_comparador_precedentes(conexion: sqlite3.Connection | None) -> None:
    st.subheader("Comparador de precedentes administrativos")
    st.caption(ADVERTENCIA_COMPARADOR)

    if conexion is None:
        st.warning("No existe base SQLite. Ejecuta primero la carga de resoluciones para comparar precedentes.")
        return

    datos_proyecto = st.session_state.get("datos_proyecto")
    diagnostico = st.session_state.get("diagnostico_actual")
    if not datos_proyecto or not diagnostico:
        st.info("Primero completa y genera el diagnóstico preliminar para utilizar el comparador.")
        return

    st.write("**Proyecto consultado**")
    st.write(
        {
            "sector": datos_proyecto.get("sector"),
            "region": datos_proyecto.get("region"),
            "subtipo": datos_proyecto.get("subtipo_energia") or datos_proyecto.get("subtipo_proyecto"),
            "riesgo_preliminar": diagnostico.get("riesgo"),
        }
    )

    with st.expander("¿Cómo se calcula la coincidencia?"):
        st.write(
            "El Nivel de coincidencia de antecedentes es descriptivo. No mide riesgo, certeza ni probabilidad jurídica. "
            "Se calcula con componentes disponibles: misma región hasta 30 puntos, mismo sector hasta 25, mismo subtipo hasta 20, "
            "palabras clave hasta 15 y literales o criterios hasta 10. Si un componente no se puede comparar, no suma al máximo evaluable."
        )

    resultado_inicial = comparar_precedentes(conexion, datos_proyecto, diagnostico, incluir_otras_regiones=False)
    incluir_otras = False
    if not resultado_inicial["hay_regionales"]:
        st.warning("No se encontraron precedentes regionales suficientes.")
        incluir_otras = st.checkbox("Ampliar voluntariamente la búsqueda a otras regiones")

    resultado = comparar_precedentes(conexion, datos_proyecto, diagnostico, incluir_otras_regiones=incluir_otras)
    precedentes = resultado["precedentes"]
    if not precedentes:
        st.info("No se encontraron resoluciones comparables con la base disponible.")
        st.write(interpretar_comparacion(resultado))
        return

    st.write("**Matriz comparativa**")
    st.dataframe(pd.DataFrame(matriz_comparativa(datos_proyecto, diagnostico, precedentes)), use_container_width=True)

    st.write("**Resoluciones comparables**")
    for indice, precedente in enumerate(precedentes, start=1):
        comparacion = precedente["comparacion"]
        etiqueta_region = " - Referencia de otra región" if precedente.get("referencia_otra_region") else ""
        titulo = texto_no_disponible(precedente.get("nombre_proyecto") or precedente.get("id_documento"))
        with st.expander(f"{indice}. {titulo}{etiqueta_region}"):
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Región", texto_no_disponible(precedente.get("region")))
            col_b.metric("Coincidencia", comparacion["clasificacion"])
            col_c.metric("Puntaje", f"{comparacion['puntos']}/{comparacion['maximo_evaluable']}")

            st.write(
                {
                    "comuna": texto_no_disponible(precedente.get("comuna")),
                    "tipo": texto_no_disponible(precedente.get("tipo_proyecto")),
                    "subtipo": texto_no_disponible(precedente.get("subtipo_proyecto")),
                    "fecha_resolucion": texto_no_disponible(precedente.get("fecha_resolucion")),
                    "resultado_sea": texto_no_disponible(precedente.get("resultado")),
                    "debe_ingresar_al_seia": texto_ingreso_comparador(precedente.get("debe_ingresar_al_seia")),
                }
            )

            st.write("**Coincidencias encontradas**")
            st.write(comparacion["coincidencias"] or ["No disponible"])
            st.write("**Diferencias detectadas**")
            st.write(comparacion["diferencias"] or ["No disponible"])
            st.write("**Información que no pudo compararse**")
            st.write(comparacion["no_comparable"] or ["No disponible"])

            st.write("**Resumen ejecutivo**")
            st.write(texto_no_disponible(precedente.get("resumen_ejecutivo")))

            criterios = precedente.get("criterios", [])[:3]
            if criterios:
                st.write("**Criterios identificados en resoluciones procesadas**")
                for criterio in criterios:
                    st.markdown(f"**{texto_no_disponible(criterio.get('criterio'))}**")
                    st.write(texto_no_disponible(criterio.get("explicacion")))
                    if criterio.get("fragmento_respaldo"):
                        st.markdown(f"> {criterio['fragmento_respaldo']}")
            else:
                st.info("Esta resolución no tiene criterios cargados.")

            normativa = precedente.get("normativa_citada", [])
            if normativa:
                st.write("**Normativa citada**")
                st.write(normativa)

    st.write("**Interpretación preliminar**")
    st.info(interpretar_comparacion(resultado))
    informe = informe_markdown(datos_proyecto, diagnostico, precedentes)
    st.download_button(
        "Descargar informe comparativo Markdown",
        data=informe.encode("utf-8"),
        file_name="informe_comparativo_preliminar.md",
        mime="text/markdown",
    )


def render_diagnostico(conexion: sqlite3.Connection | None) -> None:
    st.subheader("Diagnostico preliminar por rubrica")
    st.write(
        "Completa los datos que tengas. Si no conoces un dato, deja el campo en blanco "
        "o usa la opcion mas conservadora."
    )

    distancia_humedal_m = None
    col_1, col_2, col_3 = st.columns(3)

    with col_1:
        tipo_gestion = st.selectbox(
            "Tipo de gestion",
            ["Proyecto nuevo", "Modificacion con RCA", "Modificacion sin RCA"],
        )
        sector = st.selectbox("Sector", ["Energia", "Inmobiliario"])
        region = st.text_input("Region", value="Region del Maule")

    with col_2:
        subtipo_energia = "No aplica"
        if sector == "Energia":
            subtipo_energia = st.selectbox(
                "Subtipo energia",
                [
                    "Almacenamiento BESS",
                    "Parque fotovoltaico",
                    "Central generadora",
                    "Linea de transmision",
                    "Subestacion electrica",
                ],
            )
        respuesta_area_protegida = respuesta_si_no_no_sabe("Esta dentro de area protegida")
        respuesta_humedal = respuesta_si_no_no_sabe("Esta dentro de humedal urbano")
        en_area_protegida = respuesta_area_protegida == "Si"
        en_humedal = respuesta_humedal == "Si"

    with col_3:
        if respuesta_humedal == "Si":
            st.info("Al declarar emplazamiento dentro de humedal urbano, el MVP deriva el literal s) a revision prioritaria.")
        elif respuesta_humedal == "No sabe":
            st.info("Si no se sabe si esta dentro de humedal urbano, el diagnostico quedara indeterminado.")
        nueva_infraestructura = False
        respuesta_nueva_infraestructura = "No"
        cambia_trazado = False

    st.divider()
    potencia_mw = 0.0
    potencia_rca_mw = 0.0
    potencia_propuesta_mw = 0.0
    tension_kv = 0.0
    tension_linea_modificada_kv = 0.0
    tension_linea_rca_kv = 0.0
    tension_linea_propuesta_kv = 0.0
    longitud_linea_km = 0.0
    obras_electricas_nuevas: list[str] = []
    tension_obra_electrica_kv = 0.0
    funcion_subestacion_obra = "No aplica"
    funcion_subestacion = "No aplica"
    tiene_ipt = False
    emplazamiento_inmobiliario = "No aplica"
    tipo_inmobiliario = "No aplica"
    subtipo_equipamiento = "No aplica"
    antiguedad_proyecto = "No aplica"
    respuesta_aumenta_estacionamientos = "No"
    respuesta_aumenta_carga_ocupacion = "No"
    respuesta_sistema_agua_potable = "No"
    respuesta_sistema_aguas_servidas = "No"
    respuesta_incorpora_vialidad_publica = "No"
    respuesta_vias_expresas_troncales = "No"
    aumenta_estacionamientos = False
    aumenta_carga_ocupacion = False
    sistema_agua_potable = False
    sistema_aguas_servidas = False
    incorpora_vialidad_publica = False
    vias_expresas_troncales = False
    comuna_proyecto = ""
    respuesta_zona_saturada = "No"
    zona_saturada = False
    numero_viviendas = 0
    viviendas_rca = 0
    viviendas_propuestas = 0
    superficie_ha = 0.0
    superficie_rca_ha = 0.0
    superficie_propuesta_ha = 0.0
    agrega_bess = False
    modifica_potencia_parque = False
    cambia_punto_conexion = False
    modifica_linea_evacuacion = False
    agrega_linea_transmision = False
    seccionamiento_linea = False
    modifica_conductores_linea = False
    modifica_trazado_linea = False
    modifica_viviendas_inmobiliario = False
    modifica_superficie_inmobiliario = False
    modifica_pas = False
    otra_modificacion = False
    descripcion_otra_modificacion = ""

    if sector == "Energia":
        st.write("**Datos tecnicos de energia**")

        if (
            subtipo_energia in ["Parque fotovoltaico", "Central generadora"]
            and tipo_gestion != "Modificacion con RCA"
        ):
            potencia_mw = st.number_input(
                "Potencia del proyecto (MW)",
                min_value=0.0,
                value=0.0,
                step=0.1,
                help="Para proyecto nuevo o modificacion sin RCA, la rubrica revisa si supera 3 MW.",
            )

        elif subtipo_energia == "Linea de transmision" and tipo_gestion != "Modificacion con RCA":
            if tipo_gestion == "Modificacion sin RCA":
                st.write("**Tipo de modificacion de la linea**")
                st.caption("Marca todos los cambios que forman parte de la consulta.")
                col_lms1, col_lms2, col_lms3, col_lms4 = st.columns(4)
                with col_lms1:
                    modifica_conductores_linea = st.checkbox("Cambia conductor o capacidad de transporte")
                with col_lms2:
                    modifica_trazado_linea = st.checkbox("Cambia trazado, estructuras o faja")
                    cambia_trazado = modifica_trazado_linea
                with col_lms3:
                    agrega_linea_transmision = st.checkbox("Agrega nueva linea o tramo")
                with col_lms4:
                    otra_modificacion = st.checkbox("Otra modificacion")

                if modifica_conductores_linea or modifica_trazado_linea:
                    tension_kv = st.number_input(
                        "Tension de la linea existente (kV)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                        help=(
                            "Este dato describe la linea existente. Si solo cambia el conductor y no hay nueva linea, "
                            "la tension existente no activa por si sola el literal b.1)."
                        ),
                    )

                if agrega_linea_transmision:
                    col_nl1, col_nl2 = st.columns(2)
                    with col_nl1:
                        tension_linea_propuesta_kv = st.number_input(
                            "Tension de la nueva linea o tramo (kV)",
                            min_value=0.0,
                            value=0.0,
                            step=0.1,
                            help="Para revisar b.1), el MVP considera tension mayor a 23 kV y longitud mayor a 2 km.",
                        )
                    with col_nl2:
                        longitud_linea_km = st.number_input(
                            "Longitud de la nueva linea o tramo (km)",
                            min_value=0.0,
                            value=0.0,
                            step=0.1,
                            help="Para revisar b.1), el MVP considera si la nueva linea o tramo supera 2 km.",
                        )

                if otra_modificacion:
                    descripcion_otra_modificacion = st.text_area(
                        "Describe brevemente la otra modificacion",
                        placeholder="Ejemplo: reemplazo de aisladores, cambio de postes, ajuste de equipos, etc.",
                        height=80,
                    )
            else:
                col_ln1, col_ln2 = st.columns(2)
                with col_ln1:
                    tension_kv = st.number_input(
                        "Tension de la nueva linea (kV)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                        help="Para revisar b.1), el MVP considera tension mayor a 23 kV y longitud mayor a 2 km.",
                    )
                with col_ln2:
                    longitud_linea_km = st.number_input(
                        "Longitud de la nueva linea (km)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                        help="Para revisar b.1), el MVP considera si la nueva linea supera 2 km.",
                    )

        elif subtipo_energia == "Subestacion electrica":
            funcion_subestacion = st.selectbox(
                "Funcion subestacion",
                ["No aplica", "Distribucion", "Seccionamiento", "Mixta", "Transporte"],
                help="La rubrica distingue subestaciones de distribucion, seccionamiento, mixtas y transporte.",
            )

        elif subtipo_energia == "Almacenamiento BESS":
            st.info(
                "Para BESS puro, la potencia no se usa como criterio principal de ingreso. "
                "Lo relevante en esta version es si requiere nueva infraestructura electrica o si activa otros literales."
            )

        if (
            subtipo_energia in ["Almacenamiento BESS", "Parque fotovoltaico"]
            and tipo_gestion != "Modificacion con RCA"
        ):
            st.write("**Conexion o evacuacion electrica**")
            respuesta_nueva_infraestructura = respuesta_si_no_no_sabe(
                "La conexion o evacuacion requiere obras electricas nuevas",
                (
                    "Responde Si si el proyecto necesita construir una nueva linea, celda, paño, "
                    "subestacion, seccionamiento, punto de conexion u otra obra electrica para conectarse "
                    "o evacuar energia. Responde No si usara infraestructura existente sin nuevas obras."
                ),
            )
            nueva_infraestructura = respuesta_nueva_infraestructura == "Si"

            if respuesta_nueva_infraestructura == "Si":
                st.write("**Obras electricas nuevas asociadas a conexion o evacuacion**")
                st.caption("Marca solo las obras que forman parte del proyecto consultado.")
                opciones_obras = [
                    "Nueva linea o tramo electrico",
                    "Nueva subestacion electrica",
                    "Ampliacion de subestacion existente: celda, paño o equipos",
                    "Seccionamiento",
                    "Nuevo o cambio de punto de conexion al SEN",
                    "Otra obra electrica",
                ]
                col_o1, col_o2, col_o3 = st.columns(3)
                columnas_obras = [col_o1, col_o2, col_o3]
                for indice, obra in enumerate(opciones_obras):
                    with columnas_obras[indice % 3]:
                        if st.checkbox(obra, key=f"obra_electrica_{indice}"):
                            obras_electricas_nuevas.append(obra)

                if "Nueva linea o tramo electrico" in obras_electricas_nuevas:
                    tension_obra_electrica_kv = st.number_input(
                        "Tension de la nueva linea o tramo (kV)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                        help="Si no conoces este dato, dejalo en 0 y el MVP lo derivara a consultor.",
                    )

                if "Nueva subestacion electrica" in obras_electricas_nuevas:
                    funcion_subestacion_obra = st.selectbox(
                        "Funcion de la nueva subestacion",
                        ["No sabe", "Distribucion", "Seccionamiento", "Mixta", "Transporte"],
                        key="funcion_subestacion_obra_nueva",
                        help="La funcion ayuda a orientar el literal b.2) en el diagnostico preliminar.",
                    )

    if sector == "Inmobiliario" and tipo_gestion != "Modificacion con RCA":
        st.write("**Datos tecnicos inmobiliarios**")
        col_i1, col_i2, col_i3 = st.columns(3)
        with col_i1:
            tipo_inmobiliario = st.selectbox(
                "Tipo de proyecto inmobiliario",
                [
                    "Viviendas o loteo habitacional",
                    "Equipamiento",
                    "Otro proyecto inmobiliario",
                ],
                help=(
                    "Esto evita pedir datos de viviendas cuando el caso corresponde a equipamiento, "
                    "cementerio u otra obra no habitacional."
                ),
            )
            if tipo_inmobiliario == "Equipamiento":
                subtipo_equipamiento = st.selectbox(
                    "Subtipo de equipamiento",
                    [
                        "Centro comercial",
                        "Centro de salud",
                        "Cementerio",
                        "Otro equipamiento",
                    ],
                    help="El subtipo permite evitar preguntas habitacionales cuando no corresponden.",
                )
            comuna_proyecto = st.selectbox("Comuna del proyecto", COMUNAS_MAULE)
            emplazamiento_inmobiliario = st.selectbox(
                "Ubicacion territorial del proyecto",
                ["Area urbana", "Area de extension urbana", "Sector rural", "Area urbana y rural", "No sabe"],
                help=(
                    "Si esta en area de extension urbana o sector rural, el MVP revisa h.1.1). "
                    "Si esta en area urbana se revisa h.1) y, cuando corresponde, h.1.3)."
                ),
            )
            tiene_ipt = emplazamiento_inmobiliario in ["Area urbana", "Area urbana y rural"]
            pda_detectado = obtener_pda_maule_por_comuna(comuna_proyecto, region)
            if emplazamiento_inmobiliario in ["Area urbana", "Area urbana y rural"] and pda_detectado:
                respuesta_zona_saturada = "Si"
                st.info(
                    "La comuna seleccionada aparece en una zona con Plan de Descontaminacion Atmosferica "
                    f"registrado para el Maule ({pda_detectado}). El MVP usara ese antecedente para h.1). "
                    "Verifica igualmente si el proyecto se emplaza dentro del poligono o area aplicable."
                )
            elif emplazamiento_inmobiliario in ["Area urbana", "Area urbana y rural"] and comuna_proyecto == "No sabe / No indicada":
                respuesta_zona_saturada = "No sabe"
                st.warning("Selecciona la comuna para que el MVP pueda revisar si existe PDA o zona saturada en el Maule.")
            elif emplazamiento_inmobiliario in ["Area urbana", "Area urbana y rural"]:
                respuesta_zona_saturada = "No"
                st.caption("La comuna seleccionada no aparece en la lista local de comunas del Maule con PDA usada por este MVP.")
            else:
                respuesta_zona_saturada = "No"
            zona_saturada = respuesta_zona_saturada == "Si"

            if tipo_gestion == "Modificacion sin RCA":
                antiguedad_proyecto = st.selectbox(
                    "Inicio de operacion del proyecto existente",
                    [
                        "No sabe",
                        "Anterior a la entrada en vigencia del RSEIA (03 de abril 1997)",
                        "Posterior a la entrada en vigencia del RSEIA (03 de abril 1997)",
                    ],
                    help=(
                        "El 03 de abril de 1997 se usa como referencia por la entrada en vigencia del RSEIA. "
                        "Si es anterior, el MVP orienta el analisis hacia las obras o cambios posteriores."
                    ),
                )

            if emplazamiento_inmobiliario in ["Area de extension urbana", "Sector rural", "Area urbana y rural"]:
                st.write("**Servicios sanitarios propios - h.1.1)**")
                respuesta_sistema_agua_potable = respuesta_si_no_no_sabe(
                    "Requiere sistema propio de produccion/distribucion de agua potable"
                )
                sistema_agua_potable = respuesta_sistema_agua_potable == "Si"
                respuesta_sistema_aguas_servidas = respuesta_si_no_no_sabe(
                    "Requiere sistema propio de recoleccion/tratamiento/disposicion de aguas servidas"
                )
                sistema_aguas_servidas = respuesta_sistema_aguas_servidas == "Si"

            if tipo_inmobiliario == "Equipamiento" and subtipo_equipamiento == "Cementerio":
                st.caption("Para cementerio, h.1.2) se descarta preliminarmente si no hay apertura o incorporacion de nuevas vias publicas.")
            else:
                respuesta_incorpora_vialidad_publica = respuesta_si_no_no_sabe(
                    "Considera apertura o incorporacion de nuevas vias/calles al uso publico",
                    "Si no hay apertura de calles o vialidad publica nueva, responde No.",
                )
                incorpora_vialidad_publica = respuesta_incorpora_vialidad_publica == "Si"
                if incorpora_vialidad_publica:
                    respuesta_vias_expresas_troncales = respuesta_si_no_no_sabe(
                        "Esas vias son expresas o troncales segun el CIP",
                        "Este antecedente normalmente puede revisarse en el Certificado de Informaciones Previas.",
                    )
                    vias_expresas_troncales = respuesta_vias_expresas_troncales == "Si"
        with col_i2:
            if tipo_inmobiliario == "Viviendas o loteo habitacional":
                numero_viviendas = st.number_input("Numero de viviendas", min_value=0, value=0, step=1)
            elif tipo_inmobiliario == "Equipamiento":
                st.info("Para equipamiento, el MVP no evalua viviendas. Revisa si hay aumento de estacionamientos o carga de ocupacion.")
                respuesta_aumenta_estacionamientos = respuesta_si_no_no_sabe("Aumenta estacionamientos")
                aumenta_estacionamientos = respuesta_aumenta_estacionamientos == "Si"
        with col_i3:
            if tipo_inmobiliario == "Viviendas o loteo habitacional":
                superficie_ha = st.number_input("Superficie hectareas", min_value=0.0, value=0.0, step=0.1)
            elif tipo_inmobiliario == "Equipamiento":
                respuesta_aumenta_carga_ocupacion = respuesta_si_no_no_sabe("Aumenta carga de ocupacion")
                aumenta_carga_ocupacion = respuesta_aumenta_carga_ocupacion == "Si"

    elif sector == "Inmobiliario":
        st.write("**Datos tecnicos inmobiliarios**")
        tipo_inmobiliario = st.selectbox(
            "Tipo de proyecto inmobiliario",
            [
                "Viviendas o loteo habitacional",
                "Equipamiento",
                "Otro proyecto inmobiliario",
            ],
        )
        if tipo_inmobiliario == "Equipamiento":
            subtipo_equipamiento = st.selectbox(
                "Subtipo de equipamiento",
                [
                    "Centro comercial",
                    "Centro de salud",
                    "Cementerio",
                    "Otro equipamiento",
                ],
            )
        comuna_proyecto = st.selectbox("Comuna del proyecto", COMUNAS_MAULE)
        emplazamiento_inmobiliario = st.selectbox(
            "Ubicacion territorial del proyecto",
            ["Area urbana", "Area de extension urbana", "Sector rural", "Area urbana y rural", "No sabe"],
            help="Si esta en area de extension urbana o sector rural se revisa h.1.1). Si esta en area urbana se revisa h.1.",
        )
        tiene_ipt = emplazamiento_inmobiliario in ["Area urbana", "Area urbana y rural"]
        if emplazamiento_inmobiliario in ["Area de extension urbana", "Sector rural", "Area urbana y rural"]:
            st.write("**Servicios sanitarios propios - h.1.1)**")
            respuesta_sistema_agua_potable = respuesta_si_no_no_sabe(
                "Requiere sistema propio de produccion/distribucion de agua potable"
            )
            sistema_agua_potable = respuesta_sistema_agua_potable == "Si"
            respuesta_sistema_aguas_servidas = respuesta_si_no_no_sabe(
                "Requiere sistema propio de recoleccion/tratamiento/disposicion de aguas servidas"
            )
            sistema_aguas_servidas = respuesta_sistema_aguas_servidas == "Si"
        if tipo_inmobiliario == "Equipamiento" and subtipo_equipamiento == "Cementerio":
            st.caption("Para cementerio, h.1.2) se descarta preliminarmente si no hay apertura o incorporacion de nuevas vias publicas.")
        else:
            respuesta_incorpora_vialidad_publica = respuesta_si_no_no_sabe(
                "Considera apertura o incorporacion de nuevas vias/calles al uso publico",
                "Si no hay apertura de calles o vialidad publica nueva, responde No.",
            )
            incorpora_vialidad_publica = respuesta_incorpora_vialidad_publica == "Si"
            if incorpora_vialidad_publica:
                respuesta_vias_expresas_troncales = respuesta_si_no_no_sabe(
                    "Esas vias son expresas o troncales segun el CIP",
                    "Este antecedente normalmente puede revisarse en el Certificado de Informaciones Previas.",
                )
                vias_expresas_troncales = respuesta_vias_expresas_troncales == "Si"
        st.info(
            "Como es una modificacion con RCA, los datos de viviendas o superficie "
            "se preguntan abajo solo si forman parte de la modificacion."
        )

    area_fuera_influencia_rca = False
    modifica_impactos_evaluados = False
    modifica_medidas_rca = False
    respuesta_area_fuera_influencia_rca = "No"
    respuesta_modifica_impactos_evaluados = "No"
    respuesta_modifica_medidas_rca = "No"
    if tipo_gestion == "Modificacion con RCA":
        if sector == "Energia" and subtipo_energia == "Almacenamiento BESS":
            st.write("**Componentes de la modificacion BESS**")
            st.caption("Marca todos los componentes que forman parte de la modificacion consultada.")
            col_bess1, col_bess2, col_bess3 = st.columns(3)
            with col_bess1:
                agrega_bess = st.checkbox("Instala o agrega sistema BESS", value=True)
            with col_bess2:
                modifica_linea_evacuacion = st.checkbox("Modifica o agrega linea de conexion/evacuacion")
            with col_bess3:
                modifica_trazado_linea = st.checkbox("Modifica trazado, estructuras o faja de linea")

            col_bess4, col_bess5, col_bess6 = st.columns(3)
            with col_bess4:
                cambia_punto_conexion = st.checkbox("Cambia punto de conexion")
            with col_bess5:
                modifica_pas = st.checkbox("Modifica PAS")
            with col_bess6:
                otra_modificacion = st.checkbox("Otra modificacion")

            if modifica_linea_evacuacion or modifica_trazado_linea or cambia_punto_conexion:
                tension_linea_modificada_kv = st.number_input(
                    "Tension de la linea asociada a la modificacion (kV)",
                    min_value=0.0,
                    value=0.0,
                    step=0.1,
                    help=(
                        "Este dato permite revisar si la linea supera 23 kV. "
                        "Si es media tension y no supera 23 kV, no configura b.1) por tension."
                    ),
                )

            if otra_modificacion:
                st.warning(
                    "Para 'otra modificacion', el MVP no puede estimar riesgo automaticamente. "
                    "Se dejara como indeterminado para revision tecnica."
                )

        if sector == "Energia" and subtipo_energia == "Parque fotovoltaico":
            st.write("**Tipo de modificacion del parque fotovoltaico**")
            st.caption("Marca solo los cambios que forman parte de la modificacion consultada.")
            col_pf1, col_pf2, col_pf3 = st.columns(3)
            with col_pf1:
                modifica_potencia_parque = st.checkbox("Cambia numero de paneles o potencia del parque")
            with col_pf2:
                agrega_bess = st.checkbox("Agrega almacenamiento BESS")
            with col_pf3:
                cambia_punto_conexion = st.checkbox("Cambia punto de conexion al SEN")

            col_pf4, col_pf5, col_pf6 = st.columns(3)
            with col_pf4:
                modifica_linea_evacuacion = st.checkbox("Modifica o agrega linea de evacuacion")
            with col_pf5:
                modifica_pas = st.checkbox("Modifica PAS")
            with col_pf6:
                otra_modificacion = st.checkbox("Otra modificacion")

            if modifica_potencia_parque:
                st.caption(
                    "Compara la potencia aprobada en la RCA con la potencia propuesta. "
                    "Esto permite distinguir aumento, disminucion o mantencion de potencia."
                )
                col_pot1, col_pot2 = st.columns(2)
                with col_pot1:
                    potencia_rca_mw = st.number_input(
                        "Potencia aprobada en la RCA (MW)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                    )
                with col_pot2:
                    potencia_propuesta_mw = st.number_input(
                        "Potencia propuesta con la modificacion (MW)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                    )

            if cambia_punto_conexion or modifica_linea_evacuacion:
                tension_linea_modificada_kv = st.number_input(
                    "Tension de la nueva/modificada linea o conexion (kV)",
                    min_value=0.0,
                    value=0.0,
                    step=0.1,
                    help="Si supera 23 kV, la rubrica lo trata como alerta alta por literal b.1).",
                )

            if otra_modificacion:
                st.warning(
                    "Para 'otra modificacion', el MVP no puede estimar riesgo automaticamente. "
                    "Se dejara como indeterminado para revision tecnica."
                )

        if sector == "Energia" and subtipo_energia == "Linea de transmision":
            st.write("**Tipo de modificacion de la linea de transmision**")
            st.caption("Marca solo los cambios que forman parte de la modificacion consultada.")
            col_lt1, col_lt2, col_lt3 = st.columns(3)
            with col_lt1:
                agrega_linea_transmision = st.checkbox("Agrega nueva linea o tramo")
            with col_lt2:
                seccionamiento_linea = st.checkbox("Seccionamiento de linea")
            with col_lt3:
                modifica_conductores_linea = st.checkbox("Modifica conductores o capacidad")

            col_lt4, col_lt5 = st.columns(2)
            with col_lt4:
                modifica_trazado_linea = st.checkbox("Modifica trazado, estructuras o faja")
            with col_lt5:
                otra_modificacion = st.checkbox("Otra modificacion")

            if agrega_linea_transmision:
                tension_linea_propuesta_kv = st.number_input(
                    "Tension de la nueva linea o tramo (kV)",
                    min_value=0.0,
                    value=0.0,
                    step=0.1,
                    help="Si no conoces este dato, dejalo en 0 y el MVP lo derivara a consultor.",
                )

            if modifica_conductores_linea or modifica_trazado_linea:
                st.caption(
                    "Compara la tension aprobada en la RCA con la tension propuesta. "
                    "Esto permite distinguir si existe aumento o cambio tecnico relevante."
                )
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    tension_linea_rca_kv = st.number_input(
                        "Tension aprobada en la RCA (kV)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                    )
                with col_t2:
                    tension_linea_propuesta_kv = st.number_input(
                        "Tension propuesta con la modificacion (kV)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                    )

            if seccionamiento_linea:
                st.info(
                    "El seccionamiento requiere revisar obras asociadas, paños, subestacion, caminos, "
                    "area de influencia y cambios de impactos."
                )

            if otra_modificacion:
                st.warning(
                    "Para 'otra modificacion', el MVP no puede estimar riesgo automaticamente. "
                    "Se dejara como indeterminado para revision tecnica."
                )

        if sector == "Inmobiliario":
            st.write("**Tipo de modificacion del proyecto inmobiliario**")
            st.caption("Marca solo los cambios que forman parte de la modificacion consultada.")
            col_in1, col_in2 = st.columns(2)
            with col_in1:
                modifica_viviendas_inmobiliario = st.checkbox("Cambia numero de viviendas")
            with col_in2:
                modifica_superficie_inmobiliario = st.checkbox("Cambia superficie o area urbanizada")

            col_in4, col_in5 = st.columns(2)
            with col_in4:
                modifica_pas = st.checkbox("Modifica PAS")
            with col_in5:
                otra_modificacion = st.checkbox("Otra modificacion")

            if modifica_viviendas_inmobiliario:
                st.caption("Compara las viviendas aprobadas en la RCA con las viviendas propuestas.")
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    viviendas_rca = st.number_input("Viviendas aprobadas en la RCA", min_value=0, value=0, step=1)
                with col_v2:
                    viviendas_propuestas = st.number_input("Viviendas propuestas con la modificacion", min_value=0, value=0, step=1)

            if modifica_superficie_inmobiliario:
                st.caption("Compara la superficie aprobada en la RCA con la superficie propuesta.")
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    superficie_rca_ha = st.number_input(
                        "Superficie aprobada en la RCA (ha)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                    )
                with col_s2:
                    superficie_propuesta_ha = st.number_input(
                        "Superficie propuesta con la modificacion (ha)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                    )

            if otra_modificacion:
                st.warning(
                    "Para 'otra modificacion', el MVP no puede estimar riesgo automaticamente. "
                    "Se dejara como indeterminado para revision tecnica."
                )

        st.write("**Analisis Art. 2 letra g)**")
        st.caption(
            "Responde No cuando el cambio fue revisado y no ocurre. "
            "Si no tienes antecedentes, usa No sabe y el MVP lo derivara a revision de consultor."
        )
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            respuesta_area_fuera_influencia_rca = respuesta_si_no_no_sabe(
                "Nueva area fuera del area de influencia evaluada en la RCA",
                "Si la modificacion solo cambia ubicacion dentro del area de influencia ya evaluada, responde No.",
            )
            area_fuera_influencia_rca = respuesta_area_fuera_influencia_rca == "Si"
        with col_m2:
            respuesta_modifica_impactos_evaluados = respuesta_si_no_no_sabe(
                "Cambia extension, magnitud o duracion de impactos evaluados",
                "Incluye aumentos relevantes de emisiones, residuos, uso de recursos u otros impactos ya evaluados.",
            )
            modifica_impactos_evaluados = respuesta_modifica_impactos_evaluados == "Si"
        with col_m3:
            respuesta_modifica_medidas_rca = respuesta_si_no_no_sabe(
                "Modifica medidas de mitigacion, reparacion o compensacion",
                "Responde Si si cambia medidas establecidas en la RCA.",
            )
            modifica_medidas_rca = respuesta_modifica_medidas_rca == "Si"

    enviado = st.button("Generar diagnostico", type="primary")

    if not enviado:
        st.info("Completa el formulario y presiona Generar diagnostico.")
        return

    datos = {
        "tipo_gestion": tipo_gestion,
        "sector": sector,
        "region": region,
        "subtipo_energia": subtipo_energia,
        "en_area_protegida": en_area_protegida,
        "en_humedal": en_humedal,
        "respuesta_area_protegida": respuesta_area_protegida,
        "respuesta_humedal": respuesta_humedal,
        "distancia_humedal_m": None,
        "respuesta_nueva_infraestructura": respuesta_nueva_infraestructura,
        "nueva_infraestructura": nueva_infraestructura,
        "cambia_trazado": cambia_trazado,
        "potencia_mw": potencia_mw if potencia_mw > 0 else None,
        "potencia_rca_mw": potencia_rca_mw if potencia_rca_mw > 0 else None,
        "potencia_propuesta_mw": potencia_propuesta_mw if potencia_propuesta_mw > 0 else None,
        "tension_kv": tension_kv if tension_kv > 0 else None,
        "tension_linea_modificada_kv": tension_linea_modificada_kv if tension_linea_modificada_kv > 0 else None,
        "tension_linea_rca_kv": tension_linea_rca_kv if tension_linea_rca_kv > 0 else None,
        "tension_linea_propuesta_kv": tension_linea_propuesta_kv if tension_linea_propuesta_kv > 0 else None,
        "longitud_linea_km": longitud_linea_km if longitud_linea_km > 0 else None,
        "obras_electricas_nuevas": obras_electricas_nuevas,
        "tension_obra_electrica_kv": tension_obra_electrica_kv if tension_obra_electrica_kv > 0 else None,
        "funcion_subestacion_obra": funcion_subestacion_obra,
        "funcion_subestacion": funcion_subestacion,
        "tiene_ipt": tiene_ipt,
        "emplazamiento_inmobiliario": emplazamiento_inmobiliario,
        "tipo_inmobiliario": tipo_inmobiliario,
        "subtipo_equipamiento": subtipo_equipamiento,
        "antiguedad_proyecto": antiguedad_proyecto,
        "respuesta_aumenta_estacionamientos": respuesta_aumenta_estacionamientos,
        "respuesta_aumenta_carga_ocupacion": respuesta_aumenta_carga_ocupacion,
        "respuesta_sistema_agua_potable": respuesta_sistema_agua_potable,
        "respuesta_sistema_aguas_servidas": respuesta_sistema_aguas_servidas,
        "respuesta_incorpora_vialidad_publica": respuesta_incorpora_vialidad_publica,
        "respuesta_vias_expresas_troncales": respuesta_vias_expresas_troncales,
        "aumenta_estacionamientos": aumenta_estacionamientos,
        "aumenta_carga_ocupacion": aumenta_carga_ocupacion,
        "sistema_agua_potable": sistema_agua_potable,
        "sistema_aguas_servidas": sistema_aguas_servidas,
        "incorpora_vialidad_publica": incorpora_vialidad_publica,
        "vias_expresas_troncales": vias_expresas_troncales,
        "comuna_proyecto": "" if comuna_proyecto == "No sabe / No indicada" else comuna_proyecto.strip(),
        "respuesta_zona_saturada": respuesta_zona_saturada,
        "zona_saturada": zona_saturada,
        "numero_viviendas": numero_viviendas if numero_viviendas > 0 else None,
        "viviendas_rca": viviendas_rca if viviendas_rca > 0 else None,
        "viviendas_propuestas": viviendas_propuestas if viviendas_propuestas > 0 else None,
        "superficie_ha": superficie_ha if superficie_ha > 0 else None,
        "superficie_rca_ha": superficie_rca_ha if superficie_rca_ha > 0 else None,
        "superficie_propuesta_ha": superficie_propuesta_ha if superficie_propuesta_ha > 0 else None,
        "area_fuera_influencia_rca": area_fuera_influencia_rca,
        "modifica_impactos_evaluados": modifica_impactos_evaluados,
        "modifica_medidas_rca": modifica_medidas_rca,
        "respuesta_area_fuera_influencia_rca": respuesta_area_fuera_influencia_rca,
        "respuesta_modifica_impactos_evaluados": respuesta_modifica_impactos_evaluados,
        "respuesta_modifica_medidas_rca": respuesta_modifica_medidas_rca,
        "modifica_potencia_parque": modifica_potencia_parque,
        "agrega_bess": agrega_bess,
        "cambia_punto_conexion": cambia_punto_conexion,
        "modifica_linea_evacuacion": modifica_linea_evacuacion,
        "agrega_linea_transmision": agrega_linea_transmision,
        "seccionamiento_linea": seccionamiento_linea,
        "modifica_conductores_linea": modifica_conductores_linea,
        "modifica_trazado_linea": modifica_trazado_linea,
        "modifica_viviendas_inmobiliario": modifica_viviendas_inmobiliario,
        "modifica_superficie_inmobiliario": modifica_superficie_inmobiliario,
        "modifica_pas": modifica_pas,
        "otra_modificacion": otra_modificacion,
        "descripcion_otra_modificacion": descripcion_otra_modificacion.strip(),
    }

    diagnostico = evaluar_diagnostico(datos)
    st.session_state["datos_proyecto"] = datos
    st.session_state["diagnostico_actual"] = diagnostico

    st.divider()
    col_r1, col_r2, col_r3 = st.columns([1, 2, 2])
    col_r1.metric("Riesgo preliminar", diagnostico["riesgo"])
    col_r2.write("**Conclusion preliminar**")
    col_r2.write(diagnostico["conclusion"])
    col_r3.write("**Suficiencia de antecedentes**")
    col_r3.write(diagnostico.get("suficiencia_antecedentes", "No determinado"))
    col_r3.caption(diagnostico.get("detalle_suficiencia", "No disponible."))

    if diagnostico["datos_faltantes"]:
        st.warning("Datos faltantes relevantes: " + ", ".join(diagnostico["datos_faltantes"]))
    elif diagnostico["riesgo"] == "MEDIO":
        st.info(
            "No hay datos faltantes indispensables registrados por la rubrica para este caso. "
            "El nivel MEDIO se debe a factores evaluados como zona gris o alerta media."
        )

    st.write("**Literales o criterios relevantes**")
    st.write(", ".join(diagnostico["literales"]) if diagnostico["literales"] else "No determinados")

    st.write("**Factores evaluados**")
    for hallazgo in diagnostico["hallazgos"]:
        st.markdown(f"**{hallazgo['riesgo']} - {hallazgo['criterio']} ({hallazgo['literal']})**")
        st.write(hallazgo["explicacion"])

    st.caption(diagnostico["advertencia"])
    st.info("Para revisar resoluciones comparables, abre la pestaña Comparador de precedentes.")


def render_criterios(conexion: sqlite3.Connection | None) -> None:
    st.subheader("Criterios SEA y resoluciones procesadas")

    if conexion is None:
        st.warning("Todavia no existe la base de datos.")
        st.write("Ejecuta primero estos comandos:")
        st.code(
            "python src/extraer_texto_pdfs.py\n"
            "python src/analizar_textos.py\n"
            "python src/base_datos.py",
            language="bash",
        )
        return

    tipos = obtener_opciones(conexion, "tipo_proyecto")
    regiones = obtener_opciones(conexion, "region")

    col_tipo, col_region, col_palabra = st.columns(3)

    with col_tipo:
        tipo_proyecto = st.selectbox("Tipo de proyecto", [""] + tipos, format_func=lambda x: x or "Todos")

    with col_region:
        region = st.selectbox("Region", [""] + regiones, format_func=lambda x: x or "Todas")

    with col_palabra:
        palabra_clave = st.text_input("Palabra clave")

    documentos = buscar_documentos(conexion, tipo_proyecto, region, palabra_clave)

    st.write(f"{len(documentos)} documento(s) encontrado(s).")

    if not documentos:
        st.info("No hay resultados para los filtros seleccionados.")
        return

    for documento in documentos:
        titulo = documento["nombre_proyecto"] or documento["id_documento"]
        if titulo == "no determinado":
            titulo = documento["id_documento"]

        with st.expander(titulo):
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Region", documento["region"] or "No determinado")
            col_b.metric("Tipo", documento["tipo_proyecto"] or "No determinado")
            col_c.metric("Ingresa al SEIA", texto_ingreso_seia(documento["debe_ingresar_al_seia"]))

            st.write("**Datos principales**")
            st.write(
                {
                    "id_documento": documento["id_documento"],
                    "comuna": documento["comuna"],
                    "subtipo_proyecto": documento["subtipo_proyecto"],
                    "proponente": documento["proponente"],
                    "fecha_resolucion": documento["fecha_resolucion"],
                    "resultado": documento["resultado"],
                }
            )

            st.write("**Resumen ejecutivo**")
            st.write(documento["resumen_ejecutivo"] or "Sin resumen.")

            st.write("**Criterios extraidos**")
            criterios = obtener_criterios(conexion, documento["id"])
            if not criterios:
                st.info("Este documento no tiene criterios cargados.")
            else:
                for criterio in criterios:
                    st.markdown(f"**{criterio['criterio'] or 'Criterio no determinado'}**")
                    st.write(criterio["explicacion"] or "Sin explicacion.")
                    st.caption(f"Confianza: {criterio['nivel_confianza'] or 'no determinada'}")
                    if criterio["fragmento_respaldo"]:
                        st.markdown(f"> {criterio['fragmento_respaldo']}")


st.title("Diagnóstico Express SEA")
st.caption("MVP local para diagnóstico preliminar, comparación referencial y revisión de criterios SEA.")

conexion_app = conectar() if RUTA_BASE_DATOS.exists() else None

tab_diagnostico, tab_comparador, tab_analitica, tab_criterios = st.tabs(
    ["Diagnóstico preliminar", "Comparador de precedentes", "Analítica de datos", "Criterios SEA"]
)

with tab_diagnostico:
    render_diagnostico(conexion_app)

with tab_comparador:
    st.info(
        "Funcionalidad en desarrollo. Este módulo forma parte de la hoja de ruta del MVP y será habilitado en una "
        "siguiente etapa de desarrollo y validación. La versión actual prioriza el funcionamiento y validación del "
        "Diagnóstico Express de Pertinencia SEIA."
    )

with tab_analitica:
    st.info(
        "Funcionalidad en desarrollo. Este módulo forma parte de la hoja de ruta del MVP y será habilitado en una "
        "siguiente etapa de desarrollo y validación. La versión actual prioriza el funcionamiento y validación del "
        "Diagnóstico Express de Pertinencia SEIA."
    )

with tab_criterios:
    st.info(
        "Funcionalidad en desarrollo. Este módulo forma parte de la hoja de ruta del MVP y será habilitado en una "
        "siguiente etapa de desarrollo y validación. La versión actual prioriza el funcionamiento y validación del "
        "Diagnóstico Express de Pertinencia SEIA."
    )

if conexion_app is not None:
    conexion_app.close()
