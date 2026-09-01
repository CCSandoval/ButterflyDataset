"""Descarga desde iNaturalist, solo licencias abiertas."""

import csv
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
CORPUS = BASE / "Insectos"
METADATA = BASE / "metadata.csv"
LISTA_ESPECIES = BASE / "species_list.json"

API = "https://api.inaturalist.org/v1"
LICENCIAS = "cc0,cc-by,cc-by-nc,cc-by-sa,cc-by-nc-sa"
POR_ESPECIE = 200
PAUSA = 0.25

COLUMNAS = ["especie", "taxon_id", "observation_id", "photo_id",
            "licencia", "atribucion", "url", "archivo", "sha256"]


def nombreCorto(entrada):
    """'Anartia amathea (Linnaeus, 1758)' -> 'Anartia amathea'."""
    limpio = re.sub(r"\(.*?\)|,.*$", "", entrada)
    return " ".join(limpio.split()[:2])


def carpetaDe(nombre):
    return nombre.lower().replace(" ", "_")


def pedir(sesion, ruta, params):
    respuesta = sesion.get(f"{API}/{ruta}", params=params, timeout=30)
    respuesta.raise_for_status()
    return respuesta.json()


def buscarTaxon(sesion, nombre):
    resultados = pedir(sesion, "taxa", {"q": nombre, "rank": "species",
                                        "per_page": 1, "is_active": "true"})["results"]
    return resultados[0] if resultados else None


def fotosDe(sesion, taxonId, maximo):
    vistas, pagina = set(), 1
    while len(vistas) < maximo:
        print(f"    página {pagina} (fotos vistas: {len(vistas)}/{maximo})")
        observaciones = pedir(sesion, "observations", {
            "taxon_id": taxonId, "quality_grade": "research", "photos": "true",
            "photo_license": LICENCIAS, "order_by": "id", "order": "asc",
            "per_page": 200, "page": pagina,
        })["results"]
        if not observaciones:
            print("    sin más observaciones")
            return
        for observacion in observaciones:
            for foto in observacion["photos"]:
                if foto["id"] in vistas or not foto.get("license_code"):
                    continue
                vistas.add(foto["id"])
                yield observacion["id"], foto
                if len(vistas) >= maximo:
                    return
        pagina += 1


def descargar(sesion, url, destino):
    respuesta = sesion.get(url, timeout=45)
    respuesta.raise_for_status()
    destino.write_bytes(respuesta.content)
    return hashlib.sha256(respuesta.content).hexdigest()


def scrapear(porEspecie=POR_ESPECIE):
    print(f"Leyendo especies de {LISTA_ESPECIES.name}")
    especies = json.loads(LISTA_ESPECIES.read_text())["species"]
    print(f"{len(especies)} especies en la lista, máximo {porEspecie} fotos por especie")

    sesion = requests.Session()
    sesion.headers["User-Agent"] = "butterfly-dataset/1.0"

    # Acumula sobre lo ya descargado; escribir por tandas borró la procedencia antes.
    filas = list(csv.DictReader(METADATA.open())) if METADATA.exists() else []
    conocidas = {fila["photo_id"] for fila in filas}
    print(f"{len(filas)} fotos ya registradas en {METADATA.name}")

    for numero, entrada in enumerate(especies, start=1):
        if "sp." in entrada["name"]:
            print(f"[{numero}/{len(especies)}] {entrada['name']}: omitida (sp.)")
            continue
        nombre = nombreCorto(entrada["name"])
        print(f"[{numero}/{len(especies)}] {nombre}: buscando taxón")
        taxon = buscarTaxon(sesion, nombre)
        time.sleep(PAUSA)
        if taxon is None:
            print(f"{nombre}: sin taxón")
            continue
        print(f"  taxón {taxon['id']} ({taxon['name']})")

        carpeta = CORPUS / carpetaDe(nombre)
        carpeta.mkdir(parents=True, exist_ok=True)
        print(f"  carpeta {carpeta.name} lista")
        nuevas = 0

        for observacionId, foto in fotosDe(sesion, taxon["id"], porEspecie):
            if str(foto["id"]) in conocidas:
                continue
            url = foto["url"].replace("square", "large")
            archivo = carpeta / f"{carpetaDe(nombre)}_{foto['id']}.jpg"
            print(f"    descargando foto #{nuevas + 1}")
            filas.append({
                "especie": carpetaDe(nombre),
                "taxon_id": taxon["id"],
                "observation_id": observacionId,
                "photo_id": foto["id"],
                "licencia": foto["license_code"],
                "atribucion": foto.get("attribution", ""),
                "url": url,
                "archivo": archivo.name,
                "sha256": descargar(sesion, url, archivo),
            })
            nuevas += 1
            time.sleep(PAUSA)

        print(f"{nombre} ({taxon['name']}): +{nuevas}")

    print(f"Escribiendo {METADATA.name}")
    with METADATA.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"{len(filas)} fotos en {METADATA.name}")

    conteo = Counter(fila["especie"] for fila in filas)
    print(f"\nResumen: {len(conteo)} especies")
    for especie, total in sorted(conteo.items()):
        print(f"  {especie}: {total} imágenes")


if __name__ == "__main__":
    scrapear()
