// ===== Elementos de la página =====
const pizarra = document.getElementById("pizarra");
const ctx = pizarra.getContext("2d");
const btnBorrar = document.getElementById("btnBorrar");
const btnEnviar = document.getElementById("btnEnviar");
const btnFoto = document.getElementById("btnFoto");
const inputFoto = document.getElementById("inputFoto");
const vistaPrevia = document.getElementById("vistaPrevia");
const cajaRespuesta = document.getElementById("respuesta");
const zonaRed = document.getElementById("zonaRed");
const estadoRed = document.getElementById("estadoRed");

const DURACION_ANIMACION = 3000;   // la red se enciende en unos 3 segundos
const botonesModo = document.querySelectorAll(".modo");
let modo = "numeros";   // qué red usar: numeros, letras o dibujos

let dibujando = false;   // true mientras el dedo está apoyado
let hayTrazo = false;    // true si se dibujó algo desde el último borrado
let ladoCSS = 0;         // tamaño de la pizarra en píxeles CSS

// ===== Preparar la pizarra =====
// Multiplica el tamaño interno por devicePixelRatio para que no se vea borrosa
function prepararPizarra() {
  const ratio = window.devicePixelRatio || 1;
  ladoCSS = pizarra.clientWidth;
  pizarra.width = ladoCSS * ratio;
  pizarra.height = ladoCSS * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.lineWidth = Math.max(14, ladoCSS * 0.06);   // trazo grueso, parecido a los datos de entrenamiento
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = "#000";
  pintarFondoBlanco();
}

// Pinta todo de blanco (nunca dejar el fondo transparente)
function pintarFondoBlanco() {
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, ladoCSS, ladoCSS);
  hayTrazo = false;
}

// Posición del dedo dentro de la pizarra
function posicion(evento) {
  const caja = pizarra.getBoundingClientRect();
  return { x: evento.clientX - caja.left, y: evento.clientY - caja.top };
}

// ===== Dibujar con el dedo o el ratón =====
pizarra.addEventListener("pointerdown", (e) => {
  dibujando = true;
  pizarra.setPointerCapture(e.pointerId);
  const p = posicion(e);
  ctx.beginPath();
  ctx.moveTo(p.x, p.y);
  ctx.lineTo(p.x, p.y);   // un toque suelto deja un punto
  ctx.stroke();
  hayTrazo = true;
});

pizarra.addEventListener("pointermove", (e) => {
  if (!dibujando) return;
  const p = posicion(e);
  ctx.lineTo(p.x, p.y);
  ctx.stroke();
});

// Terminar el trazo (al levantar el dedo o si el sistema lo cancela)
function terminarTrazo() { dibujando = false; }
pizarra.addEventListener("pointerup", terminarTrazo);
pizarra.addEventListener("pointercancel", terminarTrazo);

// ===== Elegir números, letras o dibujos =====
botonesModo.forEach((boton) => {
  boton.addEventListener("click", () => {
    modo = boton.dataset.modo;
    botonesModo.forEach((b) => b.classList.toggle("activo", b === boton));
    cajaRespuesta.innerHTML = "";
    zonaRed.hidden = true;
  });
});

// ===== Borrar =====
btnBorrar.addEventListener("click", () => {
  pintarFondoBlanco();
  cajaRespuesta.innerHTML = "";
  vistaPrevia.hidden = true;
  zonaRed.hidden = true;
  if ("speechSynthesis" in window) speechSynthesis.cancel();
});

// ===== Enviar el dibujo =====
btnEnviar.addEventListener("click", () => {
  if (!hayTrazo) {
    mostrarError("Dibuja algo primero");
    return;
  }
  enviarImagen(pizarra.toDataURL("image/png"), "pizarra");
});

// ===== Foto de una hoja =====
btnFoto.addEventListener("click", () => inputFoto.click());

inputFoto.addEventListener("change", () => {
  const archivo = inputFoto.files[0];
  if (!archivo) return;
  const lector = new FileReader();
  lector.onload = () => achicarFoto(lector.result);
  lector.readAsDataURL(archivo);
  inputFoto.value = "";   // permite elegir la misma foto otra vez
});

// Si la foto mide más de 1600 px de ancho, se reduce y se guarda como JPEG
function achicarFoto(textoImagen) {
  const foto = new Image();
  foto.onload = () => {
    const anchoFinal = Math.min(foto.width, 1600);
    const altoFinal = Math.round(foto.height * (anchoFinal / foto.width));
    const aux = document.createElement("canvas");
    aux.width = anchoFinal;
    aux.height = altoFinal;
    aux.getContext("2d").drawImage(foto, 0, 0, anchoFinal, altoFinal);
    const jpeg = aux.toDataURL("image/jpeg", 0.9);
    vistaPrevia.src = jpeg;
    vistaPrevia.hidden = false;
    enviarImagen(jpeg, "foto");
  };
  foto.onerror = () => mostrarError("No se pudo leer la foto");
  foto.src = textoImagen;
}

// ===== Enviar al servidor =====
async function enviarImagen(imagen, origen) {
  btnEnviar.disabled = true;
  btnFoto.disabled = true;
  const textoOriginal = btnEnviar.textContent;
  btnEnviar.textContent = "Enviando…";
  cajaRespuesta.innerHTML = "";
  zonaRed.hidden = false;
  estadoRed.textContent = "Enviando al servidor…";
  await animarPanel([], 0);   // deja el panel vacío mientras llega la respuesta
  try {
    const respuesta = await fetch(SERVIDOR + "/predecir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ imagen: imagen, origen: origen, modo: modo })
    });
    if (!respuesta.ok) throw new Error("Error " + respuesta.status);
    const datos = await respuesta.json();

    // Primero la red en vivo, después el resultado
    estadoRed.textContent = "La red está procesando…";
    const terminada = await animarPanel(datos.capas, DURACION_ANIMACION);
    if (!terminada) return;
    estadoRed.textContent = "Así se activó la red";
    mostrarRespuesta(datos);
  } catch (error) {
    console.error(error);
    zonaRed.hidden = true;
    mostrarError("No se pudo conectar con el servidor");
  } finally {
    btnEnviar.disabled = false;
    btnFoto.disabled = false;
    btnEnviar.textContent = textoOriginal;
  }
}

// ===== Mostrar la respuesta =====
function mostrarRespuesta(datos) {
  cajaRespuesta.innerHTML = "";

  // La red no estaba segura
  if (!datos.reconocido) {
    const aviso = document.createElement("div");
    aviso.className = "no-reconocido";
    aviso.textContent = datos.mensaje;
    cajaRespuesta.appendChild(aviso);
    hablar(datos.mensaje);
    return;
  }

  // Respuesta en grande
  const grande = document.createElement("div");
  grande.className = "grande";
  grande.textContent = datos.respuesta;
  cajaRespuesta.appendChild(grande);

  // Categoría y confianza en porcentaje
  const detalle = document.createElement("div");
  detalle.className = "detalle";
  detalle.textContent = datos.categoria + " · " + Math.round(datos.confianza * 100) + " %";
  cajaRespuesta.appendChild(detalle);

  // Las otras dos opciones más probables (la primera ya es la respuesta)
  if (Array.isArray(datos.opciones) && datos.opciones.length > 1) {
    const otras = datos.opciones.slice(1, 3).map(
      (o) => o.clase + " (" + Math.round(o.probabilidad * 100) + " %)"
    );
    const opciones = document.createElement("div");
    opciones.className = "opciones";
    opciones.textContent = "Otras opciones: " + otras.join(", ");
    cajaRespuesta.appendChild(opciones);
  }

  // Texto completo si fue la foto de una hoja
  if (datos.texto) {
    const texto = document.createElement("div");
    texto.className = "texto-hoja";
    texto.textContent = datos.texto;
    cajaRespuesta.appendChild(texto);
  }

  hablar(datos.mensaje);
}

// Mensaje de error claro
function mostrarError(mensaje) {
  cajaRespuesta.innerHTML = "";
  const p = document.createElement("div");
  p.className = "error";
  p.textContent = mensaje;
  cajaRespuesta.appendChild(p);
}

// ===== Inicio =====
prepararPizarra();
