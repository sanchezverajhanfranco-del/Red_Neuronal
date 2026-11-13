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


def engrosar(recorte):
    lado_mayor = max(recorte.shape)
    distancia = cv2.distanceTransform((recorte > 0).astype(np.uint8), cv2.DIST_L2, 3)
    if distancia.max() == 0:
        return recorte
    grosor = 2 * np.percentile(distancia[distancia > 0], 90)
    falta = int(round(0.12 * lado_mayor - grosor))
    if falta <= 0:
        return recorte
    recorte = cv2.copyMakeBorder(recorte, falta, falta, falta, falta, cv2.BORDER_CONSTANT, value=0)
    nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (falta + 1, falta + 1))
    return cv2.dilate(recorte, nucleo)


def juntar_piezas(cajas):
    cambio = True
    while cambio:
        cambio = False
        juntas = []
        for caja in cajas:
            x, y, a, h = caja
            for k, (x0, y0, a0, h0) in enumerate(juntas):
                cruce = min(x0 + a0, x + a) - max(x0, x)
                hueco = max(y0, y) - min(y0 + h0, y + h)
                if cruce > 0.5 * min(a0, a) and hueco < 0.6 * max(h0, h):
                    izquierda = min(x0, x)
                    arriba = min(y0, y)
                    juntas[k] = (izquierda, arriba, max(x0 + a0, x + a) - izquierda, max(y0 + h0, y + h) - arriba)
                    cambio = True
                    break
            else:
                juntas.append(caja)
        cajas = juntas
    return cajas


def sacar_letras(sin_bordes):
    cantidad, mapa, estadisticas, centros_piezas = cv2.connectedComponentsWithStats(sin_bordes, connectivity=8)
    cajas = []
    areas = estadisticas[1:, cv2.CC_STAT_AREA]
    if len(areas) == 0:
        return []
    area_grande = np.percentile(areas, 90)
    for i in range(1, cantidad):
        x, y, ancho_pieza, alto_pieza, area = estadisticas[i]
        if area >= 20 and area >= 0.15 * area_grande:
            cajas.append((x, y, ancho_pieza, alto_pieza))
    if not cajas:
        return []
    cajas = juntar_piezas(cajas)

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
        letras = []
        for caja in sorted(renglon["cajas"], key=lambda c: c[0]):
            if letras:
                x0, y0, a0, h0 = letras[-1]
                x, y, a, h = caja
                cruce = min(x0 + a0, x + a) - max(x0, x)
                if cruce > 0.5 * min(a0, a):
                    izquierda = min(x0, x)
                    arriba = min(y0, y)
                    letras[-1] = (izquierda, arriba, max(x0 + a0, x + a) - izquierda, max(y0 + h0, y + h) - arriba)
                    continue
            letras.append(caja)
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
                recorte = engrosar(recorte)
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
