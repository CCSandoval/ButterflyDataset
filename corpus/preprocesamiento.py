"""Veredictos por foto, auditoría y escritura del dataset procesado."""

from collections import defaultdict

import cv2

from . import AUDITORIA, DATASET, IMAGENES, METADATA, escribirCsv, leerCsv
from . import duplicados
from .calidad import LADO_SALIDA, UMBRALES, redimensionar
from .dataSplits import SPLITS
from .deteccion import recortar

MINIMO_POR_ESPECIE = 40
CALIDAD_JPEG = 92

# Excluyentes y en cascada: el primero que aplica gana, de modo que la tabla de
# conteos suma el corpus entero sin doble contabilidad. La deduplicación va al
# final para que el representante que se conserva ya haya pasado los filtros.
MOTIVOS = ("sin_deteccion", "recorte_pequeno", "desenfocada", "sobreexpuesta",
           "subexpuesta", "casi_duplicado", "especie_escasa", "aceptada")

COLUMNAS = ["especie", "photo_id", "observation_id", "archivo", "ancho", "alto",
            "x1", "y1", "x2", "y2", "confianza", "cuadradoX", "cuadradoY",
            "ladoOriginal", "nitidez", "brillo", "fracSaturados", "fracNegros",
            "phash", "dhash", "grupo", "veredicto", "motivo", "split"]


def leerMetadatos():
    return leerCsv(METADATA)


def motivoDeCalidad(fila):
    """Primer motivo de descarte por calidad, o None si la foto pasa."""
    if float(fila["ladoOriginal"]) < UMBRALES["ladoOriginal"]:
        return "recorte_pequeno"
    if float(fila["nitidez"]) < UMBRALES["nitidez"]:
        return "desenfocada"
    if float(fila["fracSaturados"]) > UMBRALES["fracSaturados"]:
        return "sobreexpuesta"
    if float(fila["fracNegros"]) > UMBRALES["fracNegros"]:
        return "subexpuesta"
    return None


def construirAuditoria(detecciones, metricas):
    """Une las tres pasadas y aplica la cascada de motivos. Una fila por foto."""
    porId = {m["photo_id"]: m for m in metricas}
    observacionDe = {m["photo_id"]: m["observation_id"] for m in leerMetadatos()}

    filas = []
    for deteccion in detecciones:
        metrica = porId.get(deteccion["photo_id"])
        fila = dict.fromkeys(COLUMNAS, "")
        fila.update(deteccion)
        fila["observation_id"] = observacionDe.get(deteccion["photo_id"], "")
        fila.update(metrica or {})
        fila["motivo"] = "sin_deteccion" if metrica is None else motivoDeCalidad(metrica)
        filas.append(fila)

    marcarDuplicados(filas)
    marcarEscasas(filas)
    for fila in filas:
        fila["motivo"] = fila["motivo"] or "aceptada"
        fila["veredicto"] = "aceptada" if fila["motivo"] == "aceptada" else "descartada"
    return filas


def marcarDuplicados(filas):
    """Agrupa las que sobrevivieron a calidad y descarta todo menos la más nítida."""
    vivas = [f for f in filas if not f["motivo"]]
    if not vivas:
        return
    porId = {f["photo_id"]: f for f in vivas}
    nitidezPorFoto = {i: float(f["nitidez"]) for i, f in porId.items()}
    grupos = duplicados.agrupar(list(porId), duplicados.paresCercanos(vivas))

    for numero, grupo in enumerate(sorted(grupos), start=1):
        elegido = duplicados.elegirRepresentante(grupo, nitidezPorFoto)
        for photoId in grupo:
            porId[photoId]["grupo"] = numero
            if photoId != elegido:
                porId[photoId]["motivo"] = "casi_duplicado"


def marcarEscasas(filas):
    """Una especie que no llega al mínimo no puede repartirse 70/20/10 con sentido."""
    vivas = defaultdict(int)
    for fila in filas:
        if not fila["motivo"]:
            vivas[fila["especie"]] += 1
    escasas = {e for e, n in vivas.items() if n < MINIMO_POR_ESPECIE}
    for fila in filas:
        if not fila["motivo"] and fila["especie"] in escasas:
            fila["motivo"] = "especie_escasa"


def resumenPorMotivo(auditoria):
    conteo = defaultdict(int)
    for fila in auditoria:
        conteo[fila["motivo"]] += 1
    return [{"motivo": m, "imagenes": conteo[m],
             "porcentaje": round(100 * conteo[m] / len(auditoria), 2)}
            for m in MOTIVOS if conteo[m]]


def aceptadasPorEspecie(auditoria):
    porEspecie = defaultdict(list)
    for fila in auditoria:
        if fila["veredicto"] == "aceptada":
            porEspecie[fila["especie"]].append(fila["archivo"])
    return dict(porEspecie)


def anotarSplit(auditoria, reparto):
    ubicacion = {archivo: split for especie in reparto for split in SPLITS
                 for archivo in reparto[especie][split]}
    for fila in auditoria:
        fila["split"] = ubicacion.get(fila["archivo"], "")
    return auditoria


def escribirAuditoria(auditoria):
    print(f"→ {escribirCsv(AUDITORIA, auditoria, COLUMNAS)}")


def escribirDataset(auditoria):
    """Recorta, redimensiona y escribe Dataset/<split>/<especie>/<archivo>."""
    escritas = defaultdict(int)
    for fila in auditoria:
        if fila["veredicto"] != "aceptada" or not fila["split"]:
            continue
        imagen = cv2.imread(str(IMAGENES / fila["especie"] / fila["archivo"]))
        if imagen is None:
            continue
        recorte = recortar(imagen, int(fila["cuadradoX"]), int(fila["cuadradoY"]),
                           int(fila["ladoOriginal"]))
        carpeta = DATASET / fila["split"] / fila["especie"]
        carpeta.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(carpeta / fila["archivo"]), redimensionar(recorte, LADO_SALIDA),
                    [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPEG])
        escritas[fila["split"]] += 1
    print(f"→ {DATASET} · " + " · ".join(f"{s} {escritas[s]}" for s in SPLITS))
    return dict(escritas)


def medirFuga(reparto):
    """Porcentaje de imágenes de test cuya observación también aparece en train."""
    observacionDe = {m["archivo"]: m["observation_id"] for m in leerMetadatos()}
    enTrain = {observacionDe.get(a) for especie in reparto
               for a in reparto[especie]["train"]}
    prueba = [a for especie in reparto for a in reparto[especie]["test"]]
    filtradas = sum(1 for a in prueba if observacionDe.get(a) in enTrain)
    return 100 * filtradas / len(prueba) if prueba else 0.0
