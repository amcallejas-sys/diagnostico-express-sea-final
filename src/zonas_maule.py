import unicodedata


COMUNAS_MAULE = [
    "No sabe / No indicada",
    "Cauquenes",
    "Chanco",
    "Colbun",
    "Constitucion",
    "Curepto",
    "Curico",
    "Empedrado",
    "Hualañe",
    "Licanten",
    "Linares",
    "Longavi",
    "Maule",
    "Molina",
    "Parral",
    "Pelarco",
    "Pelluhue",
    "Pencahue",
    "Rauco",
    "Retiro",
    "Rio Claro",
    "Romeral",
    "Sagrada Familia",
    "San Clemente",
    "San Javier",
    "San Rafael",
    "Talca",
    "Teno",
    "Vichuquen",
    "Villa Alegre",
    "Yerbas Buenas",
]


COMUNAS_MAULE_CON_PDA = {
    "talca": "PDA Talca-Maule, D.S. N 49/2016 MMA",
    "maule": "PDA Talca-Maule, D.S. N 49/2016 MMA",
    "curico": "PDA Valle Central Provincia de Curico, D.S. N 44/2017 MMA",
    "teno": "PDA Valle Central Provincia de Curico, D.S. N 44/2017 MMA",
    "romeral": "PDA Valle Central Provincia de Curico, D.S. N 44/2017 MMA",
    "rauco": "PDA Valle Central Provincia de Curico, D.S. N 44/2017 MMA",
    "molina": "PDA Valle Central Provincia de Curico, D.S. N 44/2017 MMA",
    "sagrada familia": "PDA Valle Central Provincia de Curico, D.S. N 44/2017 MMA",
}


def normalizar_texto_simple(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(caracter for caracter in texto if unicodedata.category(caracter) != "Mn")
    return " ".join(texto.lower().strip().split())


def obtener_pda_maule_por_comuna(comuna: str, region: str) -> str | None:
    region_normalizada = normalizar_texto_simple(region)
    if "maule" not in region_normalizada:
        return None
    return COMUNAS_MAULE_CON_PDA.get(normalizar_texto_simple(comuna))
