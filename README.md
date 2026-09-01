# ButterflyDataset

Construcción del corpus de mariposas del Mariposario del Tolima: descarga desde
iNaturalist, inventario y partición reproducible.

Este repositorio **produce el corpus; no entrena nada**. El repositorio de modelado
([InsectsMobileNet](https://github.com/CCSandoval/InsectsMobileNet)) consume sus
artefactos. La dependencia va en un solo sentido.

## Artefactos

| Ruta                     | Qué es                                                       | Versionado |
| ------------------------ | ------------------------------------------------------------ | ---------- |
| `Insectos/<especie>/`    | imágenes descargadas                                         | no         |
| `metadata.csv`           | una fila por foto: licencia, atribución, observación, sha256 | sí         |
| `splits/semilla<N>.json` | qué archivo fue a train, test o validate                     | sí         |

Las imágenes no van a git: son obras de terceros y pesan GB. Lo que se versiona es
la receta —`metadata.csv`— que permite reconstruirlas y verificar los bytes.

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

```bash
python scraping.py                 # descarga
jupyter lab 01_corpus_y_dataset.ipynb   # inventario y publicación de la partición
```

## Pendiente

- Reconciliación taxonómica: sinónimos → identificadores estables de iNat y GBIF
- Calidad: desenfoque (varianza del Laplaciano), exposición, resolución
- Deduplicación de casi-duplicados de la misma observación
- Recorte del espécimen

Sobre la deduplicación: varias fotos de una observación son el mismo individuo con
segundos de diferencia. Al partir por imagen caen en entrenamiento y prueba a la
vez — medido, el **22,7 %** de las imágenes de prueba tenía una hermana en
entrenamiento. Se corrige eliminando los casi-duplicados, no agrupando por
observación: así las fotos genuinamente distintas, dorsal y ventral, sobreviven.
# ButterflyDataset
