import json
import sqlite3
from pathlib import Path
from typing import Any

from config import CARPETA_RESULTADOS, RUTA_BASE_DATOS, asegurar_carpetas
from validacion import validar_resultado


def conectar() -> sqlite3.Connection:
    asegurar_carpetas()
    conexion = sqlite3.connect(RUTA_BASE_DATOS)
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_tablas(conexion: sqlite3.Connection) -> None:
    conexion.executescript(
        """
        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_documento TEXT UNIQUE NOT NULL,
            archivo_json TEXT NOT NULL,
            fecha_resolucion TEXT,
            resultado TEXT,
            debe_ingresar_al_seia INTEGER,
            resumen_ejecutivo TEXT
        );

        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento_id INTEGER NOT NULL,
            nombre_proyecto TEXT,
            region TEXT,
            comuna TEXT,
            tipo_proyecto TEXT,
            subtipo_proyecto TEXT,
            proponente TEXT,
            FOREIGN KEY (documento_id) REFERENCES documentos (id)
        );

        CREATE TABLE IF NOT EXISTS criterios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento_id INTEGER NOT NULL,
            criterio TEXT,
            explicacion TEXT,
            fragmento_respaldo TEXT,
            nivel_confianza TEXT,
            FOREIGN KEY (documento_id) REFERENCES documentos (id)
        );

        CREATE TABLE IF NOT EXISTS normativa_citada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento_id INTEGER NOT NULL,
            normativa TEXT,
            FOREIGN KEY (documento_id) REFERENCES documentos (id)
        );

        CREATE TABLE IF NOT EXISTS palabras_clave (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento_id INTEGER NOT NULL,
            palabra_clave TEXT,
            FOREIGN KEY (documento_id) REFERENCES documentos (id)
        );

        CREATE INDEX IF NOT EXISTS idx_documentos_fecha
            ON documentos (fecha_resolucion);
        CREATE INDEX IF NOT EXISTS idx_proyectos_region
            ON proyectos (region);
        CREATE INDEX IF NOT EXISTS idx_proyectos_tipo
            ON proyectos (tipo_proyecto);
        CREATE INDEX IF NOT EXISTS idx_proyectos_subtipo
            ON proyectos (subtipo_proyecto);
        CREATE INDEX IF NOT EXISTS idx_criterios_documento
            ON criterios (documento_id);
        CREATE INDEX IF NOT EXISTS idx_normativa_documento
            ON normativa_citada (documento_id);
        CREATE INDEX IF NOT EXISTS idx_palabras_documento
            ON palabras_clave (documento_id);
        """
    )
    conexion.commit()


def _valor_booleano_sql(valor: bool | None) -> int | None:
    if valor is True:
        return 1
    if valor is False:
        return 0
    return None


def cargar_resultado(conexion: sqlite3.Connection, ruta_json: Path, resultado: dict[str, Any]) -> None:
    id_documento = resultado["id_documento"] or ruta_json.stem

    conexion.execute("DELETE FROM documentos WHERE id_documento = ?", (id_documento,))
    conexion.commit()

    cursor = conexion.execute(
        """
        INSERT INTO documentos (
            id_documento,
            archivo_json,
            fecha_resolucion,
            resultado,
            debe_ingresar_al_seia,
            resumen_ejecutivo
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            id_documento,
            ruta_json.name,
            resultado.get("fecha_resolucion"),
            resultado.get("resultado"),
            _valor_booleano_sql(resultado.get("debe_ingresar_al_seia")),
            resultado.get("resumen_ejecutivo"),
        ),
    )
    documento_id = cursor.lastrowid

    conexion.execute(
        """
        INSERT INTO proyectos (
            documento_id,
            nombre_proyecto,
            region,
            comuna,
            tipo_proyecto,
            subtipo_proyecto,
            proponente
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            documento_id,
            resultado.get("nombre_proyecto"),
            resultado.get("region"),
            resultado.get("comuna"),
            resultado.get("tipo_proyecto"),
            resultado.get("subtipo_proyecto"),
            resultado.get("proponente"),
        ),
    )

    for criterio in resultado.get("criterios_sea", []):
        conexion.execute(
            """
            INSERT INTO criterios (
                documento_id,
                criterio,
                explicacion,
                fragmento_respaldo,
                nivel_confianza
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                documento_id,
                criterio.get("criterio"),
                criterio.get("explicacion"),
                criterio.get("fragmento_respaldo"),
                criterio.get("nivel_confianza"),
            ),
        )

    for normativa in resultado.get("normativa_citada", []):
        conexion.execute(
            "INSERT INTO normativa_citada (documento_id, normativa) VALUES (?, ?)",
            (documento_id, str(normativa)),
        )

    for palabra in resultado.get("palabras_clave", []):
        conexion.execute(
            "INSERT INTO palabras_clave (documento_id, palabra_clave) VALUES (?, ?)",
            (documento_id, str(palabra)),
        )

    conexion.commit()


def cargar_json_a_sqlite() -> None:
    asegurar_carpetas()
    archivos_json = sorted(CARPETA_RESULTADOS.glob("*.json"))

    if not archivos_json:
        print(f"No hay JSON en {CARPETA_RESULTADOS}")
        print("Ejecuta primero: python src/analizar_textos.py")
        return

    with conectar() as conexion:
        crear_tablas(conexion)

        for ruta_json in archivos_json:
            print(f"Cargando JSON a SQLite: {ruta_json.name}")
            resultado = json.loads(ruta_json.read_text(encoding="utf-8"))
            errores = validar_resultado(resultado)

            if errores:
                print("  Se omite por errores de validacion:")
                for error in errores:
                    print(f"  - {error}")
                continue

            cargar_resultado(conexion, ruta_json, resultado)
            print("  Cargado correctamente.")

    print(f"Base de datos lista en: {RUTA_BASE_DATOS}")


if __name__ == "__main__":
    cargar_json_a_sqlite()
