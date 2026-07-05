# -*- coding: utf-8 -*-
"""
run_original_telegram_v9.py — Motor de IA V9 (PaddleOCR Real Optimizado)
═══════════════════════════════════════════════════════════════
NUEVO en V9:

  [1] Integración REAL de PaddleOCR
      - Eliminación absoluta de EasyOCR en el bucle principal.
      - Uso de `det=False` (solo reconocimiento de texto) directamente sobre el
        recorte de placa optimizado para evitar segmentación errónea de caracteres.
      - Respaldo a `det=True` solo en caso de no leer nada en la primera pasada.

  [2] Corrección del bug de logging en GPU
      - Se corrigió el print con formato `f"..."` que no evaluaba si se estaba usando GPU.

  [3] Evitar doble inferencia innecesaria
      - Optimizaciones de control de flujo para llamadas de un solo paso en la GPU.

  [4] Manteniendo:
      - Filtro Dinámico de Brillo (Día / Noche)
      - Validación de Formato de Placa Mexicana Estricto
      - Hilo de fondo y ReID
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
from ultralytics import YOLO

# Silenciar logs internos de PaddleOCR
import logging
logging.getLogger("ppocr").setLevel(logging.ERROR)

from paddleocr import PaddleOCR

import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────
# Base de Datos y Telegram
# ─────────────────────────────────────────────────────────────────────

def _get_appdata_dir():
    appdata = os.getenv('APPDATA') or os.path.expanduser('~')
    d = os.path.join(appdata, 'AlertaVecinal', 'System')
    os.makedirs(d, exist_ok=True)
    return d

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

def enviar_telegram_hilo(pd, info, rutas):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    pb  = info.get("placa", pd)
    sim = info.get("similitud", 100)
    co  = f"\nOCR: {pd} ({sim}% sim)" if pd != pb else ""
    msg = (
        f"🚨 *ALERTA VEHICULO ROBADO (V9)* 🚨\n\n"
        f"📋 Placa BD: *{pb}*{co}\n"
        f"🚗 {info.get('modelo','?')} — {info.get('color','?')}\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
        f"⚠️ *LLAME AL 911*"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10
        )
        for ruta in rutas:
            if os.path.exists(ruta):
                with open(ruta, "rb") as foto:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                        data={"chat_id": TELEGRAM_CHAT_ID}, files={"photo": foto}, timeout=15
                    )
    except:
        pass

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
    if len(texto) < 5 or len(texto) > 7:
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
# [V9] Lector PaddleOCR Real y Optimizado
# ─────────────────────────────────────────────────────────────────────

def leer_placa_completa(reader, roi_base, area):
    img_optima = preprocesamiento_dinamico(roi_base, area)
    
    # Intento 1: Reconocimiento rápido (det=False, asume que es una sola línea)
    try:
        res = reader.ocr(img_optima, det=False, cls=False)
        if res and res[0] and res[0][0]:
            txt, conf = res[0][0]
            txt_valido = validar_formato_placa(txt)
            if txt_valido and conf > 0.60:
                return txt_valido, float(conf), img_optima
    except:
        pass

    # Intento 2 (Respaldo): Detección + Reconocimiento completo
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
            if txt_valido:
                return txt_valido, conf_prom, img_optima
    except:
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
                    if prev is None or resultado['confidence'] >= prev.get('confidence',0):
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
            if conf_plate < 0.45: continue

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

            texto, conf, img_usada = leer_placa_completa(self.reader, roi_placa, area)

            if texto:
                mejores.append({
                    'plate': texto, 'confidence': conf, 'img': img_usada,
                    'bbox_global': (px1g,py1g,px2g,py2g), 'area': area,
                    'frame_num': frame_num
                })

        if not mejores: return None
        return max(mejores, key=lambda x: x['confidence'])

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def put_text(frame, text, pos, color=(0,255,0), font_scale=0.6, thickness=2, bg=(0,0,0)):
    ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    tx, ty = pos
    cv2.rectangle(frame, (tx,ty-ts[1]-5), (tx+ts[0]+5,ty+5), bg, cv2.FILLED)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    video_path    = 0
    model_path    = 'yolo11n.pt'
    lp_model_path = 'runs/detect/license_plate_detector/weights/best.pt'
    output_video  = 'output_v9.mp4'
    classes_to_detect = [0,1,2,3,5]

    print("🤖 Cargando V9 (PaddleOCR Real Optimizado + Dynamic Brillo)...")
    import torch
    usar_gpu = torch.cuda.is_available()
    print(f"⚡ GPU PyTorch/OCR: {'Sí' if usar_gpu else 'CPU'}")

    model       = YOLO(model_path)
    lp_detector = YOLO(lp_model_path)
    
    try:
        reader = PaddleOCR(use_angle_cls=False, lang='en', use_gpu=usar_gpu)
    except Exception as e:
        print(f"Error inicializando PaddleOCR: {e}")
        sys.exit(1)
        
    reider      = ReidentificadorVehiculos(max_frames=90, umbral=0.72)
    worker      = DeteccionOCRWorker(lp_detector, reader)

    class_names  = {0:"person",1:"bicycle",2:"car",3:"motorbike",5:"bus"}
    class_colors = {0:(255,255,255),1:(0,255,0),2:(0,0,255),3:(255,255,0),5:(0,255,255)}

    vehicle_plates    = {}
    votadores         = {}
    mejor_area        = {}
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

                    if track_id not in seen_ids[cls]:
                        seen_ids[cls].add(track_id)
                        total_class_count[class_names[cls]] += 1

                    reid_aplicado = False

                    if class_names[cls] in ["car","motorbike","bus"]:
                        vehicle_roi = frame[y1:y2, x1:x2]
                        if vehicle_roi.shape[0] < 50 or vehicle_roi.shape[1] < 50: continue
                        if confidence < 0.50: continue

                        placa_actual, reid_aplicado = reider.actualizar(
                            track_id, cls, (x1,y1,x2,y2), vehicle_roi, vehicle_plates.get(track_id)
                        )
                        if reid_aplicado: vehicle_plates[track_id] = placa_actual

                        vot = votadores.get(track_id)
                        if not (vot and vot.estable()):
                            worker.enviar(track_id, vehicle_roi, (x1,y1,x2,y2), frame_number)

                        res = worker.obtener(track_id)
                        if res:
                            texto, conf = res['plate'], res['confidence']
                            img_u = res['img']
                            px1g,py1g,px2g,py2g = res['bbox_global']
                            area  = res['area']

                            if track_id not in votadores:
                                votadores[track_id] = VotadorPlaca(ventana=10)
                            votadores[track_id].agregar(texto, conf)
                            texto_f, conf_f = votadores[track_id].mejor()

                            rc = (255,255,255) if area >= 3000 else ((0,255,255) if area >= 800 else (0,165,255))
                            cv2.rectangle(frame,(px1g,py1g),(px2g,py2g),rc,2)

                            if conf_f >= 0.12 and texto_f:
                                prev = vehicle_plates.get(track_id)
                                if prev is None or conf_f > prev.get('confidence',0.0):
                                    vehicle_plates[track_id] = {
                                        'plate': texto_f, 'confidence': conf_f,
                                        'checked_db': False, 'es_robado': False,
                                        'notified': False, 'info': None
                                    }
                                    parea = mejor_area.get(track_id, 0)
                                    if area >= parea:
                                        mejor_area[track_id] = area
                                        os.makedirs('plates', exist_ok=True)
                                        try: cv2.imwrite(f'plates/{frame_number}_{track_id}_{texto_f}_V9.png', img_u)
                                        except: pass

                        assigned = vehicle_plates.get(track_id)
                        if assigned:
                            bg, fg = (255,255,255), (0,0,0)
                            put_text(frame, f"Plate: {assigned['plate']}", (x1, y2+40), color=fg, bg=bg)

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
            fps_c = 1.0/(time.time()-t0)
            put_text(frame, f"FPS: {fps_c:.1f}", (10,yo), color=(0,255,255)); yo += 20
            put_text(frame, "V9: PaddleOCR Real + Dynamic", (10,yo), color=(200,200,0), font_scale=0.45)
            out.write(frame)

        if frame is not None:
            cv2.imshow('Detection and Tracking V9', frame)
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
