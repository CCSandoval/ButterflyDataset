"""Rutas del repositorio y lectura y escritura de sus CSV."""

import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
IMAGENES = BASE / "Insectos"
CACHE = BASE / "cache"
PESOS = BASE / "pesos"
VERSIONES_DIR = BASE / "versiones"
PROCESADO_DIR = BASE / "procesado"
FIGURAS = BASE / "figuras"

METADATA = BASE / "metadata.csv"
LISTA_ESPECIES = BASE / "species_list.json"


def leerCsv(ruta):
    if not Path(ruta).exists():
        return []
    return list(csv.DictReader(Path(ruta).open(encoding="utf-8")))


def escribirCsv(ruta, filas, columnas):
    """Reescribe el archivo entero: escribir por tandas ya borró la procedencia una vez."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta
