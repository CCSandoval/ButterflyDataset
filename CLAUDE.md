# CLAUDE.md

Guía para trabajar en este repositorio.

## Qué es este repositorio

Construye el corpus de mariposas del Mariposario del Tolima: descarga desde iNaturalist,
preprocesamiento y versionado. **No entrena modelos**; el repositorio de modelado
(ButterflyModeling) consume los artefactos y la dependencia va en un solo sentido.

Código y comentarios en español, `camelCase` para funciones, mayúsculas para constantes.
Comentarios escasos y de una línea.

## Comandos

```bash
jupyter lab 01_scraping.ipynb           # descarga desde iNaturalist
jupyter lab 02_preprocesamiento.ipynb   # detección, calidad, auditoría, recortes y versión
```

Dependencias implícitas: `requests`, `pandas`, `numpy`, `opencv-python`, `jupyter`, y
`ultralytics` solo para la detección del notebook 02.

## Arquitectura

**El código vive en los notebooks.** `corpus/__init__.py` tiene solo las rutas y la
lectura/escritura de CSV; todo lo demás está inline donde se ejecuta, para no tener que
saltar a un módulo al depurar.

- [01_scraping.ipynb](01_scraping.ipynb) — paginación de la API, descarga incremental a
  `Insectos/` y `metadata.csv`, e inventario del techo disponible por especie.
- [02_preprocesamiento.ipynb](02_preprocesamiento.ipynb) — cinco etapas que dejan su
  resultado en disco y saltan lo ya hecho, así que pueden correrse en días distintos:
  detección → métricas → auditoría → recortes → publicación de la versión.

### Artefactos

| Ruta                             | Contenido                                                   | En git |
| -------------------------------- | ----------------------------------------------------------- | ------ |
| `Insectos/`                      | imágenes descargadas                                        | no     |
| `cache/`                         | detecciones y métricas, para reanudar                       | no     |
| `pesos/`                         | YOLO-World y el codificador de CLIP                         | no     |
| `procesado/<version>/`           | recortes de cada versión más su `auditoria.csv`             | no     |
| `metadata.csv`                   | una fila por foto: licencia, atribución, observación, sha256 | sí     |
| `versiones/<nombre>.json`        | parámetros, conteos y reparto de una versión                 | sí     |

Las imágenes no van a git: son obras de terceros y pesan GB. Se versiona la receta, que
permite reconstruirlas y verificar los bytes.

## Invariantes

- **Solo licencias abiertas**: `cc0, cc-by, cc-by-nc, cc-by-sa, cc-by-nc-sa`. Quedan fuera
  las fotos sin licencia declarada y `cc-by-nc-nd`, cuyo ND prohíbe obras derivadas.
- **`PAUSA = 0.25`** entre llamadas a la API: cortesía con iNaturalist, no bajarla.
- **Escritura de `metadata.csv`**: se carga entero, se acumula y se reescribe **completo tras
  cada especie**. Reescribir entero (nunca anexar) evita el corte que ya borró la procedencia
  una vez; hacerlo por especie evita que interrumpir el notebook deje imágenes en disco sin
  registro. Se deduplica por `photo_id`, así que reejecutar es seguro e incremental.
- **Clase vacía en los prompts de YOLO-World**: sin ella el detector deja sin caja 10 de
  cada 40 fotos; con ella, 1 de 40. Nunca gana la predicción. No quitarla.
- **Umbrales congelados como literales**: recalcularlos por percentil cambiaría el dataset
  cada vez que el corpus crece.
- **Cascada de motivos excluyente**: el primero que aplica gana, así el resumen suma el
  corpus entero sin doble contabilidad. La deduplicación va al final para que el
  representante conservado ya haya pasado los filtros de calidad.
- **Semilla combinada con la especie**: agregar una especie no altera el reparto de las que
  ya estaban. No cambiar a una sola semilla global.
- **El manifiesto se escribe al final**: abandonar el notebook a mitad no deja una versión
  a medias en el registro.

## Problemas conocidos

- **Fuga entre splits**: el 31,4 % de las imágenes de test comparten observación con alguna
  de train. Son fotos del mismo individuo, así que inflan la métrica. El notebook 02 la
  mide al final; corregirlo exige repartir agrupando por `observation_id`.
- **Taxonomía sin reconciliar**: `species_list.json` usa nombres que en varios casos ya son
  sinónimos; iNaturalist reclasificó al menos doce. Emparejar por nombre produce errores
  silenciosos. La dirección correcta es descargar por identificador de taxón verificado.
- **Especies escasas**: 20 de 84 agotaron lo research-grade por debajo de 200 fotos, la más
  escasa con 14. Subir el tope no las mueve; solo crecerían incluyendo observaciones sin
  identificación confirmada, a cambio de ruido de etiqueta.
