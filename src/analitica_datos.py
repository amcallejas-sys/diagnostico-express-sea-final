from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd


COLUMNAS_REPORTE = [
    "id_documento",
    "fecha_resolucion",
    "nombre_proyecto",
    "region",
    "comuna",
    "tipo_proyecto",
    "subtipo_proyecto",
    "resultado",
    "debe_ingresar_al_seia_texto",
    "resumen_ejecutivo",
]


def texto_no_determinado(valor: Any) -> str:
    if valor is None:
        return "No determinado"
    texto = str(valor).strip()
    if not texto or texto.lower() == "no determinado":
        return "No determinado"
    return texto


def texto_ingreso_seia(valor: Any) -> str:
    if valor == 1 or valor is True:
        return "Si"
    if valor == 0 or valor is False:
        return "No"
    return "No determinado"


def obtener_registros(conexion: sqlite3.Connection) -> pd.DataFrame:
    """Obtiene la tabla base para analitica desde SQLite."""
    consulta = """
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
        ORDER BY d.id_documento
    """
    try:
        datos = pd.read_sql_query(consulta, conexion)
    except Exception:
        return pd.DataFrame()

    if datos.empty:
        return datos

    for columna in [
        "id_documento",
        "fecha_resolucion",
        "resultado",
        "resumen_ejecutivo",
        "nombre_proyecto",
        "region",
        "comuna",
        "tipo_proyecto",
        "subtipo_proyecto",
        "proponente",
    ]:
        if columna not in datos.columns:
            datos[columna] = "No determinado"
        datos[columna] = datos[columna].apply(texto_no_determinado)

    datos["debe_ingresar_al_seia_texto"] = datos["debe_ingresar_al_seia"].apply(texto_ingreso_seia)
    fechas = pd.to_datetime(datos["fecha_resolucion"], errors="coerce", dayfirst=True, format="mixed")
    datos["fecha_valida"] = fechas
    datos["anio_resolucion"] = fechas.dt.year.astype("Int64")
    datos["mes_resolucion"] = fechas.dt.to_period("M").astype(str)
    datos.loc[fechas.isna(), "mes_resolucion"] = "No determinado"
    return datos


def opciones_filtro(datos: pd.DataFrame, columna: str) -> list[str]:
    if datos.empty or columna not in datos.columns:
        return ["Todas"]
    valores = sorted(
        {
            texto_no_determinado(valor)
            for valor in datos[columna].dropna().tolist()
            if texto_no_determinado(valor) != "No determinado"
        }
    )
    return ["Todas"] + valores


def opciones_anio(datos: pd.DataFrame) -> list[str]:
    if datos.empty or "anio_resolucion" not in datos.columns:
        return ["Todos"]
    valores = sorted({int(valor) for valor in datos["anio_resolucion"].dropna().tolist()})
    return ["Todos"] + [str(valor) for valor in valores]


def aplicar_filtros(
    datos: pd.DataFrame,
    region: str = "Todas",
    comuna: str = "Todas",
    tipo_proyecto: str = "Todas",
    subtipo_proyecto: str = "Todas",
    anio: str = "Todos",
) -> pd.DataFrame:
    filtrados = datos.copy()
    filtros = {
        "region": region,
        "comuna": comuna,
        "tipo_proyecto": tipo_proyecto,
        "subtipo_proyecto": subtipo_proyecto,
    }
    for columna, valor in filtros.items():
        if valor not in ("Todas", "Todos") and columna in filtrados.columns:
            filtrados = filtrados[filtrados[columna] == valor]

    if anio not in ("Todas", "Todos") and "anio_resolucion" in filtrados.columns:
        filtrados = filtrados[filtrados["anio_resolucion"].astype("Int64").astype(str) == str(anio)]
    return filtrados


def _contiene(datos: pd.DataFrame, columna: str, texto: str) -> int:
    if datos.empty or columna not in datos.columns:
        return 0
    return int(datos[columna].str.lower().str.contains(texto, na=False).sum())


def calcular_indicadores(datos: pd.DataFrame) -> dict[str, Any]:
    total = int(len(datos))
    regiones = int(datos.loc[datos["region"] != "No determinado", "region"].nunique()) if total else 0
    comunas = int(datos.loc[datos["comuna"] != "No determinado", "comuna"].nunique()) if total else 0
    energia = _contiene(datos, "tipo_proyecto", "energia")
    inmobiliario = _contiene(datos, "tipo_proyecto", "inmobili")

    ingreso = datos["debe_ingresar_al_seia_texto"].value_counts().to_dict() if total else {}
    denominador = total
    conteos_ingreso = {}
    for etiqueta in ["Si", "No", "No determinado"]:
        conteo = int(ingreso.get(etiqueta, 0))
        porcentaje = (conteo / denominador * 100) if denominador else 0
        conteos_ingreso[etiqueta] = {"conteo": conteo, "porcentaje": porcentaje, "denominador": denominador}

    return {
        "total_resoluciones": total,
        "regiones_representadas": regiones,
        "comunas_representadas": comunas,
        "resoluciones_energia": energia,
        "resoluciones_inmobiliarias": inmobiliario,
        "ingreso_seia": conteos_ingreso,
        "sin_region": int((datos["region"] == "No determinado").sum()) if total else 0,
        "sin_tipo_proyecto": int((datos["tipo_proyecto"] == "No determinado").sum()) if total else 0,
    }


def conteo_por_columna(datos: pd.DataFrame, columna: str, limite: int | None = None) -> pd.DataFrame:
    if datos.empty or columna not in datos.columns:
        return pd.DataFrame(columns=[columna, "cantidad"])
    conteo = datos[columna].fillna("No determinado").replace("", "No determinado").value_counts().reset_index()
    conteo.columns = [columna, "cantidad"]
    if limite:
        conteo = conteo.head(limite)
    return conteo


def conteo_temporal(datos: pd.DataFrame) -> pd.DataFrame:
    if datos.empty or "anio_resolucion" not in datos.columns:
        return pd.DataFrame(columns=["anio_resolucion", "cantidad"])
    validos = datos.dropna(subset=["anio_resolucion"]).copy()
    if validos.empty:
        return pd.DataFrame(columns=["anio_resolucion", "cantidad"])
    validos["anio_resolucion"] = validos["anio_resolucion"].astype(int).astype(str)
    conteo = validos["anio_resolucion"].value_counts().sort_index().reset_index()
    conteo.columns = ["anio_resolucion", "cantidad"]
    return conteo


def preparar_tabla_descarga(datos: pd.DataFrame) -> pd.DataFrame:
    if datos.empty:
        return pd.DataFrame(columns=COLUMNAS_REPORTE)
    columnas = [columna for columna in COLUMNAS_REPORTE if columna in datos.columns]
    return datos[columnas].copy()


def calidad_datos(datos: pd.DataFrame) -> pd.DataFrame:
    filas = []
    if datos.empty:
        return pd.DataFrame(columns=["campo", "faltantes_o_no_determinados", "total", "porcentaje"])
    total = len(datos)
    for columna in [
        "fecha_resolucion",
        "nombre_proyecto",
        "region",
        "comuna",
        "tipo_proyecto",
        "subtipo_proyecto",
        "resultado",
        "debe_ingresar_al_seia_texto",
        "resumen_ejecutivo",
    ]:
        if columna not in datos.columns:
            continue
        faltantes = int(datos[columna].apply(texto_no_determinado).eq("No determinado").sum())
        filas.append(
            {
                "campo": columna,
                "faltantes_o_no_determinados": faltantes,
                "total": total,
                "porcentaje": round((faltantes / total * 100) if total else 0, 1),
            }
        )
    return pd.DataFrame(filas)
