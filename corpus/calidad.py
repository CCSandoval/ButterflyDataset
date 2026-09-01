"""Métricas de calidad del recorte: nitidez, exposición y resolución."""

import cv2
import numpy as np

from . import CACHE, IMAGENES, escribirCsv, leerCsv
from . import duplicados
from .deteccion import cuadradoDe, recortar

METRICAS = CACHE / "metricas.csv"

LADO_METRICA = 384
LADO_SALIDA = 448

# Calibrados sobre los recortes del corpus con las rejillas de frontera del
# notebook 02. Se congelan como literales: recalcular el percentil cambiaría el
# dataset cada vez que el corpus crece.
UMBRALES = {
    "nitidez": 60.0,
    "fracSaturados": 0.06,
    "fracNegros": 0.20,
    "ladoOriginal": 200,
}

COLUMNAS = ["photo_id", "cuadradoX", "cuadradoY", "ladoOriginal", "nitidez",
            "brillo", "fracSaturados", "fracNegros", "phash", "dhash"]


def redimensionar(imagen, lado):
    interpolacion = cv2.INTER_AREA if imagen.shape[0] > lado else cv2.INTER_CUBIC
    return cv2.resize(imagen, (lado, lado), interpolation=interpolacion)


def metricasDe(recorte):
    """Nitidez, exposición y los dos hashes, sobre el recorte ya normalizado.

    Medir la varianza del Laplaciano sobre la imagen original haría el umbral
    dependiente del tamaño; a 384x384 todas se comparan en la misma escala.
    """
    normalizado = redimensionar(recorte, LADO_METRICA)
    gris = cv2.cvtColor(normalizado, cv2.COLOR_BGR2GRAY)
    valor = cv2.cvtColor(normalizado, cv2.COLOR_BGR2HSV)[:, :, 2]
    return {
        "nitidez": float(cv2.Laplacian(gris, cv2.CV_64F).var()),
        "brillo": float(np.median(valor)),
        "fracSaturados": float(np.mean(valor >= 250)),
        "fracNegros": float(np.mean(valor <= 5)),
        "phash": duplicados.aHex(duplicados.hashPerceptual(gris)),
        "dhash": duplicados.aHex(duplicados.hashDiferencial(gris)),
    }


def medirCorpus(detecciones, tanda=500):
    """Mide cada recorte, reanudable. Las que no tienen caja quedan fuera."""
    filas = leerCsv(METRICAS)
    conocidas = {fila["photo_id"] for fila in filas}
    pendientes = [d for d in detecciones if d["photo_id"] not in conocidas]
    print(f"{len(filas)} en caché · {len(pendientes)} pendientes")

    for numero, deteccion in enumerate(pendientes, start=1):
        cuadrado = cuadradoDe(deteccion)
        if cuadrado is None:
            continue
        x, y, lado = cuadrado
        imagen = cv2.imread(str(IMAGENES / deteccion["especie"] / deteccion["archivo"]))
        if imagen is None or lado < 8:
            continue
        fila = {"photo_id": deteccion["photo_id"], "cuadradoX": x, "cuadradoY": y,
                "ladoOriginal": lado}
        fila.update(metricasDe(recortar(imagen, x, y, lado)))
        filas.append(fila)
        if numero % tanda == 0:
            escribirCsv(METRICAS, filas, COLUMNAS)
            print(f"  {numero}/{len(pendientes)}")
    escribirCsv(METRICAS, filas, COLUMNAS)
    print(f"→ {METRICAS}")
    return filas


def umbralPorPercentil(serie, percentil):
    return float(np.percentile(np.asarray(serie, dtype=float), percentil))
