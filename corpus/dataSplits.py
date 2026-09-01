"""Inventario del corpus y partición train/test/validate."""

import json
import random

from . import IMAGENES as CORPUS, SPLITS_DIR

EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}
SPLITS = ("train", "test", "validate")
PROPORCIONES = (0.70, 0.20)


def imagenesDe(especie, corpus=CORPUS):
    return sorted(
        p.name for p in (corpus / especie).iterdir()
        if p.suffix.lower() in EXTENSIONES
    )


def inventariar(corpus=CORPUS):
    return {
        carpeta.name: len(imagenesDe(carpeta.name, corpus))
        for carpeta in sorted(corpus.iterdir())
        if carpeta.is_dir()
    }


def repartir(especies, semilla, corpus=CORPUS, archivosPorEspecie=None):
    """Combina la semilla con el nombre de la especie, de modo que agregar
    especies no altera el reparto de las que ya estaban.

    Con archivosPorEspecie reparte una lista en memoria (las imágenes que
    sobreviven al preprocesamiento) en vez de leer el disco."""
    reparto = {}
    for especie in sorted(especies):
        archivos = (sorted(archivosPorEspecie[especie]) if archivosPorEspecie is not None
                    else imagenesDe(especie, corpus))
        mezclados = random.Random(f"{semilla}:{especie}").sample(archivos, len(archivos))
        corte1 = round(len(archivos) * PROPORCIONES[0])
        corte2 = corte1 + round(len(archivos) * PROPORCIONES[1])
        reparto[especie] = {
            "train": mezclados[:corte1],
            "test": mezclados[corte1:corte2],
            "validate": mezclados[corte2:],
        }
    return reparto


def contar(reparto):
    conteos = {s: sum(len(r[s]) for r in reparto.values()) for s in SPLITS}
    conteos["total"] = sum(conteos.values())
    return conteos


def publicar(reparto, semilla, nombre=None):
    """Escribe el reparto: es lo que consume el repositorio de modelado."""
    SPLITS_DIR.mkdir(exist_ok=True)
    ruta = SPLITS_DIR / (nombre or f"semilla{semilla}.json")
    ruta.write_text(json.dumps({
        "semilla": semilla,
        "num_clases": len(reparto),
        "conteos": contar(reparto),
        "reparto": reparto,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    return ruta
