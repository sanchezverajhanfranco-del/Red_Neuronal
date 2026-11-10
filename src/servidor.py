from pathlib import Path
import base64
import cv2
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from red import cargar_red, activaciones
from procesamiento import limpiar_foto, sacar_letras

Carpeta_Proyecto = Path(__file__).parent.parent
Carpeta_modelos = Carpeta_Proyecto / "modelos"
Carpeta_web = Carpeta_Proyecto / "web"

tabla_clases = pd.read_csv(Carpeta_modelos / "clases_red_completa.csv", dtype=str)
clases = tabla_clases["clase"].tolist()
grupos = tabla_clases["grupo"].tolist()
es_letra = np.array([g == "letra" for g in grupos])
es_animal = np.array([g == "animal" for g in grupos])

red = cargar_red(Carpeta_modelos / "red_completa.pt", n_salidas=len(clases))
red_digitos = cargar_red(Carpeta_modelos / "red_digitos.pt", n_salidas=10)
nombres_digitos = [str(i) for i in range(10)]

UMBRAL = 0.25
NO_RECONOCIDO = "No se pudo reconocer el dibujo"

app = FastAPI()


class Pedido(BaseModel):
    imagen: str
    origen: str = "pizarra"
    modo: str = "numeros"


@app.get("/estado")
def estado():
    return {"mensaje": "servidor encendido", "clases": len(clases)}


def leer_imagen(texto_imagen):
    datos = base64.b64decode(texto_imagen.split(",")[-1])
    return cv2.imdecode(np.frombuffer(datos, np.uint8), cv2.IMREAD_COLOR)


def dibujo_a_28(sin_bordes, lado=20):
    filas, columnas = np.where(sin_bordes > 0)
    if len(filas) == 0:
        return None
    recorte = sin_bordes[filas.min():filas.max() + 1, columnas.min():columnas.max() + 1]
    alto_r, ancho_r = recorte.shape
    escala = lado / max(alto_r, ancho_r)
    nuevo_ancho_r = max(1, int(ancho_r * escala))
    nuevo_alto_r = max(1, int(alto_r * escala))
    chico = cv2.resize(recorte, (nuevo_ancho_r, nuevo_alto_r), interpolation=cv2.INTER_AREA)
    imagen_28 = np.zeros((28, 28), np.uint8)
    arriba = (28 - nuevo_alto_r) // 2
    izquierda = (28 - nuevo_ancho_r) // 2
    imagen_28[arriba:arriba + nuevo_alto_r, izquierda:izquierda + nuevo_ancho_r] = chico
    return imagen_28

NOMBRES_CAPAS = {
    "conv1": "Convolución 1",
    "conv2": "Convolución 2",
    "densa1": "Densa 1",
    "densa2": "Densa 2",
    "salida": "Salida",
}


def capas_para_panel(capas):
    lista = []
    for clave, nombre in NOMBRES_CAPAS.items():
        valores = capas[clave]
        maximo = valores.max()
        if maximo > 0:
            valores = valores / maximo
        lista.append({"nombre": nombre, "valores": valores.round(3).tolist()})
    return lista

GRUPO_DEL_MODO = {"numeros": "dígito", "letras": "letra", "dibujos": "animal"}
LADO_DEL_MODO = {"numeros": 20, "letras": 24, "dibujos": 26}


def mensaje_para(clase, grupo):
    if grupo == "dígito":
        return f"Es el número {clase}"
    if grupo == "letra":
        return f"Es la letra {clase}"
    return f"Es un {clase}"


def opciones_de(probabilidades, nombres, cantidad=3):
    mejores = probabilidades.argsort()[::-1][:cantidad]
    return [{"clase": nombres[k], "probabilidad": round(float(probabilidades[k]), 4)} for k in mejores]


def respuesta_no_reconocida(capas=None, confianza=0.0):
    return {
        "reconocido": False,
        "respuesta": "?",
        "mensaje": NO_RECONOCIDO,
        "categoria": NO_RECONOCIDO,
        "confianza": round(confianza, 4),
        "opciones": [],
        "capas": capas_para_panel(capas) if capas else [],
    }


def red_del_modo(modo):
    if modo == "numeros":
        return red_digitos, nombres_digitos, None
    if modo == "letras":
        return red, clases, es_letra
    return red, clases, es_animal


def probabilidades_del_modo(imagenes, modo):
    red_usada, nombres, solo_grupo = red_del_modo(modo)
    x = torch.tensor(np.array(imagenes) / 255.0, dtype=torch.float32).reshape(-1, 1, 28, 28)
    with torch.no_grad():
        probabilidades = torch.softmax(red_usada(x), dim=1).numpy()
    if solo_grupo is not None:
        probabilidades[:, ~solo_grupo] = 0
        probabilidades = probabilidades / probabilidades.sum(axis=1, keepdims=True)
    return probabilidades, nombres


def separar_caracteres(sin_bordes):
    cantidad, mapa, estadisticas, _ = cv2.connectedComponentsWithStats(sin_bordes, connectivity=8)
    piezas = []
    for i in range(1, cantidad):
        x, y, ancho, alto, area = estadisticas[i]
        piezas.append([x, x + ancho, [i]])
    piezas.sort(key=lambda p: p[0])

    juntas = []
    for izquierda, derecha, ids in piezas:
        if juntas:
            anterior = juntas[-1]
            cruce = min(derecha, anterior[1]) - max(izquierda, anterior[0])
            mas_angosta = min(derecha - izquierda, anterior[1] - anterior[0])
            if cruce > 0.5 * mas_angosta:
                anterior[1] = max(anterior[1], derecha)
                anterior[2] += ids
                continue
        juntas.append([izquierda, derecha, ids])

    partes = []
    for izquierda, derecha, ids in juntas:
        parte = np.where(np.isin(mapa, ids), 255, 0).astype(np.uint8)
        partes.append(parte)
    return partes


def leer_varios(partes, modo):
    imagenes = [dibujo_a_28(parte, lado=LADO_DEL_MODO.get(modo, 20)) for parte in partes]
    probabilidades, nombres = probabilidades_del_modo(imagenes, modo)
    elegidas = probabilidades.argmax(1)
    seguras = probabilidades.max(1) >= UMBRAL
    texto = "".join(nombres[k] if ok else "?" for k, ok in zip(elegidas, seguras))
    confianza = float(probabilidades.max(1).mean())
    red_usada, _, _ = red_del_modo(modo)
    capas = activaciones(red_usada, imagenes[0])
    if confianza < UMBRAL:
        return respuesta_no_reconocida(capas, confianza)
    return {
        "reconocido": True,
        "respuesta": texto,
        "mensaje": f"Dice {' '.join(texto)}",
        "categoria": "texto",
        "confianza": round(confianza, 4),
        "opciones": [],
        "capas": capas_para_panel(capas),
    }


def leer_dibujo(sin_bordes, modo):
    imagen_28 = dibujo_a_28(sin_bordes, lado=LADO_DEL_MODO.get(modo, 20))
    if imagen_28 is None:
        return respuesta_no_reconocida()

    red_usada, nombres, _ = red_del_modo(modo)
    capas = activaciones(red_usada, imagen_28)
    probabilidades, nombres = probabilidades_del_modo([imagen_28], modo)
    probabilidades = probabilidades[0]

    k = int(probabilidades.argmax())
    confianza = float(probabilidades[k])

    if modo != "dibujos":
        partes = separar_caracteres(sin_bordes)
        if len(partes) >= 2:
            varios = leer_varios(partes, modo)
            if varios["confianza"] >= confianza:
                return varios

    if confianza < UMBRAL:
        return respuesta_no_reconocida(capas, confianza)

    grupo = GRUPO_DEL_MODO.get(modo, "animal")
    return {
        "reconocido": True,
        "respuesta": nombres[k],
        "mensaje": mensaje_para(nombres[k], grupo),
        "categoria": grupo,
        "confianza": round(confianza, 4),
        "opciones": opciones_de(probabilidades, nombres),
        "capas": capas_para_panel(capas),
    }


def quitar_ruido(sin_bordes):
    engrosado = cv2.dilate(sin_bordes, np.ones((3, 3), np.uint8), iterations=1)
    cantidad, mapa, estadisticas, _ = cv2.connectedComponentsWithStats(engrosado, connectivity=8)
    if cantidad <= 1:
        return engrosado
    altos = estadisticas[1:, cv2.CC_STAT_HEIGHT]
    areas = estadisticas[1:, cv2.CC_STAT_AREA]
    alto_normal = np.median(altos)
    area_normal = np.median(areas)
    limpio = np.zeros_like(engrosado)
    for i in range(1, cantidad):
        x, y, ancho, alto, area = estadisticas[i]
        if area < 0.2 * area_normal:
            continue
        if alto > 3 * alto_normal or ancho > 8 * alto_normal:
            continue
        limpio[mapa == i] = 255
    return limpio


def armar_texto(texto_letras, elegidas, nombres):
    posicion = 0
    lineas = []
    for linea in texto_letras:
        palabras = []
        for palabra in linea:
            caracteres = ""
            for _ in palabra:
                caracteres += nombres[elegidas[posicion]]
                posicion += 1
            palabras.append(caracteres)
        lineas.append(" ".join(palabras))
    return "\n".join(lineas)


def leer_hoja(sin_bordes, modo):
    if modo == "dibujos":
        return leer_dibujo(sin_bordes, modo)

    sin_bordes = quitar_ruido(sin_bordes)
    try:
        texto_letras = sacar_letras(sin_bordes)
    except Exception:
        return respuesta_no_reconocida()

    imagenes = [letra for linea in texto_letras for palabra in linea for letra in palabra]
    if not imagenes:
        return respuesta_no_reconocida()

    probabilidades, nombres = probabilidades_del_modo(imagenes, modo)
    elegidas = probabilidades.argmax(1)
    nombres = nombres + ["?"]
    elegidas = np.where(probabilidades.max(1) >= UMBRAL, elegidas, len(nombres) - 1)
    texto = armar_texto(texto_letras, elegidas, nombres)
    confianza = float(probabilidades.max(1).mean())
    red_usada, _, _ = red_del_modo(modo)
    capas = activaciones(red_usada, imagenes[0])

    return {
        "reconocido": True,
        "respuesta": "Texto leído",
        "mensaje": texto,
        "categoria": "hoja",
        "confianza": round(confianza, 4),
        "opciones": [],
        "texto": texto,
        "capas": capas_para_panel(capas),
    }


@app.post("/predecir")
def predecir_imagen(pedido: Pedido):
    foto = leer_imagen(pedido.imagen)
    if foto is None:
        return respuesta_no_reconocida()
    sin_bordes = limpiar_foto(foto)
    if pedido.origen == "foto":
        return leer_hoja(sin_bordes, pedido.modo)
    return leer_dibujo(sin_bordes, pedido.modo)


@app.get("/")
def inicio():
    return RedirectResponse("/celular/")


app.mount("/", StaticFiles(directory=Carpeta_web, html=True), name="web")
