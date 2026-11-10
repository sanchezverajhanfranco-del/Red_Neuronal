// ===== Panel de la red en vivo =====
// Dibuja las capas de la red y las enciende una tras otra, de izquierda a derecha.
// Viene del proyector.js de la versión anterior, adaptado al celular.

const lienzoPanel = document.getElementById("panel");
const ctxPanel = lienzoPanel.getContext("2d");

const COLOR_APAGADA = [38, 48, 68];     // gris oscuro (valor 0)
const COLOR_ENCENDIDA = [90, 220, 255]; // celeste brillante (valor 1)

let capasPanel = [];          // capas que llegaron del servidor
let capasEncendidas = 0;      // cuántas capas ya se encendieron
let animacionActual = 0;      // número de animación, para cancelar la anterior

// Ajusta el canvas a su tamaño real en pantalla (sin verse borroso)
function ajustarPanel() {
  const ratio = window.devicePixelRatio || 1;
  lienzoPanel.width = lienzoPanel.clientWidth * ratio;
  lienzoPanel.height = lienzoPanel.clientHeight * ratio;
  ctxPanel.setTransform(ratio, 0, 0, ratio, 0, 0);
  dibujarPanel();
}
window.addEventListener("resize", ajustarPanel);

// Enciende las capas una por una. Tarda en total más o menos "duracionMs".
// Devuelve true si terminó, false si otra animación la reemplazó.
async function animarPanel(nuevasCapas, duracionMs) {
  const miNumero = ++animacionActual;
  capasPanel = Array.isArray(nuevasCapas) ? nuevasCapas : [];
  capasEncendidas = 0;
  ajustarPanel();
  if (capasPanel.length === 0) return true;
  const pausa = duracionMs / capasPanel.length;
  for (let i = 0; i < capasPanel.length; i++) {
    await new Promise((listo) => setTimeout(listo, pausa));
    if (miNumero !== animacionActual) return false;
    capasEncendidas = i + 1;
    dibujarPanel();
  }
  return true;
}

// Mezcla el color apagado y el encendido según el valor (0 a 1)
function colorNeurona(valor) {
  const v = Math.max(0, Math.min(1, valor));
  const c = COLOR_APAGADA.map((a, i) => Math.round(a + (COLOR_ENCENDIDA[i] - a) * v));
  return "rgb(" + c[0] + "," + c[1] + "," + c[2] + ")";
}

// Posición (x, y) de la neurona j de la capa i
function posicionNeurona(i, j, ancho, alto) {
  const margenX = ancho * 0.1;
  const x = capasPanel.length === 1
    ? ancho / 2
    : margenX + (ancho - 2 * margenX) * (i / (capasPanel.length - 1));
  const total = capasPanel[i].valores.length;
  const margenSup = alto * 0.05;
  const margenInf = alto * 0.16;
  const y = total === 1
    ? (margenSup + alto - margenInf) / 2
    : margenSup + (alto - margenSup - margenInf) * (j / (total - 1));
  return { x, y };
}

function dibujarPanel() {
  const ancho = lienzoPanel.clientWidth;
  const alto = lienzoPanel.clientHeight;
  ctxPanel.clearRect(0, 0, ancho, alto);
  if (capasPanel.length === 0) return;

  const maxNeuronas = Math.max(...capasPanel.map((c) => c.valores.length));
  const radio = Math.max(1.5, Math.min(alto * 0.03, (alto * 0.8) / (maxNeuronas * 2.4)));

  // Líneas entre una capa y la siguiente
  ctxPanel.lineWidth = 0.6;
  for (let i = 0; i < capasPanel.length - 1; i++) {
    const siguienteEncendida = i + 1 < capasEncendidas;
    for (let a = 0; a < capasPanel[i].valores.length; a++) {
      const origen = posicionNeurona(i, a, ancho, alto);
      const fuerza = i < capasEncendidas ? capasPanel[i].valores[a] : 0;
      const opacidad = 0.03 + (siguienteEncendida ? 0.2 * fuerza : 0);
      ctxPanel.strokeStyle = "rgba(" + COLOR_ENCENDIDA.join(",") + "," + opacidad + ")";
      for (let b = 0; b < capasPanel[i + 1].valores.length; b++) {
        const destino = posicionNeurona(i + 1, b, ancho, alto);
        ctxPanel.beginPath();
        ctxPanel.moveTo(origen.x, origen.y);
        ctxPanel.lineTo(destino.x, destino.y);
        ctxPanel.stroke();
      }
    }
  }

  // Neuronas
  for (let i = 0; i < capasPanel.length; i++) {
    const encendida = i < capasEncendidas;
    for (let j = 0; j < capasPanel[i].valores.length; j++) {
      const p = posicionNeurona(i, j, ancho, alto);
      ctxPanel.beginPath();
      ctxPanel.arc(p.x, p.y, radio, 0, Math.PI * 2);
      ctxPanel.fillStyle = colorNeurona(encendida ? capasPanel[i].valores[j] : 0);
      ctxPanel.fill();
    }
  }

  // Nombre de cada capa, debajo de su columna
  ctxPanel.fillStyle = "#9fb0cc";
  ctxPanel.textAlign = "center";
  ctxPanel.font = "11px system-ui, sans-serif";
  for (let i = 0; i < capasPanel.length; i++) {
    const x = posicionNeurona(i, 0, ancho, alto).x;
    const palabras = capasPanel[i].nombre.split(" ");   // "Convolución 1" va en dos renglones
    palabras.forEach((palabra, n) => {
      ctxPanel.fillText(palabra, x, alto - 18 + n * 13);
    });
  }
}
