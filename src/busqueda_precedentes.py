import sqlite3
from typing import Any


def buscar_precedentes(
    conexion: sqlite3.Connection,
    sector: str,
    region: str = "",
    subtipo: str = "",
    limite: int = 5,
) -> list[dict[str, Any]]:
    """Busca resoluciones parecidas usando filtros simples de la base SQLite."""
    condiciones = []
    parametros: list[str] = []

    if sector:
        condiciones.append("LOWER(p.tipo_proyecto) LIKE LOWER(?)")
        parametros.append(f"%{sector}%")

    if region:
        condiciones.append("LOWER(p.region) LIKE LOWER(?)")
        parametros.append(f"%{region}%")

    palabras_subtipo = [p.strip() for p in subtipo.replace("/", ",").split(",") if p.strip()]
    if palabras_subtipo:
        subcondiciones = []
        for palabra in palabras_subtipo:
            subcondiciones.append(
                """
                (
                    LOWER(p.subtipo_proyecto) LIKE LOWER(?)
                    OR EXISTS (
                        SELECT 1
                        FROM palabras_clave pc
                        WHERE pc.documento_id = d.id
                          AND LOWER(pc.palabra_clave) LIKE LOWER(?)
                    )
                )
                """
            )
            parametros.extend([f"%{palabra}%", f"%{palabra}%"])
        condiciones.append("(" + " OR ".join(subcondiciones) + ")")

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    parametros.append(str(limite))

    filas = conexion.execute(
        f"""
        SELECT
            d.id,
            d.id_documento,
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
        {where}
        ORDER BY d.id DESC
        LIMIT ?
        """,
        parametros,
    ).fetchall()

    return [dict(fila) for fila in filas]


def obtener_criterios_precedente(conexion: sqlite3.Connection, documento_id: int) -> list[dict[str, Any]]:
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
