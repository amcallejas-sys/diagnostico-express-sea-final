from pathlib import Path


RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
CARPETA_DATA = RAIZ_PROYECTO / "data"
CARPETA_PDFS = CARPETA_DATA / "pdfs"
CARPETA_TEXTOS = CARPETA_DATA / "textos"
CARPETA_RESULTADOS = CARPETA_DATA / "resultados"
RUTA_BASE_DATOS = CARPETA_DATA / "diagnostico_express.sqlite"


def asegurar_carpetas() -> None:
    """Crea las carpetas necesarias si todavia no existen."""
    for carpeta in [CARPETA_PDFS, CARPETA_TEXTOS, CARPETA_RESULTADOS]:
        carpeta.mkdir(parents=True, exist_ok=True)
