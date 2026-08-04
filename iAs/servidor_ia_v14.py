# -*- coding: utf-8 -*-
"""
servidor_ia_v14.py — Plataforma SaaS Multiusuario de IA para Reconocimiento de Placas V14

Esta versión implementa una arquitectura SaaS Multi-tenant optimizada:
  1. Base de datos para cuentas de usuario (`cuentas_usuario`) con contraseñas cifradas (SHA256 + Sal).
  2. Endpoints HTTP para registro (`/api/register`), inicio de sesión (`/api/login`) y configuración de cámara/alertas (`/api/config`).
  3. Autenticación WebSocket por Token Seguro (`/ws/{token}`).
  4. Pipelines de procesamiento independientes por usuario (Clase `UserPipeline`), permitiendo que múltiples usuarios
     procesen sus propias cámaras RTSP en paralelo sobre la GPU T4 sin interferir entre sí.
  5. Envío de alertas de Telegram personalizadas según el Chat ID y Token de cada usuario.
  6. CORRECCIÓN DE PERSPECTIVA V14: Mejora la precisión del OCR corrigiendo inclinación de la placa.
  7. EJECUCIÓN PERSISTENTE 24/7: La IA no se detiene cuando el usuario cierra la app, sigue monitoreando y alertando.
  8. SUSPENSIÓN DE STREAMING INACTIVO: Ahorra GPU al suspender la codificación de video si no hay clientes visualizándolo.
"""

import os
import sys
import warnings
import asyncio
import base64
import json
import queue
import threading
import time
import argparse
import socket
import re
import csv
import secrets
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from collections import defaultdict, Counter
from PIL import Image

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from paddleocr import PaddleOCR
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from databases.database import DatabasePlacas, obtener_conexion

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(line_buffering=True)

# ─── Argumentos del Servidor ──────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Servidor IA SaaS AlertaVecinal — WebSocket V14")
parser.add_argument("--port", type=int, default=8765, help="Puerto del servidor (default: 8765)")
args, unknown = parser.parse_known_args()
SERVER_PORT = args.port

# ─── Inicialización de Base de Datos y Modelos Globales (Memoria Compartida) ───

db_global = DatabasePlacas()

# Cargamos los modelos de YOLO una sola vez en memoria de la GPU/CPU para ahorrar recursos
usar_gpu = torch.cuda.is_available()
print(f"⚡ GPU CUDA disponible para modelos de IA: {'SÍ' if usar_gpu else 'NO'}")

def resource_path(relative_path: str) -> str:
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)

print("🤖 Cargando modelo base de vehículos YOLOv11...")
modelo_vehiculos_global = YOLO(resource_path("yolo11n.pt"))

print("🤖 Cargando modelo de detección de placas...")
modelo_placas_global = YOLO(resource_path("runs/detect/license_plate_detector/weights/best.pt"))

print("⚡ Inicializando PaddleOCR...")
try:
    reader_ocr_global = PaddleOCR(use_angle_cls=False, lang='en', use_gpu=False)
except Exception as e:
    print(f"❌ Error al inicializar PaddleOCR: {e}")
    sys.exit(1)

# ─── Utilidades de Contraseñas y Tokens ────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{key.hex()}"

def verify_password(password: str, hashed_pw: str) -> bool:
    try:
        salt, hex_key = hashed_pw.split(':')
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return secrets.compare_digest(key.hex(), hex_key)
    except:
        return False

def generar_token() -> str:
    return secrets.token_hex(32)

# ─── Constantes de IA V14 ─────────────────────────────────────────────────────

PRECISION_MAXIMA        = True
VENTANA_VOTADOR          = 25
GEMINI_IMG_MAX_W         = 640
GEMINI_MAX_REINTENTOS    = 4
GEMINI_REINTENTO_FRAMES  = 45
GEMINI_MODEL_NAME        = "models/gemini-1.5-flash"

try:
    import google.generativeai as genai
    GEMINI_DISPONIBLE = True
except ImportError:
    GEMINI_DISPONIBLE = False

FUENTE_PESO = {
    'Gemini': 3.0,
    'Local' : 1.0,
}

# Colores globales para OpenCV
ROJO    = (0, 0, 255)
VERDE   = (0, 200, 50)
NARANJA = (0, 130, 255)
AMARILLO= (0, 220, 255)
NEGRO   = (0, 0, 0)
BLANCO  = (255, 255, 255)

# ─── Clase PipelineUsuario (Multi-tenant AI Engine) ───────────────────────────

class UserPipeline:
    """Encapsula la captura de video, el análisis IA V14 y la transmisión WebSocket
    de manera independiente por cada usuario en el sistema SaaS."""

    def __init__(self, usuario_id: int, user_data: dict):
        self.usuario_id = usuario_id
        self.email = user_data["email"]
        
        # Configuraciones de integraciones de este usuario
        self.rtsp_url = user_data.get("rtsp_url")
        self.telegram_chat_id = user_data.get("telegram_chat_id")
        self.telegram_token = user_data.get("telegram_token")
        self.gemini_api_key = user_data.get("gemini_api_key")
        self.bot_username = None
        self._cargar_bot_username()
        
        # Conexiones activas de este usuario (PWA, celular, etc.)
        self.clientes: set[WebSocket] = set()
        self.bloqueo_clientes = threading.Lock()

        # Fotogramas y estados de la transmisión
        self.frame_actual: bytes | None = None
        self.bloqueo_fotograma = threading.Lock()
        
        self.cap: cv2.VideoCapture | None = None
        self.lock_procesar_manual = threading.Lock()
        self.cambio_camara_solicitado: str | None = None
        self.ref_hilo_camara = None
        
        self.inteligencia_artificial_ejecutandose = False
        self.fps_actual = 0.0
        self.conteo_fotogramas = 0
        
        # Detecciones para visualización en tiempo real
        self.ultimas_cajas = []
        self.ultimas_cajas_personas = []
        self.ultimos_ids_rastreo = []
        self.ultimas_confianzas = []
        self.cache_placas = {}
        self.intentos_ocr = {}
        self.fotograma_crudo = None

        # Motores internos de IA V14 para este usuario
        self.reider = ReidentificadorVehiculos(max_frames=90, umbral=0.72)
        self.votadores = {}
        self.mejor_nitidez = {}
        self.mejor_recorte = {}
        self.vehiculos_alertados = set()
        self.lock_arbitro = threading.Lock()
        self.ejecutor_ocr = ThreadPoolExecutor(max_workers=2)
        
        self.hilo_ia = None
        self.hilo_streaming = None
        self.running = True

    def iniciar(self):
        """Inicia los hilos de fondo del pipeline del usuario."""
        if not self.rtsp_url:
            print(f"[User {self.usuario_id}] ⚠️ Sin cámara configurada. Pipeline en espera.")
            return

        try:
            self.cap = abrir_captura(self.rtsp_url)
        except Exception as e:
            print(f"[User {self.usuario_id}] ⚠️ No se pudo abrir cámara {self.rtsp_url}: {e}")
            self.cap = None

        self.ref_hilo_camara = HiloCapturaCamara(self.cap, self.rtsp_url)
        
        self.hilo_ia = threading.Thread(target=self._bucle_ia, daemon=True)
        self.hilo_ia.start()

        self.hilo_streaming = threading.Thread(target=self._trabajador_streaming, daemon=True)
        self.hilo_streaming.start()

    def detener(self):
        """Termina todos los procesos y libera recursos de este usuario."""
        self.running = False
        if self.ref_hilo_camara:
            self.ref_hilo_camara.stop()
        if self.cap:
            try: self.cap.release()
            except: pass
        self.ejecutor_ocr.shutdown(wait=False)
        print(f"[User {self.usuario_id}] 🛑 Pipeline detenido y recursos liberados.")

    def actualizar_credenciales(self, user_data: dict):
        """Actualiza la cámara y los tokens de notificación del usuario en caliente."""
        nueva_rtsp = user_data.get("rtsp_url")
        self.telegram_chat_id = user_data.get("telegram_chat_id")
        self.gemini_api_key = user_data.get("gemini_api_key")

        # Si el token de telegram cambia o se inicializa, actualizar el username del bot
        if self.telegram_token != user_data.get("telegram_token"):
            self.telegram_token = user_data.get("telegram_token")
            self._cargar_bot_username()

        if nueva_rtsp != self.rtsp_url:
            print(f"[User {self.usuario_id}] Cambiando cámara de {self.rtsp_url} a {nueva_rtsp}")
            self.rtsp_url = nueva_rtsp
            if self.hilo_ia is None or not self.hilo_ia.is_alive():
                # El hilo no estaba iniciado porque no había cámara al arrancar. Iniciar ahora.
                self.iniciar()
            else:
                self.cambio_camara_solicitado = nueva_rtsp

    def _cargar_bot_username(self):
        if self.telegram_token:
            def fetch_bot_name():
                try:
                    import requests
                    r = requests.get(f"https://api.telegram.org/bot{self.telegram_token}/getMe", timeout=5)
                    if r.status_code == 200 and r.json().get("ok"):
                        self.bot_username = r.json()["result"].get("username")
                        print(f"[Config] Nombre de usuario del bot obtenido para Usuario {self.usuario_id}: @{self.bot_username}")
                        
                        # Difundir el nuevo estado del bot a los clientes conectados
                        self._difundir_evento_privado({
                            "type": "status",
                            "ai": "running" if self.inteligencia_artificial_ejecutandose else "iniciando",
                            "camera": self.rtsp_url or "Ninguna",
                            "fps": round(self.fps_actual, 1),
                            "bot_username": self.bot_username
                        })
                except Exception as e:
                    print(f"[Config Error] No se pudo obtener username del bot: {e}")
            threading.Thread(target=fetch_bot_name, daemon=True).start()

    def _bucle_ia(self):
        self.inteligencia_artificial_ejecutandose = True
        print(f"[User {self.usuario_id}] 🚀 Loop de IA V14 iniciado.")
        
        while self.running:
            try:
                inicio = time.time()

                # Cambiar de cámara solicitado
                if self.cambio_camara_solicitado is not None:
                    nueva_fuente = self.cambio_camara_solicitado
                    self.cambio_camara_solicitado = None
                    self.ref_hilo_camara.stop()
                    if self.cap:
                        try: self.cap.release()
                        except: pass
                    self.rtsp_url = nueva_fuente
                    try:
                        self.cap = abrir_captura(nueva_fuente)
                    except Exception as e:
                        print(f"[User {self.usuario_id}] Error reconexión: {e}")
                        self.cap = None
                    self.ref_hilo_camara = HiloCapturaCamara(self.cap, nueva_fuente)
                    self.votadores.clear()
                    self.mejor_nitidez.clear()
                    self.mejor_recorte.clear()
                    self.vehiculos_alertados.clear()
                    self.intentos_ocr.clear()
                    self.cache_placas.clear()
                    self.conteo_fotogramas = 0

                ret, fotograma = self.ref_hilo_camara.read()
                if not ret or fotograma is None:
                    time.sleep(0.01)
                    continue

                self.conteo_fotogramas += 1

                # YOLO Tracking de Vehículos y Personas (para privacidad)
                cajas_det, ids_rastreo_det, confianzas_det, clases_det = [], [], [], []
                try:
                    results = modelo_vehiculos_global.track(fotograma, persist=True, classes=[0, 2, 3, 5, 7], conf=0.15, verbose=False)
                    if results and results[0].boxes is not None and len(results[0].boxes) > 0:
                        cajas_det       = results[0].boxes.xyxy.int().cpu().tolist()
                        confianzas_det  = results[0].boxes.conf.cpu().tolist()
                        clases_det      = results[0].boxes.cls.int().cpu().tolist()
                        if results[0].boxes.id is not None:
                            ids_rastreo_det = results[0].boxes.id.int().cpu().tolist()
                        else:
                            ids_rastreo_det = list(range(1, len(cajas_det) + 1))
                except Exception as e:
                    print(f"[YOLO Track Error] {e}")

                # Aplicar desenfoque de privacidad a todas las personas detectadas en caliente
                for box_p, cls_val in zip(cajas_det, clases_det):
                    if cls_val == 0:  # Persona
                        px1, py1, px2, py2 = box_p
                        h_img, w_img = fotograma.shape[:2]
                        px1, py1 = max(0, px1), max(0, py1)
                        px2, py2 = min(w_img, px2), min(h_img, py2)
                        if px2 > px1 and py2 > py1:
                            roi_persona = fotograma[py1:py2, px1:px2]
                            blurred = cv2.GaussianBlur(roi_persona, (99, 99), 30)
                            fotograma[py1:py2, px1:px2] = blurred

                # Filtrar listas para excluir personas del pipeline de vehículos y OCR
                ids_vistos = set()
                ultimas_cajas = []
                ultimas_cajas_personas = []
                ultimos_ids_rastreo = []
                ultimas_confianzas = []
                for box_v, id_rastreo, conf_v, cls_v in zip(cajas_det, ids_rastreo_det, confianzas_det, clases_det):
                    if cls_v != 0:  # No es persona, es vehículo
                        ultimas_cajas.append(box_v)
                        ultimos_ids_rastreo.append(id_rastreo)
                        ultimas_confianzas.append(conf_v)
                    else:
                        ultimas_cajas_personas.append(box_v)

                with self.bloqueo_fotograma:
                    self.fotograma_crudo = fotograma.copy()
                    self.ultimas_cajas = ultimas_cajas
                    self.ultimas_cajas_personas = ultimas_cajas_personas
                    self.ultimos_ids_rastreo = ultimos_ids_rastreo
                    self.ultimas_confianzas = ultimas_confianzas

                    for box, track_id, conf_v in zip(ultimas_cajas, ultimos_ids_rastreo, ultimas_confianzas):
                        if conf_v < 0.35: continue
                        x1, y1, x2, y2 = box
                        ids_vistos.add(track_id)

                        # ReID para no perder el rastro de la placa
                        placa_prev = self.cache_placas.get(track_id)
                        track_id, placa_prev, reid_aplicado = self.reider.actualizar(
                            track_id, 2, (x1, y1, x2, y2), fotograma[y1:y2, x1:x2], placa_prev
                        )
                        if reid_aplicado and placa_prev:
                            self.cache_placas[track_id] = placa_prev

                        # Medición de nitidez para Gemini
                        recorte_vehiculo = fotograma[y1:y2, x1:x2]
                        nitidez = calidad_imagen(recorte_vehiculo)
                        pnitidez = self.mejor_nitidez.get(track_id, 0.0)
                        if nitidez > pnitidez and recorte_vehiculo.size > 0:
                            self.mejor_nitidez[track_id] = nitidez
                            self.mejor_recorte[track_id] = recorte_vehiculo.copy()

                        # OCR Local Asíncrono
                        vot = self.votadores.get(track_id)
                        if not (vot and vot.stable(min_lecturas=6, min_confianza=0.75)):
                            # Detección de placas en recorte (con umbral optimizado para compresión)
                            resultados_p = modelo_placas_global(recorte_vehiculo, conf=0.15, verbose=False)
                            if resultados_p and len(resultados_p[0].boxes) > 0:
                                mejor_idx = int(resultados_p[0].boxes.conf.argmax())
                                conf_placa = float(resultados_p[0].boxes.conf[mejor_idx])
                                if conf_placa >= 0.15:
                                    px1, py1, px2, py2 = resultados_p[0].boxes.xyxy[mejor_idx].int().cpu().tolist()
                                    
                                    # Agregar margen inteligente (padding) para evitar recortes muy ajustados
                                    pw = px2 - px1
                                    m = max(int(pw * 0.15), 4)
                                    px1c = max(0, px1 - m)
                                    py1c = max(0, py1 - m)
                                    px2c = min(recorte_vehiculo.shape[1], px2 + m)
                                    py2c = min(recorte_vehiculo.shape[0], py2 + m)
                                    
                                    roi_placa = recorte_vehiculo[py1c:py2c, px1c:px2c]
                                    area = roi_placa.shape[0] * roi_placa.shape[1]

                                    if roi_placa.size > 0:
                                        self.ejecutor_ocr.submit(self._ejecutar_ocr_hilo, track_id, roi_placa.copy(), area)

                        # Gemini V14 asíncrono si está habilitada su API Key
                        vot = self.votadores.get(track_id)
                        if (self.gemini_api_key and vot and not vot.gemini_ya_leyo() 
                                and not self.cache_placas.get(track_id, {}).get('gemini_done', False)):
                            intentos_info = self.intentos_ocr.setdefault(track_id, {"intentos": 0, "ultimo_f": 0})
                            if (self.conteo_fotogramas - intentos_info["ultimo_f"]) >= GEMINI_REINTENTO_FRAMES:
                                intentos_info["ultimo_f"] = self.conteo_fotogramas
                                intentos_info["intentos"] += 1
                                veh_img = self.mejor_recorte.get(track_id)
                                if veh_img is not None:
                                    threading.Thread(
                                        target=self._consultar_gemini_hilo,
                                        args=(track_id, veh_img.copy()),
                                        daemon=True
                                    ).start()

                self.reider.marcar_ids(ids_vistos)

                # Guardar estados para renderizador a 60 FPS
                with self.bloqueo_fotograma:
                    self.ultimas_cajas = ultimas_cajas
                    self.ultimos_ids_rastreo = ultimos_ids_rastreo
                    self.ultimas_confianzas = ultimas_confianzas
                    self.conteo_fotogramas = self.conteo_fotogramas

                t_elapsed = time.time() - inicio
                self.fps_actual = 1.0 / t_elapsed if t_elapsed > 0 else 60.0

            except Exception as e:
                print(f"[User {self.usuario_id} IA Loop Error] {e}")
                time.sleep(0.1)

    def procesar_frame_manual(self, b64_img: str, socket_cliente=None):
        if not self.lock_procesar_manual.acquire(blocking=False):
            return
        try:
            if "," in b64_img:
                b64_img = b64_img.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_img)
            nparr = np.frombuffer(img_bytes, np.uint8)
            fotograma = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if fotograma is None:
                return

            self.conteo_fotogramas += 1

            # YOLO Tracking de Vehículos y Personas (para privacidad)
            cajas_det, ids_rastreo_det, confianzas_det, clases_det = [], [], [], []
            try:
                results = modelo_vehiculos_global.track(fotograma, persist=True, classes=[0, 2, 3, 5, 7], conf=0.15, verbose=False)
                if results and results[0].boxes is not None and len(results[0].boxes) > 0:
                    cajas_det       = results[0].boxes.xyxy.int().cpu().tolist()
                    confianzas_det  = results[0].boxes.conf.cpu().tolist()
                    clases_det      = results[0].boxes.cls.int().cpu().tolist()
                    if results[0].boxes.id is not None:
                        ids_rastreo_det = results[0].boxes.id.int().cpu().tolist()
                    else:
                        ids_rastreo_det = list(range(1, len(cajas_det) + 1))
            except Exception as e:
                print(f"[YOLO Manual Track Error] {e}")

            # Aplicar desenfoque de privacidad a todas las personas detectadas en caliente
            for box_p, cls_val in zip(cajas_det, clases_det):
                if cls_val == 0:  # Persona
                    px1, py1, px2, py2 = box_p
                    h_img, w_img = fotograma.shape[:2]
                    px1, py1 = max(0, px1), max(0, py1)
                    px2, py2 = min(w_img, px2), min(h_img, py2)
                    if px2 > px1 and py2 > py1:
                        roi_persona = fotograma[py1:py2, px1:px2]
                        blurred = cv2.GaussianBlur(roi_persona, (99, 99), 30)
                        fotograma[py1:py2, px1:px2] = blurred

            # Filtrar listas para excluir personas del pipeline de vehículos y OCR
            ids_vistos = set()
            ultimas_cajas = []
            ultimas_cajas_personas = []
            ultimos_ids_rastreo = []
            ultimas_confianzas = []
            for box_v, id_rastreo, conf_v, cls_v in zip(cajas_det, ids_rastreo_det, confianzas_det, clases_det):
                if cls_v != 0:  # No es persona, es vehículo
                    ultimas_cajas.append(box_v)
                    ultimos_ids_rastreo.append(id_rastreo)
                    ultimas_confianzas.append(conf_v)
                else:
                    ultimas_cajas_personas.append(box_v)

            # ReID & OCR
            for box, track_id, conf_v in zip(ultimas_cajas, ultimos_ids_rastreo, ultimas_confianzas):
                if conf_v < 0.35: continue
                x1, y1, x2, y2 = box
                ids_vistos.add(track_id)

                # ReID
                placa_prev = self.cache_placas.get(track_id)
                track_id, placa_prev, reid_aplicado = self.reider.actualizar(
                    track_id, 2, (x1, y1, x2, y2), fotograma[y1:y2, x1:x2], placa_prev
                )
                if reid_aplicado and placa_prev:
                    self.cache_placas[track_id] = placa_prev

                # Nitidez
                recorte_vehiculo = fotograma[y1:y2, x1:x2]
                nitidez = calidad_imagen(recorte_vehiculo)
                pnitidez = self.mejor_nitidez.get(track_id, 0.0)
                if nitidez > pnitidez and recorte_vehiculo.size > 0:
                    self.mejor_nitidez[track_id] = nitidez
                    self.mejor_recorte[track_id] = recorte_vehiculo.copy()

                # OCR Local Asíncrono
                vot = self.votadores.get(track_id)
                if not (vot and vot.stable(min_lecturas=6, min_confianza=0.75)):
                    resultados_p = modelo_placas_global(recorte_vehiculo, conf=0.15, verbose=False)
                    if resultados_p and len(resultados_p[0].boxes) > 0:
                        mejor_idx = int(resultados_p[0].boxes.conf.argmax())
                        conf_placa = float(resultados_p[0].boxes.conf[mejor_idx])
                        if conf_placa >= 0.15:
                            px1, py1, px2, py2 = resultados_p[0].boxes.xyxy[mejor_idx].int().cpu().tolist()
                            
                            # Agregar margen inteligente (padding) para evitar recortes muy ajustados
                            pw = px2 - px1
                            m = max(int(pw * 0.15), 4)
                            px1c = max(0, px1 - m)
                            py1c = max(0, py1 - m)
                            px2c = min(recorte_vehiculo.shape[1], px2 + m)
                            py2c = min(recorte_vehiculo.shape[0], py2 + m)
                            
                            roi_placa = recorte_vehiculo[py1c:py2c, px1c:px2c]
                            area = roi_placa.shape[0] * roi_placa.shape[1]
                            if roi_placa.size > 0:
                                self.ejecutor_ocr.submit(self._ejecutar_ocr_hilo, track_id, roi_placa.copy(), area)

            self.reider.marcar_ids(ids_vistos)

            # Dibujar detecciones en el fotograma para enviar de vuelta
            ROJO    = (0, 0, 255)
            VERDE   = (0, 200, 50)
            NARANJA = (0, 130, 255)
            AMARILLO= (0, 220, 255)
            NEGRO   = (0, 0, 0)
            BLANCO  = (255, 255, 255)

            ORIGEN_COLORES = {
                'Gemini'       : ((0, 220, 255), (0, 0, 0)),
                'Gemini Fix'   : ((0, 165, 255), (0, 0, 0)),
                'Confirmado'   : ((0, 255, 100), (0, 0, 0)),
                'Local Estable': ((0, 200, 200), (0, 0, 0)),
                'YOLO (local)' : ((200, 200, 200), (0, 0, 0)),
            }

            for box, id_rastreo, conf_v in zip(ultimas_cajas, ultimos_ids_rastreo, ultimas_confianzas):
                if conf_v < 0.35: continue
                x1, y1, x2, y2 = box
                cache = self.cache_placas.get(id_rastreo)
                if cache and cache.get('plate'):
                    texto  = cache['plate']
                    origen = cache.get('origen', 'Local')
                    n      = cache.get('n_lecturas', 0)
                    bg_c, fg_c = ORIGEN_COLORES.get(origen, (BLANCO, NEGRO))

                    if cache.get('es_robado'):
                        color = NARANJA if (self.conteo_fotogramas // 15) % 2 == 0 else AMARILLO
                        cv2.rectangle(fotograma, (x1, y1), (x2, y2), color, 3)
                        dibujar_etiqueta(fotograma, f"⚠ ROBADO | {texto}", x1, y1, color, NEGRO)
                        info = cache.get('info') or {}
                        dibujar_etiqueta(fotograma, f"{info.get('modelo','')} {info.get('color','')}", x1, y2 + 15, color, NEGRO)
                    else:
                        cv2.rectangle(fotograma, (x1, y1), (x2, y2), VERDE, 2)
                        dibujar_etiqueta(fotograma, f"Plate: {texto} ({origen}, n={n})", x1, y1, bg_c, fg_c)
                else:
                    cv2.rectangle(fotograma, (x1, y1), (x2, y2), ROJO, 1)

            # Codificar y transmitir de regreso
            _, buf = cv2.imencode(".jpg", fotograma, [cv2.IMWRITE_JPEG_QUALITY, 75])
            
            if socket_cliente:
                meta = json.dumps({
                    "type": "frame_meta",
                    "fps": round(self.fps_actual, 1),
                    "clients": len(self.clientes),
                    "size": len(buf.tobytes()),
                })
                asyncio.run_coroutine_threadsafe(socket_cliente.send_text(meta), estado_servidor_saas.loop)
                asyncio.run_coroutine_threadsafe(socket_cliente.send_bytes(buf.tobytes()), estado_servidor_saas.loop)
            else:
                self._difundir_fotograma_privado(buf.tobytes())

        except Exception as e:
            print(f"[procesar_frame_manual Error] {e}")
        finally:
            self.lock_procesar_manual.release()

    def _ejecutar_ocr_hilo(self, tid, roi_placa, area):
        try:
            lecturas, _ = leer_todas_variantes(reader_ocr_global, roi_placa, area, tid)
            for texto_ocr, conf_ocr in lecturas:
                self._actualizar_estado_consenso(tid, texto_ocr, conf_ocr, 'Local')
        except Exception as e:
            print(f"[OCR Error tid:{tid}] {e}")

    def _consultar_gemini_hilo(self, track_id, img_vehiculo, intento=1):
        if not GEMINI_DISPONIBLE:
            return
        try:
            h, w = img_vehiculo.shape[:2]
            max_w = GEMINI_IMG_MAX_W
            if w > max_w:
                scale = max_w / w
                img_vehiculo = cv2.resize(img_vehiculo, (max_w, int(h * scale)), interpolation=cv2.INTER_AREA)

            pil_img = Image.fromarray(cv2.cvtColor(img_vehiculo, cv2.COLOR_BGR2RGB))
            
            # Configurar dinámicamente Gemini con la API key de ESTE usuario
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            prompt = (
                "You are analyzing a security camera image of a vehicle. "
                "Your ONLY task is to read the Mexican license plate number visible on this vehicle. "
                "Standard private ('TRANSPORTE PRIVADO') plates from Tamaulipas have exactly 7 alphanumeric "
                "characters: 3 letters followed by 4 digits (e.g. XKK2850, ILE3865). "
                "Respond with ONLY the 7-character plate number in uppercase, no spaces, no hyphens, no explanation. "
                "If you truly cannot read any plate, respond exactly: NONE"
            )
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            response = model.generate_content(
                [prompt, pil_img],
                generation_config=genai.types.GenerationConfig(temperature=0.0, max_output_tokens=20),
                safety_settings=safety_settings
            )
            texto_raw = re.sub(r'[^A-Z0-9]', '', response.text.strip().upper())[:7]
            if texto_raw and texto_raw != "NONE" and len(texto_raw) >= 6:
                texto_limpio = validar_formato_placa(texto_raw)
                if not texto_limpio and len(texto_raw) == 7:
                    texto_limpio = texto_raw
                if texto_limpio:
                    print(f"[User {self.usuario_id} Gemini] ID {track_id} → '{texto_limpio}'")
                    self._actualizar_estado_consenso(track_id, texto_limpio, 0.95, 'Gemini')
                    return
        except Exception as e:
            msg = str(e)
            es_rate_limit = "429" in msg or "quota" in msg.lower() or "rate" in msg.lower()
            if intento < GEMINI_MAX_REINTENTOS:
                time.sleep(1.5 if es_rate_limit else 0.5)
                self._consultar_gemini_hilo(track_id, img_vehiculo, intento + 1)
                return
        with self.lock_arbitro:
            if track_id in self.cache_placas:
                self.cache_placas[track_id]['gemini_done'] = True

    def _actualizar_estado_consenso(self, track_id, texto, conf, fuente):
        with self.lock_arbitro:
            votador = self.votadores.get(track_id)
            if votador is None:
                votador = VotadorPlacaCaracter()
                self.votadores[track_id] = votador
            votador.agregar(texto, conf, fuente)
            placa_consenso, confianza_consenso, n = votador.consenso()

            estado_plate = self.cache_placas.get(track_id, {})
            estado_plate.setdefault('checked_db', False)
            estado_plate.setdefault('es_robado', False)
            estado_plate.setdefault('notified', False)
            estado_plate.setdefault('info', None)

            if fuente == 'Gemini':
                estado_plate['gemini_plate'] = texto
                estado_plate['gemini_done'] = True

            if not placa_consenso:
                self.cache_placas[track_id] = estado_plate
                return

            gemini_txt = votador.ultima_lectura_gemini()
            if gemini_txt and gemini_txt == placa_consenso:
                origen = 'Confirmado'
            elif gemini_txt:
                origen = 'Gemini Fix'
            elif n >= 6 and confianza_consenso >= 0.75:
                origen = 'Local Estable'
            else:
                origen = 'YOLO (local)'

            estado_plate['plate']      = placa_consenso
            estado_plate['origen']     = origen
            estado_plate['confidence'] = round(min(0.99, 0.5 + confianza_consenso * 0.5), 2)
            estado_plate['n_lecturas'] = n

            # Validar con la base de datos central de placas sospechosas
            if not estado_plate['checked_db'] or estado_plate['plate'] != placa_consenso:
                es_robado, info = db_global.consultar_placa(placa_consenso)
                estado_plate['checked_db'] = True
                estado_plate['es_robado']  = es_robado
                estado_plate['info']       = info

                # Si es un auto reportado, emitir alerta de seguridad privada
                if es_robado and not estado_plate['notified'] and track_id not in self.vehiculos_alertados:
                    self.vehiculos_alertados.add(track_id)
                    estado_plate['notified'] = True
                    print(f"\n🚨 [ALERTA USER {self.usuario_id}] PLACA ROBADA: {placa_consenso}!")

                    with self.bloqueo_fotograma:
                        crudo = self.fotograma_crudo.copy() if self.fotograma_crudo is not None else None

                    ruta_v, ruta_p = "", ""
                    if crudo is not None:
                        ruta_v, ruta_p = guardar_capturas(crudo, crudo, placa_consenso)
                        db_global.registrar_alerta(
                            placa_bd=info.get("placa", placa_consenso),
                            placa_detectada=placa_consenso,
                            similitud=(info.get("similitud", 100.0) / 100.0),
                            ruta_vehiculo=ruta_v,
                            ruta_placa=ruta_p,
                            usuario_id=self.usuario_id
                        )

                    alerta_ws = {
                        "type": "alert",
                        "placa": placa_consenso,
                        "es_robado": True,
                        "placa_bd": info.get("placa", placa_consenso),
                        "similitud": info.get("similitud", 100.0),
                        "modelo": info.get("modelo", "?"),
                        "color": info.get("color", "?"),
                        "propietario": info.get("propietario", "?"),
                        "id_rastreo": track_id,
                        "foto_vehiculo": ruta_v,
                        "foto_placa": ruta_p,
                        "timestamp": datetime.now().isoformat(),
                    }
                    
                    # Difundir a sus clientes WebSocket conectados
                    self._difundir_evento_privado(alerta_ws)
                    
                    # Enviar notificación privada a su chat de Telegram configurado
                    if self.telegram_token and self.telegram_chat_id:
                        enviar_alerta_telegram_privada(
                            self.telegram_token,
                            self.telegram_chat_id,
                            placa_consenso,
                            info,
                            [ruta_v] if ruta_v else None
                        )

            self.cache_placas[track_id] = estado_plate
            log_consenso(track_id, placa_consenso, origen, estado_plate['confidence'], n)

    def _trabajador_streaming(self):
        interval = 1.0 / 60.0
        PARAMETROS_JPEG = [cv2.IMWRITE_JPEG_QUALITY, 75]
        ultimo_emit = 0.0

        ROJO    = (0, 0, 255)
        VERDE   = (0, 200, 50)
        NARANJA = (0, 130, 255)
        AMARILLO= (0, 220, 255)
        NEGRO   = (0, 0, 0)
        BLANCO  = (255, 255, 255)

        ORIGEN_COLORES = {
            'Gemini'       : ((0, 220, 255), (0, 0, 0)),
            'Gemini Fix'   : ((0, 165, 255), (0, 0, 0)),
            'Confirmado'   : ((0, 255, 100), (0, 0, 0)),
            'Local Estable': ((0, 200, 200), (0, 0, 0)),
            'YOLO (local)' : ((200, 200, 200), (0, 0, 0)),
        }

        while self.running:
            if not self.inteligencia_artificial_ejecutandose or self.ref_hilo_camara is None:
                time.sleep(0.1)
                continue

            # OPTIMIZACIÓN: Si no hay clientes visualizando, suspender procesamiento JPEG
            if not self.clientes:
                time.sleep(0.1)
                continue

            ahora = time.time()
            if ahora - ultimo_emit >= interval:
                try:
                    ret, fotograma_crudo = self.ref_hilo_camara.read()
                    if ret and fotograma_crudo is not None:
                        fotograma = fotograma_crudo.copy()
                        with self.bloqueo_fotograma:
                            boxes       = list(self.ultimas_cajas)
                            cajas_personas = list(self.ultimas_cajas_personas) if hasattr(self, 'ultimas_cajas_personas') else []
                            ids_rastreo = list(self.ultimos_ids_rastreo)
                            confianzas  = list(self.ultimas_confianzas)
                            copia_cache = {tid: dict(info) for tid, info in self.cache_placas.items()}
                            conteo_f    = self.conteo_fotogramas

                        # Aplicar desenfoque de privacidad a todas las personas en el frame antes de enviar
                        for box_p in cajas_personas:
                            px1, py1, px2, py2 = box_p
                            h_img, w_img = fotograma.shape[:2]
                            px1, py1 = max(0, px1), max(0, py1)
                            px2, py2 = min(w_img, px2), min(h_img, py2)
                            if px2 > px1 and py2 > py1:
                                roi_persona = fotograma[py1:py2, px1:px2]
                                blurred = cv2.GaussianBlur(roi_persona, (99, 99), 30)
                                fotograma[py1:py2, px1:px2] = blurred

                        for box, id_rastreo, conf_v in zip(boxes, ids_rastreo, confianzas):
                            if conf_v < 0.35: continue
                            x1, y1, x2, y2 = box
                            cache = copia_cache.get(id_rastreo)

                            if cache and cache.get('plate'):
                                texto  = cache['plate']
                                origen = cache.get('origen', 'Local')
                                n      = cache.get('n_lecturas', 0)
                                bg_c, fg_c = ORIGEN_COLORES.get(origen, (BLANCO, NEGRO))

                                if cache.get('es_robado'):
                                    color = NARANJA if (conteo_f // 15) % 2 == 0 else AMARILLO
                                    cv2.rectangle(fotograma, (x1, y1), (x2, y2), color, 3)
                                    dibujar_etiqueta(fotograma, f"⚠ ROBADO | {texto}", x1, y1, color, NEGRO)
                                    info = cache.get('info') or {}
                                    dibujar_etiqueta(fotograma, f"{info.get('modelo','')} {info.get('color','')}", x1, y2 + 15, color, NEGRO)
                                else:
                                    cv2.rectangle(fotograma, (x1, y1), (x2, y2), VERDE, 2)
                                    dibujar_etiqueta(fotograma, f"Plate: {texto} ({origen}, n={n})", x1, y1, bg_c, fg_c)
                            else:
                                cv2.rectangle(fotograma, (x1, y1), (x2, y2), ROJO, 1)

                        _, buf = cv2.imencode(".jpg", fotograma, PARAMETROS_JPEG)
                        self._difundir_fotograma_privado(buf.tobytes())
                        ultimo_emit = time.time()
                except Exception as e:
                    pass
                time.sleep(max(0.001, interval - (time.time() - ahora)))
            else:
                time.sleep(0.005)

    def _difundir_fotograma_privado(self, bytes_fotograma: bytes):
        if not self.clientes: return
        meta = json.dumps({
            "type": "frame_meta",
            "fps": round(self.fps_actual, 1),
            "clients": len(self.clientes),
            "size": len(bytes_fotograma),
        })
        
        # Copia local de clientes para evitar exclusión mutua larga
        with self.bloqueo_clientes:
            instantanea_clientes = list(self.clientes)

        muertos = []
        for socket_cliente in instantanea_clientes:
            try:
                # Enviar metadatos asíncronos y fotograma en binario directo
                asyncio.run_coroutine_threadsafe(socket_cliente.send_text(meta), estado_servidor_saas.loop)
                asyncio.run_coroutine_threadsafe(socket_cliente.send_bytes(bytes_fotograma), estado_servidor_saas.loop)
            except Exception:
                muertos.append(socket_cliente)

        if muertos:
            with self.bloqueo_clientes:
                for socket_cliente in muertos:
                    self.clientes.discard(socket_cliente)

    def _difundir_evento_privado(self, data: dict):
        if not self.clientes: return
        payload = json.dumps(data, ensure_ascii=False)
        with self.bloqueo_clientes:
            instantanea_clientes = list(self.clientes)
        for socket_cliente in instantanea_clientes:
            try:
                asyncio.run_coroutine_threadsafe(socket_cliente.send_text(payload), estado_servidor_saas.loop)
            except:
                pass

# ─── Orquestador de Pipelines SaaS (Gestiona múltiples usuarios activos) ──────

class EstadoServidorSaaS:
    def __init__(self):
        # Mapea usuario_id -> UserPipeline
        self.pipelines: dict[int, UserPipeline] = {}
        self.lock_pipelines = threading.Lock()
        self.loop = None

    def obtener_o_crear_pipeline(self, usuario_id: int, user_data: dict) -> UserPipeline:
        with self.lock_pipelines:
            if usuario_id not in self.pipelines:
                print(f"[Orquestador] 🛠️ Creando pipeline para el usuario {usuario_id} ({user_data['email']})")
                pipeline = UserPipeline(usuario_id, user_data)
                pipeline.iniciar()
                self.pipelines[usuario_id] = pipeline
            return self.pipelines[usuario_id]

    def detener_pipeline(self, usuario_id: int):
        with self.lock_pipelines:
            if usuario_id in self.pipelines:
                self.pipelines[usuario_id].detener()
                del self.pipelines[usuario_id]

    def apagar_todo(self):
        with self.lock_pipelines:
            for p in self.pipelines.values():
                p.detener()
            self.pipelines.clear()

estado_servidor_saas = EstadoServidorSaaS()

# ─── FastAPI App con Middleware CORS ──────────────────────────────────────────

app = FastAPI(title="AlertaVecinal SaaS Server V14")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Endpoints de la API REST para Usuarios ────────────────────────────────────

@app.post("/api/register")
async def register(payload: dict = Body(...)):
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Faltan credenciales obligatorias.")
    
    hashed = hash_password(password)
    creado = db_global.crear_cuenta(email, hashed)
    if not creado:
        raise HTTPException(status_code=400, detail="La cuenta de correo ya se encuentra registrada.")
    return {"message": "Cuenta creada con éxito."}

@app.post("/api/login")
async def login(payload: dict = Body(...)):
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Faltan credenciales obligatorias.")

    cuenta = db_global.obtener_cuenta_por_email(email)
    if not cuenta or not verify_password(password, cuenta["password_hash"]):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")

    # Generar un token único de sesión segura
    token_sesion = generar_token()
    db_global.actualizar_token_cuenta(cuenta["id"], token_sesion)

    return {
        "token": token_sesion,
        "email": cuenta["email"],
        "user_id": cuenta["id"],
        "config": {
            "rtsp_url": cuenta.get("rtsp_url") or "",
            "telegram_chat_id": cuenta.get("telegram_chat_id") or "",
            "telegram_token": cuenta.get("telegram_token") or "",
            "gemini_api_key": cuenta.get("gemini_api_key") or ""
        }
    }

@app.post("/api/config")
async def save_config(payload: dict = Body(...)):
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Token no provisto.")
    
    cuenta = db_global.obtener_cuenta_por_token(token)
    if not cuenta:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    rtsp_url = payload.get("rtsp_url", "")
    telegram_chat_id = payload.get("telegram_chat_id", "")
    telegram_token = payload.get("telegram_token", "")
    gemini_api_key = payload.get("gemini_api_key", "")

    db_global.actualizar_config_cuenta(cuenta["id"], rtsp_url, telegram_chat_id, telegram_token, gemini_api_key)
    
    # Actualizar en caliente el pipeline del usuario si está activo
    updated_data = db_global.obtener_cuenta_por_token(token)
    with estado_servidor_saas.lock_pipelines:
        if cuenta["id"] in estado_servidor_saas.pipelines:
            estado_servidor_saas.pipelines[cuenta["id"]].actualizar_credenciales(updated_data)

    return {"message": "Configuración guardada correctamente."}

@app.post("/api/history")
async def get_history(payload: dict = Body(...)):
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Token no provisto.")
    cuenta = db_global.obtener_cuenta_por_token(token)
    if not cuenta:
        raise HTTPException(status_code=401, detail="Token inválido.")
    
    limite = int(payload.get("limit", 20))
    hist = db_global.listar_historial(limite=limite, usuario_id=cuenta["id"])
    return {"alerts": hist}

# ─── Endpoint WebSocket Autenticado / Compatibilidad PWA ──────────────────────

@app.websocket("/ws")
async def websocket_legacy(websocket: WebSocket):
    await websocket.accept()
    usuario_id = 1
    # Asegurar que el usuario administrador por defecto exista en la base de datos
    cuenta = db_global.obtener_cuenta_por_id(usuario_id)
    if not cuenta:
        db_global.crear_cuenta("admin@alertavecinal.com", hash_password("admin123"))
        cuenta = db_global.obtener_cuenta_por_email("admin@alertavecinal.com")
        
    pipeline = estado_servidor_saas.obtener_o_crear_pipeline(usuario_id, cuenta)
    
    with pipeline.bloqueo_clientes:
        pipeline.clientes.add(websocket)
    print(f"[WS Legacy] Cliente conectado sin token asignado a Admin (ID: {usuario_id}). Total: {len(pipeline.clientes)}")

    # Enviar historial al conectarse
    hist = db_global.listar_historial(limite=15, usuario_id=usuario_id)
    await websocket.send_text(json.dumps({"type": "history", "alerts": hist}))

    # Enviar estado actual de su cámara
    await websocket.send_text(json.dumps({
        "type": "status",
        "ai": "running" if pipeline.inteligencia_artificial_ejecutandose else "iniciando",
        "camera": pipeline.rtsp_url or "Ninguna",
        "fps": round(pipeline.fps_actual, 1),
        "bot_username": pipeline.bot_username
    }))

    try:
        while True:
            datos_crudos = await websocket.receive_text()
            cmd = json.loads(datos_crudos)
            action = cmd.get("cmd", "")

            if action == "change_camera_url":
                url = cmd.get("url", "")
                if url:
                    db_global.actualizar_config_cuenta(
                        usuario_id, url, pipeline.telegram_chat_id, pipeline.telegram_token, pipeline.gemini_api_key
                    )
                    pipeline.actualizar_credenciales(db_global.obtener_cuenta_por_id(usuario_id))
            
            elif action == "change_camera":
                idx = cmd.get("index", 0)
                url = str(idx)
                db_global.actualizar_config_cuenta(
                    usuario_id, url, pipeline.telegram_chat_id, pipeline.telegram_token, pipeline.gemini_api_key
                )
                pipeline.actualizar_credenciales(db_global.obtener_cuenta_por_id(usuario_id))

            elif action == "list_cameras":
                loop = asyncio.get_running_loop()
                def realizar_escaneo_legacy():
                    cams = []
                    for i in range(5):
                        try:
                            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if sys.platform.startswith('win') else cv2.VideoCapture(i)
                            if cap.isOpened():
                                ret, _ = cap.read()
                                if ret:
                                    cams.append(f"📹 Cámara USB {i}")
                                cap.release()
                        except:
                            pass
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_text(json.dumps({"type": "cameras", "list": cams})),
                        loop
                    )
            elif action == "process_frame":
                b64_img = cmd.get("image", "")
                if b64_img:
                    threading.Thread(target=pipeline.procesar_frame_manual, args=(b64_img, websocket), daemon=True).start()

            elif action == "ptz":
                direccion = cmd.get("action", "")
                if pipeline.rtsp_url and pipeline.rtsp_url.startswith("rtsp://"):
                    ip, user, passwd = extraer_credenciales_rtsp(pipeline.rtsp_url)
                    if ip:
                        threading.Thread(
                            target=mover_camara_onvif,
                            args=(ip, user, passwd, direccion),
                            daemon=True
                        ).start()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS Legacy Error] {e}")
    finally:
        with pipeline.bloqueo_clientes:
            pipeline.clientes.discard(websocket)
        print(f"[WS Legacy] Cliente desconectado.")

@app.websocket("/ws/{token}")
async def websocket_saas(websocket: WebSocket, token: str):
    await websocket.accept()
    
    # Validar que el token pertenezca a un usuario registrado
    cuenta = db_global.obtener_cuenta_por_token(token)
    if not cuenta:
        await websocket.close(code=4001)
        return

    usuario_id = cuenta["id"]
    
    # Obtener o crear el pipeline para esta cámara
    pipeline = estado_servidor_saas.obtener_o_crear_pipeline(usuario_id, cuenta)
    
    with pipeline.bloqueo_clientes:
        pipeline.clientes.add(websocket)
    print(f"[WS User {usuario_id}] Cliente conectado al WebSocket privado. Total: {len(pipeline.clientes)}")

    # Enviar historial privado al conectarse
    hist = db_global.listar_historial(limite=15, usuario_id=usuario_id)
    await websocket.send_text(json.dumps({"type": "history", "alerts": hist}))

    # Enviar estado actual de su cámara
    await websocket.send_text(json.dumps({
        "type": "status",
        "ai": "running" if pipeline.inteligencia_artificial_ejecutandose else "iniciando",
        "camera": pipeline.rtsp_url or "Ninguna",
        "fps": round(pipeline.fps_actual, 1),
        "bot_username": pipeline.bot_username
    }))

    try:
        while True:
            # Escuchar mensajes/comandos del cliente móvil
            datos_crudos = await websocket.receive_text()
            cmd = json.loads(datos_crudos)
            action = cmd.get("cmd", "")

            if action == "change_camera_url":
                url = cmd.get("url", "")
                if url:
                    db_global.actualizar_config_cuenta(
                        usuario_id, url, pipeline.telegram_chat_id, pipeline.telegram_token, pipeline.gemini_api_key
                    )
                    pipeline.actualizar_credenciales(db_global.obtener_cuenta_por_token(token))
            
            elif action == "change_camera":
                idx = cmd.get("index", 0)
                url = str(idx)
                db_global.actualizar_config_cuenta(
                    usuario_id, url, pipeline.telegram_chat_id, pipeline.telegram_token, pipeline.gemini_api_key
                )
                pipeline.actualizar_credenciales(db_global.obtener_cuenta_por_token(token))

            elif action == "list_cameras":
                loop = asyncio.get_running_loop()
                # Escanear cámaras USB en un hilo para no bloquear el bucle de eventos
                def realizar_escaneo():
                    cams = []
                    for i in range(5):
                        try:
                            # Probar con backend DSHOW primero en Windows, luego normal
                            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if sys.platform.startswith('win') else cv2.VideoCapture(i)
                            if cap.isOpened():
                                ret, _ = cap.read()
                                if ret:
                                    cams.append(f"📹 Cámara USB {i}")
                                cap.release()
                        except:
                            pass
                    # Enviar de regreso al cliente
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_text(json.dumps({"type": "cameras", "list": cams})),
                        loop
                    )
            elif action == "process_frame":
                b64_img = cmd.get("image", "")
                if b64_img:
                    threading.Thread(target=pipeline.procesar_frame_manual, args=(b64_img, websocket), daemon=True).start()

            elif action == "ptz":
                direccion = cmd.get("action", "")
                if pipeline.rtsp_url and pipeline.rtsp_url.startswith("rtsp://"):
                    ip, user, passwd = extraer_credenciales_rtsp(pipeline.rtsp_url)
                    if ip:
                        threading.Thread(
                            target=mover_camara_onvif,
                            args=(ip, user, passwd, direccion),
                            daemon=True
                        ).start()

    except WebSocketDisconnect:
        pass
    finally:
        with pipeline.bloqueo_clientes:
            pipeline.clientes.discard(websocket)
            n_restantes = len(pipeline.clientes)
        print(f"[WS User {usuario_id}] Cliente desconectado. Total: {n_restantes}")
        
        # PERSISTENCIA: Ya no detenemos el pipeline. Queda trabajando 24/7 en segundo plano.

# ─── Hilo de Captura y Utilidades del Stream ──────────────────────────────────

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
                time.sleep(2.0)
                try:
                    self.cap = abrir_captura(self.fuente)
                except:
                    self.cap = None
                continue

            ret, fotograma = self.cap.read()
            if not ret or fotograma is None:
                fallos_consecutivos += 1
                if fallos_consecutivos > 30:
                    try: self.cap.release()
                    except: pass
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

def abrir_captura(fuente_str: str) -> cv2.VideoCapture:
    if fuente_str.isdigit():
        idx = int(fuente_str)
        backends = [(cv2.CAP_MSMF, "MSMF"), (cv2.CAP_DSHOW, "DSHOW"), (cv2.CAP_ANY, "ANY")]
        for backend, nombre in backends:
            try: c = cv2.VideoCapture(idx, backend)
            except: continue
            if c.isOpened():
                ret, _ = c.read()
                if ret: return c
                c.release()
        raise Exception(f"No se pudo abrir cámara USB {idx}")
    elif fuente_str.lower().startswith("rtsp://"):
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
        cap = cv2.VideoCapture(fuente_str, cv2.CAP_FFMPEG)
    else:
        cap = cv2.VideoCapture(fuente_str)
    if not cap.isOpened():
        raise Exception(f"No se pudo abrir fuente: {fuente_str}")
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap

# ─── Utilidades PTZ, Imagen y Formato V14 ─────────────────────────────────────

def extraer_credenciales_rtsp(url_rtsp):
    match = re.match(r"rtsp://([^:]+):([^@]+)@([^:/]+)(?::\d+)?", url_rtsp)
    if match:
        return match.group(3), match.group(1), match.group(2)
    match_ip = re.match(r"rtsp://([^:/]+)(?::\d+)?", url_rtsp)
    if match_ip:
        return match_ip.group(1), "admin", ""
    return None, None, None

def mover_camara_onvif(ip, user, passwd, direccion, duracion=0.5):
    try:
        from onvif import ONVIFCamera
    except ImportError: return False
    ports = [8899, 80, 5000, 8080]
    cam = None
    for port in ports:
        try:
            cam = ONVIFCamera(ip, port, user, passwd)
            cam.devicemgmt.GetDeviceInformation()
            break
        except: cam = None
    if not cam: return False
    try:
        media = cam.create_media_service()
        ptz = cam.create_ptz_service()
        profiles = media.GetProfiles()
        if not profiles: return False
        token = profiles[0].token
        x, y = 0.0, 0.0
        speed = 0.4
        if direccion == "left": x = -speed
        elif direccion == "right": x = speed
        elif direccion == "up": y = speed
        elif direccion == "down": y = -speed
        request = ptz.create_type('ContinuousMove')
        request.ProfileToken = token
        request.Velocity = {'PanTilt': {'x': x, 'y': y}}
        ptz.ContinuousMove(request)
        time.sleep(duracion)
        ptz.Stop({'ProfileToken': token})
        return True
    except: return False

def corregir_perspectiva(roi):
    """V14: Corrige la inclinación y perspectiva de la placa mediante detección de contornos cuadriláteros."""
    try:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(cv2.GaussianBlur(gray,(5,5),0), 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts: return roi
        for cnt in sorted(cnts, key=cv2.contourArea, reverse=True)[:3]:
            peri  = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04*peri, True)
            if len(approx) == 4:
                pts = approx.reshape(4,2).astype(np.float32)
                s, d = pts.sum(axis=1), np.diff(pts, axis=1)
                o = np.zeros((4,2), dtype=np.float32)
                o[0], o[2] = pts[np.argmin(s)], pts[np.argmax(s)]
                o[1], o[3] = pts[np.argmin(d)], pts[np.argmax(d)]
                w = max(np.linalg.norm(o[1]-o[0]), np.linalg.norm(o[2]-o[3]))
                h = max(np.linalg.norm(o[3]-o[0]), np.linalg.norm(o[2]-o[1]))
                if w < 20 or h < 8: continue
                dst = np.array([[0,0],[w,0],[w,h],[0,h]], dtype=np.float32)
                return cv2.warpPerspective(roi, cv2.getPerspectiveTransform(o, dst), (int(w), int(h)))
    except: pass
    return roi

def calidad_imagen(roi):
    if roi is None or roi.size == 0: return 0.0
    try:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except: return 0.0

def rotar_imagen(img, angulo):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w/2, h/2), angulo, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def enfocar(gray):
    blur = cv2.GaussianBlur(gray, (0, 0), 2.0)
    return cv2.addWeighted(gray, 1.5, blur, -0.5, 0)

def preprocesamiento_dinamico(roi_base, area, alto_objetivo=180.0):
    h, w = roi_base.shape[:2]
    if h == 0 or w == 0: return roi_base
    T = float(alto_objetivo)
    if area >= 3000:
        sc = T / h
        img = cv2.resize(roi_base, (max(1,int(w*sc)), max(1,int(h*sc))), interpolation=cv2.INTER_LANCZOS4)
    else:
        img = roi_base.copy()
        for _ in range(4):
            if img.shape[0] >= int(T): break
            img = cv2.resize(img,(img.shape[1]*2,img.shape[0]*2), interpolation=cv2.INTER_CUBIC)
        sc = T/img.shape[0]
        img = cv2.resize(img,(max(1,int(img.shape[1]*sc)),max(1,int(img.shape[0]*sc))), interpolation=cv2.INTER_LANCZOS4)
    
    # Aplicar corrección de perspectiva V14
    img = corregir_perspectiva(img)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brillo_medio = cv2.mean(gray)[0]
    if brillo_medio > 170:
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(6,6))
        eq = clahe.apply(gray)
        bl = cv2.GaussianBlur(eq, (5,5), 1.5)
        res = cv2.addWeighted(eq, 1.6, bl, -0.6, 0)
    elif brillo_medio < 70:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4,4))
        eq = clahe.apply(gray)
        res = cv2.bilateralFilter(eq, d=11, sigmaColor=80, sigmaSpace=80)
        res = enfocar(res)
    else:
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6,6))
        eq = clahe.apply(gray)
        res = cv2.bilateralFilter(eq, d=9, sigmaColor=60, sigmaSpace=60)
        res = enfocar(res)
    return cv2.cvtColor(res, cv2.COLOR_GRAY2BGR)

def variantes_angulo(roi_base, area):
    out = []
    for ang in [-15, 15, 180]:
        try:
            rotada = rotar_imagen(roi_base, ang)
            out.append(preprocesamiento_dinamico(rotada, area))
        except: pass
    return out

def validar_formato_placa(texto):
    texto = re.sub(r'[^A-Z0-9]', '', texto.upper())
    if len(texto) != 7: return ""
    fl = {'0':'O','1':'I','5':'S','8':'B'}.get
    fn = {'O':'0','I':'1','S':'5','Z':'2','B':'8','G':'6'}.get
    p012 = [fl(c, c) for c in texto[0:3]]
    p345 = [fn(c, c) for c in texto[3:6]]
    p6   = texto[6]
    if not all(c.isalpha() for c in p012): return ""
    if not all(c.isdigit() for c in p345): return ""
    return "".join(p012) + "".join(p345) + p6

# ─── Votador Consenso V14 ─────────────────────────────────────────────────────

class VotadorPlacaCaracter:
    def __init__(self, ventana=VENTANA_VOTADOR):
        self.historial = []
        self.ventana = ventana

    def agregar(self, texto, conf, fuente):
        if texto and len(texto) == 7:
            self.historial.append((texto, float(conf), fuente))
            if len(self.historial) > self.ventana:
                self.historial.pop(0)

    def consenso(self):
        if not self.historial: return "", 0.0, 0
        posiciones = [defaultdict(float) for _ in range(7)]
        for texto, conf, fuente in self.historial:
            peso = FUENTE_PESO.get(fuente, 1.0) * max(conf, 0.05)
            for i, ch in enumerate(texto):
                posiciones[i][ch] += peso
        placa = []
        certeza_total = 0.0
        for pos in posiciones:
            if not pos: return "", 0.0, len(self.historial)
            mejor_ch = max(pos, key=pos.get)
            total = sum(pos.values())
            certeza_total += (pos[mejor_ch] / total) if total > 0 else 0.0
            placa.append(mejor_ch)
        return "".join(placa), round(certeza_total / 7.0, 3), len(self.historial)

    def gemini_ya_leyo(self):
        return any(f == 'Gemini' for _, _, f in self.historial)

    def ultima_lectura_gemini(self):
        for texto, conf, fuente in reversed(self.historial):
            if fuente == 'Gemini': return texto
        return None

# ─── ReID (Reidentificación por histograma) ───────────────────────────────────

class ReidentificadorVehiculos:
    def __init__(self, max_frames=90, umbral=0.72):
        self.activos  = {}
        self.perdidos = {}
        self.max_frames = max_frames
        self.umbral = umbral

    def _hist(self, roi):
        if roi is None or roi.size == 0: return None
        try:
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            h = cv2.calcHist([hsv], [0,1], None, [18,16], [0,180,0,256])
            cv2.normalize(h, h)
            return h.flatten()
        except: return None

    def _sim(self, h1, h2):
        if h1 is None or h2 is None: return 0.0
        return float(cv2.compareHist(h1.reshape(-1,1).astype(np.float32), h2.reshape(-1,1).astype(np.float32), cv2.HISTCMP_CORREL))

    def actualizar(self, tid, cls, bbox, roi, placa_actual):
        cx, cy = (bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2
        area = (bbox[2]-bbox[0])*(bbox[3]-bbox[1])
        hist = self._hist(roi)
        reid = False
        if tid not in self.activos:
            mejor_pid, mejor_sc = None, 0.0
            for pid, info in self.perdidos.items():
                if info['cls'] != cls: continue
                sc = 0.7*self._sim(hist, info['hist']) + 0.3*max(0., 1.0 - np.sqrt((cx-info['pos'][0])**2+(cy-info['pos'][1])**2)/400.)
                if sc > mejor_sc:
                    mejor_sc, mejor_pid = sc, pid
            if mejor_pid and mejor_sc >= self.umbral:
                heredada = self.perdidos[mejor_pid].get('placa_data')
                if heredada and (placa_actual is None or heredada.get('confidence',0) > placa_actual.get('confidence',0)):
                    placa_actual = dict(heredada)
                del self.perdidos[mejor_pid]
                tid = mejor_pid
                reid = True
        prev = self.activos.get(tid, {})
        if area > prev.get('area', 0):
            self.activos[tid] = {'cls':cls, 'hist':hist, 'area':area, 'pos':(cx,cy), 'placa_data':placa_actual}
        else:
            self.activos[tid]['pos'] = (cx, cy)
            self.activos[tid]['placa_data'] = placa_actual
        return tid, placa_actual, reid

    def marcar_ids(self, ids_vistos):
        for did in set(self.activos.keys()) - ids_vistos:
            info = self.activos.pop(did)
            info['frames_sin_ver'] = 0
            self.perdidos[did] = info
        viejos = [p for p, i in self.perdidos.items() if i.get('frames_sin_ver', 0) > self.max_frames]
        for p in viejos: del self.perdidos[p]
        for p in self.perdidos: self.perdidos[p]['frames_sin_ver'] += 1

# ─── OCR Variantes y Consenso ────────────────────────────────────────────────

def _ocr_intentar(reader, img, track_id, label):
    try:
        res = reader.ocr(img, det=False, cls=False)
        if res and res[0] and res[0][0]:
            txt, conf = res[0][0]
            tv = validar_formato_placa(txt)
            if tv and conf > 0.40: return tv, float(conf), img
    except: pass
    try:
        res = reader.ocr(img, det=True, cls=False)
        if res and res[0]:
            lineas = sorted(res[0], key=lambda r: r[0][0][0])
            txt = "".join(r[1][0] for r in lineas)
            conf = sum(r[1][1] for r in lineas) / len(lineas) if len(lineas) > 0 else 0.0
            tv = validar_formato_placa(txt)
            if tv: return tv, conf, img
    except: pass
    return "", 0.0, img

def leer_todas_variantes(reader, roi_base, area, track_id):
    lecturas = []
    mejor_img = None
    variantes = [
        (preprocesamiento_dinamico(roi_base, area, alto_objetivo=180.0), "recto"),
        (preprocesamiento_dinamico(roi_base, area, alto_objetivo=260.0), "recto-lejos"),
    ]
    if PRECISION_MAXIMA:
        variantes += [(img, f"ang{i}") for i, img in enumerate(variantes_angulo(roi_base, area))]

    for img, label in variantes:
        txt, conf, img_usada = _ocr_intentar(reader, img, track_id, label)
        if txt:
            lecturas.append((txt, conf))
            mejor_img = img_usada
    if mejor_img is None:
        mejor_img = variantes[0][0]
    return lecturas, mejor_img

def log_consenso(track_id, texto, origen, confianza, n_lecturas):
    try:
        os.makedirs('logs', exist_ok=True)
        existe = os.path.exists('logs/consenso_log.csv')
        with open('logs/consenso_log.csv', 'a', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            if not existe:
                w.writerow(['timestamp', 'track_id', 'placa', 'origen', 'confianza', 'n_lecturas'])
            w.writerow([datetime.now().isoformat(timespec='seconds'), track_id, texto, origen, confianza, n_lecturas])
    except: pass

def guardar_capturas(vehiculo_img, placa_img, texto_placa):
    os.makedirs('runs/capturas', exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_v = f"runs/capturas/{ts}_{texto_placa}_vehiculo.jpg"
    ruta_p = f"runs/capturas/{ts}_{texto_placa}_placa.jpg"
    try:
        cv2.imwrite(ruta_v, vehiculo_img)
        cv2.imwrite(ruta_p, placa_img)
    except: pass
    return ruta_v, ruta_p

def enviar_alerta_telegram_privada(token, chat_id, placa_detectada, info, rutas_imagenes=None):
    msg = (
        f"🚨 *ALERTA DE SEGURIDAD VECINAL* 🚨\n\n"
        f"📍 *Placa Detectada:* `{placa_detectada}`\n"
        f"🚘 *Vehículo:* {info.get('modelo', 'Desconocido')} | Color: {info.get('color', 'Desconocido')}\n"
        f"👤 *Propietario:* {info.get('propietario', 'Desconocido')}\n"
        f"🎯 *Similitud:* {info.get('similitud', 100.0)}%\n"
        f"⏰ *Fecha y Hora:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    try:
        if rutas_imagenes and len(rutas_imagenes) > 0 and os.path.exists(rutas_imagenes[0]):
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(rutas_imagenes[0], 'rb') as foto:
                requests.post(url, data={"chat_id": chat_id, "caption": msg, "parse_mode": "Markdown"}, files={"photo": foto}, timeout=15)
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except:
        pass

def dibujar_etiqueta(fotograma, texto, x1, y1, color_fondo, color_texto=BLANCO, escala=0.55):
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    grosor = 1
    (ancho, alto), _ = cv2.getTextSize(texto, fuente, escala, grosor + 1)
    cv2.rectangle(fotograma, (x1, y1 - alto - 8), (x1 + ancho + 6, y1), color_fondo, -1)
    cv2.putText(fotograma, texto, (x1 + 3, y1 - 4), fuente, escala, color_texto, grosor + 1, cv2.LINE_AA)

# ─── Inicialización de Puertos y Event Loop ───────────────────────────────────

def liberar_puerto_si_ocupado(port: int):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.close()
    except OSError:
        try:
            import subprocess
            if os.name == 'nt':
                output = subprocess.check_output(f'netstat -ano | findstr LISTENING | findstr :{port}', shell=True).decode('utf-8', errors='ignore')
                for line in output.strip().split('\n'):
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        if pid.isdigit() and int(pid) != os.getpid():
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                output = subprocess.check_output(f'lsof -t -i:{port}', shell=True).decode('utf-8', errors='ignore')
                for line in output.strip().split('\n'):
                    pid = line.strip()
                    if pid.isdigit() and int(pid) != os.getpid(): os.kill(int(pid), 9)
            time.sleep(1.5)
        except: pass

@app.on_event("startup")
async def _on_startup():
    estado_servidor_saas.loop = asyncio.get_running_loop()

    # Sincronizar automáticamente config.env con el usuario admin (ID: 1) para no usar configuraciones obsoletas
    for config_path in ["config.env", "../yolo-plate-recognition/config.env"]:
        if os.path.exists(config_path):
            try:
                env_tok, env_chat, env_gemini = "", "", ""
                with open(config_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("TELEGRAM_TOKEN="):
                            env_tok = line.split("=", 1)[1].strip()
                        elif line.startswith("TELEGRAM_CHAT_ID="):
                            env_chat = line.split("=", 1)[1].strip()
                        elif line.startswith("GEMINI_API_KEY="):
                            env_gemini = line.split("=", 1)[1].strip()
                if env_tok or env_chat:
                    cuenta = db_global.obtener_cuenta_por_id(1)
                    if not cuenta:
                        db_global.crear_cuenta("admin@alertavecinal.com", hash_password("admin123"))
                        cuenta = db_global.obtener_cuenta_por_id(1)
                    
                    if cuenta:
                        db_global.actualizar_config_cuenta(
                            1,
                            cuenta.get("rtsp_url") or "",
                            env_chat or cuenta.get("telegram_chat_id") or "",
                            env_tok or cuenta.get("telegram_token") or "",
                            env_gemini or cuenta.get("gemini_api_key") or ""
                        )
                        print(f"[Startup Config] Telegram Token y Chat ID actualizados para Admin (ID: 1) desde config.env")
            except Exception as e:
                print(f"[Startup Config Error] {e}")

    # Autoiniciar pipelines para todos los usuarios con cámaras al arrancar el servidor
    try:
        cuentas_con_camara = db_global.obtener_todas_las_cuentas_con_camara()
        print(f"[Startup] Inicializando pipelines persistentes para {len(cuentas_con_camara)} cuentas...")
        for cuenta in cuentas_con_camara:
            estado_servidor_saas.obtener_o_crear_pipeline(cuenta["id"], cuenta)
    except Exception as e:
        print(f"[Startup] Error iniciando pipelines por defecto: {e}")

@app.on_event("shutdown")
async def _on_shutdown():
    estado_servidor_saas.apagar_todo()

if __name__ == "__main__":
    print("=" * 60)
    print("  🖥️  AlertaVecinal — Servidor IA SaaS WebSocket V14")
    print("=" * 60)
    print(f"  Puerto del Servidor: {SERVER_PORT}")
    print("=" * 60 + "\n")

    liberar_puerto_si_ocupado(SERVER_PORT)

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=SERVER_PORT,
            log_level="warning",
            ws_max_size=64 * 1024 * 1024,
        )
    except KeyboardInterrupt:
        print("Apagando servidor...")
