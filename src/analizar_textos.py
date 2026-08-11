import json
import os
import re
import unicodedata
from typing import Any

from dotenv import load_dotenv

from config import CARPETA_RESULTADOS, CARPETA_TEXTOS, asegurar_carpetas
from validacion import validar_resultado


load_dotenv()


PROMPT_SISTEMA = """
Actua como asistente tecnico para revisar resoluciones publicas del Servicio de Evaluacion Ambiental de Chile sobre consultas de pertinencia.

Extrae informacion administrativa y criterios usados por el SEA.
No inventes datos. Si un dato no aparece claramente en el texto, usa null, "no determinado" o una lista vacia.

Devuelve solo un JSON valido, sin texto antes ni despues.

El JSON debe tener exactamente esta estructura:
{
  "id_documento": "",
  "nombre_proyecto": "",
  "region": "",
  "comuna": "",
  "tipo_proyecto": "",
  "subtipo_proyecto": "",
  "proponente": "",
  "fecha_resolucion": "",
  "resultado": "",
  "debe_ingresar_al_seia": null,
  "normativa_citada": [],
  "criterios_sea": [
    {
      "criterio": "",
      "explicacion": "",
      "fragmento_respaldo": "",
      "nivel_confianza": ""
    }
  ],
  "resumen_ejecutivo": "",
  "palabras_clave": []
}

Reglas:
- resultado debe indicar si debe ingresar al SEIA, no debe ingresar, es inadmisible, otro resultado o no determinado.
- debe_ingresar_al_seia debe ser true, false o null.
- fragmento_respaldo debe ser una cita breve del texto original.
- nivel_confianza debe ser "alto", "medio" o "bajo".
- No entregues asesoria juridica definitiva.
""".strip()


def quitar_tildes(texto: str) -> str:
    """Normaliza texto para buscar aunque venga con tildes o caracteres raros."""
    texto_normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto_normalizado if not unicodedata.combining(c))


def limpiar_espacios(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip(" .,\n\t")


def buscar_patron(texto: str, patron: str, grupo: int = 1) -> str | None:
    encontrado = re.search(patron, texto, flags=re.IGNORECASE | re.DOTALL)
    if not encontrado:
        return None
    return limpiar_espacios(encontrado.group(grupo))


def extraer_linea_region(texto: str) -> str:
    for linea in texto.splitlines():
        linea_simple = quitar_tildes(linea).strip()
        encontrado = re.search(r"^REGION\s+DEL\s+(.+)$", linea_simple, flags=re.IGNORECASE)
        if encontrado:
            region = limpiar_espacios(encontrado.group(1)).title()
            return f"Region del {region}"
    return "no determinado"


def extraer_comuna(texto: str) -> str:
    patrones = [
        r"comuna\s+y\s+provincia\s+de\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]+?),",
        r"comuna\s+de\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]+?)(?:,|\.|\s+region)",
        r"comuna\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]+?)(?:,|\.|\s+region)",
    ]
    for patron in patrones:
        valor = buscar_patron(texto, patron)
        if valor:
            return valor
    return "no determinado"


def extraer_proponente(texto: str) -> str:
    patrones = [
        r"el proponente\s+(.+?)\s*,\s+a trav[eé]s",
        r"realizada por .*? en representaci[oó]n de\s+(.+?),\s+mediante",
        r"SOLICITADO POR .*? EN REPRESENTACI[OÓ]N DE\s+(.+?)\.",
    ]
    for patron in patrones:
        valor = buscar_patron(texto, patron)
        if valor:
            return valor
    return "no determinado"


def extraer_nombre_proyecto(texto: str) -> str:
    texto_plano = limpiar_espacios(texto)
    patrones = [
        r"pertinencia de ingreso a SEIA del proyecto denominado\s+([^\n.]+)",
        r"solicit[oó] pronunciamiento.+?proyecto denominado\s+([^\n.]+)",
        r"Modificaci[oó]n de RCA.+?proyecto\s+([^\n.]+)",
        r"proyecto denominado\s+(.+?)\s*\.",
    ]
    for patron in patrones:
        valor = buscar_patron(texto_plano, patron)
        if not valor:
            continue
        valor_simple = quitar_tildes(valor).lower()
        valor_invalido = any(
            palabra in valor_simple
            for palabra in ["solicitado por", "vistos", "considerando", "republica de chile"]
        )
        if not valor_invalido and len(valor) <= 180 and len(valor.strip(" ,")) > 5:
            return valor
    return "no determinado"


def extraer_fecha_resolucion(texto: str) -> str:
    patrones = [
        r"fecha\s+(\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+\s+de\s+\d{4})",
        r"(\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+\s+de\s+\d{4})",
    ]
    for patron in patrones:
        valor = buscar_patron(texto, patron)
        if valor:
            return valor
    return "no determinado"


def extraer_tipo_proyecto(texto: str, nombre_proyecto: str, id_documento: str) -> str:
    texto_busqueda = quitar_tildes(f"{id_documento} {nombre_proyecto} {texto[:5000]}").lower()
    if any(palabra in texto_busqueda for palabra in ["fotovoltaico", "solar", "bess", "energia"]):
        return "energia"
    if any(palabra in texto_busqueda for palabra in ["inmobiliario", "loteo", "vivienda", "edificio"]):
        return "inmobiliario"
    return "no determinado"


def extraer_subtipo_proyecto(texto: str, nombre_proyecto: str) -> str:
    texto_busqueda = quitar_tildes(f"{nombre_proyecto} {texto[:6000]}").lower()
    subtipos: list[str] = []
    if "fotovoltaico" in texto_busqueda or "solar" in texto_busqueda:
        subtipos.append("fotovoltaico")
    if "bess" in texto_busqueda or "bateria" in texto_busqueda or "almacenamiento" in texto_busqueda:
        subtipos.append("almacenamiento de energia")
    if "modificacion" in texto_busqueda or "modifica" in texto_busqueda:
        subtipos.append("modificacion de proyecto")
    return ", ".join(subtipos) if subtipos else "no determinado"


def extraer_resultado(texto: str) -> tuple[str, bool | None, str]:
    patrones_no_ingresa = [
        r"no requiere ingresar obligatoriamente al SEIA[^.\n]*",
        r"no requiere ingresar al Sistema de Evaluaci[oó]n de Impacto Ambiental[^.\n]*",
        r"no requiere ingresar al SEIA[^.\n]*",
        r"no debe ingresar al SEIA[^.\n]*",
        r"no se encuentra obligado a ingresar[^.\n]*",
    ]
    patrones_ingresa = [
        r"requiere ingresar obligatoriamente al SEIA[^.\n]*",
        r"debe ingresar al SEIA[^.\n]*",
        r"debe someterse al SEIA[^.\n]*",
    ]

    for patron in patrones_no_ingresa:
        valor = buscar_patron(texto, f"({patron})")
        if valor:
            return "no debe ingresar al SEIA", False, valor

    for patron in patrones_ingresa:
        valor = buscar_patron(texto, f"({patron})")
        if valor:
            return "debe ingresar al SEIA", True, valor

    if re.search(r"inadmisible|inadmisibilidad", texto, flags=re.IGNORECASE):
        return "inadmisible", None, "Se detecta referencia a inadmisibilidad, revisar manualmente."

    return "no determinado", None, texto[:350].replace("\n", " ")


def extraer_normativa(texto: str) -> list[str]:
    normativa_posible = [
        "Ley N° 19.300",
        "Ley N° 19.880",
        "D.S. N° 40/2012",
        "Reglamento del SEIA",
        "Oficio Ordinario D.E. N°20249910281136",
        "articulo 10 de la Ley N° 19.300",
        "articulos 2 y 3 del Reglamento del SEIA",
    ]
    texto_simple = quitar_tildes(texto).lower()
    encontradas: list[str] = []
    for norma in normativa_posible:
        if quitar_tildes(norma).lower().replace("°", "") in texto_simple.replace("°", ""):
            encontradas.append(norma)
    return encontradas


def extraer_palabras_clave(texto: str, tipo_proyecto: str, subtipo_proyecto: str) -> list[str]:
    candidatas = [
        "consulta de pertinencia",
        "SEIA",
        "RCA",
        "fotovoltaico",
        "energia",
        "BESS",
        "almacenamiento",
        "inmobiliario",
        "humedal",
        "area protegida",
        "modificacion de proyecto",
    ]
    texto_simple = quitar_tildes(texto).lower()
    palabras = []
    for palabra in candidatas:
        if quitar_tildes(palabra).lower() in texto_simple:
            palabras.append(palabra)
    if tipo_proyecto != "no determinado":
        palabras.append(tipo_proyecto)
    if subtipo_proyecto != "no determinado":
        palabras.extend([p.strip() for p in subtipo_proyecto.split(",")])
    return sorted(set(palabras))


def limpiar_json_respuesta(texto_respuesta: str) -> str:
    """Quita cercos markdown si el modelo los agrega por error."""
    texto_limpio = texto_respuesta.strip()
    if texto_limpio.startswith("```json"):
        texto_limpio = texto_limpio.removeprefix("```json").strip()
    if texto_limpio.startswith("```"):
        texto_limpio = texto_limpio.removeprefix("```").strip()
    if texto_limpio.endswith("```"):
        texto_limpio = texto_limpio.removesuffix("```").strip()
    return texto_limpio


def analizar_con_openai(texto: str, id_documento: str) -> dict[str, Any]:
    """Envia el texto a OpenAI y espera un JSON con la estructura del MVP."""
    from openai import OpenAI

    modelo = os.getenv("OPENAI_MODEL", "gpt-5")
    max_caracteres = int(os.getenv("MAX_CARACTERES_IA", "60000"))
    texto_recortado = texto[:max_caracteres]

    cliente = OpenAI()
    respuesta = cliente.responses.create(
        model=modelo,
        input=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {
                "role": "user",
                "content": (
                    f"id_documento: {id_documento}\n\n"
                    "Texto de la resolucion:\n"
                    f"{texto_recortado}"
                ),
            },
        ],
    )

    contenido = limpiar_json_respuesta(respuesta.output_text)
    resultado = json.loads(contenido)
    resultado["id_documento"] = resultado.get("id_documento") or id_documento
    return resultado


def analizar_con_reglas(texto: str, id_documento: str = "") -> dict[str, Any]:
    """
    Analisis inicial del MVP.

    Aplica reglas simples sobre el texto extraido para obtener campos utiles
    sin consumir API ni servicios pagados.
    """
    nombre_proyecto = extraer_nombre_proyecto(texto)
    region = extraer_linea_region(texto)
    comuna = extraer_comuna(texto)
    proponente = extraer_proponente(texto)
    fecha_resolucion = extraer_fecha_resolucion(texto)
    tipo_proyecto = extraer_tipo_proyecto(texto, nombre_proyecto, id_documento)
    subtipo_proyecto = extraer_subtipo_proyecto(texto, nombre_proyecto)
    resultado, debe_ingresar, fragmento_resultado = extraer_resultado(texto)
    normativa = extraer_normativa(texto)
    palabras_clave = extraer_palabras_clave(texto, tipo_proyecto, subtipo_proyecto)

    return {
        "id_documento": id_documento,
        "nombre_proyecto": nombre_proyecto,
        "region": region,
        "comuna": comuna,
        "tipo_proyecto": tipo_proyecto,
        "subtipo_proyecto": subtipo_proyecto,
        "proponente": proponente,
        "fecha_resolucion": fecha_resolucion,
        "resultado": resultado,
        "debe_ingresar_al_seia": debe_ingresar,
        "normativa_citada": normativa,
        "criterios_sea": [
            {
                "criterio": "Pronunciamiento sobre ingreso obligatorio al SEIA",
                "explicacion": (
                    "Extraccion inicial por reglas. Este criterio debe revisarse "
                    "manualmente antes de usarlo como conclusion tecnica."
                ),
                "fragmento_respaldo": fragmento_resultado,
                "nivel_confianza": "medio" if debe_ingresar is not None else "bajo",
            }
        ],
        "resumen_ejecutivo": (
            f"Documento {id_documento}. Proyecto: {nombre_proyecto}. "
            f"Region: {region}. Comuna: {comuna}. Resultado preliminar: {resultado}. "
            "Informacion extraida automaticamente y sujeta a revision humana."
        ),
        "palabras_clave": palabras_clave,
    }


def analizar_con_ia(texto: str, id_documento: str = "") -> dict[str, Any]:
    """
    Usa OpenAI si existe OPENAI_API_KEY. Si no existe, usa reglas locales.

    No pongas claves API reales en este archivo. Usa el archivo .env.
    """
    if os.getenv("OPENAI_API_KEY"):
        return analizar_con_openai(texto, id_documento)

    return analizar_con_reglas(texto, id_documento)


def procesar_textos() -> None:
    asegurar_carpetas()
    archivos_texto = sorted(CARPETA_TEXTOS.glob("*.txt"))

    if not archivos_texto:
        print(f"No hay archivos .txt en {CARPETA_TEXTOS}")
        print("Ejecuta primero: python src/extraer_texto_pdfs.py")
        return

    for ruta_texto in archivos_texto:
        print(f"Analizando texto: {ruta_texto.name}")
        if os.getenv("OPENAI_API_KEY"):
            print("  Modo IA real: OpenAI")
        else:
            print("  Modo local: reglas simples, sin costo API")
        texto = ruta_texto.read_text(encoding="utf-8", errors="replace")

        try:
            resultado = analizar_con_ia(texto, id_documento=ruta_texto.stem)
        except Exception as error:
            print(f"  Error al analizar {ruta_texto.name}: {error}")
            print("  Se omite este archivo para que puedas revisar el problema.")
            continue

        errores = validar_resultado(resultado)

        if errores:
            print("  El resultado no paso la validacion basica:")
            for error in errores:
                print(f"  - {error}")
            continue

        ruta_salida = CARPETA_RESULTADOS / f"{ruta_texto.stem}.json"
        ruta_salida.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  JSON guardado en: {ruta_salida}")

    print("Analisis terminado.")


if __name__ == "__main__":
    procesar_textos()
