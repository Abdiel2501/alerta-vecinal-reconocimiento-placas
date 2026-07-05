# -*- coding: utf-8 -*-
"""
run_original_telegram_v11.py — Motor de IA V11 (Gemini Fallback + EasyOCR Estable)
═══════════════════════════════════════════════════════════════
NUEVO en V11:

  [1] Gemini API Fallback (Respaldo Inteligente)
      - Si una placa está en el cuadro de diagnóstico (cuadro gris) por más de 2 segundos
        (aprox. 30 a 45 frames) y el OCR local no ha logrado leer un texto válido, la IA
        toma una captura del recorte de la placa y lo envía a la API de Gemini 1.5 Flash.
      - Esta llamada se ejecuta en un hilo secundario independiente para no congelar los FPS.
      - Si Gemini detecta el texto, se actualiza el estado del vehículo en vivo.
      - Para activarlo, agrega `GEMINI_API_KEY=tu_clave_aqui` en tu archivo `config.env`.
        Si no hay clave, el sistema simplemente usará el OCR local sin problemas.

  [2] Reversión a EasyOCR Estable
      - Debido a que PaddleOCR tiene severos conflictos de versiones con CUDA y Protobuf
        en Windows (provocando congelamientos al abrir la cámara), regresamos a EasyOCR.
      - Se mantiene el filtro dinámico de contraste y brillo para preprocesar.
      
  [3] Cuadro Gris de Diagnóstico en Tiempo Real
      - Muestra un cuadro gris delgado cuando YOLO detecta la placa, y se vuelve de color
        y con texto solo cuando el OCR local (o Gemini) logran descifrarla.
"""
import cv2
import time
import os
import sys
import io
import queue
import threading
import sqlite3
import difflib
import requests
import re
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime
from PIL import Image
from ultralytics import YOLO
from paddleocr import PaddleOCR

# Silenciar logs internos de PaddleOCR
import logging
logging.getLogger("ppocr").setLevel(logging.ERROR)

# Cargar soporte de Gemini si está disponible
try:
    import google.generativeai as genai
    GEMINI_DISPONIBLE = True
except ImportError:
    GEMINI_DISPONIBLE = False

import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────
# Carga de credenciales desde config.env
# ─────────────────────────────────────────────────────────────────────

def _get_appdata_dir():
    appdata = os.getenv('APPDATA') or os.path.expanduser('~')
    d = os.path.join(appdata, 'AlertaVecinal', 'System')
    os.makedirs(d, exist_ok=True)
    return d

DB_PATH = os.path.join(_get_appdata_dir(), "secure_placas.db")
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
GEMINI_API_KEY = ""

# Intentar leer desde las ubicaciones estándar
for r in ["config.env", "../yolo-plate-recognition/config.env"]:
    if os.path.exists(r):
        with open(r, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_TOKEN="):
                    TELEGRAM_TOKEN = line.split("=", 1)[1].strip()
                elif line.startswith("TELEGRAM_CHAT_ID="):
                    TELEGRAM_CHAT_ID = line.split("=", 1)[1].strip()
                elif line.startswith("GEMINI_API_KEY="):
                    GEMINI_API_KEY = line.split("=", 1)[1].strip()
        break

GEMINI_MODEL_NAME = "models/gemini-1.5-flash" # Default fallback

if GEMINI_DISPONIBLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("💡 Gemini API configurada exitosamente para fallback.")
        # Listar y buscar modelo compatible dinamicamente
        modelos = [m.name for m in genai.list_models()]
        print(f"📦 Modelos Gemini disponibles: {modelos}")
        
        # Buscar el mejor modelo de Flash disponible, de lo contrario un Pro anterior
        encontrado = False
        for m in ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-1.5-pro", "models/gemini-pro"]:
            if m in modelos:
                GEMINI_MODEL_NAME = m
                encontrado = True
                break
        if not encontrado:
            # Buscar coincidencia parcial
            for m in modelos:
                if "gemini" in m and "flash" in m:
                    GEMINI_MODEL_NAME = m
                    break
        print(f"🎯 Usando modelo Gemini: {GEMINI_MODEL_NAME}")
    except Exception as e:
        print(f"⚠️ Error configurando Gemini: {e}")
        GEMINI_API_KEY = ""
else:
    print("⚠️ Gemini no configurado. Para activarlo, añade GEMINI_API_KEY=tu_clave en config.env")

class DatabasePlacas:
    def consultar_placa(self, texto, umbral=0.78):
        if not os.path.exists(DB_PATH):
            return False, None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM placas_robadas WHERE placa=? AND activo=1", (texto,))
            f = cur.fetchone()
            if f:
                conn.close()
                return True, {**dict(f), "similitud": 1.0}
            cur.execute("SELECT * FROM placas_robadas WHERE activo=1")
            todas = cur.fetchall()
            conn.close()
            mejor, ms = None, 0.0
            for row in todas:
                s = difflib.SequenceMatcher(None, texto, row["placa"]).ratio()
                if s > ms:
                    ms, mejor = s, row
            if ms >= umbral and mejor:
                return True, {**dict(mejor), "similitud": round(ms * 100, 1)}
        except:
            pass
        return False, None

# ─────────────────────────────────────────────────────────────────────
# ReID e Identificación
# ─────────────────────────────────────────────────────────────────────

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
                    placa_actual['checked_db'] = False
                    reid = True
                del self.perdidos[mejor_pid]

        prev = self.activos.get(tid, {})
        if area > prev.get('area', 0):
            self.activos[tid] = {'cls':cls, 'hist':hist, 'area':area, 'pos':(cx,cy), 'placa_data':placa_actual}
        else:
            self.activos[tid]['pos'] = (cx, cy)
            self.activos[tid]['placa_data'] = placa_actual
        return placa_actual, reid

    def marcar_ids(self, ids_vistos):
        for did in set(self.activos.keys()) - ids_vistos:
            info = self.activos.pop(did)
            info['frames_sin_ver'] = 0
            self.perdidos[did] = info
        viejos = [p for p, i in self.perdidos.items() if i.get('frames_sin_ver', 0) > self.max_frames]
        for p in viejos: del self.perdidos[p]
        for p in self.perdidos: self.perdidos[p]['frames_sin_ver'] += 1

# ─────────────────────────────────────────────────────────────────────
# Preprocesamiento Dinámico
# ─────────────────────────────────────────────────────────────────────

def corregir_perspectiva(roi):
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

def preprocesamiento_dinamico(roi_base, area):
    h, w = roi_base.shape[:2]
    if h == 0 or w == 0: return roi_base
    
    T = 180.0
    if area >= 3000:
        sc = T / h
        img = cv2.resize(roi_base, (max(1,int(w*sc)), max(1,int(h*sc))), interpolation=cv2.INTER_LANCZOS4)
    else:
        img = roi_base.copy()
        for _ in range(3):
            if img.shape[0] >= int(T): break
            img = cv2.resize(img,(img.shape[1]*2,img.shape[0]*2), interpolation=cv2.INTER_CUBIC)
        sc = T/img.shape[0]
        img = cv2.resize(img,(max(1,int(img.shape[1]*sc)),max(1,int(img.shape[0]*sc))), interpolation=cv2.INTER_LANCZOS4)

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
    else:
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6,6))
        eq = clahe.apply(gray)
        res = cv2.bilateralFilter(eq, d=9, sigmaColor=60, sigmaSpace=60)
        
    return cv2.cvtColor(res, cv2.COLOR_GRAY2BGR)

# ─────────────────────────────────────────────────────────────────────
# Validaciones de placa
# ─────────────────────────────────────────────────────────────────────

def validar_formato_placa(texto):
    texto = re.sub(r'[^A-Z0-9]', '', texto.upper())
    # Las placas de coche de Tamaulipas/México tienen exactamente 7 caracteres (ej: XKR3865)
    if len(texto) != 7:
        return ""
        
    letras = sum(1 for c in texto if c.isalpha())
    numeros = sum(1 for c in texto if c.isdigit())
    
    if letras == 0 or numeros == 0:
        return ""
    if letras > 4 or numeros > 4:
        return ""
        
    if re.match(r'^[A-Z]{3}[0-9]{2}[A-Z0-9][0-9]{2}$', texto):
        texto = texto[:5] + texto[6:]
        
    if len(texto) == 7:
        fl = {'0':'O','1':'I','5':'S','8':'B'}.get
        fn = {'O':'0','I':'1','S':'5','Z':'2','B':'8','G':'6'}.get
        texto = (fl(texto[0],texto[0]) + fl(texto[1],texto[1]) + fl(texto[2],texto[2]) +
                 fn(texto[3],texto[3]) + fn(texto[4],texto[4]) +
                 fn(texto[5],texto[5]) + fn(texto[6],texto[6]))
                 
    return texto

# ─────────────────────────────────────────────────────────────────────
# Hilo de Inferencia de Gemini (Asíncrono)
# ─────────────────────────────────────────────────────────────────────

def consultar_gemini_hilo(img_placa, track_id, vehicle_plates_ref, lock, es_vehiculo_completo=False):
    if not GEMINI_DISPONIBLE or not GEMINI_API_KEY:
        return
        
    try:
        pil_img = Image.fromarray(cv2.cvtColor(img_placa, cv2.COLOR_BGR2RGB))
        print(f"[Gemini API] Solicitando lectura de placa para ID {track_id} (Vehículo completo: {es_vehiculo_completo}) usando {GEMINI_MODEL_NAME}...")
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        
        if es_vehiculo_completo:
            prompt = (
                "Locate the license plate on this vehicle and extract the plate number. "
                "It is a Mexican license plate (usually from Tamaulipas state). "
                "Return ONLY the alphanumeric plate number in plain uppercase text without spaces or hyphens. "
                "Example output: XKR3865 or XLK7269. "
                "If no plate is visible or readable, respond exactly with 'NONE'."
            )
        else:
            prompt = (
                "Extract the license plate number from this cropped vehicle image. "
                "It is a Mexican license plate (usually from Tamaulipas state). "
                "Return ONLY the alphanumeric plate number in plain uppercase text without spaces or hyphens. "
                "Example output: XKR3865 or XLK7269. "
                "If no text or plate is visible, respond exactly with 'NONE'."
            )
        
        response = model.generate_content([prompt, pil_img])
        texto_raw = response.text.strip().upper()
        
        if texto_raw and texto_raw != "NONE":
            texto_limpio = validar_formato_placa(texto_raw)
            if texto_limpio:
                print(f"✅ [Gemini API] Éxito para ID {track_id} -> Leído: '{texto_limpio}'")
                with lock:
                    prev = vehicle_plates_ref.get(track_id)
                    # Doble verificación: si ya había lectura local
                    if prev and prev.get('plate'):
                        if prev['plate'] == texto_limpio:
                            vehicle_plates_ref[track_id]['origen'] = 'Local/Gemini'
                        else:
                            # Gemini tiene prioridad absoluta por precisión, sobreescribimos
                            vehicle_plates_ref[track_id]['plate'] = texto_limpio
                            vehicle_plates_ref[track_id]['confidence'] = 0.99
                            vehicle_plates_ref[track_id]['origen'] = 'Gemini (Overridden)'
                    else:
                        # Si local no había leído nada
                        vehicle_plates_ref[track_id] = {
                            'plate': texto_limpio, 'confidence': 0.99,
                            'checked_db': False, 'es_robado': False,
                            'notified': False, 'info': None,
                            'origen': 'Gemini'
                        }
            else:
                print(f"❌ [Gemini API] Texto detectado no tiene formato de placa: '{texto_raw}'")
        else:
            print(f"⚠️ [Gemini API] No se pudo leer ninguna placa para ID {track_id}")
            
    except Exception as e:
        print(f"🚨 [Gemini API Error] Falló llamada: {e}")

# ─────────────────────────────────────────────────────────────────────
# Lector EasyOCR local
# ─────────────────────────────────────────────────────────────────────

def leer_placa_completa(reader, roi_base, area, track_id):
    img_optima = preprocesamiento_dinamico(roi_base, area)
    
    # Intento 1: Reconocimiento rápido (det=False)
    try:
        res = reader.ocr(img_optima, det=False, cls=False)
        if res and res[0] and res[0][0]:
            txt, conf = res[0][0]
            txt_valido = validar_formato_placa(txt)
            print(f"[OCR Debug] ID {track_id} -> Rápido: '{txt}' (Conf: {conf:.2f}) -> Válido: '{txt_valido}'")
            if txt_valido and conf > 0.50:
                return txt_valido, float(conf), img_optima
    except Exception as e:
        pass

    # Intento 2 (Respaldo): Detección + Reconocimiento
    try:
        res = reader.ocr(img_optima, det=True, cls=False)
        if res and res[0]:
            lineas = sorted(res[0], key=lambda r: r[0][0][0])
            txt_completo = ""
            conf_acum = 0.0
            for r in lineas:
                txt_completo += r[1][0]
                conf_acum += r[1][1]
            conf_prom = conf_acum / len(lineas) if lineas else 0.0
            txt_valido = validar_formato_placa(txt_completo)
            print(f"[OCR Debug] ID {track_id} -> Completo: '{txt_completo}' (Conf: {conf_prom:.2f}) -> Válido: '{txt_valido}'")
            if txt_valido:
                return txt_valido, conf_prom, img_optima
    except Exception as e:
        pass

    return "", 0.0, img_optima

class VotadorPlaca:
    def __init__(self, ventana=10):
        self.historial = []
        self.ventana   = ventana

    def agregar(self, texto, conf):
        if texto:
            self.historial.append((texto, conf))
            if len(self.historial) > self.ventana:
                self.historial.pop(0)

    def mejor(self):
        if not self.historial: return "", 0.0
        votos = {}
        for t, c in self.historial: votos[t] = votos.get(t, 0) + c
        g = max(votos, key=votos.get)
        return g, max(c for t, c in self.historial if t == g)

    def estable(self):
        if len(self.historial) < 6: return False
        t, c = self.mejor()
        return c >= 0.75 and sum(1 for txt,_ in self.historial if txt==t) >= 6

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def put_text(frame, text, pos, color=(0,255,0), font_scale=0.6, thickness=2, bg=(0,0,0)):
    ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    tx, ty = pos
    cv2.rectangle(frame, (tx,ty-ts[1]-5), (tx+ts[0]+5,ty+5), bg, cv2.FILLED)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

# ─────────────────────────────────────────────────────────────────────
# Hilo OCR
# ─────────────────────────────────────────────────────────────────────

class DeteccionOCRWorker:
    def __init__(self, lp_detector, reader):
        self.lp_detector = lp_detector
        self.reader      = reader
        self.cola        = queue.Queue(maxsize=6)
        self.resultados  = {}
        self.lock        = threading.Lock()
        self.running     = True
        self.hilo        = threading.Thread(target=self._loop, daemon=True)
        self.hilo.start()

    def enviar(self, track_id, vehicle_roi, veh_bbox, frame_num):
        try: self.cola.put_nowait((track_id, vehicle_roi.copy(), veh_bbox, frame_num))
        except queue.Full: pass

    def obtener(self, track_id):
        with self.lock: return self.resultados.get(track_id)

    def detener(self):
        self.running = False
        try: self.cola.put_nowait(None)
        except queue.Full: pass

    def _loop(self):
        while self.running:
            try: item = self.cola.get(timeout=1.0)
            except queue.Empty: continue
            if item is None: break
            track_id, vehicle_roi, veh_bbox, frame_num = item
            resultado = self._procesar(track_id, vehicle_roi, veh_bbox, frame_num)
            if resultado:
                with self.lock:
                    prev = self.resultados.get(track_id)
                    if prev is None or (resultado['plate'] and not prev.get('plate')) or resultado['confidence'] >= prev.get('confidence',0):
                        self.resultados[track_id] = resultado
            self.cola.task_done()

    def _procesar(self, track_id, vehicle_roi, veh_bbox, frame_num):
        try: plate_results = self.lp_detector.predict(vehicle_roi, verbose=False)
        except: return None

        if not plate_results or len(plate_results[0].boxes) == 0:
            return None

        x1v, y1v = veh_bbox[0], veh_bbox[1]
        mejores = []

        for plate_box in plate_results[0].boxes:
            conf_plate = float(plate_box.conf[0])
            if conf_plate < 0.35: continue

            lpx1,lpy1,lpx2,lpy2 = map(int, plate_box.xyxy[0])
            ph, pw = lpy2-lpy1, lpx2-lpx1
            area   = ph * pw

            m = max(int(pw * 0.12), 4)
            lpx1c = max(0, lpx1 - m)
            lpy1c = max(0, lpy1 - m)
            lpx2c = min(vehicle_roi.shape[1], lpx2 + m)
            lpy2c = min(vehicle_roi.shape[0], lpy2 + m)

            px1g,py1g = lpx1c+x1v, lpy1c+y1v
            px2g,py2g = lpx2c+x1v, lpy2c+y1v

            roi_placa = vehicle_roi[lpy1c:lpy2c, lpx1c:lpx2c]
            if roi_placa.size == 0: continue

            texto, conf, img_usada = leer_placa_completa(self.reader, roi_placa, area, track_id)

            mejores.append({
                'plate': texto, 'confidence': conf, 'img': img_usada,
                'bbox_global': (px1g,py1g,px2g,py2g), 'area': area,
                'frame_num': frame_num, 'roi_cruda': roi_placa.copy()
            })

        if not mejores: return None
        con_texto = [m for m in mejores if m['plate']]
        if con_texto:
            return max(con_texto, key=lambda x: x['confidence'])
        return mejores[0]

# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    video_path    = 0
    model_path    = 'yolo11n.pt'
    lp_model_path = 'runs/detect/license_plate_detector/weights/best.pt'
    output_video  = 'output_v11.mp4'
    classes_to_detect = [0,1,2,3,5]

    print("🤖 Cargando V11 (PaddleOCR CPU + Gemini Fallback)...")
    import torch
    usar_gpu = torch.cuda.is_available()
    print(f"⚡ GPU PyTorch/OCR: {'Sí' if usar_gpu else 'CPU'}")

    model       = YOLO(model_path)
    lp_detector = YOLO(lp_model_path)
    # Forzamos use_gpu=False para PaddleOCR en CPU y evitar la colisión CUDA con YOLO en la GPU
    try:
        reader = PaddleOCR(use_angle_cls=False, lang='en', use_gpu=False)
    except Exception as e:
        print(f"Error cargando PaddleOCR: {e}")
        sys.exit(1)
        
    reider      = ReidentificadorVehiculos(max_frames=90, umbral=0.72)
    worker      = DeteccionOCRWorker(lp_detector, reader)

    class_names  = {0:"person",1:"bicycle",2:"car",3:"motorbike",5:"bus"}
    class_colors = {0:(255,255,255),1:(0,255,0),2:(0,0,255),3:(255,255,0),5:(0,255,255)}

    vehicle_plates    = {}
    votadores         = {}
    mejor_area        = {}
    track_first_seen  = {}  # Registra cuándo vimos el vehículo por primera vez
    gemini_consultado = set()  # Evita repetir consultas de Gemini para un mismo ID
    total_class_count = Counter()
    seen_ids          = defaultdict(set)
    frame_number      = 0
    blur_enabled      = True
    paused            = False

    lock_plates = threading.Lock()

    print("📹 Abriendo cámara...")
    cap = None
    for backend, nombre in [(cv2.CAP_MSMF,"MSMF"),(cv2.CAP_DSHOW,"DSHOW"),(cv2.CAP_ANY,"ANY")]:
        c = cv2.VideoCapture(video_path, backend)
        if c.isOpened():
            ret, fot = c.read()
            if ret and fot is not None:
                cap = c
                break
            c.release()

    if cap is None or not cap.isOpened():
        worker.detener()
        sys.exit(1)

    fps_cam = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    out = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*'mp4v'), fps_cam, (fw,fh))

    frame = None
    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret or frame is None: break

            t0 = time.time()
            frame_number += 1

            results = model.track(frame, persist=True, classes=classes_to_detect, verbose=False)
            current_frame_count = Counter()
            ids_vistos = set()

            for result in results:
                for box in result.boxes:
                    x1,y1,x2,y2 = map(int, box.xyxy[0])
                    cls          = int(box.cls[0])
                    confidence   = round(float(box.conf[0]), 2)

                    if box.id is None: continue
                    track_id = int(box.id[0].tolist())
                    ids_vistos.add(track_id)

                    if track_id not in track_first_seen:
                        track_first_seen[track_id] = frame_number

                    if track_id not in seen_ids[cls]:
                        seen_ids[cls].add(track_id)
                        total_class_count[class_names[cls]] += 1

                    reid_aplicado = False

                    if class_names[cls] in ["car","motorbike","bus"]:
                        vehicle_roi = frame[y1:y2, x1:x2]
                        if vehicle_roi.shape[0] < 50 or vehicle_roi.shape[1] < 50: continue
                        if confidence < 0.50: continue

                        with lock_plates:
                            placa_actual, reid_aplicado = reider.actualizar(
                                track_id, cls, (x1,y1,x2,y2), vehicle_roi, vehicle_plates.get(track_id)
                            )
                            if reid_aplicado: vehicle_plates[track_id] = placa_actual

                        # Solo enviamos a OCR si no tiene texto estable leído
                        vot = votadores.get(track_id)
                        if not (vot and vot.estable()):
                            worker.enviar(track_id, vehicle_roi, (x1,y1,x2,y2), frame_number)

                        res = worker.obtener(track_id)
                        texto = ""
                        conf = 0.0
                        px1g,py1g,px2g,py2g = 0,0,0,0
                        area = 0

                        if res:
                            texto, conf = res['plate'], res['confidence']
                            img_u = res['img']
                            px1g,py1g,px2g,py2g = res['bbox_global']
                            area  = res['area']

                            if texto:
                                if track_id not in votadores:
                                    votadores[track_id] = VotadorPlaca(ventana=10)
                                votadores[track_id].agregar(texto, conf)
                                texto_f, conf_f = votadores[track_id].mejor()

                                cv2.rectangle(frame,(px1g,py1g),(px2g,py2g),
                                              (255,255,255) if area >= 3000 else ((0,255,255) if area >= 800 else (0,165,255)),
                                              2)

                                if conf_f >= 0.12 and texto_f:
                                    with lock_plates:
                                        prev = vehicle_plates.get(track_id)
                                        # Solo actualizamos localmente si no hay lectura previa, o si la lectura previa era Local y esta es mejor.
                                        # NUNCA sobreescribimos si el origen es Gemini, Gemini (Overridden) o Local/Gemini.
                                        if prev is None or (prev.get('origen') == 'Local' and conf_f > prev.get('confidence', 0.0)):
                                            vehicle_plates[track_id] = {
                                                'plate': texto_f, 'confidence': conf_f,
                                                'checked_db': False, 'es_robado': False,
                                                'notified': False, 'info': None,
                                                'origen': 'Local'
                                            }
                                            parea = mejor_area.get(track_id, 0)
                                            if area >= parea:
                                                mejor_area[track_id] = area
                                                os.makedirs('plates', exist_ok=True)
                                                try: cv2.imwrite(f'plates/{frame_number}_{track_id}_{texto_f}_V11.png', img_u)
                                                except: pass
                            else:
                                # YOLO detectó placa, pero OCR local no ha leído nada (Gris Diagnóstico)
                                cv2.rectangle(frame,(px1g,py1g),(px2g,py2g),(128,128,128),1)

                        # [V11 FALLBACK/DOBLE VERIFICACIÓN INMEDIATA DE GEMINI]
                        # En cuanto se detecta y procesa la placa, lanzamos Gemini de inmediato para verificar
                        if (track_id not in gemini_consultado and GEMINI_API_KEY and res):
                            # Marcamos de inmediato para no hacer más de una llamada de API simultánea para este ID
                            gemini_consultado.add(track_id)
                            
                            # Lanzar consulta en un hilo separado con el recorte de la placa
                            roi_cruda_placa = res.get('roi_cruda')
                            if roi_cruda_placa is not None and roi_cruda_placa.size > 0:
                                t_gemini = threading.Thread(
                                    target=consultar_gemini_hilo,
                                    args=(roi_cruda_placa, track_id, vehicle_plates, lock_plates, False),
                                    daemon=True
                                )
                                t_gemini.start()

                        # [V11 FALLBACK DE VEHÍCULO COMPLETO SIN PLACA DETECTADA]
                        # Si ha pasado 1 segundo (15 frames) y YOLO detector de placa NO encontró ninguna placa (res es None),
                        # pero el coche sigue en pantalla sin placa registrada, mandamos el coche completo a Gemini.
                        frames_visible = frame_number - track_first_seen[track_id]
                        with lock_plates:
                            placa_registrada = vehicle_plates.get(track_id)
                        tiene_texto = placa_registrada is not None and placa_registrada.get('plate') != ""
                        
                        if (frames_visible >= 15 and not tiene_texto and 
                            track_id not in gemini_consultado and GEMINI_API_KEY and res is None):
                            
                            gemini_consultado.add(track_id)
                            if vehicle_roi is not None and vehicle_roi.size > 0:
                                t_gemini = threading.Thread(
                                    target=consultar_gemini_hilo,
                                    args=(vehicle_roi, track_id, vehicle_plates, lock_plates, True),
                                    daemon=True
                                )
                                t_gemini.start()

                        with lock_plates:
                            assigned = vehicle_plates.get(track_id)
                        if assigned:
                            bg, fg = (255,255,255), (0,0,0)
                            org = assigned.get('origen', 'Local')
                            put_text(frame, f"Plate: {assigned['plate']} ({org})", (x1, y2+40), color=fg, bg=bg)

                    color = class_colors.get(cls,(0,0,0))
                    cv2.rectangle(frame,(x1,y1),(x2,y2),color,3)
                    put_text(frame, f"{class_names[cls]} {confidence}", (x1,y1-10), color=color)
                    put_text(frame, f"ID: {track_id}", (x1,y2+20), color=color)

                    if class_names[cls] == "person" and blur_enabled:
                        p = frame[y1:y2,x1:x2]
                        if p.size > 0: frame[y1:y2,x1:x2] = cv2.GaussianBlur(p,(51,51),30)
                    current_frame_count[class_names[cls]] += 1

            reider.marcar_ids(ids_vistos)

            yo = 30
            for cn, ct in total_class_count.items(): put_text(frame, f"Total {cn}: {ct}", (10,yo)); yo += 20
            for cn, ct in current_frame_count.items(): put_text(frame, f"Frame {cn}: {ct}", (10,yo), color=(255,255,255)); yo += 20
            diff = time.time() - t0
            fps_c = 1.0 / diff if diff > 0 else 30.0
            put_text(frame, f"FPS: {fps_c:.1f}", (10,yo), color=(0,255,255)); yo += 20
            # Se removio el mensaje de V11 a peticion del usuario
            out.write(frame)

        if frame is not None:
            cv2.imshow('Detection and Tracking V11', frame)
        key = cv2.waitKey(1 if not paused else 0) & 0xFF
        if key == 27: break
        elif key == ord(' '): paused = not paused
        elif key == ord('b'): blur_enabled = not blur_enabled

    worker.detener()
    cap.release()
    out.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
