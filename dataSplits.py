"""Inventario del corpus y partición train/test/validate."""

import json
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent
CORPUS = BASE / "Insectos"
SPLITS_DIR = BASE / "splits"

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


def repartir(especies, semilla, corpus=CORPUS):
    """Combina la semilla con el nombre de la especie, de modo que agregar
    especies no altera el reparto de las que ya estaban."""
    reparto = {}
    for especie in sorted(especies):
        archivos = imagenesDe(especie, corpus)
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


def publicar(reparto, semilla, destino=SPLITS_DIR):
    """Escribe el reparto: es lo que consume el repositorio de modelado."""
    destino.mkdir(exist_ok=True)
    ruta = destino / f"semilla{semilla}.json"
    ruta.write_text(json.dumps({
        "semilla": semilla,
        "num_clases": len(reparto),
        "conteos": contar(reparto),
        "reparto": reparto,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    return ruta
