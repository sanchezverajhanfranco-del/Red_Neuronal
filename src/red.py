import numpy as np
import torch
from torch import nn


class RedConvolucional(nn.Module):
    def __init__(self, n_salidas=10, abandono=0.25):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.agrupar = nn.MaxPool2d(2)
        self.activacion = nn.ReLU()
        self.aplanar = nn.Flatten()
        self.densa1 = nn.Linear(32 * 7 * 7, 64)
        self.abandono = nn.Dropout(abandono)
        self.densa2 = nn.Linear(64, 32)
        self.salida = nn.Linear(32, n_salidas)

    def forward(self, x):
        c1 = self.agrupar(self.activacion(self.conv1(x)))
        c2 = self.agrupar(self.activacion(self.conv2(c1)))
        d1 = self.activacion(self.densa1(self.aplanar(c2)))
        d2 = self.activacion(self.densa2(self.abandono(d1)))
        s = self.salida(d2)
        return s


def cargar_red(ruta, n_salidas=10):
    red = RedConvolucional(n_salidas=n_salidas)
    red.load_state_dict(torch.load(ruta, map_location="cpu"))
    red.eval()
    return red


def predecir(red, imagenes):
    x = torch.tensor(np.array(imagenes) / 255.0, dtype=torch.float32).reshape(-1, 1, 28, 28)
    with torch.no_grad():
        probabilidades = torch.softmax(red(x), dim=1)
    seguridad, respuesta = probabilidades.max(1)
    return respuesta.numpy(), seguridad.numpy()
