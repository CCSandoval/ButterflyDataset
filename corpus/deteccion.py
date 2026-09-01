"""Detección de la mariposa con YOLO-World y geometría del recorte cuadrado."""

import time

from . import CACHE, IMAGENES, PESOS, escribirCsv, leerCsv

DETECCIONES = CACHE / "detecciones.csv"
MODELO = PESOS / "yolov8s-worldv2.pt"

# La cadena vacía es un sumidero de fondo: sin ella el modelo deja sin caja 10 de
# cada 40 fotos; con ella, 1 de 40, y nunca gana.
PROMPTS = ("butterfly", "moth", "insect", "")
CLASES_VALIDAS = 3
CONFIANZA_MIN = 0.05
IMGSZ = 640
MARGEN = 0.15
AREA_MIN_RELATIVA = 0.005

COLUMNAS = ["photo_id", "especie", "archivo", "ancho", "alto",
            "x1", "y1", "x2", "y2", "confianza"]


def cargarModelo():
    """Carga YOLO-World con las clases por texto.

    set_classes descarga un codificador de CLIP de 338 MB a la carpeta de pesos
    de ultralytics, que se fija al importar; se reapunta para no acabar con dos
    carpetas de pesos en la raíz.
    """
    from ultralytics import YOLOWorld
    from ultralytics.nn import text_model

    PESOS.mkdir(exist_ok=True)
    text_model.WEIGHTS_DIR = PESOS
    modelo = YOLOWorld(str(MODELO) if MODELO.exists() else MODELO.name)
    modelo.set_classes(list(PROMPTS))
    return modelo


def mejorCaja(resultado):
    """La caja más confiable de las clases reales con área suficiente."""
    cajas = resultado.boxes
    alto, ancho = resultado.orig_shape
    mejor, mejorConfianza = None, -1.0
    for indice in range(len(cajas)):
        if int(cajas.cls[indice]) >= CLASES_VALIDAS:
            continue
        x1, y1, x2, y2 = (float(v) for v in cajas.xyxy[indice])
        if (x2 - x1) * (y2 - y1) < AREA_MIN_RELATIVA * ancho * alto:
            continue
        confianza = float(cajas.conf[indice])
        if confianza > mejorConfianza:
            mejor, mejorConfianza = (x1, y1, x2, y2), confianza
    return mejor, mejorConfianza


def photoIdDe(ruta):
    return ruta.stem.rsplit("_", 1)[-1]


def rutasDelCorpus():
    return [p for carpeta in sorted(IMAGENES.iterdir()) if carpeta.is_dir()
            for p in sorted(carpeta.glob("*.jpg"))]


def detectarLote(modelo, rutas):
    resultados = modelo.predict([str(r) for r in rutas], imgsz=IMGSZ,
                                conf=CONFIANZA_MIN, verbose=False)
    filas = []
    for ruta, resultado in zip(rutas, resultados):
        alto, ancho = resultado.orig_shape
        caja, confianza = mejorCaja(resultado)
        x1, y1, x2, y2 = caja if caja else ("", "", "", "")
        filas.append({
            "photo_id": photoIdDe(ruta), "especie": ruta.parent.name,
            "archivo": ruta.name, "ancho": ancho, "alto": alto,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "confianza": confianza if caja else "",
        })
    return filas


def detectarCorpus(modelo=None, tanda=64, aviso=640):
    """Pasada de YOLO sobre el corpus, reanudable: salta lo que ya está en la caché.

    Es la parte cara del pipeline, unos 0,28 s por imagen. Guarda cada `tanda`,
    así que interrumpir el kernel no pierde trabajo.
    """
    filas = leerCsv(DETECCIONES)
    conocidas = {fila["photo_id"] for fila in filas}
    pendientes = [r for r in rutasDelCorpus() if photoIdDe(r) not in conocidas]
    print(f"{len(filas)} en caché · {len(pendientes)} pendientes")
    if not pendientes:
        return filas

    modelo = modelo or cargarModelo()
    inicio = time.time()
    for comienzo in range(0, len(pendientes), tanda):
        filas.extend(detectarLote(modelo, pendientes[comienzo:comienzo + tanda]))
        escribirCsv(DETECCIONES, filas, COLUMNAS)
        hechas = min(comienzo + tanda, len(pendientes))
        if hechas % aviso < tanda or hechas == len(pendientes):
            ritmo = (time.time() - inicio) / hechas
            print(f"  {hechas}/{len(pendientes)} · {ritmo:.2f} s/img · "
                  f"faltan {ritmo * (len(pendientes) - hechas) / 60:.0f} min")
    print(f"→ {DETECCIONES}")
    return filas


def cuadradoDesde(x1, y1, x2, y2, ancho, alto):
    """Cuadrado centrado en la caja; ante un borde se desplaza, nunca se rellena.

    Un borde negro o reflejado es una textura sintética que la red aprende como
    atajo; perder unos píxeles de ala no lo es.
    """
    lado = min(max(x2 - x1, y2 - y1) * (1 + 2 * MARGEN), ancho, alto)
    x = min(max((x1 + x2) / 2 - lado / 2, 0), ancho - lado)
    y = min(max((y1 + y2) / 2 - lado / 2, 0), alto - lado)
    return int(round(x)), int(round(y)), int(round(lado))


def cuadradoDe(deteccion):
    """El cuadrado de una fila de detecciones, o None si no hubo caja."""
    if deteccion["x1"] == "":
        return None
    caja = [float(deteccion[c]) for c in ("x1", "y1", "x2", "y2")]
    return cuadradoDesde(*caja, int(deteccion["ancho"]), int(deteccion["alto"]))


def recortar(imagen, x, y, lado):
    return imagen[y:y + lado, x:x + lado]
