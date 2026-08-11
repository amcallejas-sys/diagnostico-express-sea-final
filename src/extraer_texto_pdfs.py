from pathlib import Path

import pdfplumber

from config import CARPETA_PDFS, CARPETA_TEXTOS, asegurar_carpetas


def extraer_texto_pdf(ruta_pdf: Path) -> str:
    """Extrae texto seleccionable desde un PDF usando pdfplumber."""
    textos_paginas: list[str] = []

    with pdfplumber.open(ruta_pdf) as pdf:
        for numero_pagina, pagina in enumerate(pdf.pages, start=1):
            texto_pagina = pagina.extract_text() or ""
            if texto_pagina.strip():
                textos_paginas.append(f"\n\n--- Pagina {numero_pagina} ---\n{texto_pagina}")

    return "\n".join(textos_paginas).strip()


def procesar_pdfs() -> None:
    asegurar_carpetas()
    archivos_pdf = sorted(CARPETA_PDFS.glob("*.pdf"))

    if not archivos_pdf:
        print(f"No hay PDF en {CARPETA_PDFS}")
        print("Copia primero entre 10 y 20 resoluciones PDF en esa carpeta.")
        return

    for ruta_pdf in archivos_pdf:
        print(f"Procesando PDF: {ruta_pdf.name}")
        ruta_salida = CARPETA_TEXTOS / f"{ruta_pdf.stem}.txt"

        try:
            texto = extraer_texto_pdf(ruta_pdf)
        except Exception as error:
            print(f"  Error al leer {ruta_pdf.name}: {error}")
            continue

        if not texto:
            print("  No se encontro texto seleccionable. Puede requerir OCR.")
            continue

        ruta_salida.write_text(texto, encoding="utf-8")
        print(f"  Texto guardado en: {ruta_salida}")

    print("Extraccion terminada.")


if __name__ == "__main__":
    procesar_pdfs()
