// ===== Preguntas frecuentes =====
// Cada pregunta tiene su respuesta. Al tocarla, se muestra y se lee en voz alta.

const PREGUNTAS = [
  {
    pregunta: "¿Qué es una red neuronal convolucional?",
    respuesta: "Es un modelo de aprendizaje profundo diseñado para imágenes. Sus capas convolucionales aplican filtros que detectan bordes, curvas y trazos. Las capas densas combinan esos rasgos y la capa de salida asigna un porcentaje a cada clase posible."
  },
  {
    pregunta: "¿Qué capas tiene esta red?",
    respuesta: "Tiene dos capas convolucionales, de 16 y 32 filtros, cada una seguida de una agrupación que reduce la imagen a la mitad. Luego tiene dos capas densas, de 64 y 32 neuronas, con abandono del 25 por ciento durante el entrenamiento, y una capa de salida con una neurona por cada clase: 10 en el modo Números y 67 en los modos Letras y Dibujos."
  },
  {
    pregunta: "¿Qué muestra la animación de la red?",
    respuesta: "Muestra la red real procesando la imagen enviada. Cada círculo es una neurona o un filtro, y su brillo indica cuánto se activó. Las capas se encienden de izquierda a derecha, en el mismo orden en que la información atraviesa la red, hasta llegar a la capa de salida."
  },
  {
    pregunta: "¿Cómo se prepara la imagen antes de entrar a la red?",
    respuesta: "La imagen se convierte a escala de grises, se corrige la iluminación del fondo y se separa la tinta del papel con el algoritmo K-Means. Después se recorta cada carácter y se escala: en la pizarra, su lado mayor mide 20 píxeles en números, 24 en letras y 26 en dibujos; en la foto de una hoja mide 20, salvo en el modo Dibujos, que también usa 26. Luego se centra en un cuadro de 28 por 28 y sus valores se normalizan entre 0 y 1."
  },
  {
    pregunta: "¿Con qué datos se entrenó la red?",
    respuesta: "Se usaron datos reales: MNIST para los dígitos, EMNIST para las letras y QuickDraw para los dibujos de animales. En total, la red aprendió 67 clases: 10 dígitos, 37 letras y 20 animales."
  },
  {
    pregunta: "¿Qué tan precisa es la red?",
    respuesta: "En las imágenes de prueba, que la red nunca vio durante el entrenamiento, alcanzó una exactitud de 97,82 por ciento en dígitos, 86,27 por ciento en letras y 65,13 por ciento en animales. Los animales tienen menor exactitud porque, a 28 por 28 píxeles, varios dibujos son muy parecidos entre sí."
  },
  {
    pregunta: "¿Por qué se eligió una red y no KNN o SVM?",
    respuesta: "En la prueba con dígitos, la red convolucional obtuvo cerca de 98,7 por ciento de exactitud, frente a 97,67 por ciento del SVM y 97,05 por ciento del KNN. Además, la red reconoce formas gracias a sus filtros, mientras que KNN y SVM comparan los píxeles uno por uno."
  },
  {
    pregunta: "¿Por qué a veces dice que no reconoció el dibujo?",
    respuesta: "La red calcula un porcentaje de seguridad para su respuesta. Si ese porcentaje es menor al 25 por ciento, el sistema no muestra una respuesta inventada y avisa que no pudo reconocer el dibujo."
  }
];

const listaPreguntas = document.getElementById("listaPreguntas");
const respuestaPregunta = document.getElementById("respuestaPregunta");

PREGUNTAS.forEach((item) => {
  const boton = document.createElement("button");
  boton.textContent = item.pregunta;
  boton.addEventListener("click", () => {
    respuestaPregunta.textContent = item.respuesta;
    hablar(item.respuesta);
  });
  listaPreguntas.appendChild(boton);
});

// ===== Voz =====
// Usa la voz del propio navegador: no necesita claves ni servicios externos.
function hablar(texto) {
  if (!("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const frase = new SpeechSynthesisUtterance(texto);
  frase.lang = "es-ES";
  frase.rate = 1;
  speechSynthesis.speak(frase);
}
