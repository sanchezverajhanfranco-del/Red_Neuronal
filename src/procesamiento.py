import cv2
import numpy as np
from sklearn.cluster import KMeans


def limpiar_foto(foto):
    alto, ancho = foto.shape[:2]
    nuevo_ancho = 1200
    nuevo_alto = int(alto * nuevo_ancho / ancho)
    foto_scala = cv2.resize(foto, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_AREA)
    gris = cv2.cvtColor(foto_scala, cv2.COLOR_BGR2GRAY)

    nucleo = np.ones((15, 15), np.uint8)
    fondo = cv2.medianBlur(cv2.dilate(gris, nucleo), 31)
    gris_parejo = cv2.divide(gris, fondo, scale=255)

    puntos = gris_parejo.reshape(-1, 1).astype(np.float32)
    generador = np.random.default_rng(42)
    muestra = puntos[generador.choice(len(puntos), 20000, replace=False)]
    km = KMeans(n_clusters=2, random_state=42, n_init=10)
    km.fit(muestra)
    grupos = km.predict(puntos)

    centros = km.cluster_centers_.ravel()
    gr_tinta = np.argmin(centros)
    grupos_imagen = grupos.reshape(gris_parejo.shape)
    binaria_km = np.where(grupos_imagen == gr_tinta, 255, 0).astype(np.uint8)

    sin_bordes = binaria_km.copy()
    cantidad, mapa, estadisticas, centros_piezas = cv2.connectedComponentsWithStats(sin_bordes, connectivity=8)
    alto_imagen, ancho_imagen = sin_bordes.shape
    for i in range(1, cantidad):
        x, y, ancho_pieza, alto_pieza, area = estadisticas[i]
        if x == 0 or y == 0 or x + ancho_pieza == ancho_imagen or y + alto_pieza == alto_imagen:
            sin_bordes[mapa == i] = 0

    return sin_bordes


def sacar_letras(sin_bordes):
    cantidad, mapa, estadisticas, centros_piezas = cv2.connectedComponentsWithStats(sin_bordes, connectivity=8)
    cajas = []
    for i in range(1, cantidad):
        x, y, ancho_pieza, alto_pieza, area = estadisticas[i]
        if area >= 20:
            cajas.append((x, y, ancho_pieza, alto_pieza))

    altura_normal = float(np.median([alto_pieza for x, y, ancho_pieza, alto_pieza in cajas]))

    renglones = []
    margen = 0.5 * altura_normal
    for caja in sorted(cajas, key=lambda c: c[1]):
        x, y, ancho_pieza, alto_pieza = caja
        if renglones and y <= renglones[-1]["abajo"] + margen:
            renglones[-1]["cajas"].append(caja)
            renglones[-1]["abajo"] = max(renglones[-1]["abajo"], y + alto_pieza)
        else:
            renglones.append({"arriba": y, "abajo": y + alto_pieza, "cajas": [caja]})

    umbral_espacio = 0.5 * altura_normal
    for renglon in renglones:
        letras = sorted(renglon["cajas"], key=lambda c: c[0])
        palabras = []
        palabra_actual = []
        for i in range(len(letras)):
            letra = letras[i]
            palabra_actual.append(letra)
            if i == len(letras) - 1:
                palabras.append(palabra_actual)
            else:
                siguiente = letras[i + 1]
                distancia = siguiente[0] - (letra[0] + letra[2])
                if distancia > umbral_espacio:
                    palabras.append(palabra_actual)
                    palabra_actual = []
        renglon["palabras"] = palabras

    texto_letras = []
    for renglon in renglones:
        linea = []
        for palabra in renglon["palabras"]:
            palabra_28 = []
            for x, y, ancho_pieza, alto_pieza in palabra:
                recorte = sin_bordes[y:y + alto_pieza, x:x + ancho_pieza]
                alto_r, ancho_r = recorte.shape
                escala = 20 / max(alto_r, ancho_r)
                nuevo_ancho_r = max(1, int(ancho_r * escala))
                nuevo_alto_r = max(1, int(alto_r * escala))
                chico = cv2.resize(recorte, (nuevo_ancho_r, nuevo_alto_r), interpolation=cv2.INTER_AREA)
                letra_28 = np.zeros((28, 28), np.uint8)
                arriba = (28 - nuevo_alto_r) // 2
                izquierda = (28 - nuevo_ancho_r) // 2
                letra_28[arriba:arriba + nuevo_alto_r, izquierda:izquierda + nuevo_ancho_r] = chico
                palabra_28.append(letra_28)
            linea.append(palabra_28)
        texto_letras.append(linea)

    return texto_letras
