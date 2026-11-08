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
