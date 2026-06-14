"""
servidor_ia.py — Motor de IA como Servidor WebSocket de Red Local

Arquitectura Cliente-Servidor para AlertaVecinal:
  - Este script corre en la PC SERVIDOR (potente, con GPU opcional).
  - La app Flutter se conecta a él por WebSocket desde cualquier PC de la red local.
  - Multi-cliente: N clientes pueden conectarse y recibir el mismo feed sin overhead adicional.
  - Autónomo: Las alertas de Telegram y detección de placas funcionan sin clientes conectados.
  - Auto-descubrimiento: Se anuncia en la red local con mDNS para que Flutter lo encuentre solo.

Uso:
    pip install -r requirements_server.txt
    python servidor_ia.py [--video 0] [--port 8765]

Protocolo WebSocket (JSON):
  Servidor → Cliente:
    {"type": "fotograma",   "data": "<base64_jpeg>", "fps": 30.1, "clients": 2}
    {"type": "alert",   "placa": "ABC123", "es_robado": true, "placa_bd": "ABC123",
                        "similitud": 100.0, "modelo": "Toyota", "color": "Blanco",
                        "id_rastreo": 5, "timestamp": "2025-01-10T14:23:00"}
    {"type": "cameras", "list": [{"index": 0, "name": "Webcam HD"}]}
    {"type": "history", "alerts": [...]}   ← al conectarse, últimas 15 alertas
    {"type": "status",  "ai": "running", "camera": "USB 0", "fps": 29.8}

  Cliente → Servidor:
    {"cmd": "list_cameras"}
    {"cmd": "change_camera", "index": 1}
    {"cmd": "change_camera_url", "url": "rtsp://192.168.1.50/stream"}
    {"cmd": "get_history", "limite_historial": 15}
"""

import os
import sys
import warnings
import asyncio
import base64
import json
import threading
import time
import argparse
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

warnings.filterwarnings("ignore", category=UserWarning)
sys.stdout.reconfigure(line_buffering=True)

# ─── Dependencias ────────────────────────────────────────────────────────────

import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn

# mDNS para auto-descubrimiento (zeroconf)
try:
    from zeroconf import ServiceInfo, Zeroconf
    MDNS_DISPONIBLE = True
except ImportError:
    MDNS_DISPONIBLE = False
    print("[mDNS] zeroconf no instalado — auto-descubrimiento desactivado. "
          "Instala con: pip install zeroconf")

from database import DatabasePlacas
from alerta_telegram import enviar_alerta_telegram, guardar_capturas

# ─── Argumentos ──────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Servidor IA AlertaVecinal — WebSocket")
parser.add_argument("--video", type=str, default="0",
                    help="Índice de cámara USB (0,1,2...) o URL RTSP/HTTP")
parser.add_argument("--port", type=int, default=8765,
                    help="Puerto WebSocket del servidor (default: 8765)")
args = parser.parse_args()

SERVER_PORT = args.port

# ─── Rutas de recursos ────────────────────────────────────────────────────────

def resource_path(relative_path: str) -> str:
    """Ruta absoluta compatible con PyInstaller y modo dev."""
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)


# ─── Estado Global del Servidor ──────────────────────────────────────────────

class EstadoServidor:
    """Estado compartido entre el bucle de IA y los WebSockets."""

    def __init__(self):
        # Clientes WebSocket conectados
        self.clientes: set[WebSocket] = set()
        self.bloqueo_clientes = asyncio.Lock()

        # Fotograma actual codificado en JPEG bytes (ya procesado por la IA)
        self.frame_actual: bytes | None = None
        self.bloqueo_fotograma = threading.Lock()

        # Cámara y fuente de video
        self.origen_video: str = args.video
        self.cap: cv2.VideoCapture | None = None
        self.cambio_camara_solicitado: str | None = None

        # Cámaras disponibles detectadas
        self.camaras_disponibles: list[dict] = []

        # IA running
        self.inteligencia_artificial_ejecutandose = False
        self.fps_actual = 0.0

        # Alertas históricas (en RAM, últimas 100)
        self.historial_alertas: list[dict] = []
        self.bloqueo_historial = threading.Lock()

        # Event loop del servidor (se asigna al arrancar uvicorn)
        self.loop: asyncio.AbstractEventLoop | None = None

        # Datos compartidos para el hilo de streaming a 60 FPS
        self.ultimas_cajas = []
        self.ultimos_ids_rastreo = []
        self.ultimas_confianzas = []
        self.cache_placas = {}
        self.intentos_ocr = {}
        self.conteo_fotogramas = 0
        self.fotograma_crudo = None
        self.ref_hilo_camara = None


estado = EstadoServidor()

# ─── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(title="AlertaVecinal IA Server")


@app.get("/health")
async def health():
    """Endpoint de verificación de estado — usado por Flutter para confirmar que el servidor existe."""
    return JSONResponse({
        "status": "ok",
        "ia": "running" if estado.inteligencia_artificial_ejecutandose else "iniciando",
        "fps": round(estado.fps_actual, 1),
        "clients": len(estado.clientes),
        "camera": estado.origen_video,
        "cameras": estado.camaras_disponibles,
    })


@app.websocket("/ws")
async def punto_enlace_socket(socket_cliente: WebSocket):
    await socket_cliente.accept()
    async with estado.bloqueo_clientes:
        estado.clientes.add(socket_cliente)
    n = len(estado.clientes)
    print(f"[WS] ✅ Cliente conectado. Total: {n}")

    # Enviar historial inmediatamente al conectarse
    with estado.bloqueo_historial:
        instantanea_historial = list(estado.historial_alertas[-15:])
    await _enviar_seguro(socket_cliente, {"type": "history", "alerts": instantanea_historial})

    # Enviar estado inicial
    await _enviar_seguro(socket_cliente, {
        "type": "status",
        "ai": "running" if estado.inteligencia_artificial_ejecutandose else "iniciando",
        "camera": estado.origen_video,
        "fps": round(estado.fps_actual, 1),
        "cameras": estado.camaras_disponibles,
    })

    try:
        while True:
            try:
                datos_crudos = await asyncio.wait_for(socket_cliente.receive_text(), timeout=30.0)
                await _procesar_comando(socket_cliente, datos_crudos)
            except asyncio.TimeoutError:
                # Ping periódico para mantener la conexión viva
                await _enviar_seguro(socket_cliente, {"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Error cliente: {e}")
    finally:
        async with estado.bloqueo_clientes:
            estado.clientes.discard(socket_cliente)
        print(f"[WS] ❌ Cliente desconectado. Total: {len(estado.clientes)}")


async def _enviar_seguro(socket_cliente: WebSocket, data: dict) -> bool:
    """Envía JSON a un cliente, retorna False si falló."""
    try:
        await socket_cliente.send_text(json.dumps(data, ensure_ascii=False))
        return True
    except Exception:
        return False


async def _procesar_comando(socket_cliente: WebSocket, datos_crudos: str):
    """Procesa comandos recibidos desde un cliente Flutter."""
    try:
        cmd = json.loads(datos_crudos)
    except Exception:
        return

    action = cmd.get("cmd", "")

    if action == "list_cameras":
        # Escanear las cámaras USB en tiempo real en un hilo secundario para no bloquear el WebSocket
        def escanear_y_responder():
            estado.camaras_disponibles = detectar_camaras_usb()
            if estado.loop and not estado.loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    _enviar_seguro(socket_cliente, {"type": "cameras", "list": estado.camaras_disponibles}),
                    estado.loop
                )
        threading.Thread(target=escanear_y_responder, daemon=True).start()

    elif action == "change_camera":
        index = cmd.get("index", 0)
        estado.cambio_camara_solicitado = str(index)
        await _enviar_seguro(socket_cliente, {"type": "status", "ai": "switching", "camera": str(index), "fps": 0})

    elif action == "change_camera_url":
        url = cmd.get("url", "")
        if url:
            estado.cambio_camara_solicitado = url
            await _enviar_seguro(socket_cliente, {"type": "status", "ai": "switching", "camera": url, "fps": 0})

    elif action == "get_history":
        limite_historial = int(cmd.get("limite_historial", 15))
        with estado.bloqueo_historial:
            hist = list(estado.historial_alertas[-limite_historial:])
        await _enviar_seguro(socket_cliente, {"type": "history", "alerts": hist})


async def _difundir_fotograma(bytes_fotograma: bytes):
    """Envía el fotograma procesado a TODOS los clientes conectados como bytes binarios.
    
    Protocolo binario: los primeros 4 bytes son un header JSON codificado en UTF-8
    cuyo tamaño está dado por los primeros 4 bytes (uint32 big-endian).
    El resto son los bytes JPEG crudos.
    
    Para compatibilidad simple, usamos un prefijo JSON de longitud fija:
    - Primero se envía un frame JSON con metadata (fps, clients)
    - Luego los bytes JPEG crudos directamente como mensaje binario
    """
    if not estado.clientes:
        return

    # Enviar metadatos como JSON de texto
    meta = json.dumps({
        "type": "frame_meta",
        "fps": round(estado.fps_actual, 1),
        "clients": len(estado.clientes),
        "size": len(bytes_fotograma),
    })

    async with estado.bloqueo_clientes:
        instantanea_clientes = list(estado.clientes)

    muertos = []
    for socket_cliente in instantanea_clientes:
        try:
            # Enviar metadatos
            await socket_cliente.send_text(meta)
            # Enviar frame JPEG como bytes binarios (sin base64 — mucho más rápido)
            await socket_cliente.send_bytes(bytes_fotograma)
        except Exception:
            muertos.append(socket_cliente)

    if muertos:
        async with estado.bloqueo_clientes:
            for socket_cliente in muertos:
                estado.clientes.discard(socket_cliente)


async def _difundir_evento(data: dict):
    """Envía un evento JSON (alerta, status, etc.) a TODOS los clientes."""
    if not estado.clientes:
        return
    carga_util_datos = json.dumps(data, ensure_ascii=False)
    async with estado.bloqueo_clientes:
        instantanea_clientes = list(estado.clientes)
    muertos = []
    for socket_cliente in instantanea_clientes:
        try:
            await socket_cliente.send_text(carga_util_datos)
        except Exception:
            muertos.append(socket_cliente)
    if muertos:
        async with estado.bloqueo_clientes:
            for socket_cliente in muertos:
                estado.clientes.discard(socket_cliente)


def _registrar_alerta_local(alerta: dict):
    """Agrega una alerta al historial en RAM (máx 100)."""
    with estado.bloqueo_historial:
        estado.historial_alertas.append(alerta)
        if len(estado.historial_alertas) > 100:
            estado.historial_alertas.pop(0)


def _emitir_alerta(alerta: dict):
    """Emite una alerta a todos los clientes desde el hilo de IA (thread-safe)."""
    _registrar_alerta_local(alerta)
    if estado.loop and not estado.loop.is_closed():
        asyncio.run_coroutine_threadsafe(_difundir_evento(alerta), estado.loop)


def _emitir_fotograma(bytes_fotograma: bytes):
    """Emite un fotograma a todos los clientes desde el hilo de IA (thread-safe)."""
    if estado.loop and not estado.loop.is_closed() and estado.clientes:
        asyncio.run_coroutine_threadsafe(_difundir_fotograma(bytes_fotograma), estado.loop)


# ─── Utilidades de video ─────────────────────────────────────────────────────


# ─── Captura de Pantalla ─────────────────────────────────────────────────────

try:
    import mss
except ImportError:
    pass
import ctypes
from ctypes import wintypes

class CapturaPantalla:
    def __init__(self, monitor_id=1):
        self.abierto = True
        self.sct = None
        
    def isOpened(self):
        return self.abierto
        
    def read(self):
        if not self.abierto:
            return False, None
            
        if self.sct is None:
            self.sct = mss.mss()
            
        # Intentar localizar la ventana activa de YI IOT buscando por proceso
        rect_ventana = None
        try:
            import psutil
            pids = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name']
                    if name and ('yiiot' in name.lower() or 'yi_iot' in name.lower() or 'yi' in name.lower()):
                        if 'client' in name.lower() or 'yiiot' in name.lower():
                            pids.append(proc.info['pid'])
                except Exception:
                    pass
            
            if pids:
                max_area = 0
                rect_temp = ctypes.wintypes.RECT()
                
                def foreach_window(hwnd, lParam):
                    nonlocal rect_ventana, max_area
                    win_pid = ctypes.c_ulong()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
                    if win_pid.value in pids:
                        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect_temp))
                        w = rect_temp.right - rect_temp.left
                        h = rect_temp.bottom - rect_temp.top
                        if rect_temp.left > -10000 and rect_temp.top > -10000:
                            if w > 200 and h > 200:
                                area = w * h
                                if area > max_area:
                                    max_area = area
                                    rect_ventana = (rect_temp.left, rect_temp.top, w, h)
                    return True
                
                ctypes.windll.user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))(foreach_window), None)
        except Exception:
            pass

        if rect_ventana:
            region = {
                "top": rect_ventana[1],
                "left": rect_ventana[0],
                "width": rect_ventana[2],
                "height": rect_ventana[3]
            }
            try:
                sct_img = self.sct.grab(region)
                import numpy as np
                import cv2
                img_bgra = np.array(sct_img)
                img_bgr = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2BGR)
                return True, img_bgr
            except Exception as e:
                print(f"Error al capturar region de ventana: {e}")
                pass
                        
        # Si la app oficial no está abierta, hacer respaldo al monitor primario
        monitor = self.sct.monitors[1] if len(self.sct.monitors) > 1 else self.sct.monitors[0]
        try:
            sct_img = self.sct.grab(monitor)
            import numpy as np
            import cv2
            img_bgra = np.array(sct_img)
            img_bgr = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2BGR)
            return True, img_bgr
        except Exception as e:
            print(f"Error al capturar monitor primario: {e}")
            return False, None
        
    def release(self):
        self.abierto = False
        if self.sct:
            try:
                self.sct.close()
            except Exception:
                pass
            self.sct = None

    def set(self, propId, value):
        pass

def abrir_captura(fuente_str: str) -> cv2.VideoCapture:
    if fuente_str.lower() in ("pantalla", "screen", "999"):
        print("🖥️  Capturando ventana oficial YI IOT...")
        return CapturaPantalla()

    if fuente_str.isdigit():
        idx = int(fuente_str)
        print(f"📹 Abriendo cámara USB índice {idx}...")
        backends = [(cv2.CAP_DSHOW, "DSHOW"), (cv2.CAP_MSMF, "MSMF"), (cv2.CAP_ANY, "ANY")]
        for backend, nombre in backends:
            c = cv2.VideoCapture(idx, backend)
            if c.isOpened():
                ok = False
                for _ in range(30):
                    ret, fot = c.read()
                    if ret and fot is not None:
                        ok = True
                        break
                    time.sleep(0.1)
                if ok:
                    print(f"   ✅ Backend {nombre} funciona correctamente.")
                    return c
                c.release()
        raise Exception(f"No se pudo abrir la cámara USB {idx}.")
    elif fuente_str.lower().startswith("rtsp://"):
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
        cap = cv2.VideoCapture(fuente_str, cv2.CAP_FFMPEG)
        print(f"📡 Cámara RTSP: {fuente_str}")
    else:
        cap = cv2.VideoCapture(fuente_str)
        print(f"🌐 Fuente: {fuente_str}")
    if not cap.isOpened():
        raise Exception(f"No se pudo abrir: {fuente_str}")
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def detectar_camaras_usb() -> list[dict]:
    """Detecta cámaras USB disponibles en Windows."""
    camaras = []
    for i in range(8):
        c = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if c.isOpened():
            ret, _ = c.read()
            if ret:
                camaras.append({"index": i, "name": f"Cámara USB {i}"})
            c.release()
        else:
            c.release()
    if not camaras:
        camaras.append({"index": 0, "name": "Cámara Predeterminada"})
    camaras.insert(0, {"index": 999, "name": "📹 Cámara Oficial YI IOT"})
    return camaras


# ─── Utilidades de dibujo ─────────────────────────────────────────────────────

ROJO    = (0,   0,   255)
VERDE   = (0,   200,  50)
NARANJA = (0,   130, 255)
BLANCO  = (255, 255, 255)
NEGRO   = (0,     0,   0)
AMARILLO= (0,   220, 255)


def dibujar_etiqueta(fotograma, texto, x1, y1, color_fondo, color_texto=BLANCO, escala=0.55):
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    grosor = 1
    (ancho, alto), _ = cv2.getTextSize(texto, fuente, escala, grosor + 1)
    cv2.rectangle(fotograma, (x1, y1 - alto - 8), (x1 + ancho + 6, y1), color_fondo, -1)
    cv2.putText(fotograma, texto, (x1 + 3, y1 - 4), fuente, escala, color_texto, grosor + 1, cv2.LINE_AA)


def preprocesar_placa(roi_placa):
    h, w = roi_placa.shape[:2]
    if h == 0:
        return None
    scale = 100.0 / h
    resized = cv2.resize(roi_placa, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    gaussian = cv2.GaussianBlur(resized, (5, 5), 2.0)
    return cv2.addWeighted(resized, 1.5, gaussian, -0.5, 0)


# ─── Hilo de captura de cámara ────────────────────────────────────────────────

class HiloCapturaCamara:
    def __init__(self, cap, fuente):
        self.cap = cap
        self.fuente = fuente
        self.ultimo_fotograma = None
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        fallos_consecutivos = 0
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                print(f"[Cámara] ⚠️  Conexión perdida con la fuente {self.fuente}. Reintentando conectar en 2s...")
                time.sleep(2.0)
                try:
                    self.cap = abrir_captura(self.fuente)
                    print("[Cámara] ✅ Reconexión exitosa tras pérdida de señal.")
                except Exception as e:
                    print(f"[Cámara] ❌ Error al intentar reconectar: {e}")
                continue

            ret, fotograma = self.cap.read()
            if not ret or fotograma is None:
                fallos_consecutivos += 1
                # Si fallan más de 30 frames consecutivos (~2 segundos a 15fps), asumimos desconexión o suspensión del equipo
                if fallos_consecutivos > 30:
                    print("[Cámara] ⚠️  Múltiples fallos consecutivos de fotogramas (posible suspensión/bloqueo). Liberando y reconectando...")
                    try:
                        self.cap.release()
                    except Exception:
                        pass
                    self.cap = None
                    fallos_consecutivos = 0
                time.sleep(0.05)
                continue
            
            fallos_consecutivos = 0
            with self.lock:
                self.ultimo_fotograma = fotograma.copy()

    def read(self):
        with self.lock:
            if self.ultimo_fotograma is None:
                return False, None
            return True, self.ultimo_fotograma.copy()

    def stop(self):
        self.running = False
        self.thread.join(timeout=2)


# ─── Bucle Principal de IA (corre en un hilo separado) ───────────────────────

def bucle_inteligencia_artificial():
    """
    Bucle principal de la IA — idéntico al main.py original.
    Corre en un hilo de fondo, completamente autónomo.
    Las alertas de Telegram se envían independientemente de si hay clientes conectados.
    """
    print("🤖 Cargando modelos de IA...")
    modelo_vehiculos = YOLO(resource_path("yolo11n.pt"))
    modelo_placas    = YOLO(resource_path("runs/detect/license_plate_detector/weights/best.pt"))

    usar_gpu = torch.cuda.is_available()
    print(f"⚡ GPU para OCR: {'Sí (CUDA)' if usar_gpu else 'No (CPU)'}")
    lector_ocr = easyocr.Reader(['en'], gpu=usar_gpu)

    db = DatabasePlacas()

    try:
        cap = abrir_captura(estado.origen_video)
    except Exception as e:
        print(f"⚠️ [IA] Error inicial abriendo cámara {estado.origen_video}: {e}. El servidor continuará ejecutándose y reintentando...")
        cap = None
    hilo_camara = HiloCapturaCamara(cap, estado.origen_video)
    estado.ref_hilo_camara = hilo_camara
    ejecutor_ocr = ThreadPoolExecutor(max_workers=2)

    cache_placas        = {}
    vehiculos_alertados = set()
    intentos_ocr        = {}
    conteo_fotogramas         = 0
    ultimas_cajas          = []
    ultimos_ids_rastreo      = []
    ultimas_confianzas          = []

    PARAMETROS_JPEG = [cv2.IMWRITE_JPEG_QUALITY, 75]
    INTERVALO_EMISION_FOTOGRAMA = 1.0 / 60.0  # Hasta 60 FPS de emisión
    ultimo_emit = 0.0

    estado.inteligencia_artificial_ejecutandose = True
    intervalo_salto = 2 if not usar_gpu else 1

    print(f"📹 Servidor IA activo — transmitiendo en socket_cliente://0.0.0.0:{SERVER_PORT}/socket_cliente\n")

    while True:
        try:
            inicio = time.time()

            # ── Cambio de cámara solicitado por un cliente Flutter ────────────────
            if estado.cambio_camara_solicitado is not None:
                nueva_fuente = estado.cambio_camara_solicitado
                estado.cambio_camara_solicitado = None
                print(f"[IA] Cambiando a fuente: {nueva_fuente}")
                hilo_camara.stop()
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
                estado.origen_video = nueva_fuente
                try:
                    cap = abrir_captura(nueva_fuente)
                except Exception as e:
                    print(f"⚠️ [IA] Error al cambiar a cámara {nueva_fuente}: {e}. Intentando reconectar en segundo plano...")
                    cap = None
                hilo_camara = HiloCapturaCamara(cap, nueva_fuente)
                estado.ref_hilo_camara = hilo_camara
                cache_placas.clear()
                vehiculos_alertados.clear()
                intentos_ocr.clear()
                conteo_fotogramas = 0

            ret, fotograma = hilo_camara.read()
            if not ret:
                time.sleep(0.05)
                continue
                
            with estado.bloqueo_fotograma:
                estado.fotograma_crudo = fotograma.copy()

            conteo_fotogramas += 1

            # ── Detección YOLO de vehículos ───────────────────────────────────────
            if conteo_fotogramas % intervalo_salto == 0 or not ultimas_cajas:
                resultados_v = modelo_vehiculos.track(
                    fotograma, persist=True, classes=[2, 3, 5, 7], verbose=False
                )
                if resultados_v[0].boxes.id is not None:
                    ultimas_cajas     = resultados_v[0].boxes.xyxy.int().cpu().tolist()
                    ultimos_ids_rastreo = resultados_v[0].boxes.id.int().cpu().tolist()
                    ultimas_confianzas     = resultados_v[0].boxes.conf.cpu().tolist()
                else:
                    ultimas_cajas, ultimos_ids_rastreo, ultimas_confianzas = [], [], []
        except Exception as e:
            import traceback
            print(f"[AI Loop Error] {e}")
            traceback.print_exc()
            time.sleep(0.1)
            continue

        # ── Anotación y OCR ───────────────────────────────────────────────────
        for box, id_rastreo, conf_vehiculo in zip(ultimas_cajas, ultimos_ids_rastreo, ultimas_confianzas):
            if conf_vehiculo < 0.20:
                continue

            x1, y1, x2, y2 = box
            cache = cache_placas.get(id_rastreo)

            if id_rastreo not in intentos_ocr:
                intentos_ocr[id_rastreo] = {"ultimo_fotograma": 0, "intentos": 0, "en_proceso": False}

            intentos_info = intentos_ocr[id_rastreo]
            conf_actual = cache["confianza"] if cache else 0.0
            puede_escanear = (cache is None) or (conf_actual < 0.85 and intentos_info["intentos"] < 20)

            if puede_escanear:
                if not intentos_info["en_proceso"] and (conteo_fotogramas - intentos_info["ultimo_fotograma"] >= 5):
                    roi_auto = fotograma[y1:y2, x1:x2].copy()
                    if roi_auto.size == 0:
                        continue
                    resultados_p = modelo_placas(roi_auto, verbose=False)
                    if len(resultados_p[0].boxes) > 0:
                        confianza_p = float(resultados_p[0].boxes.conf[0])
                        if confianza_p >= 0.20:
                            px1, py1, px2, py2 = resultados_p[0].boxes.xyxy[0].int().cpu().tolist()
                            roi_placa = roi_auto[py1:py2, px1:px2].copy()
                            if roi_placa.size > 0:
                                img_ocr_procesada = preprocesar_placa(roi_placa)
                                if img_ocr_procesada is not None:
                                    intentos_info["ultimo_fotograma"] = conteo_fotogramas
                                    intentos_info["intentos"] += 1
                                    intentos_info["en_proceso"] = True
                                    copia_vehiculo = roi_auto.copy()
                                    copia_placa = roi_placa.copy()

                                    def _ocr_task(id_r, img, veh, pl):
                                        try:
                                            res_ocr = lector_ocr.readtext(
                                                img,
                                                allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                                            )
                                            mejor_texto, mejor_confianza = "", 0.0
                                            for r in res_ocr:
                                                txt = r[1].strip().upper().replace(" ", "").replace("-", "")
                                                c = float(r[2])
                                                if len(txt) >= 4 and c > mejor_confianza:
                                                    mejor_texto, mejor_confianza = txt, c

                                            if mejor_confianza >= 0.25:
                                                print(f"🔍 [OCR] ID {id_r} → {mejor_texto} (Conf: {mejor_confianza:.2f})")
                                                es_robado, info = db.consultar_placa(mejor_texto)

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
                                                        "confianza": mejor_confianza,
                                                    }
                                                    if es_robado:
                                                        alerta = {
                                                            "type": "alert",
                                                            "placa": mejor_texto,
                                                            "es_robado": True,
                                                            "placa_bd": info.get("placa", mejor_texto) if info else mejor_texto,
                                                            "similitud": info.get("similitud", 100.0) if info else 100.0,
                                                            "modelo": info.get("modelo", "?") if info else "?",
                                                            "color": info.get("color", "?") if info else "?",
                                                            "propietario": info.get("propietario", "?") if info else "?",
                                                            "id_rastreo": id_r,
                                                            "timestamp": datetime.now().isoformat(),
                                                        }
                                                        if id_r not in vehiculos_alertados:
                                                            vehiculos_alertados.add(id_r)
                                                            print(f"\n🚨 [ALERTA] VEHÍCULO ROBADO: {mejor_texto}")
                                                            ruta_v, ruta_p = guardar_capturas(veh, pl, mejor_texto)
                                                            db.registrar_alerta(
                                                                placa_bd=info.get("placa", mejor_texto) if info else mejor_texto,
                                                                placa_detectada=mejor_texto,
                                                                similitud=(info.get("similitud", 100) / 100
                                                                           if isinstance(info.get("similitud"), float)
                                                                           else 1.0) if info else 1.0,
                                                                ruta_vehiculo=ruta_v,
                                                                ruta_placa=ruta_p,
                                                            )
                                                            alerta["foto_vehiculo"] = ruta_v
                                                            alerta["foto_placa"] = ruta_p
                                                            enviar_alerta_telegram(
                                                                placa_detectada=mejor_texto,
                                                                info=info,
                                                                rutas_imagenes=[ruta_v, ruta_p]
                                                            )
                                                        _emitir_alerta(alerta)
                                        finally:
                                            intentos_ocr[id_r]["en_proceso"] = False

                                    ejecutor_ocr.submit(_ocr_task, id_rastreo, img_ocr_procesada, copia_vehiculo, copia_placa)

        # Update global state for ddatos_crudosing thread
        with estado.bloqueo_fotograma:
            estado.ultimas_cajas = ultimas_cajas
            estado.ultimos_ids_rastreo = ultimos_ids_rastreo
            estado.ultimas_confianzas = ultimas_confianzas
            estado.cache_placas = dict(cache_placas)
            estado.intentos_ocr = dict(intentos_ocr)
            estado.conteo_fotogramas = conteo_fotogramas

        # ── FPS de la Inteligencia Artificial ─────────────────────────────────────────────────────────
        tiempo_transcurrido_total = time.time() - inicio
        estado.fps_actual = 1.0 / tiempo_transcurrido_total if tiempo_transcurrido_total > 0 else 60.0


# ─── mDNS / Auto-descubrimiento ──────────────────────────────────────────────

def iniciar_mdns():
    """Anuncia el servidor en la red local para que Flutter lo encuentre automáticamente."""
    if not MDNS_DISPONIBLE:
        return

    try:
        # Obtener IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()

        ip_bytes = socket.inet_aton(ip_local)

        info = ServiceInfo(
            "_alertavecinal._tcp.local.",
            f"ServidorIA._alertavecinal._tcp.local.",
            addresses=[ip_bytes],
            port=SERVER_PORT,
            properties={
                "version": b"1.0",
                "app": b"AlertaVecinal",
                "socket_cliente_path": b"/socket_cliente",
                "health": b"/health",
            },
        )

        zeroconf = Zeroconf()
        zeroconf.register_service(info)
        print(f"[mDNS] ✅ Servidor anunciado en la red — {ip_local}:{SERVER_PORT}")
        print(f"[mDNS] Flutter lo encontrará automáticamente en la red local.\n")
        return zeroconf, info
    except Exception as e:
        print(f"[mDNS] No se pudo iniciar el anuncio: {e}")
        return None, None


# ─── Bucle de Streaming (60 FPS) ─────────────────────────────────────────────

def trabajador_transmision():
    """
    Lee el último fotograma capturado y los últimos resultados de la IA,
    dibuja los recuadros y lo transmite a los clientes Flutter a 60 FPS.
    """
    interval = 1.0 / 60.0
    ultimo_emit = 0.0
    PARAMETROS_JPEG = [cv2.IMWRITE_JPEG_QUALITY, 75]
    
    while True:
        if not estado.inteligencia_artificial_ejecutandose or estado.ref_hilo_camara is None:
            time.sleep(0.1)
            continue
            
        ahora = time.time()
        if ahora - ultimo_emit >= interval:
            try:
                ret, fotograma_crudo = estado.ref_hilo_camara.read()
                if ret and fotograma_crudo is not None:
                    fotograma = fotograma_crudo.copy()
                    
                    with estado.bloqueo_fotograma:
                        boxes = list(estado.ultimas_cajas)
                        ids_rastreo = list(estado.ultimos_ids_rastreo)
                        confianzas = list(estado.ultimas_confianzas)
                        copia_cache = dict(estado.cache_placas)
                        copia_intentos = dict(estado.intentos_ocr)
                        conteo_f = estado.conteo_fotogramas

                    # Dibujar IA
                    for box, id_rastreo, conf_vehiculo in zip(boxes, ids_rastreo, confianzas):
                        if conf_vehiculo < 0.20:
                            continue
                        x1, y1, x2, y2 = box
                        cache = copia_cache.get(id_rastreo)
                        
                        if cache is not None:
                            texto = cache["texto"]
                            if cache["es_robado"]:
                                color = NARANJA if (conteo_f // 15) % 2 == 0 else AMARILLO
                                cv2.rectangle(fotograma, (x1, y1), (x2, y2), color, 3)
                                dibujar_etiqueta(fotograma, f"⚠ ROBADO | {texto}", x1, y1, color, NEGRO)
                                info = cache.get("info", {})
                                dibujar_etiqueta(fotograma, f"{info.get('modelo','?')} {info.get('color','')}", x1, y2 + 20, color, NEGRO)
                            else:
                                cv2.rectangle(fotograma, (x1, y1), (x2, y2), VERDE, 2)
                                dibujar_etiqueta(fotograma, f"[OK] {texto} | LIBRE", x1, y1, VERDE)
                                
                        intentos_info = copia_intentos.get(id_rastreo)
                        if intentos_info is not None:
                            conf_actual = cache["confianza"] if cache else 0.0
                            puede_escanear = (cache is None) or (conf_actual < 0.85 and intentos_info["intentos"] < 20)
                            if puede_escanear and cache is None:
                                cv2.rectangle(fotograma, (x1, y1), (x2, y2), ROJO, 2)
                                dibujar_etiqueta(fotograma, f"ID:{id_rastreo} Escaneando...", x1, y1, ROJO)
                    
                    _, buf = cv2.imencode(".jpg", fotograma, PARAMETROS_JPEG)
                    _emitir_fotograma(buf.tobytes())
                    ultimo_emit = time.time()
            except Exception as e:
                import traceback
                print(f"[Streaming Error] {e}")
                traceback.print_exc()
                
            time.sleep(max(0.001, interval - (time.time() - ahora)))
        else:
            time.sleep(0.005)


# ─── Punto de entrada ────────────────────────────────────────────────────────

def liberar_puerto_si_ocupado(port: int):
    """
    Detecta si el puerto de red está ocupado.
    Si lo está, busca el PID del proceso huérfano responsable (especialmente en Windosocket_cliente)
    y lo termina de forma segura para permitir que este nuevo servidor se enlace sin fallas.
    """
    import socket
    import subprocess
    import os
    
    try:
        # Intentar enlazar el puerto de manera local para verificar disponibilidad
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.close()
    except OSError:
        print(f"\n[Puerto {port}] ⚠️  ¡El puerto ya está ocupado! Iniciando autorecuperación...")
        try:
            pids = set()
            if os.name == 'nt':
                # netstat en Windosocket_cliente para buscar el PID que escucha en el puerto
                output = subprocess.check_output(
                    f'netstat -ano | findstr LISTENING | findstr :{port}', 
                    shell=True
                ).decode('utf-8', errors='ignore')
                for line in output.strip().split('\n'):
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid_str = parts[-1]
                        if pid_str.isdigit() and int(pid_str) != os.getpid():
                            pids.add(int(pid_str))
            else:
                # lsof / fuser en sistemas POSIX
                output = subprocess.check_output(
                    f'lsof -t -i:{port}', 
                    shell=True
                ).decode('utf-8', errors='ignore')
                for line in output.strip().split('\n'):
                    if line.strip().isdigit() and int(line.strip()) != os.getpid():
                        pids.add(int(line.strip()))

            for pid in pids:
                print(f"[Puerto {port}] 🛠️ Terminando proceso huérfano bloqueador con PID {pid}...")
                if os.name == 'nt':
                    subprocess.run(
                        f'taskkill /F /PID {pid}', 
                        shell=True, 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL
                    )
                else:
                    import signal
                    os.kill(pid, signal.SIGKILL)
            
            # Pequeña pausa para permitir que el sistema operativo libere el socket de red
            time.sleep(1.5)
            print(f"[Puerto {port}] ✅ Autorecuperación exitosa. Puerto liberado.\n")
        except Exception as e:
            print(f"[Puerto {port}] ❌ No se pudo liberar el puerto automáticamente: {e}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("  🖥️  AlertaVecinal — Servidor IA de Red Local")
    print("=" * 60)
    print(f"  Puerto WebSocket : {SERVER_PORT}")
    print(f"  Fuente de video  : {args.video}")
    print("=" * 60 + "\n")

    # Autorecuperación de puertos activa antes de iniciar el servidor
    liberar_puerto_si_ocupado(SERVER_PORT)

    # Detectar cámaras disponibles al arrancar
    estado.camaras_disponibles = detectar_camaras_usb()
    print(f"📷 Cámaras detectadas: {[c['name'] for c in estado.camaras_disponibles]}")

    # Anunciar en red local con mDNS
    zc, zc_info = None, None
    zc, zc_info = iniciar_mdns()

    # Arrancar la IA en un hilo de fondo (autónomo, no bloquea el servidor WebSocket)
    hilo_ia = threading.Thread(target=bucle_inteligencia_artificial, daemon=True)
    hilo_ia.start()
    
    # Arrancar el hilo de streaming de 60 FPS
    hilo_streaming = threading.Thread(target=trabajador_transmision, daemon=True)
    hilo_streaming.start()

    # Capturar el event loop de asyncio una vez que uvicorn lo crea
    @app.on_event("startup")
    async def _capturar_loop():
        estado.loop = asyncio.get_running_loop()

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=SERVER_PORT,
            log_level="warning",  # Solo errores en consola — el hilo de IA imprime lo importante
            ws_max_size=64 * 1024 * 1024,  # 64 MB — necesario para frames JPEG en Base64
        )
    finally:
        if zc and zc_info:
            zc.unregister_service(zc_info)
            zc.close()
