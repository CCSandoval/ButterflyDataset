# ButterflyDataset

Construcción del corpus de mariposas del Mariposario del Tolima: descarga desde
iNaturalist, inventario y partición reproducible.

Este repositorio **produce el corpus; no entrena nada**. El repositorio de modelado
([InsectsMobileNet](https://github.com/CCSandoval/InsectsMobileNet)) consume sus
artefactos. La dependencia va en un solo sentido.

## Artefactos

| Ruta                               | Qué es                                                        | Versionado |
| ---------------------------------- | ------------------------------------------------------------- | ---------- |
| `Insectos/<especie>/`              | imágenes descargadas                                          | no         |
| `Dataset/<split>/<especie>/`       | recortes cuadrados 448×448, ya filtrados y repartidos         | no         |
| `metadata.csv`                     | una fila por foto: licencia, atribución, observación, sha256   | sí         |
| `auditoria.csv`                    | una fila por foto: recorte, métricas, veredicto y motivo       | sí         |
| `splits/semilla<N>.json`           | qué archivo fue a train, test o validate                       | sí         |
| `splits/procesado_semilla<N>.json` | lo mismo, sobre las imágenes que sobrevivieron al filtro       | sí         |

Las imágenes no van a git: son obras de terceros y pesan GB. Lo que se versiona es
la receta —`metadata.csv` y `auditoria.csv`— que permite reconstruirlas, verificar los
bytes y explicar por qué se descartó cada foto.

## Preprocesamiento

`02_preprocesamiento.ipynb` convierte el corpus crudo en el dataset de entrenamiento:

1. **Recorte.** YOLO-World localiza la mariposa —COCO no tiene clase de mariposa, así que
   un YOLO estándar no sirve— y la caja se convierte en un cuadrado con margen. Ante un
   borde el cuadrado se desplaza en vez de rellenarse: un borde negro sería una textura
   sintética que la red aprendería como atajo.
2. **Calidad.** Varianza del Laplaciano para el desenfoque, medida sobre el recorte ya
   normalizado a 384×384 para que el umbral no dependa del tamaño; mediana del canal V y
   fracción de píxeles quemados o negros para la exposición; lado mínimo del recorte para
   no ampliar detalle inexistente.
3. **Duplicados.** pHash y dHash sobre el recorte, comparados solo dentro de cada especie.
   El `observation_id` sirve de conjunto de validación: el valle entre las distancias
   dentro de una observación y las de observaciones distintas es lo que fija el umbral. De
   cada grupo se conserva la foto más nítida.

Cada foto sale con un veredicto y un motivo excluyente, y el notebook publica la tabla de
conteos por motivo, las rejillas de ejemplos de cada descarte y la fuga antes y después.

## Solo licencias abiertas

Se aceptan `cc0`, `cc-by`, `cc-by-nc`, `cc-by-sa` y `cc-by-nc-sa`. La API de
iNaturalist filtra del lado del servidor.

Quedan fuera dos casos:

- **Sin licencia declarada** (todos los derechos reservados). En el corpus previo
  eran el **29,6 %**; iNaturalist las sirve desde `static.inaturalist.org` en vez
  del bucket `inaturalist-open-data`.
- **`cc-by-nc-nd`**: el ND prohíbe obras derivadas, y recortar y aumentar imágenes
  para entrenar es exactamente eso.

## La taxonomía hay que reconciliarla

`species_list.json` usa nombres que en varios casos ya son sinónimos. iNaturalist
reclasificó al menos doce: _Vettius fantasos_ → _Troyus fantasos_, _Pyrgus adepta_
→ _Burnsius adepta_, _Urbanus procne_ → _Spicauda procne_.

iNaturalist y GBIF además no coinciden, y emparejar por nombre produce errores
silenciosos:

| Consulta          | GBIF devuelve                    | Riesgo                   |
| ----------------- | -------------------------------- | ------------------------ |
| `Pyrgus adepta`   | `Pyrgus communis`, 2104 imágenes | otra especie             |
| `Cissia confusa`  | `Senna cruckshanksii`            | una planta               |
| `Spicauda procne` | sinónimo de `Urbanus procne`     | dirección opuesta a iNat |

Por eso conviene descargar por identificador de taxón verificado, no por nombre.

## Uso

Todo el código Python vive en el paquete `corpus/`; los notebooks lo orquestan.

```bash
python -m corpus.scraping               # descarga
jupyter lab 01_corpus_y_dataset.ipynb   # inventario y publicación de la partición
jupyter lab 02_preprocesamiento.ipynb   # recorte, calidad, deduplicación y dataset en disco
```

La detección necesita `ultralytics`, que el resto del repositorio no usa.

## Pendiente

- Reconciliación taxonómica: sinónimos → identificadores estables de iNat y GBIF
- Calibrar los umbrales de calidad y de distancia contra el corpus completo: los que hay en
  `corpus/calidad.py` y `corpus/duplicados.py` son un punto de partida, y el notebook 02
  está montado para ajustarlos a la vista de las rejillas de frontera
- Decidir qué hacer con las fotos sin detección, que hoy se descartan
