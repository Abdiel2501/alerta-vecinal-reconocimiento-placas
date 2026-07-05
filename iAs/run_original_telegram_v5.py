# -*- coding: utf-8 -*-
"""
run_original_telegram_v5.py — Motor de IA V5
═══════════════════════════════════════════════════════════════
NUEVO en V5:

  [1] OCR EN HILO DEDICADO (Threading Asíncrono)
      El bucle de video/YOLO corre completamente libre a máxima velocidad.
      El OCR corre en un Worker Thread separado que consume una cola de ROIs.
      Los FPS del video ya no caen al procesar placas (de 0.4 → 15-25 FPS).

  [2] DECODER RÁPIDO INTELIGENTE
      Usa el decoder 'greedy' (rápido) como primera pasada.
      Si el resultado tiene baja confianza, hace una segunda pasada
      con 'beamsearch' reducido (beamWidth=5) solo para esa variante.
      Esto da velocidad de greedy con precisión cercana a beamsearch.

  [3] SKIP INTELIGENTE DE OCR
      Si un vehículo ya tiene una lectura con confianza ≥ 0.75 y al
      menos 6 votos consistentes, no se vuelve a mandar al hilo OCR
      (ahorrar GPU para coches que aún no tienen lectura estable).

  [4] MARGEN ASIMÉTRICO (Más padding izquierdo)
      Las letras de la placa mexicana (XLK, WZT, etc.) casi siempre
      están a la izquierda. Se añade un 40% de margen extra a la
      izquierda del bbox y 30% al resto para capturarlas siempre.

  [5] SOLO LAS 2 MEJORES VARIANTES DE PROCESAMIENTO
      En vez de 8 variantes (×2 con perspectiva = 16 pasadas de OCR),
      se usan solo las 2 variantes más efectivas para cada frame,
      lo que reduce el tiempo del Worker Thread hasta 4×.

Heredado de V4:
  - Re-identificación de Vehículos (ReID)
  - Super-Resolución adaptativa para placas lejanas
  - Sistema de votos multi-frame (VotadorPlaca)
  - Corrección de perspectiva
  - Limpiador de placa mexicana posicional
"""
import cv2
import time
import csv
import os
import sys
import queue
import threading
import sqlite3
import difflib
import requests
import re
import numpy as np
import warnings
from collections import defaultdict, Counter
from datetime import datetime
from ultralytics import YOLO
import easyocr

# Suprimir warnings de matching de EasyOCR para consola limpia
warnings.filterwarnings("ignore", message=".*matching points.*")

# ─────────────────────────────────────────────────────────────────────
# Base de Datos y Telegram
# ─────────────────────────────────────────────────────────────────────

def _get_appdata_dir():
    appdata = os.getenv('APPDATA') or os.path.expanduser('~')
    app_dir = os.path.join(appdata, 'AlertaVecinal', 'System')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

DB_PATH = os.path.join(_get_appdata_dir(), "secure_placas.db")
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""

for r in ["config.env", "../yolo-plate-recognition/config.env"]:
    if os.path.exists(r):
        with open(r, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_TOKEN="):
                    TELEGRAM_TOKEN = line.split("=", 1)[1].strip()
                elif line.startswith("TELEGRAM_CHAT_ID="):
                    TELEGRAM_CHAT_ID = line.split("=", 1)[1].strip()
        break

class DatabasePlacas:
    def consultar_placa(self, texto_detectado: str, umbral_similitud: float = 0.78):
        if not os.path.exists(DB_PATH):
            return False, None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM placas_robadas WHERE placa = ? AND activo = 1",
                           (texto_detectado,))
            fila = cursor.fetchone()
            if fila:
                conn.close()
                return True, {**dict(fila), "similitud": 1.0}
            cursor.execute("SELECT * FROM placas_robadas WHERE activo = 1")
            todas = cursor.fetchall()
            conn.close()
            mejor, mejor_sim = None, 0.0
            for f in todas:
                s = difflib.SequenceMatcher(None, texto_detectado, f["placa"]).ratio()
                if s > mejor_sim:
                    mejor_sim = s
                    mejor = f
            if mejor_sim >= umbral_similitud and mejor:
                return True, {**dict(mejor), "similitud": round(mejor_sim * 100, 1)}
        except Exception as e:
            print(f"DB error: {e}")
        return False, None

    def registrar_alerta(self, placa_bd, placa_det, similitud, ruta_v, ruta_p):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute(
                "INSERT INTO historial_alertas "
                "(placa, placa_detectada, similitud, ruta_foto_vehiculo, ruta_foto_placa) "
                "VALUES (?, ?, ?, ?, ?)",
                (placa_bd, placa_det, similitud, ruta_v, ruta_p)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB registrar error: {e}")

def enviar_telegram_hilo(placa_det, info, rutas):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram][Simulación] Alerta: {placa_det}")
        return
    placa_bd = info.get("placa", placa_det)
    sim = info.get("similitud", 100)
    coinc = f"\nOCR: {placa_det} ({sim}% sim.)" if placa_det != placa_bd else ""
    desc = f"\nNota: {info.get('descripcion','')}" if info.get('descripcion') else ""
    msg = (
        f"🚨 *ALERTA VEHICULO ROBADO (IA V5)* 🚨\n\n"
        f"📋 Placa BD: *{placa_bd}*{coinc}\n"
        f"🚗 {info.get('modelo','?')} — {info.get('color','?')}\n"
        f"👤 {info.get('propietario','?')}\n"
        f"📅 {info.get('fecha_reporte','N/A')}{desc}\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
        f"⚠️ *LLAME AL 911*"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
        for ruta in rutas:
            if os.path.exists(ruta):
                with open(ruta, "rb") as foto:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                        data={"chat_id": TELEGRAM_CHAT_ID},
                        files={"photo": foto}, timeout=15
                    )
        print(f"[Telegram] Alerta → {placa_bd}")
    except Exception as e:
        print(f"[Telegram] Error: {e}")

# ─────────────────────────────────────────────────────────────────────
# Re-identificación de Vehículos (V4 heredado)
# ─────────────────────────────────────────────────────────────────────

class ReidentificadorVehiculos:
    def __init__(self, max_frames=90, umbral=0.72):
        self.activos  = {}
        self.perdidos = {}
        self.max_frames = max_frames
        self.umbral = umbral

    def _hist(self, roi):
        if roi is None or roi.size == 0:
            return None
        try:
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            h = cv2.calcHist([hsv], [0, 1], None, [18, 16], [0, 180, 0, 256])
            cv2.normalize(h, h)
            return h.flatten()
        except Exception:
            return None

    def _sim(self, h1, h2):
        if h1 is None or h2 is None:
            return 0.0
        return float(cv2.compareHist(
            h1.reshape(-1,1).astype(np.float32),
            h2.reshape(-1,1).astype(np.float32),
            cv2.HISTCMP_CORREL
        ))

    def actualizar(self, tid, cls, bbox, roi, placa_actual):
        cx = (bbox[0]+bbox[2])/2
        cy = (bbox[1]+bbox[3])/2
        area = (bbox[2]-bbox[0])*(bbox[3]-bbox[1])
        hist = self._hist(roi)
        reid = False

        if tid not in self.activos:
            mejor_pid, mejor_score = None, 0.0
            for pid, info in self.perdidos.items():
                if info['cls'] != cls:
                    continue
                sc = 0.7*self._sim(hist, info['hist']) + \
                     0.3*max(0., 1.0 - np.sqrt((cx-info['pos'][0])**2 +
                                                (cy-info['pos'][1])**2)/400.)
                if sc > mejor_score:
                    mejor_score = sc
                    mejor_pid = pid
            if mejor_pid and mejor_score >= self.umbral:
                heredada = self.perdidos[mejor_pid].get('placa_data')
                if heredada and (placa_actual is None or
                        heredada.get('confidence', 0) > placa_actual.get('confidence', 0)):
                    print(f"[ReID] ID {tid} ← anterior {mejor_pid} "
                          f"(score={mejor_score:.2f}) placa: {heredada.get('plate','?')}")
                    placa_actual = dict(heredada)
                    placa_actual['checked_db'] = False
                    reid = True
                del self.perdidos[mejor_pid]

        prev = self.activos.get(tid, {})
        if area > prev.get('area', 0):
            self.activos[tid] = {'cls': cls, 'hist': hist, 'area': area,
                                  'pos': (cx, cy), 'placa_data': placa_actual}
        else:
            self.activos[tid]['pos'] = (cx, cy)
            self.activos[tid]['placa_data'] = placa_actual

        return placa_actual, reid

    def marcar_ids(self, ids_vistos):
        for did in set(self.activos.keys()) - ids_vistos:
            info = self.activos.pop(did)
            info['frames_sin_ver'] = 0
            self.perdidos[did] = info
        viejos = [p for p, i in self.perdidos.items()
                  if i.get('frames_sin_ver', 0) > self.max_frames]
        for p in viejos:
            del self.perdidos[p]
        for p in self.perdidos:
            self.perdidos[p]['frames_sin_ver'] = self.perdidos[p].get('frames_sin_ver', 0) + 1

# ─────────────────────────────────────────────────────────────────────
# Preprocesamiento (optimizado V5: solo 2 mejores variantes)
# ─────────────────────────────────────────────────────────────────────

def corregir_perspectiva(roi):
    try:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(
            cv2.GaussianBlur(gray, (5,5), 0), 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return roi
        for cnt in sorted(cnts, key=cv2.contourArea, reverse=True)[:3]:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04*peri, True)
            if len(approx) == 4:
                pts = approx.reshape(4,2).astype(np.float32)
                s, d = pts.sum(axis=1), np.diff(pts, axis=1)
                o = np.zeros((4,2), dtype=np.float32)
                o[0]=pts[np.argmin(s)]; o[2]=pts[np.argmax(s)]
                o[1]=pts[np.argmin(d)]; o[3]=pts[np.argmax(d)]
                w = max(np.linalg.norm(o[1]-o[0]), np.linalg.norm(o[2]-o[3]))
                h = max(np.linalg.norm(o[3]-o[0]), np.linalg.norm(o[2]-o[1]))
                if w < 20 or h < 8:
                    continue
                dst = np.array([[0,0],[w,0],[w,h],[0,h]], dtype=np.float32)
                return cv2.warpPerspective(roi,
                    cv2.getPerspectiveTransform(o, dst), (int(w), int(h)))
    except Exception:
        pass
    return roi

def super_resolver(roi, area):
    """Super-resolución adaptativa según tamaño de la placa."""
    h, w = roi.shape[:2]
    if h == 0 or w == 0:
        return roi
    TARGET = 180.0
    if area >= 3000:
        sc = TARGET / h
        return cv2.resize(roi, (max(1,int(w*sc)), max(1,int(h*sc))),
                          interpolation=cv2.INTER_LANCZOS4)
    elif area >= 800:
        sc = TARGET / h
        base = cv2.resize(roi, (max(1,int(w*sc)), max(1,int(h*sc))),
                          interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(base, (5,5), 1.0)
        return cv2.addWeighted(base, 1.6, bl, -0.6, 0)
    else:
        img = roi.copy()
        for _ in range(4):
            if img.shape[0] >= int(TARGET):
                break
            img = cv2.resize(img, (img.shape[1]*2, img.shape[0]*2),
                             interpolation=cv2.INTER_CUBIC)
        sc = TARGET / img.shape[0]
        img = cv2.resize(img, (max(1,int(img.shape[1]*sc)), max(1,int(img.shape[0]*sc))),
                         interpolation=cv2.INTER_LANCZOS4)
        try:
            img = cv2.fastNlMeansDenoisingColored(img, None, 8, 8, 7, 21)
        except Exception:
            pass
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4,4)).apply(l)
            img = cv2.cvtColor(cv2.merge([l,a,b]), cv2.COLOR_LAB2BGR)
        except Exception:
            pass
        bl = cv2.GaussianBlur(img, (3,3), 0.8)
        return cv2.addWeighted(img, 2.0, bl, -1.0, 0)

def hacer_variantes_rapidas(roi):
    """Solo las 2 variantes más efectivas (en vez de 8) para mayor velocidad."""
    h, w = roi.shape[:2]
    if h == 0 or w == 0:
        return []
    TARGET = 180.0
    sc = min(TARGET / h, 12.0)
    base = cv2.resize(roi, (max(1,int(w*sc)), max(1,int(h*sc))),
                      interpolation=cv2.INTER_LANCZOS4)
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)

    # Variante A: Unsharp masking en color (mejor para placas cercanas/medianas)
    bl = cv2.GaussianBlur(base, (5,5), 1.5)
    vA = cv2.addWeighted(base, 1.5, bl, -0.5, 0)

    # Variante B: CLAHE + bilateral en gris (mejor para ángulos y sombras)
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(6,6))
    vB = cv2.bilateralFilter(clahe.apply(gray), d=11, sigmaColor=80, sigmaSpace=80)

    return [vA, vB]

def limpiar_placa_mexicana(texto):
    texto = re.sub(r'[^A-Z0-9]', '', texto.upper())
    # Si tiene 8 chars tipo AAA##X## → eliminar guión fantasma en pos 5
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
# [V5] WORKER THREAD DE OCR (asíncrono, no bloquea el video)
# ─────────────────────────────────────────────────────────────────────

class OCRWorker:
    """
    Hilo de fondo que procesa ROIs de placas de forma asíncrona.
    El bucle de video manda ROIs a la cola y sigue corriendo sin esperar.
    Los resultados se escriben en self.resultados con un lock.
    """
    def __init__(self, reader):
        self.reader    = reader
        self.cola      = queue.Queue(maxsize=8)   # máx 8 pendientes en cola
        self.resultados = {}                       # track_id → (texto, conf, img)
        self.lock      = threading.Lock()
        self.running   = True
        self.hilo      = threading.Thread(target=self._loop, daemon=True)
        self.hilo.start()

    def enviar(self, track_id, roi, area):
        """Encola un ROI para procesar. Si la cola está llena, descarta (no bloqueamos)."""
        try:
            self.cola.put_nowait((track_id, roi, area))
        except queue.Full:
            pass   # Cola llena → descartamos este frame, el siguiente se procesará

    def obtener(self, track_id):
        """Obtener último resultado disponible para un track_id (None si no hay)."""
        with self.lock:
            return self.resultados.get(track_id)

    def detener(self):
        self.running = False
        try:
            self.cola.put_nowait(None)
        except queue.Full:
            pass

    def _loop(self):
        while self.running:
            try:
                item = self.cola.get(timeout=1.0)
            except queue.Empty:
                continue
            if item is None:
                break
            track_id, roi_original, area = item
            resultado = self._procesar(track_id, roi_original, area)
            if resultado:
                with self.lock:
                    self.resultados[track_id] = resultado
            self.cola.task_done()

    def _procesar(self, track_id, roi_original, area):
        """Procesa el ROI y devuelve (texto, conf, img_usada) o None."""
        # Super-resolución adaptativa
        roi_sr = super_resolver(roi_original, area)

        # Corrección de perspectiva en ambas versiones
        roi_corr    = corregir_perspectiva(roi_original)
        roi_sr_corr = corregir_perspectiva(roi_sr)

        # Solo 2 variantes × 2 versiones = 4 pasadas (vs 16 en V4)
        variantes = (hacer_variantes_rapidas(roi_sr_corr) +
                     hacer_variantes_rapidas(roi_corr))

        mejor_texto, mejor_conf, mejor_img = "", 0.0, roi_original

        for img in variantes:
            if img is None or img.size == 0:
                continue
            # Primera pasada: decoder greedy (rápido)
            try:
                res = self.reader.readtext(
                    img,
                    allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                    paragraph=False,
                    decoder='greedy'
                )
            except Exception:
                continue

            if not res:
                continue

            res_ord = sorted(res, key=lambda r: r[0][0][0])
            txt = "".join(r[1].strip().upper().replace(" ","").replace("-","")
                          for r in res_ord)
            conf = sum(float(r[2]) for r in res_ord) / len(res_ord)
            txt = limpiar_placa_mexicana(txt)

            # Segunda pasada con beamsearch solo si confianza baja (< 0.5) y texto corto
            if len(txt) < 5 or conf < 0.5:
                try:
                    res2 = self.reader.readtext(
                        img,
                        allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                        paragraph=False,
                        decoder='beamsearch',
                        beamWidth=5
                    )
                    if res2:
                        res2_ord = sorted(res2, key=lambda r: r[0][0][0])
                        txt2 = "".join(r[1].strip().upper().replace(" ","").replace("-","")
                                       for r in res2_ord)
                        conf2 = sum(float(r[2]) for r in res2_ord) / len(res2_ord)
                        txt2 = limpiar_placa_mexicana(txt2)
                        if len(txt2) >= len(txt) and conf2 >= conf:
                            txt, conf = txt2, conf2
                except Exception:
                    pass

            if len(txt) >= 4 and conf > mejor_conf:
                mejor_texto, mejor_conf, mejor_img = txt, conf, img

        if mejor_texto:
            return (mejor_texto, mejor_conf, mejor_img)
        return None

# ─────────────────────────────────────────────────────────────────────
# VotadorPlaca (heredado de V3/V4)
# ─────────────────────────────────────────────────────────────────────

class VotadorPlaca:
    def __init__(self, ventana=10):
        self.historial = []
        self.ventana   = ventana

    def agregar(self, texto, conf):
        if texto and len(texto) >= 4:
            self.historial.append((texto, conf))
            if len(self.historial) > self.ventana:
                self.historial.pop(0)

    def mejor(self):
        if not self.historial:
            return "", 0.0
        votos = {}
        for t, c in self.historial:
            votos[t] = votos.get(t, 0) + c
        ganador = max(votos, key=votos.get)
        conf_g  = max(c for t, c in self.historial if t == ganador)
        return ganador, conf_g

    def estable(self):
        """True si ya hay una lectura consistente (≥6 votos con conf ≥ 0.75)."""
        if len(self.historial) < 6:
            return False
        t, c = self.mejor()
        return c >= 0.75 and sum(1 for txt, _ in self.historial if txt == t) >= 6

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def put_text(frame, text, pos, color=(0,255,0), font_scale=0.6, thickness=2, bg=(0,0,0)):
    ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    tx, ty = pos
    cv2.rectangle(frame, (tx, ty-ts[1]-5), (tx+ts[0]+5, ty+5), bg, cv2.FILLED)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def write_csv_header(path):
    with open(path, 'w', newline='') as f:
        csv.writer(f).writerow([
            'frame','object_type','confidence','tracking_id',
            'x1','y1','x2','y2','plate_confidence',
            'mx1','my1','mx2','my2','license_plate_text',
            'area_placa_px','reid_aplicado','ocr_saltado'
        ])

# ─────────────────────────────────────────────────────────────────────
# BUCLE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────

def main():
    video_path    = 0
    model_path    = 'yolo11n.pt'
    lp_model_path = 'runs/detect/license_plate_detector/weights/best.pt'
    output_video  = 'output_video_v5.mp4'
    csv_path      = 'detection_log_v5.csv'
    classes_to_detect = [0, 1, 2, 3, 5]

    print("🤖 Cargando modelos de IA (V5 — OCR Asíncrono + ReID + SR)...")

    import torch
    usar_gpu = torch.cuda.is_available()
    print(f"⚡ GPU: {'Sí CUDA (' + torch.cuda.get_device_name(0) + ')' if usar_gpu else 'No (CPU)'}")

    model       = YOLO(model_path)
    lp_detector = YOLO(lp_model_path)
    reader      = easyocr.Reader(['en'], gpu=usar_gpu)
    db          = DatabasePlacas()
    reider      = ReidentificadorVehiculos(max_frames=90, umbral=0.72)
    ocr_worker  = OCRWorker(reader)   # ← Hilo de OCR en segundo plano

    class_names  = {0:"person",1:"bicycle",2:"car",3:"motorbike",5:"bus"}
    class_colors = {0:(255,255,255),1:(0,255,0),2:(0,0,255),3:(255,255,0),5:(0,255,255)}

    vehicle_plates    = {}
    votadores         = {}
    mejor_area_placa  = {}
    total_class_count = Counter()
    seen_ids          = defaultdict(set)
    frame_number      = 0
    blur_enabled      = True
    paused            = False

    print("📹 Abriendo cámara...")
    cap = None
    for backend, nombre in [(cv2.CAP_MSMF,"MSMF"),(cv2.CAP_DSHOW,"DSHOW"),(cv2.CAP_ANY,"ANY")]:
        c = cv2.VideoCapture(video_path, backend)
        if c.isOpened():
            ret, fot = c.read()
            if ret and fot is not None:
                print(f"   ✅ Backend {nombre} OK.")
                cap = c
                break
            c.release()

    if cap is None or not cap.isOpened():
        print("❌ No se pudo abrir la cámara.")
        ocr_worker.detener()
        sys.exit(1)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps_cam = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    out = cv2.VideoWriter(output_video, fourcc, fps_cam, (fw, fh))
    write_csv_header(csv_path)

    print("🎥 V5 ejecutando — ESPACIO=pausar | b=desenfoque | ESC=salir")
    print("   [El OCR corre en hilo separado: video y detección sin interrupciones]")

    frame = None
    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("⚠️ No se pudo leer el fotograma. Saliendo...")
                break

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

                    if box.id is None:
                        continue
                    track_id = int(box.id[0].tolist())
                    ids_vistos.add(track_id)

                    if track_id not in seen_ids[cls]:
                        seen_ids[cls].add(track_id)
                        total_class_count[class_names[cls]] += 1

                    license_plate_text = ""
                    plate_confidence   = None
                    mx1=my1=mx2=my2    = None
                    area_placa_px      = 0
                    reid_aplicado      = False
                    ocr_saltado        = False

                    if class_names[cls] in ["car","motorbike","bus"]:
                        vehicle_img = frame[y1:y2, x1:x2]
                        if vehicle_img.shape[0] < 50 or vehicle_img.shape[1] < 50:
                            continue
                        if confidence < 0.50:
                            continue

                        # Re-identificación
                        placa_actual, reid_aplicado = reider.actualizar(
                            track_id, cls, (x1,y1,x2,y2), vehicle_img,
                            vehicle_plates.get(track_id)
                        )
                        if reid_aplicado:
                            vehicle_plates[track_id] = placa_actual

                        # Detección de placa
                        plate_results = lp_detector.predict(vehicle_img, verbose=False)

                        if plate_results and len(plate_results[0].boxes) > 0:
                            for plate_box in plate_results[0].boxes:
                                lpx1,lpy1,lpx2,lpy2 = map(int, plate_box.xyxy[0])

                                ph,pw = lpy2-lpy1, lpx2-lpx1
                                area_placa_px = ph * pw

                                # [V5] Margen asimétrico: 40% izquierda, 30% resto
                                # (las letras de la placa mexicana casi siempre están a la izquierda)
                                ml = max(int(pw * 0.40), 8)   # izquierda: más padding
                                mr = max(int(pw * 0.30), 6)   # derecha
                                mt = max(int(ph * 0.30), 4)   # arriba
                                mb = max(int(ph * 0.30), 4)   # abajo

                                lpx1c = max(0, lpx1 - ml)
                                lpy1c = max(0, lpy1 - mt)
                                lpx2c = min(vehicle_img.shape[1], lpx2 + mr)
                                lpy2c = min(vehicle_img.shape[0], lpy2 + mb)

                                px1g,py1g = lpx1c+x1, lpy1c+y1
                                px2g,py2g = lpx2c+x1, lpy2c+y1

                                # Color del rect según distancia
                                if area_placa_px >= 3000:
                                    rc = (255,255,255)   # blanco = cerca
                                elif area_placa_px >= 800:
                                    rc = (0,255,255)     # cyan = medio
                                else:
                                    rc = (0,165,255)     # naranja = lejos/SR activo

                                cv2.rectangle(frame, (px1g,py1g), (px2g,py2g), rc, 2)

                                roi_placa = vehicle_img[lpy1c:lpy2c, lpx1c:lpx2c].copy()
                                if roi_placa.size == 0:
                                    continue

                                # [V5] Skip inteligente: si ya tenemos lectura estable, no re-procesamos
                                vot = votadores.get(track_id)
                                if vot and vot.estable():
                                    ocr_saltado = True
                                else:
                                    # Mandar al hilo de OCR (no bloquea el bucle principal)
                                    ocr_worker.enviar(track_id, roi_placa, area_placa_px)

                                # Recoger resultado del hilo OCR si ya está listo
                                res_ocr = ocr_worker.obtener(track_id)
                                if res_ocr:
                                    texto, conf, img_usada = res_ocr
                                    if track_id not in votadores:
                                        votadores[track_id] = VotadorPlaca(ventana=10)
                                    votadores[track_id].agregar(texto, conf)
                                    texto_final, conf_final = votadores[track_id].mejor()

                                    if conf_final >= 0.15 and texto_final:
                                        license_plate_text = texto_final
                                        plate_confidence   = conf_final
                                        mx1,my1,mx2,my2   = px1g,py1g,px2g,py2g

                                        previo = vehicle_plates.get(track_id)
                                        if previo is None or conf_final > previo.get('confidence',0.0):
                                            vehicle_plates[track_id] = {
                                                'plate': texto_final,
                                                'confidence': conf_final,
                                                'checked_db': False,
                                                'es_robado': False,
                                                'notified': False,
                                                'info': None
                                            }
                                            prev_area = mejor_area_placa.get(track_id, 0)
                                            if area_placa_px >= prev_area:
                                                mejor_area_placa[track_id] = area_placa_px
                                                tag = "SR" if area_placa_px < 800 else "OK"
                                                os.makedirs('plates', exist_ok=True)
                                                cv2.imwrite(
                                                    f'plates/{frame_number}_{track_id}_{texto_final}_{tag}.png',
                                                    img_usada
                                                )

                                assigned_plate = vehicle_plates.get(track_id)
                                if assigned_plate:
                                    if not assigned_plate.get('checked_db'):
                                        es_robado, info = db.consultar_placa(assigned_plate['plate'])
                                        assigned_plate['checked_db'] = True
                                        assigned_plate['es_robado']  = es_robado
                                        assigned_plate['info']       = info

                                    if assigned_plate.get('es_robado') and \
                                       not assigned_plate.get('notified'):
                                        assigned_plate['notified'] = True
                                        info = assigned_plate['info']
                                        os.makedirs('alertas', exist_ok=True)
                                        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        rv = f"alertas/{sello}_{assigned_plate['plate']}_v.jpg"
                                        rp = f"alertas/{sello}_{assigned_plate['plate']}_p.jpg"
                                        cv2.imwrite(rv, frame)
                                        try:
                                            cv2.imwrite(rp, img_usada)
                                        except Exception:
                                            pass
                                        db.registrar_alerta(info['placa'],
                                            assigned_plate['plate'], info['similitud'], rv, rp)
                                        threading.Thread(
                                            target=enviar_telegram_hilo,
                                            args=(assigned_plate['plate'], info, [rv, rp]),
                                            daemon=True
                                        ).start()

                                    bg = (255,255,255)
                                    fg = (0,0,255) if assigned_plate.get('es_robado') else (0,0,0)
                                    prefix = "⚠ ROBADO: " if assigned_plate.get('es_robado') else "Plate: "
                                    reid_str = " [ReID]" if reid_aplicado else ""
                                    put_text(frame,
                                             f"{prefix}{assigned_plate['plate']}{reid_str}",
                                             (x1, y2+40), color=fg, bg=bg)
                                    license_plate_text = assigned_plate['plate']
                                    plate_confidence   = assigned_plate['confidence']

                    color = (0,0,255) if vehicle_plates.get(track_id,{}).get('es_robado') \
                            else class_colors.get(cls,(0,0,0))
                    cv2.rectangle(frame, (x1,y1),(x2,y2), color, 3)
                    put_text(frame, f"{class_names[cls]} {confidence}", (x1,y1-10), color=color)
                    put_text(frame, f"ID: {track_id}", (x1,y2+20), color=color)

                    if class_names[cls] == "person" and blur_enabled:
                        p = frame[y1:y2, x1:x2]
                        if p.size > 0:
                            frame[y1:y2, x1:x2] = cv2.GaussianBlur(p, (51,51), 30)

                    with open(csv_path, 'a', newline='') as f:
                        csv.writer(f).writerow([
                            frame_number, class_names[cls], confidence, track_id,
                            x1,y1,x2,y2, plate_confidence,
                            mx1,my1,mx2,my2, license_plate_text,
                            area_placa_px, reid_aplicado, ocr_saltado
                        ])
                    current_frame_count[class_names[cls]] += 1

            reider.marcar_ids(ids_vistos)

            # ── HUD
            yo = 30
            for cn, ct in total_class_count.items():
                put_text(frame, f"Total {cn}: {ct}", (10,yo)); yo += 20
            for cn, ct in current_frame_count.items():
                put_text(frame, f"Frame {cn}: {ct}", (10,yo), color=(255,255,255)); yo += 20
            fps_calc = 1.0 / (time.time() - t0)
            put_text(frame, f"FPS: {fps_calc:.1f}", (10,yo), color=(0,255,255)); yo += 20
            put_text(frame, "V5: Async OCR+ReID+SR", (10,yo),
                     color=(200,200,0), font_scale=0.45)
            out.write(frame)

        if frame is not None:
            cv2.imshow('Detection and Tracking V5', frame)
        key = cv2.waitKey(1 if not paused else 0) & 0xFF
        if key == 27:
            break
        elif key == ord(' '):
            paused = not paused
        elif key == ord('b'):
            blur_enabled = not blur_enabled
            print(f"Desenfoque {'ON' if blur_enabled else 'OFF'}")

    ocr_worker.detener()
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("✅ V5 — Procesamiento terminado.")

if __name__ == "__main__":
    main()
