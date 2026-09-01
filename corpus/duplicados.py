"""Casi-duplicados por hash perceptual, agrupados con union-find."""

from collections import defaultdict

import cv2
import numpy as np

# Calibrados con el valle entre las distribuciones intra e inter observación
# (ver validarUmbral() y su figura en el notebook 02).
UMBRAL = 8
UMBRAL_RAFAGA = 12

POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def hashPerceptual(gris):
    """pHash: DCT de 32x32, bloque 8x8 de baja frecuencia contra su mediana."""
    pequena = cv2.resize(gris, (32, 32), interpolation=cv2.INTER_AREA)
    transformada = cv2.dct(np.float32(pequena))[:8, :8]
    return empaquetar((transformada > np.median(transformada)).ravel())


def hashDiferencial(gris):
    """dHash: 9x8, cada bit compara un píxel con su vecino de la derecha."""
    pequena = cv2.resize(gris, (9, 8), interpolation=cv2.INTER_AREA)
    return empaquetar((pequena[:, 1:] > pequena[:, :-1]).ravel())


def empaquetar(bits):
    valor = 0
    for bit in bits:
        valor = (valor << 1) | int(bit)
    return valor


def aHex(valor):
    return f"{valor:016x}"


def distanciasEn(hashes):
    """Matriz de distancias de Hamming de todos contra todos."""
    matriz = np.array([[(int(h, 16) >> (8 * i)) & 0xFF for i in range(8)]
                       for h in hashes], dtype=np.uint8)
    return POPCOUNT[matriz[:, None, :] ^ matriz[None, :, :]].sum(axis=2)


def porEspecie(filas):
    grupos = defaultdict(list)
    for fila in filas:
        grupos[fila["especie"]].append(fila)
    return {e: g for e, g in sorted(grupos.items()) if len(g) > 1}


def paresCercanos(filas):
    """Pares de casi-duplicados, comparando solo dentro de cada especie.

    Compartir observación es evidencia previa, no veredicto: relaja el umbral,
    pero el dorsal y el ventral de un ejemplar distan mucho más y sobreviven.
    """
    pares = []
    for grupo in porEspecie(filas).values():
        for nombre in ("phash", "dhash"):
            distancias = distanciasEn([f[nombre] for f in grupo])
            for i, j in zip(*np.triu_indices(len(grupo), k=1)):
                misma = grupo[i]["observation_id"] == grupo[j]["observation_id"]
                if distancias[i, j] <= (UMBRAL_RAFAGA if misma else UMBRAL):
                    pares.append((grupo[i]["photo_id"], grupo[j]["photo_id"]))
    return pares


def agrupar(idsFotos, pares):
    """Union-find: cierre transitivo de los pares cercanos."""
    padre = {i: i for i in idsFotos}

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    for a, b in pares:
        if raiz(a) != raiz(b):
            padre[raiz(b)] = raiz(a)

    grupos = defaultdict(list)
    for i in idsFotos:
        grupos[raiz(i)].append(i)
    return [sorted(g) for g in grupos.values() if len(g) > 1]


def elegirRepresentante(grupo, nitidezPorFoto):
    """El más nítido; desempate por photo_id menor para que sea determinista."""
    return min(grupo, key=lambda i: (-nitidezPorFoto[i], int(i)))


def validarUmbral(filas):
    """Distancias intra y entre observaciones: el valle entre ambas es el umbral.

    El observation_id da un conjunto de validación gratuito, y es lo que hace
    que el número elegido deje de ser arbitrario.
    """
    intra, inter = [], []
    for grupo in porEspecie(filas).values():
        distancias = distanciasEn([f["phash"] for f in grupo])
        for i, j in zip(*np.triu_indices(len(grupo), k=1)):
            misma = grupo[i]["observation_id"] == grupo[j]["observation_id"]
            (intra if misma else inter).append(int(distancias[i, j]))
    return np.array(intra), np.array(inter)
