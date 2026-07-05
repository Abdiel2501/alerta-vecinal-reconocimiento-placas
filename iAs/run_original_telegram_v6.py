# -*- coding: utf-8 -*-
"""
run_original_telegram_v6.py — Motor de IA V6
═══════════════════════════════════════════════════════════════
NUEVO en V6:

  [1] LECTOR DE PLACA POR ZONAS (fix de letras faltantes tipo XLK)
      Divide el recorte de la placa en dos zonas:
        • Zona izquierda (40%): donde están las 3 letras del estado (XLK, WZT...)
          Se procesa con inversión y alto contraste para texto claro sobre fondo oscuro.
        • Zona derecha (60%): donde están los 4 números.
          Se procesa con CLAHE normal para texto oscuro sobre blanco.
      Los resultados se concatenan ordenando por posición x, garantizando
      que nunca se pierdan las letras del lado izquierdo.

  [2] PIPELINE COMPLETO EN HILO DE FONDO (fix de FPS)
      El hilo worker ahora hace TODO el trabajo pesado:
        • lp_detector.predict() (detección de la placa)
        • Preprocesamiento y super-resolución
        • OCR por zonas
      El bucle principal solo ejecuta model.track() (YOLO vehículos) y dibuja.
      Esto debería llevar los FPS a 12-25 según la carga de la GPU.

  [3] PARÁMETROS OCR MEJORADOS para letras de baja confianza
      • low_text=0.3 (default 0.4) → detecta texto más tenue
      • text_threshold=0.5 (default 0.7) → más permisivo con caracteres difusos
      • width_ths=0.9 → agrupa caracteres cercanos en un solo bloque
      • Dos pasadas: greedy primero, beamsearch solo si confianza < 0.55

  [4] SILENCIO TOTAL DE WARNINGS DE EASYOCR
      Redirige stderr durante la inferencia para eliminar todos los
      "WARNING not enough matching points" de la consola.

Heredado de V5:
  - Re-identificación de Vehículos (ReID por histograma de color)
  - Super-Resolución adaptativa (escala según tamaño de placa)
  - Sistema de votos multi-frame (VotadorPlaca)
  - Corrección de perspectiva automática
  - Limpiador posicional de placa mexicana
  - Skip inteligente cuando lectura ya está estable
"""
import cv2
import time
import csv
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
import easyocr

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
        except Exception as e:
            print(f"DB error: {e}")
        return False, None

    def registrar_alerta(self, pb, pd, sim, rv, rp):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute(
                "INSERT INTO historial_alertas "
                "(placa,placa_detectada,similitud,ruta_foto_vehiculo,ruta_foto_placa) "
                "VALUES (?,?,?,?,?)", (pb, pd, sim, rv, rp)
            )
            conn.commit(); conn.close()
        except Exception as e:
            print(f"DB alerta error: {e}")

def enviar_telegram_hilo(pd, info, rutas):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram][Sim] {pd}")
        return
    pb  = info.get("placa", pd)
    sim = info.get("similitud", 100)
    co  = f"\nOCR: {pd} ({sim}% sim)" if pd != pb else ""
    de  = f"\nNota: {info.get('descripcion','')}" if info.get('descripcion') else ""
    msg = (
        f"🚨 *ALERTA VEHICULO ROBADO (V6)* 🚨\n\n"
        f"📋 Placa BD: *{pb}*{co}\n"
        f"🚗 {info.get('modelo','?')} — {info.get('color','?')}\n"
        f"👤 {info.get('propietario','?')}\n"
        f"📅 {info.get('fecha_reporte','N/A')}{de}\n"
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
        print(f"[Telegram] → {pb}")
    except Exception as e:
        print(f"[Telegram] Error: {e}")

# ─────────────────────────────────────────────────────────────────────
# Re-identificación de Vehículos
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
            mejor_pid, mejor_sc = None, 0.0
            for pid, info in self.perdidos.items():
                if info['cls'] != cls:
                    continue
                sc = 0.7*self._sim(hist, info['hist']) + \
                     0.3*max(0., 1.0 - np.sqrt((cx-info['pos'][0])**2+(cy-info['pos'][1])**2)/400.)
                if sc > mejor_sc:
                    mejor_sc, mejor_pid = sc, pid
            if mejor_pid and mejor_sc >= self.umbral:
                heredada = self.perdidos[mejor_pid].get('placa_data')
                if heredada and (placa_actual is None or
                        heredada.get('confidence',0) > placa_actual.get('confidence',0)):
                    print(f"[ReID] ID {tid} ← {mejor_pid} (score={mejor_sc:.2f}) "
                          f"placa: {heredada.get('plate','?')}")
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
            self.perdidos[p]['frames_sin_ver'] = self.perdidos[p].get('frames_sin_ver',0) + 1

# ─────────────────────────────────────────────────────────────────────
# Preprocesamiento
# ─────────────────────────────────────────────────────────────────────

def corregir_perspectiva(roi):
    try:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(cv2.GaussianBlur(gray,(5,5),0), 0, 255,
                               cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return roi
        for cnt in sorted(cnts, key=cv2.contourArea, reverse=True)[:3]:
            peri  = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04*peri, True)
            if len(approx) == 4:
                pts = approx.reshape(4,2).astype(np.float32)
                s, d = pts.sum(axis=1), np.diff(pts, axis=1)
                o = np.zeros((4,2), dtype=np.float32)
                o[0]=pts[np.argmin(s)]; o[2]=pts[np.argmax(s)]
                o[1]=pts[np.argmin(d)];  o[3]=pts[np.argmax(d)]
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
    h, w = roi.shape[:2]
    if h == 0 or w == 0:
        return roi
    T = 180.0
    if area >= 3000:
        sc = T / h
        return cv2.resize(roi, (max(1,int(w*sc)), max(1,int(h*sc))),
                          interpolation=cv2.INTER_LANCZOS4)
    elif area >= 800:
        sc = T / h
        base = cv2.resize(roi, (max(1,int(w*sc)), max(1,int(h*sc))),
                          interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(base,(5,5),1.0)
        return cv2.addWeighted(base,1.6,bl,-0.6,0)
    else:
        img = roi.copy()
        for _ in range(4):
            if img.shape[0] >= int(T):
                break
            img = cv2.resize(img,(img.shape[1]*2,img.shape[0]*2),
                             interpolation=cv2.INTER_CUBIC)
        sc = T/img.shape[0]
        img = cv2.resize(img,(max(1,int(img.shape[1]*sc)),max(1,int(img.shape[0]*sc))),
                         interpolation=cv2.INTER_LANCZOS4)
        try:
            img = cv2.fastNlMeansDenoisingColored(img,None,8,8,7,21)
        except Exception:
            pass
        try:
            lab = cv2.cvtColor(img,cv2.COLOR_BGR2LAB)
            l,a,b = cv2.split(lab)
            l = cv2.createCLAHE(clipLimit=5.0,tileGridSize=(4,4)).apply(l)
            img = cv2.cvtColor(cv2.merge([l,a,b]),cv2.COLOR_LAB2BGR)
        except Exception:
            pass
        bl = cv2.GaussianBlur(img,(3,3),0.8)
        return cv2.addWeighted(img,2.0,bl,-1.0,0)

def limpiar_placa_mexicana(texto):
    texto = re.sub(r'[^A-Z0-9]', '', texto.upper())
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
# [V6] LECTURA POR ZONAS — Fix de letras faltantes (XLK, WZT…)
# ─────────────────────────────────────────────────────────────────────

def _ocr_silencioso(reader, img, **kwargs):
    """Llama a reader.readtext() suprimiendo los WARNINGs de stderr."""
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        return reader.readtext(img, **kwargs)
    finally:
        sys.stderr = old_stderr

def _ocr_una_imagen(reader, img):
    """
    Hace OCR en una imagen con parámetros optimizados para placas mexicanas.
    Primera pasada: greedy (rápido).
    Si confianza baja → segunda pasada beamsearch reducido.
    """
    base_kwargs = dict(
        allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        paragraph=False,
        width_ths=0.9,
        low_text=0.3,
        text_threshold=0.5,
    )
    try:
        res = _ocr_silencioso(reader, img, decoder='greedy', **base_kwargs)
    except Exception:
        return []

    if not res:
        return []

    conf_prom = sum(float(r[2]) for r in res) / len(res)
    txt = "".join(r[1].strip().upper().replace(" ","").replace("-","") for r in res)

    if len(txt) < 5 or conf_prom < 0.55:
        try:
            res2 = _ocr_silencioso(reader, img, decoder='beamsearch',
                                    beamWidth=5, **base_kwargs)
            if res2:
                conf2 = sum(float(r[2]) for r in res2)/len(res2)
                txt2  = "".join(r[1].strip().upper().replace(" ","").replace("-","")
                                 for r in res2)
                if len(txt2) > len(txt) or (len(txt2) == len(txt) and conf2 > conf_prom):
                    return res2
        except Exception:
            pass

    return res

def leer_placa_por_zonas(reader, roi_base, area):
    """
    [V6] Divide la placa en zona izquierda (letras) y zona derecha (números),
    procesa cada una por separado con el preprocessamiento óptimo para cada tipo
    de texto, y luego combina ordenando por posición x.
    Esto resuelve el problema de que las letras (XLK) se pierdan porque tienen
    menor contraste que los números.
    """
    # Super-resolución primero
    roi = super_resolver(roi_base, area)
    roi = corregir_perspectiva(roi)

    h, w = roi.shape[:2]
    if h == 0 or w == 0:
        return "", 0.0, roi

    # ── Preparar imagen base escalada para OCR
    TARGET = 180.0
    sc = min(TARGET/h, 12.0)
    base = cv2.resize(roi, (max(1,int(w*sc)), max(1,int(h*sc))),
                      interpolation=cv2.INTER_LANCZOS4)
    bh, bw = base.shape[:2]
    gray   = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    clahe  = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(6,6))

    # ── ZONA IZQUIERDA (40% del ancho): letras del estado (XLK, WZT…)
    # Las letras en placas mexicanas suelen ser claras sobre fondo oscuro/coloreado
    split_x = int(bw * 0.42)

    # Variante A: inversión + CLAHE fuerte (detecta texto claro sobre oscuro)
    zona_izq_gray = gray[:, :split_x]
    zona_izq_inv  = cv2.bitwise_not(zona_izq_gray)
    zona_izq_cl   = clahe.apply(zona_izq_inv)
    # Realce de bordes para las letras
    bl = cv2.GaussianBlur(zona_izq_cl,(3,3),0.5)
    zona_izq_A = cv2.addWeighted(zona_izq_cl,1.8,bl,-0.8,0)

    # Variante B: CLAHE normal (letras oscuras sobre claro, como la zona numérica)
    zona_izq_B = clahe.apply(zona_izq_gray)

    # ── ZONA DERECHA (60% del ancho): números
    zona_der_gray = gray[:, split_x:]
    zona_der_cl   = clahe.apply(zona_der_gray)
    bl2 = cv2.GaussianBlur(zona_der_cl,(3,3),0.8)
    zona_der_A = cv2.addWeighted(zona_der_cl,1.5,bl2,-0.5,0)

    # ── IMAGEN COMPLETA (como fallback / confirmación)
    bl_full = cv2.GaussianBlur(base,(5,5),1.5)
    full_A  = cv2.addWeighted(base,1.5,bl_full,-0.5,0)   # color
    full_B  = clahe.apply(gray)                            # gris CLAHE

    mejor_texto, mejor_conf, mejor_img = "", 0.0, base

    # ── Leer zonas por separado y combinar
    # La estrategia: leer izquierda + leer derecha → concatenar
    # Si la combinación da más caracteres que la lectura completa, usar combinación
    for variante_izq, variante_der in [(zona_izq_A, zona_der_A), (zona_izq_B, zona_der_A)]:
        res_izq = _ocr_una_imagen(reader, variante_izq)
        res_der = _ocr_una_imagen(reader, variante_der)

        # Ajustar coordenadas x de la zona derecha (sumamos split_x al x real)
        res_der_ajust = []
        for r in res_der:
            bbox_ajust = [[p[0]+split_x, p[1]] for p in r[0]]
            res_der_ajust.append((bbox_ajust, r[1], r[2]))

        todos = sorted(res_izq + res_der_ajust, key=lambda r: r[0][0][0])
        if not todos:
            continue

        txt  = "".join(r[1].strip().upper().replace(" ","").replace("-","") for r in todos)
        conf = sum(float(r[2]) for r in todos) / len(todos)
        txt  = limpiar_placa_mexicana(txt)

        if len(txt) >= 4 and conf > mejor_conf:
            mejor_texto, mejor_conf, mejor_img = txt, conf, base

    # ── Fallback: leer la placa completa directamente
    for img_full in [full_A, full_B]:
        res = _ocr_una_imagen(reader, img_full)
        if not res:
            continue
        res_ord = sorted(res, key=lambda r: r[0][0][0])
        txt  = "".join(r[1].strip().upper().replace(" ","").replace("-","") for r in res_ord)
        conf = sum(float(r[2]) for r in res_ord) / len(res_ord)
        txt  = limpiar_placa_mexicana(txt)
        if len(txt) >= 4 and conf > mejor_conf:
            mejor_texto, mejor_conf, mejor_img = txt, conf, img_full

    return mejor_texto, mejor_conf, mejor_img

# ─────────────────────────────────────────────────────────────────────
# VotadorPlaca
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
        g = max(votos, key=votos.get)
        return g, max(c for t, c in self.historial if t == g)

    def estable(self):
        if len(self.historial) < 6:
            return False
        t, c = self.mejor()
        return c >= 0.75 and sum(1 for txt,_ in self.historial if txt==t) >= 6

# ─────────────────────────────────────────────────────────────────────
# [V6] WORKER THREAD — Detección de placa + OCR en hilo de fondo
# ─────────────────────────────────────────────────────────────────────

class DeteccionOCRWorker:
    """
    Worker que hace TODO el trabajo pesado en segundo plano:
    1. lp_detector.predict(vehicle_roi)  → detectar bbox de la placa
    2. Recortar placa con margen asimétrico
    3. Super-resolución + OCR por zonas

    El bucle principal solo manda ROIs del vehículo y recibe resultados.
    """
    def __init__(self, lp_detector, reader):
        self.lp_detector = lp_detector
        self.reader      = reader
        self.cola        = queue.Queue(maxsize=6)
        self.resultados  = {}     # track_id → dict resultado
        self.lock        = threading.Lock()
        self.running     = True
        self.hilo        = threading.Thread(target=self._loop, daemon=True)
        self.hilo.start()
        print("[Worker V6] Hilo de detección+OCR iniciado.")

    def enviar(self, track_id, vehicle_roi, veh_bbox, frame_num):
        """Envía ROI del vehículo al hilo. Si la cola está llena, descarta."""
        try:
            self.cola.put_nowait((track_id, vehicle_roi.copy(), veh_bbox, frame_num))
        except queue.Full:
            pass

    def obtener(self, track_id):
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
            track_id, vehicle_roi, veh_bbox, frame_num = item
            resultado = self._procesar(track_id, vehicle_roi, veh_bbox, frame_num)
            if resultado:
                with self.lock:
                    prev = self.resultados.get(track_id)
                    if prev is None or resultado['confidence'] >= prev.get('confidence',0):
                        self.resultados[track_id] = resultado
            self.cola.task_done()

    def _procesar(self, track_id, vehicle_roi, veh_bbox, frame_num):
        """Detectar placa en el ROI y ejecutar OCR. Devuelve dict o None."""
        try:
            plate_results = self.lp_detector.predict(vehicle_roi, verbose=False)
        except Exception as e:
            print(f"[Worker] lp_detector error: {e}")
            return None

        if not plate_results or len(plate_results[0].boxes) == 0:
            return None

        x1v, y1v = veh_bbox[0], veh_bbox[1]
        mejores = []   # (texto, conf, img, px1g, py1g, px2g, py2g, area)

        for plate_box in plate_results[0].boxes:
            lpx1,lpy1,lpx2,lpy2 = map(int, plate_box.xyxy[0])
            ph, pw = lpy2-lpy1, lpx2-lpx1
            area   = ph * pw

            # [V6] Margen asimétrico: más a la izquierda para no perder letras
            ml = max(int(pw * 0.45), 10)   # izquierda: 45%
            mr = max(int(pw * 0.30), 6)    # derecha
            mt = max(int(ph * 0.30), 4)    # arriba
            mb = max(int(ph * 0.30), 4)    # abajo

            lpx1c = max(0, lpx1 - ml)
            lpy1c = max(0, lpy1 - mt)
            lpx2c = min(vehicle_roi.shape[1], lpx2 + mr)
            lpy2c = min(vehicle_roi.shape[0], lpy2 + mb)

            px1g,py1g = lpx1c+x1v, lpy1c+y1v
            px2g,py2g = lpx2c+x1v, lpy2c+y1v

            roi_placa = vehicle_roi[lpy1c:lpy2c, lpx1c:lpx2c]
            if roi_placa.size == 0:
                continue

            # OCR por zonas [V6]
            texto, conf, img_usada = leer_placa_por_zonas(self.reader, roi_placa, area)

            if texto and conf >= 0.10:
                mejores.append({
                    'plate': texto, 'confidence': conf, 'img': img_usada,
                    'bbox_global': (px1g,py1g,px2g,py2g), 'area': area,
                    'frame_num': frame_num
                })

        if not mejores:
            return None

        # Elegir el resultado con mayor confianza
        return max(mejores, key=lambda x: x['confidence'])

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def put_text(frame, text, pos, color=(0,255,0), font_scale=0.6, thickness=2, bg=(0,0,0)):
    ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    tx, ty = pos
    cv2.rectangle(frame, (tx,ty-ts[1]-5), (tx+ts[0]+5,ty+5), bg, cv2.FILLED)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def write_csv_header(path):
    with open(path,'w',newline='') as f:
        csv.writer(f).writerow([
            'frame','object_type','confidence','tracking_id',
            'x1','y1','x2','y2','plate_text','plate_conf','area_placa','reid'
        ])

# ─────────────────────────────────────────────────────────────────────
# BUCLE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────

def main():
    video_path    = 0
    model_path    = 'yolo11n.pt'
    lp_model_path = 'runs/detect/license_plate_detector/weights/best.pt'
    output_video  = 'output_v6.mp4'
    csv_path      = 'detection_v6.csv'
    classes_to_detect = [0,1,2,3,5]

    print("🤖 Cargando modelos V6 (OCR Asíncrono Total + Zonas + ReID + SR)...")
    import torch
    usar_gpu = torch.cuda.is_available()
    print(f"⚡ GPU: {'Sí CUDA (' + torch.cuda.get_device_name(0) + ')' if usar_gpu else 'CPU'}")

    model       = YOLO(model_path)
    lp_detector = YOLO(lp_model_path)
    reader      = easyocr.Reader(['en'], gpu=usar_gpu)
    db          = DatabasePlacas()
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
                print(f"   ✅ Backend {nombre} OK.")
                cap = c
                break
            c.release()

    if cap is None or not cap.isOpened():
        print("❌ No se pudo abrir la cámara.")
        worker.detener()
        sys.exit(1)

    fps_cam = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    out = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*'mp4v'), fps_cam, (fw,fh))
    write_csv_header(csv_path)

    print("🎥 V6 corriendo — ESPACIO=pausar | b=desenfoque | ESC=salir")
    print("   [Detección de placa + OCR en hilo separado. Video a máxima velocidad]")

    frame = None
    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("⚠️ No se pudo leer fotograma. Saliendo...")
                break

            t0 = time.time()
            frame_number += 1

            # ── Solo YOLO en el hilo principal (el más rápido)
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

                    reid_aplicado = False

                    if class_names[cls] in ["car","motorbike","bus"]:
                        vehicle_roi = frame[y1:y2, x1:x2]
                        if vehicle_roi.shape[0] < 50 or vehicle_roi.shape[1] < 50:
                            continue
                        if confidence < 0.50:
                            continue

                        # Re-identificación (solo histograma en hilo principal, no bloquea GPU)
                        placa_actual, reid_aplicado = reider.actualizar(
                            track_id, cls, (x1,y1,x2,y2), vehicle_roi,
                            vehicle_plates.get(track_id)
                        )
                        if reid_aplicado:
                            vehicle_plates[track_id] = placa_actual

                        # [V6] Enviar al worker solo si no tenemos lectura estable
                        vot = votadores.get(track_id)
                        if not (vot and vot.estable()):
                            worker.enviar(track_id, vehicle_roi, (x1,y1,x2,y2), frame_number)

                        # Recoger resultado del worker (si ya está listo)
                        res = worker.obtener(track_id)
                        if res:
                            texto = res['plate']
                            conf  = res['confidence']
                            img_u = res['img']
                            px1g,py1g,px2g,py2g = res['bbox_global']
                            area  = res['area']

                            if track_id not in votadores:
                                votadores[track_id] = VotadorPlaca(ventana=10)
                            votadores[track_id].agregar(texto, conf)
                            texto_f, conf_f = votadores[track_id].mejor()

                            # Dibujar bbox de la placa
                            if area >= 3000:
                                rc = (255,255,255)
                            elif area >= 800:
                                rc = (0,255,255)
                            else:
                                rc = (0,165,255)
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
                                        tag = "SR" if area < 800 else "OK"
                                        os.makedirs('plates', exist_ok=True)
                                        try:
                                            cv2.imwrite(
                                                f'plates/{frame_number}_{track_id}_{texto_f}_{tag}.png',
                                                img_u
                                            )
                                        except Exception:
                                            pass

                        assigned = vehicle_plates.get(track_id)
                        if assigned:
                            if not assigned.get('checked_db'):
                                er, info = db.consultar_placa(assigned['plate'])
                                assigned.update({'checked_db':True,'es_robado':er,'info':info})

                            if assigned.get('es_robado') and not assigned.get('notified'):
                                assigned['notified'] = True
                                info = assigned['info']
                                os.makedirs('alertas', exist_ok=True)
                                sello = datetime.now().strftime("%Y%m%d_%H%M%S")
                                rv = f"alertas/{sello}_{assigned['plate']}_v.jpg"
                                rp = f"alertas/{sello}_{assigned['plate']}_p.jpg"
                                cv2.imwrite(rv, frame)
                                threading.Thread(
                                    target=enviar_telegram_hilo,
                                    args=(assigned['plate'], info, [rv, rp]),
                                    daemon=True
                                ).start()
                                db.registrar_alerta(
                                    info['placa'], assigned['plate'],
                                    info['similitud'], rv, rp
                                )

                            bg = (255,255,255)
                            fg = (0,0,255) if assigned.get('es_robado') else (0,0,0)
                            pre = "⚠ ROBADO: " if assigned.get('es_robado') else "Plate: "
                            rs  = " [ReID]" if reid_aplicado else ""
                            put_text(frame, f"{pre}{assigned['plate']}{rs}",
                                     (x1, y2+40), color=fg, bg=bg)

                    color = (0,0,255) if vehicle_plates.get(track_id,{}).get('es_robado') \
                            else class_colors.get(cls,(0,0,0))
                    cv2.rectangle(frame,(x1,y1),(x2,y2),color,3)
                    put_text(frame, f"{class_names[cls]} {confidence}", (x1,y1-10), color=color)
                    put_text(frame, f"ID: {track_id}", (x1,y2+20), color=color)

                    if class_names[cls] == "person" and blur_enabled:
                        p = frame[y1:y2,x1:x2]
                        if p.size > 0:
                            frame[y1:y2,x1:x2] = cv2.GaussianBlur(p,(51,51),30)

                    with open(csv_path,'a',newline='') as f_csv:
                        ap = vehicle_plates.get(track_id,{})
                        csv.writer(f_csv).writerow([
                            frame_number, class_names[cls], confidence, track_id,
                            x1,y1,x2,y2,
                            ap.get('plate',''), ap.get('confidence',''),
                            mejor_area.get(track_id,''), reid_aplicado
                        ])
                    current_frame_count[class_names[cls]] += 1

            reider.marcar_ids(ids_vistos)

            # HUD
            yo = 30
            for cn, ct in total_class_count.items():
                put_text(frame, f"Total {cn}: {ct}", (10,yo)); yo += 20
            for cn, ct in current_frame_count.items():
                put_text(frame, f"Frame {cn}: {ct}", (10,yo), color=(255,255,255)); yo += 20
            fps_c = 1.0/(time.time()-t0)
            put_text(frame, f"FPS: {fps_c:.1f}", (10,yo), color=(0,255,255)); yo += 20
            put_text(frame, "V6: Zonas+AsyncTotal+ReID+SR", (10,yo),
                     color=(200,200,0), font_scale=0.45)
            out.write(frame)

        if frame is not None:
            cv2.imshow('Detection and Tracking V6', frame)
        key = cv2.waitKey(1 if not paused else 0) & 0xFF
        if key == 27:
            break
        elif key == ord(' '):
            paused = not paused
        elif key == ord('b'):
            blur_enabled = not blur_enabled
            print(f"Desenfoque {'ON' if blur_enabled else 'OFF'}")

    worker.detener()
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("✅ V6 — Procesamiento terminado.")

if __name__ == "__main__":
    main()
