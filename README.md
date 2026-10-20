# ButterflyDataset

Construcción del corpus de mariposas del Tolima: 100 especies con presencia registrada en el departamento, descargadas de iNaturalist, con inventario y partición reproducibles.

Este repositorio **produce el corpus; no entrena nada**. El repositorio de modelado ([ButterflyModeling](https://github.com/CCSandoval/ButterflyModeling)) consume sus artefactos.

El corpus ya construido está depositado en Zenodo con DOI [10.5281/zenodo.23502753](https://doi.org/10.5281/zenodo.23502753): los 25 306 recortes, el manifiesto con la partición, la procedencia por foto y la auditoría. Bajarlo de ahí evita volver a descargar de iNaturalist. Ese DOI es el de esta versión, que es el que cita el artículo.

## Artefactos

| Ruta                        | Qué es                                                        | Rastreado en Git |
| --------------------------- | ------------------------------------------------------------- | ---------- |
| `Insectos/<especie>/`       | imágenes descargadas de iNaturalist                            | no         |
| `procesado/<especie>/`      | recortes cuadrados de 448×448, ya filtrados                    | no         |
| `cache/`                    | detecciones y métricas, para reanudar una corrida              | no         |
| `species_list.json`         | las 100 especies, con su `taxon_id` verificado                 | sí         |
| `metadata.csv`              | una fila por foto: licencia, atribución, observación, sha256   | sí         |
| `auditoria.csv`             | una fila por candidata: caja, métricas, veredicto y split      | sí         |
| `manifiesto.json`           | parámetros, conteos y reparto del corpus                       | sí         |
| `fichas/` y `fichas.json`   | una imagen y una ficha por especie, para el prototipo          | sí         |

Las imágenes no van a git: son obras de terceros y pesan GB. Lo que se versiona es la estrategia para reproducir el corpus (`metadata.csv` y `auditoria.csv`).

## Preprocesamiento

`02_preprocesamiento.ipynb` convierte el corpus crudo en el dataset de entrenamiento:

1. **Recorte.** YOLO-World localiza la mariposa —COCO no tiene clase de mariposa, así que un YOLO estándar no sirve— y la caja se convierte en un cuadrado con margen. Ante un borde el cuadrado se desplaza en vez de rellenarse: un borde negro sería una textura sintética que la red aprendería como atajo.
2. **Calidad.** Varianza del Laplaciano para el desenfoque, medida sobre el recorte ya normalizado a 384×384 para que el umbral no dependa del tamaño; mediana del canal V y fracción de píxeles quemados o negros para la exposición; lado mínimo del recorte para no ampliar detalle inexistente.
3. **Duplicados.** pHash y dHash sobre el recorte, comparados solo dentro de cada especie. El `observation_id` sirve de conjunto de validación: el valle entre las distancias dentro de una observación y las de observaciones distintas es lo que fija el umbral. De cada grupo se conserva la foto más nítida.

Cada foto sale con un veredicto y un motivo excluyente, y el notebook publica la tabla de conteos por motivo, las rejillas de ejemplos de cada descarte y la fuga antes y después.

## Solo licencias abiertas

Se aceptan `cc0`, `cc-by`, `cc-by-nc`, `cc-by-sa` y `cc-by-nc-sa`. La API de iNaturalist filtra del lado del servidor.

Quedan fuera dos casos:

- **Sin licencia declarada** (todos los derechos reservados).
- **`cc-by-nc-nd`**: el ND prohíbe obras derivadas, (en este caso, recortar y aumentar imágenes para entrenar).

## Uso

Los notebooks se corren en orden y `corpus/` solo contiene las rutas del repositorio y la lectura y escritura de sus CSV; la lógica vive en los notebooks.

| notebook | qué hace | cuándo correrlo |
|---|---|---|
| `00_especies` | describe `species_list.json` | siempre que exista el archivo |
| `01_scraping` | descarga las 34 804 fotos de `metadata.csv` | para reconstruir el corpus |
| `02_preprocesamiento` | recorta desde las cajas de `auditoria.csv` | después de `01` |
| `03_eda` | describe el corpus | opcional |
| `04_fichas` | fichas de especie para el prototipo | Ya pobladas, no es necesario |

Los tres primeros arrancan por defecto en modo **describir o reconstruir lo publicado**. Cada uno tiene arriba la bandera que lo cambia (`HAY_LISTA` se deduce si existe el archivo `species_list.json`, `RECONSTRUIR` se pone a mano) y se toca para **construir un corpus nuevo**, que daría otras cifras y dejaría de corresponder con los modelos ya entrenados.

`metadata.csv` trae la URL y el `sha256` de cada foto, y `auditoria.csv` la caja con que se recortó. La auditoría importa porque la detección **no** es reproducible (con otra versión de los pesos de YOLO-World hay diferencias en los resultados), así que recortar con las cajas guardadas es lo que hace que el corpus salga igual, y de paso ahorra tiempo en detección.

La detección solo hace falta para construir un corpus nuevo, y necesita `ultralytics`, que el resto del repositorio no usa.
