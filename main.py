import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import argparse
import torch
import time
import sys

# Forzar flush en prints para que Flutter lea los logs al instante
sys.stdout.reconfigure(line_buffering=True)

# Forzar flush en prints para que Flutter lea los logs al instante
sys.stdout.reconfigure(line_buffering=True)

from database import DatabasePlacas
from alerta_telegram import enviar_alerta_telegram, guardar_capturas

# ─── Inicialización ───────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Sistema de Reconocimiento de Placas")
parser.add_argument("--video", type=str, default="0",
                    help="Índice de cámara (0,1,2...), URL RTSP, HTTP o ruta de video")
args = parser.parse_args()

print("🔒 Iniciando Sistema de Vigilancia Inteligente...")

db = DatabasePlacas()
placas_en_bd = db.listar_placas()
print(f"📋 [DB] {len(placas_en_bd)} placa(s) robada(s) cargadas en memoria.")


def resource_path(relative_path):
    """Obtener ruta absoluta, funciona en dev y PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Modelos YOLO
print("🤖 Cargando modelos de IA...")
modelo_vehiculos = YOLO(resource_path("yolo11n.pt"))
modelo_placas    = YOLO(resource_path("runs/detect/license_plate_detector/weights/best.pt"))

# EasyOCR (Usar solo 'en' que es mucho más rápido y ligero para caracteres de matrículas)
usar_gpu = torch.cuda.is_available()
print(f"⚡ GPU para OCR: {'Sí (CUDA)' if usar_gpu else 'No (CPU)'}")
lector_ocr = easyocr.Reader(['en'], gpu=usar_gpu)

# ─── Apertura de fuente de video ──────────────────────────────────────────────


# ─── Captura de Pantalla ─────────────────────────────────────────────────────

try:
    import mss
except ImportError:
    pass

class CapturaPantalla:
    def __init__(self, monitor_id=1):
        self.sct = mss.mss()
        # monitor_id=1 es usualmente la pantalla primaria. monitor_id=0 es todas unidas
        self.monitor = self.sct.monitors[monitor_id] if len(self.sct.monitors) > monitor_id else self.sct.monitors[0]
        self.abierto = True
        
    def isOpened(self):
        return self.abierto
        
    def read(self):
        if not self.abierto:
            return False, None
        sct_img = self.sct.grab(self.monitor)
        # Convertir a numpy, la captura viene en BGRA, OpenCV espera BGR
        import numpy as np
        img_bgra = np.array(sct_img)
        # Removiendo canal Alpha usando slicing (mucho más rapido que cvtColor)
        img_bgr = img_bgra[:, :, :3]
        return True, img_bgr
        
    def release(self):
        self.abierto = False
        self.sct.close()

    def set(self, propId, value):
        pass

def abrir_captura(fuente_str: str) -> cv2.VideoCapture:
    """
    Abre una fuente de video. Soporta:
      - Entero (0,1,2...): cámara USB local (prueba MSMF → DSHOW → sin backend)
      - rtsp://...        : cámara IP/WiFi/BT por RTSP
      - http://...        : cámara IP/WiFi por HTTP MJPEG
      - ruta de archivo   : video grabado
    """
    if fuente_str.lower() in ("pantalla", "screen", "999"):
        print("🖥️  Capturando pantalla primaria (monitor oficial)...")
        return CapturaPantalla()

    if fuente_str.isdigit():
        idx = int(fuente_str)
        print(f"📹 Intentando abrir cámara USB índice {idx}...")

        # Prueba cada backend: verifica que abre Y que puede leer al menos 1 fotograma.
        # Algunos backends (MSMF) abren sin error pero fallan al leer en ciertas webcams.
        backends = [
            (cv2.CAP_MSMF,  "MSMF"),
            (cv2.CAP_DSHOW, "DSHOW"),
            (cv2.CAP_ANY,   "ANY"),
        ]
        cap = None
        for backend, nombre in backends:
            c = cv2.VideoCapture(idx, backend)
            if c.isOpened():
                # Test de lectura real — esperar hasta 3 segundos por un fotograma válido
                ok = False
                for _ in range(30):
                    ret, fot = c.read()
                    if ret and fot is not None:
                        ok = True
                        break
                    time.sleep(0.1)
                if ok:
                    print(f"   ✅ Backend {nombre} funcionó y lee fotogramas correctamente.")
                    cap = c
                    break
                else:
                    print(f"   ⚠️  Backend {nombre} abrió pero no puede leer fotogramas, probando siguiente...")
                    c.release()
            else:
                print(f"   ⚠️  Backend {nombre} no pudo abrir la cámara, probando siguiente...")
                c.release()

        if cap is None or not cap.isOpened():
            print(f"❌ [ERROR] No se pudo abrir la cámara USB {idx} con ningún backend.")
            sys.exit(1)

    elif fuente_str.lower().startswith("rtsp://"):
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
        cap = cv2.VideoCapture(fuente_str, cv2.CAP_FFMPEG)
        print(f"📡 Cámara RTSP: {fuente_str}")
        if not cap.isOpened():
            print(f"❌ [ERROR] No se pudo abrir RTSP: {fuente_str}")
            sys.exit(1)

    elif fuente_str.lower().startswith("http"):
        cap = cv2.VideoCapture(fuente_str)
        print(f"🌐 Cámara HTTP: {fuente_str}")
        if not cap.isOpened():
            print(f"❌ [ERROR] No se pudo abrir HTTP: {fuente_str}")
            sys.exit(1)

    else:
        cap = cv2.VideoCapture(fuente_str)
        print(f"📁 Fuente de video: {fuente_str}")
        if not cap.isOpened():
            print(f"❌ [ERROR] No se pudo abrir: {fuente_str}")
            sys.exit(1)

    if not fuente_str.isdigit():
        # Reducir buffer para minimizar latencia en red
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return cap

origen_video_str = args.video
cap = abrir_captura(origen_video_str)

# ─── Preparar directorio de salida ───────────────────────────────────────────

appdata = os.getenv('APPDATA') or os.path.expanduser('~')
dir_app = os.path.join(appdata, 'AlertaVecinal', 'System')
os.makedirs(dir_app, exist_ok=True)
ruta_fotograma = os.path.join(dir_app, 'ultimo_fotograma.jpg')

# Parámetros de escritura JPEG — calidad 70 reduce tamaño ~50% vs 95 con pérdida imperceptible
PARAMETROS_JPEG = [cv2.IMWRITE_JPEG_QUALITY, 70]

# ─── Estado de seguimiento ────────────────────────────────────────────────────

cache_placas        = {}  # { id_rastreo: { "texto": str, "es_robado": bool, "info": dict|None } }
vehiculos_alertados = set()
conteo_fotogramas         = 0
ultimas_cajas          = []
ultimos_ids_rastreo      = []
intentos_ocr        = {}  # { id_rastreo: {"ultimo_fotograma": int, "intentos": int} }

# ─── Throttle de escritura de fotograma ─────────────────────────────────────────
# Escribimos el fotograma a disco máximo a 15 FPS para reducir I/O
_ultimo_fotograma_escrito  = 0.0
INTERVALO_ESCRITURA_FOTOGRAMA   = 1.0 / 15.0  # 15 Fotogramas por segundo máximo en disco

# ─── Utilidades de dibujo ─────────────────────────────────────────────────────

ROJO    = (0,   0,   255)
VERDE   = (0,   200,  50)
NARANJA = (0,   130, 255)
BLANCO  = (255, 255, 255)
NEGRO   = (0,     0,   0)
AMARILLO= (0,   220, 255)


def dibujar_etiqueta(fotograma, texto, x1, y1, color_fondo, color_texto=BLANCO, escala=0.55):
    """Dibuja una etiqueta con fondo sólido sobre la imagen."""
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    grosor = 1
    (ancho, alto), _ = cv2.getTextSize(texto, fuente, escala, grosor + 1)
    cv2.rectangle(fotograma, (x1, y1 - alto - 8), (x1 + ancho + 6, y1), color_fondo, -1)
    cv2.putText(fotograma, texto, (x1 + 3, y1 - 4), fuente, escala, color_texto, grosor + 1, cv2.LINE_AA)


def preprocesar_placa(roi_placa):
    """Pipeline de Grado Industrial (Real-World): Interpolación Lanczos y Unsharp Masking para la calle."""
    h, w = roi_placa.shape[:2]
    if h == 0:
        return None
    
    # 1. Ampliación de alta definición usando algoritmo Lanczos4 (Óptimo para asfalto, polvo y movimiento real)
    scale = 100.0 / h
    resized = cv2.resize(roi_placa, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    
    # 2. Algoritmo "Unsharp Masking" (Enfoque extremo de laboratorio)
    # Extrae el micro-contraste de las letras borrosas de autos en movimiento sin afectar el color
    gaussian = cv2.GaussianBlur(resized, (5, 5), 2.0)
    imagen_enfocada = cv2.addWeighted(resized, 1.5, gaussian, -0.5, 0)
    
    return imagen_enfocada


# ─── Bucle principal ──────────────────────────────────────────────────────────

import threading
from concurrent.futures import ThreadPoolExecutor

class HiloCapturaCamara:
    def __init__(self, cap):
        self.cap = cap
        self.ultimo_fotograma = None
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def _run(self):
        while self.running and self.cap.isOpened():
            ret, fotograma = self.cap.read()
            if not ret:
                if origen_video_str.isdigit():
                    time.sleep(0.05)
                    continue
                else:
                    print("⚠️  Stream de red perdido, deteniendo hilo temporalmente...")
                    time.sleep(1.0)
                    break
            
            with self.lock:
                self.ultimo_fotograma = fotograma.copy()

    def read(self):
        with self.lock:
            if self.ultimo_fotograma is None:
                return False, None
            return True, self.ultimo_fotograma.copy()

    def stop(self):
        self.running = False
        self.thread.join()

print(f"📹 Monitoreo activo ({'Cámara USB' if origen_video_str.isdigit() else origen_video_str}). "
      f"Ctrl+C para salir.\n")

hilo_camara = HiloCapturaCamara(cap)
ejecutor_ocr = ThreadPoolExecutor(max_workers=1)

# Estado de seguimiento y almacenamiento intermedio
ultimas_cajas      = []
ultimos_ids_rastreo  = []
ultimas_confianzas      = []

while True:
    tiempo_inicio_bucle = time.time()
    
    ret, fotograma = hilo_camara.read()
    if not ret:
        if not hilo_camara.thread.is_alive() and not origen_video_str.isdigit():
            print("⚠️  Reconectando cámara de red...")
            cap.release()
            cap = abrir_captura(origen_video_str)
            hilo_camara = HiloCapturaCamara(cap)
        time.sleep(0.05)
        continue

    conteo_fotogramas += 1

    # Salto de fotogramas inteligente: Procesar YOLO cada 2 fotogramas en CPU para ahorrar 50% CPU
    # En sistemas con GPU activa (usar_gpu == True), procesamos todos los fotogramas (sin salto)
    intervalo_salto = 2 if not usar_gpu else 1
    
    if conteo_fotogramas % intervalo_salto == 0 or len(ultimas_cajas) == 0:
        resultados_vehiculos = modelo_vehiculos.track(
            fotograma, persist=True, classes=[2, 3, 5, 7], verbose=False
        )
        if resultados_vehiculos[0].boxes.id is not None:
            ultimas_cajas     = resultados_vehiculos[0].boxes.xyxy.int().cpu().tolist()
            ultimos_ids_rastreo = resultados_vehiculos[0].boxes.id.int().cpu().tolist()
            ultimas_confianzas     = resultados_vehiculos[0].boxes.conf.cpu().tolist()
        else:
            ultimas_cajas     = []
            ultimos_ids_rastreo = []
            ultimas_confianzas     = []

    for box, id_rastreo, conf_vehiculo in zip(ultimas_cajas, ultimos_ids_rastreo, ultimas_confianzas):
        # Reducimos el umbral de confianza drásticamente a 0.20 para que pueda detectar 
        # vehículos a través de pantallas de celular (los reflejos bajan mucho la confianza de la IA).
        if conf_vehiculo < 0.20:
            continue

        x1, y1, x2, y2 = box

        # Obtener información almacenada en el caché
        cache = cache_placas.get(id_rastreo)

        # Dibujar etiqueta correspondiente en base al estado del caché
        if cache is not None:
            texto = cache["texto"]
            if cache["es_robado"]:
                color = NARANJA if (conteo_fotogramas // 15) % 2 == 0 else AMARILLO
                cv2.rectangle(fotograma, (x1, y1), (x2, y2), color, 3)
                dibujar_etiqueta(fotograma, f"⚠ ROBADO | {texto}", x1, y1, color, NEGRO)
                info = cache.get("info", {})
                modelo_color = f"{info.get('modelo','?')} {info.get('color','')}"
                dibujar_etiqueta(fotograma, modelo_color, x1, y2 + 20, color, NEGRO)
            else:
                cv2.rectangle(fotograma, (x1, y1), (x2, y2), VERDE, 2)
                dibujar_etiqueta(fotograma, f"[OK] {texto} | LIBRE", x1, y1, VERDE)

        # Inicializar contador de intentos de OCR para el nuevo coche
        if id_rastreo not in intentos_ocr:
            intentos_ocr[id_rastreo] = {"ultimo_fotograma": 0, "intentos": 0, "en_proceso": False}

        intentos_info = intentos_ocr[id_rastreo]
        
        # Determinar si podemos seguir escaneando para refinar la lectura:
        # - Si aún no está en caché.
        # - O si ya está en caché pero con confianza baja (< 0.85) y no hemos superado 5 intentos totales.
        conf_actual = cache["confianza"] if cache is not None else 0.0
        # Aumentamos intentos máximos a 20 y verificamos que no hay límite estricto si sigue en pantalla
        puede_escanear = (cache is None) or (conf_actual < 0.85 and intentos_info["intentos"] < 20)

        if puede_escanear:
            # Dibujar etiqueta "Escaneando..." solo si no hay una lectura inicial (para evitar sobreponer etiquetas)
            if cache is None:
                cv2.rectangle(fotograma, (x1, y1), (x2, y2), ROJO, 2)
                dibujar_etiqueta(fotograma, f"ID:{id_rastreo} Escaneando...", x1, y1, ROJO)

            # Iniciar escaneo de placa si no hay otra tarea en ejecución y pasaron al menos 5 frames
            if not intentos_info["en_proceso"] and (conteo_fotogramas - intentos_info["ultimo_fotograma"] >= 5):
                # Extraer ROI limpio antes de dibujar anotaciones en el fotograma
                roi_auto_limpio = fotograma[y1:y2, x1:x2].copy()
                if roi_auto_limpio.size == 0:
                    continue

                # Correr detector de placas en la región recortada (resolución original sin compresión)
                resultados_placas = modelo_placas(roi_auto_limpio, verbose=False)
                if len(resultados_placas[0].boxes) > 0:
                    confianza_placa = float(resultados_placas[0].boxes.conf[0])
                    # Mismo caso: bajamos a 0.20 para detectar la placa aunque la pantalla del celular brille
                    if confianza_placa >= 0.20:
                        px1, py1, px2, py2 = resultados_placas[0].boxes.xyxy[0].int().cpu().tolist()
                        roi_placa_limpio = roi_auto_limpio[py1:py2, px1:px2].copy()
                        if roi_placa_limpio.size > 0:
                            imagen_ocr = preprocesar_placa(roi_placa_limpio)
                            if imagen_ocr is not None:
                                intentos_info["ultimo_fotograma"] = conteo_fotogramas
                                intentos_info["intentos"] += 1
                                intentos_info["en_proceso"] = True
                                copia_vehiculo = roi_auto_limpio.copy()
                                copia_placa = roi_placa_limpio.copy()
                                
                                def procesar_ocr_async(id_r, img_ocr_procesada, copia_vehiculo, copia_pl):
                                    try:
                                        # Usar allowlist para acelerar la decodificación en CPU al 300% y restringir ruidos
                                        resultados_ocr = lector_ocr.readtext(img_ocr_procesada, allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                                        mejor_texto = ""
                                        mejor_confianza = 0.0
                                        for res in resultados_ocr:
                                            texto_detectado = res[1].strip().upper().replace(" ", "").replace("-", "")
                                            valor_confianza = float(res[2])
                                            # Validar largo y guardar la lectura con mayor confianza
                                            if len(texto_detectado) >= 4 and valor_confianza > mejor_confianza:
                                                mejor_texto = texto_detectado
                                                mejor_confianza = valor_confianza

                                        if mejor_confianza >= 0.25:
                                            print(f"🔍 [OCR] Auto ID {id_r} → Placa: {mejor_texto} (Conf: {mejor_confianza:.2f}, Intento: {intentos_ocr[id_r]['intentos']})")
                                            es_robado, info = db.consultar_placa(mejor_texto)
                                            
                                            # Decidir si actualizamos el caché
                                            guardar = False
                                            if id_r not in cache_placas:
                                                guardar = True
                                            else:
                                                previo = cache_placas[id_r]
                                                if mejor_confianza > previo.get("confianza", 0.0):
                                                    guardar = True
                                                if es_robado and not previo.get("es_robado", False):
                                                    guardar = True

                                            if guardar:
                                                cache_placas[id_r] = {
                                                    "texto": mejor_texto,
                                                    "es_robado": es_robado,
                                                    "info": info,
                                                    "confianza": mejor_confianza
                                                }

                                                if es_robado and id_r not in vehiculos_alertados:
                                                    vehiculos_alertados.add(id_r)
                                                    placa_bd = info.get("placa", mejor_texto)
                                                    sim      = info.get("similitud", 100)
                                                    sim_str  = f"({sim}% similitud)" if isinstance(sim, float) and sim < 100.0 else ""
                                                    print(f"\n🚨 [ALERTA] VEHÍCULO ROBADO! OCR: {mejor_texto} → BD: {placa_bd} {sim_str}")
                                                    # Guardar fotos sincrónicamente para SQLite
                                                    ruta_v, ruta_p = guardar_capturas(copia_vehiculo, copia_pl, mejor_texto)

                                                    db.registrar_alerta(
                                                        placa_bd=placa_bd,
                                                        placa_detectada=mejor_texto,
                                                        similitud=sim / 100 if isinstance(sim, float) else 1.0,
                                                        ruta_vehiculo=ruta_v,
                                                        ruta_placa=ruta_p
                                                    )
                                                    enviar_alerta_telegram(
                                                        placa_detectada=mejor_texto,
                                                        info=info,
                                                        rutas_imagenes=[ruta_v, ruta_p]
                                                    )
                                    finally:
                                        intentos_ocr[id_r]["en_proceso"] = False
                                        
                                ejecutor_ocr.submit(procesar_ocr_async, id_rastreo, imagen_ocr, copia_vehiculo, copia_placa)

    # ── Escritura del fotograma a disco (throttled a 15 FPS) ─────────────────────
    ahora = time.time()
    if ahora - _ultimo_fotograma_escrito >= INTERVALO_ESCRITURA_FOTOGRAMA:
        cv2.imwrite(ruta_fotograma, fotograma, PARAMETROS_JPEG)
        _ultimo_fotograma_escrito = ahora

    # ── Regulador de FPS: apuntar a 30 FPS de procesamiento ─────────────────
    tiempo_transcurrido = time.time() - tiempo_inicio_bucle
    retraso_restante = (1.0 / 30.0) - tiempo_transcurrido
    if retraso_restante > 0:
        time.sleep(retraso_restante)

# ─── Limpieza ─────────────────────────────────────────────────────────────────
cap.release()
cv2.destroyAllWindosocket_cliente()
print(f"\n✅ Monitoreo finalizado. "
      f"Vehículos: {len(cache_placas)} | Alertas: {len(vehiculos_alertados)}")