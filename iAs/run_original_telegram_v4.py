# -*- coding: utf-8 -*-
"""
run_original_telegram_v4.py — Motor de IA V4
Mejoras sobre V3:

  [V4 NUEVO] Re-identificación de Vehículos:
    Si un coche desaparece detrás de un obstáculo y el tracker le asigna un
    nuevo ID, la IA compara histograma de color y clase del vehículo para
    detectar que es el mismo y transfiere automáticamente la placa ya leída
    al nuevo ID, evitando releer desde cero.

  [V4 NUEVO] Super-Resolución para Placas Lejanas:
    Cuando una placa detectada es pequeña (vehículo lejos), se aplica un
    pipeline de super-resolución basado en upscaling iterativo + filtros de
    realce adaptativo antes de pasar al OCR. Esto permite leer placas que
    antes eran completamente ilegibles por su reducido tamaño en píxeles.
    La IA también guarda automáticamente la captura de la placa en el
    momento en que el vehículo esté más cerca (mayor área del bbox).

  [Heredado de V3]:
    - Corrección de perspectiva
    - Margen amplio del 25%
    - Concatenación completa de OCR
    - Sistema de votos multi-frame (VotadorPlaca)
    - Corrección posicional de caracteres para placas mexicanas
"""
import cv2
import time
import csv
import os
import sys
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
# Lógica de Base de Datos y Telegram
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
            cursor.execute("SELECT * FROM placas_robadas WHERE placa = ? AND activo = 1", (texto_detectado,))
            fila = cursor.fetchone()
            if fila:
                conn.close()
                return True, {**dict(fila), "similitud": 1.0}
            cursor.execute("SELECT * FROM placas_robadas WHERE activo = 1")
            todas = cursor.fetchall()
            conn.close()
            mejor_coincidencia, mejor_similitud = None, 0.0
            for fila in todas:
                s = difflib.SequenceMatcher(None, texto_detectado, fila["placa"]).ratio()
                if s > mejor_similitud:
                    mejor_similitud = s
                    mejor_coincidencia = fila
            if mejor_similitud >= umbral_similitud and mejor_coincidencia:
                return True, {**dict(mejor_coincidencia), "similitud": round(mejor_similitud * 100, 1)}
        except Exception as e:
            print(f"Error al consultar base de datos: {e}")
        return False, None

    def registrar_alerta(self, placa_bd, placa_detectada, similitud, ruta_v, ruta_p):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute(
                "INSERT INTO historial_alertas (placa, placa_detectada, similitud, ruta_foto_vehiculo, ruta_foto_placa) VALUES (?, ?, ?, ?, ?)",
                (placa_bd, placa_detectada, similitud, ruta_v, ruta_p)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error al registrar alerta: {e}")

def enviar_telegram_hilo(placa_detectada, info, rutas_imagenes):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram] [Simulación] Alerta para placa: {placa_detectada}")
        return
    placa_bd    = info.get("placa", placa_detectada)
    similitud   = info.get("similitud", 100)
    coincidencia_str = f"\nDetectada por OCR: {placa_detectada} ({similitud}% similitud)" if placa_detectada != placa_bd else ""
    desc_str    = f"\nNota: {info.get('descripcion', '')}" if info.get('descripcion') else ""
    mensaje = (
        f"🚨 *ALERTA DE VEHICULO ROBADO (IA V4)* 🚨\n\n"
        f"📋 Placa en BD: *{placa_bd}*{coincidencia_str}\n"
        f"🚗 Vehículo: {info.get('modelo','?')} — {info.get('color','?')}\n"
        f"👤 Propietario: {info.get('propietario','?')}\n"
        f"📅 Fecha del reporte: {info.get('fecha_reporte','N/A')}{desc_str}\n"
        f"🕐 Hora de detección: {datetime.now().strftime('%H:%M:%S  %d/%m/%Y')}\n\n"
        f"⚠️ *ATENCIÓN:* Llame al 911."
    )
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
        for ruta in rutas_imagenes:
            if os.path.exists(ruta):
                with open(ruta, "rb") as foto:
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                                  data={"chat_id": TELEGRAM_CHAT_ID}, files={"photo": foto}, timeout=15)
        print(f"[Telegram] Alerta enviada para {placa_bd}.")
    except Exception as e:
        print(f"Error al enviar Telegram: {e}")

# ─────────────────────────────────────────────────────────────────────
# [V4] RE-IDENTIFICACIÓN DE VEHÍCULOS
# ─────────────────────────────────────────────────────────────────────

class ReidentificadorVehiculos:
    """
    Cuando el tracker pierde un vehículo (su ID deja de aparecer) y un
    nuevo ID aparece con características similares (misma clase + histograma
    de color parecido + posición cercana), se considera el mismo vehículo
    y se transfiere la placa ya leída al nuevo ID automáticamente.
    """
    def __init__(self, max_frames_perdido=60, umbral_similitud=0.75):
        # track_id → {cls, histograma, bbox_area, placa_data, frames_sin_ver, ultima_pos}
        self.vehiculos_activos = {}
        self.vehiculos_perdidos = {}   # IDs que desaparecieron pero aún recordamos
        self.max_frames_perdido = max_frames_perdido
        self.umbral_similitud = umbral_similitud

    def _calcular_histograma(self, frame_roi):
        """Histograma de color HSV normalizado del ROI del vehículo."""
        if frame_roi is None or frame_roi.size == 0:
            return None
        try:
            hsv = cv2.cvtColor(frame_roi, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [18, 16], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            return hist.flatten()
        except Exception:
            return None

    def _similitud_histograma(self, h1, h2):
        """Correlación entre dos histogramas (1.0 = idénticos)."""
        if h1 is None or h2 is None:
            return 0.0
        return float(cv2.compareHist(
            h1.reshape(-1, 1).astype(np.float32),
            h2.reshape(-1, 1).astype(np.float32),
            cv2.HISTCMP_CORREL
        ))

    def actualizar(self, track_id, cls, bbox, frame_roi, placa_data_actual):
        """
        Llamar en cada frame por cada vehículo detectado.
        Devuelve la placa_data a usar (puede ser la transferida de un ID anterior).
        """
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        hist = self._calcular_histograma(frame_roi)

        # ── ¿Es un ID completamente nuevo? Intentar re-identificar
        if track_id not in self.vehiculos_activos:
            mejor_match_id = None
            mejor_score = 0.0
            for pid, pinfo in self.vehiculos_perdidos.items():
                if pinfo['cls'] != cls:
                    continue
                # Similitud de color
                sim_color = self._similitud_histograma(hist, pinfo['hist'])
                # Similitud de posición (cercano = bueno)
                px, py = pinfo['ultima_pos']
                dist = np.sqrt((cx - px) ** 2 + (cy - py) ** 2)
                sim_pos = max(0.0, 1.0 - dist / 400.0)
                score = 0.7 * sim_color + 0.3 * sim_pos
                if score > mejor_score:
                    mejor_score = score
                    mejor_match_id = pid

            if mejor_match_id is not None and mejor_score >= self.umbral_similitud:
                placa_heredada = self.vehiculos_perdidos[mejor_match_id].get('placa_data')
                if placa_heredada and (placa_data_actual is None or
                        placa_heredada.get('confidence', 0) > placa_data_actual.get('confidence', 0)):
                    print(f"[ReID] ID {track_id} reconocido como anterior ID {mejor_match_id} "
                          f"(score={mejor_score:.2f}) → placa heredada: {placa_heredada.get('plate','?')}")
                    placa_data_actual = dict(placa_heredada)
                    placa_data_actual['checked_db'] = False   # re-verificar en DB por seguridad
                del self.vehiculos_perdidos[mejor_match_id]

        # ── Actualizar estado activo
        existing = self.vehiculos_activos.get(track_id, {})
        # Guardar el mejor histograma (del frame con mayor área del vehículo)
        if area > existing.get('area', 0):
            self.vehiculos_activos[track_id] = {
                'cls': cls, 'hist': hist, 'area': area,
                'ultima_pos': (cx, cy), 'placa_data': placa_data_actual
            }
        else:
            self.vehiculos_activos[track_id]['ultima_pos'] = (cx, cy)
            self.vehiculos_activos[track_id]['placa_data'] = placa_data_actual

        return placa_data_actual

    def marcar_ids_actuales(self, ids_vistos: set):
        """
        Llamar una vez por frame con el conjunto de IDs detectados.
        Mueve los IDs no vistos a 'perdidos' y limpia los que llevan
        demasiados frames sin aparecer.
        """
        # IDs que estaban activos pero ya no se ven
        desaparecidos = set(self.vehiculos_activos.keys()) - ids_vistos
        for did in desaparecidos:
            info = self.vehiculos_activos.pop(did)
            info['frames_sin_ver'] = 0
            self.vehiculos_perdidos[did] = info

        # Envejecer y limpiar perdidos
        viejos = []
        for pid in self.vehiculos_perdidos:
            self.vehiculos_perdidos[pid]['frames_sin_ver'] = \
                self.vehiculos_perdidos[pid].get('frames_sin_ver', 0) + 1
            if self.vehiculos_perdidos[pid]['frames_sin_ver'] > self.max_frames_perdido:
                viejos.append(pid)
        for pid in viejos:
            del self.vehiculos_perdidos[pid]

# ─────────────────────────────────────────────────────────────────────
# [V4] SUPER-RESOLUCIÓN PARA PLACAS LEJANAS
# ─────────────────────────────────────────────────────────────────────

def super_resolver_placa(roi, area_placa_px):
    """
    Aplica super-resolución adaptativa según el tamaño de la placa en píxeles.
    - Placas grandes (cerca): upscaling estándar, ya tiene suficiente detalle.
    - Placas medianas: LANCZOS4 + Unsharp Masking moderado.
    - Placas pequeñas (lejos): Upscaling iterativo 2x + CLAHE agresivo
      + denoising + realce de bordes antes de OCR.

    Retorna la imagen procesada lista para OCR.
    """
    h, w = roi.shape[:2]
    if h == 0 or w == 0:
        return roi

    TARGET_H = 180.0

    # ── CLASIFICAR según tamaño real de la placa en la imagen
    if area_placa_px >= 3000:
        # PLACA GRANDE (cerca) — preprocesamiento estándar como V3
        scale = TARGET_H / h
        rh = max(1, int(h * scale))
        rw = max(1, int(w * scale))
        return cv2.resize(roi, (rw, rh), interpolation=cv2.INTER_LANCZOS4)

    elif area_placa_px >= 800:
        # PLACA MEDIANA — upscaling + sharpening moderado
        scale = TARGET_H / h
        rh = max(1, int(h * scale))
        rw = max(1, int(w * scale))
        base = cv2.resize(roi, (rw, rh), interpolation=cv2.INTER_LANCZOS4)
        blur = cv2.GaussianBlur(base, (5, 5), 1.0)
        return cv2.addWeighted(base, 1.6, blur, -0.6, 0)

    else:
        # PLACA PEQUEÑA (lejos) — pipeline agresivo de super-resolución
        # Paso 1: Upscaling iterativo 2x (mejor que escalar de golpe)
        img = roi.copy()
        pasos = 0
        while img.shape[0] < int(TARGET_H) and pasos < 4:
            img = cv2.resize(img, (img.shape[1] * 2, img.shape[0] * 2),
                             interpolation=cv2.INTER_CUBIC)
            pasos += 1

        # Ajustar al target final
        scale = TARGET_H / img.shape[0]
        img = cv2.resize(img, (max(1, int(img.shape[1] * scale)),
                               max(1, int(img.shape[0] * scale))),
                         interpolation=cv2.INTER_LANCZOS4)

        # Paso 2: Denoising para eliminar artefactos del upscaling
        try:
            img = cv2.fastNlMeansDenoisingColored(img, None, h=8, hColor=8,
                                                   templateWindowSize=7,
                                                   searchWindowSize=21)
        except Exception:
            pass

        # Paso 3: CLAHE muy agresivo en canal L del espacio LAB
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
            l = clahe.apply(l)
            img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        except Exception:
            pass

        # Paso 4: Realce de bordes fuerte (Unsharp Masking agresivo)
        blur = cv2.GaussianBlur(img, (3, 3), 0.8)
        img = cv2.addWeighted(img, 2.0, blur, -1.0, 0)

        return img

# ─────────────────────────────────────────────────────────────────────
# PIPELINE DE PREPROCESAMIENTO (Heredado de V3 + mejoras V4)
# ─────────────────────────────────────────────────────────────────────

def corregir_perspectiva(roi):
    try:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(cv2.GaussianBlur(gray, (5, 5), 0), 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return roi
        for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:3]:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            if len(approx) == 4:
                pts = approx.reshape(4, 2).astype(np.float32)
                s, diff = pts.sum(axis=1), np.diff(pts, axis=1)
                ordered = np.zeros((4, 2), dtype=np.float32)
                ordered[0] = pts[np.argmin(s)]
                ordered[2] = pts[np.argmax(s)]
                ordered[1] = pts[np.argmin(diff)]
                ordered[3] = pts[np.argmax(diff)]
                w = max(np.linalg.norm(ordered[1] - ordered[0]),
                        np.linalg.norm(ordered[2] - ordered[3]))
                h = max(np.linalg.norm(ordered[3] - ordered[0]),
                        np.linalg.norm(ordered[2] - ordered[1]))
                if w < 20 or h < 8:
                    continue
                dst = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
                return cv2.warpPerspective(roi, cv2.getPerspectiveTransform(ordered, dst),
                                           (int(w), int(h)))
    except Exception:
        pass
    return roi

def generar_variantes(roi):
    h, w = roi.shape[:2]
    if h == 0 or w == 0:
        return []
    target_h = 180.0
    scale = min(target_h / h, 12.0)
    base = cv2.resize(roi, (max(1, int(w * scale)), max(1, int(h * scale))),
                      interpolation=cv2.INTER_LANCZOS4)
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(6, 6))

    g = cv2.GaussianBlur(base, (5, 5), 1.5)
    v1 = cv2.addWeighted(base, 1.5, g, -0.5, 0)

    eq = clahe.apply(gray)
    v2 = cv2.bilateralFilter(eq, d=11, sigmaColor=80, sigmaSpace=80)

    eq2 = cv2.equalizeHist(gray)
    v3 = cv2.adaptiveThreshold(eq2, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 25, 8)
    if cv2.mean(v3)[0] < 128:
        v3 = cv2.bitwise_not(v3)

    hsv = cv2.cvtColor(base, cv2.COLOR_BGR2HSV)
    v4 = clahe.apply(hsv[:, :, 2])

    return [v1, v2, v3, v4]

def limpiar_placa_mexicana(texto):
    texto = re.sub(r'[^A-Z0-9]', '', texto.upper())
    if re.match(r'^[A-Z]{3}[0-9]{2}[A-Z0-9][0-9]{2}$', texto):
        texto = texto[:5] + texto[6:]
    if len(texto) == 7:
        fl = {'0': 'O', '1': 'I', '5': 'S', '8': 'B'}.get
        fn = {'O': '0', 'I': '1', 'S': '5', 'Z': '2', 'B': '8', 'G': '6'}.get
        texto = (fl(texto[0], texto[0]) + fl(texto[1], texto[1]) + fl(texto[2], texto[2]) +
                 fn(texto[3], texto[3]) + fn(texto[4], texto[4]) +
                 fn(texto[5], texto[5]) + fn(texto[6], texto[6]))
    return texto

def leer_placa_ocr(reader, roi_original, area_placa_px):
    """Pipeline V4: super-resolución adaptativa + perspectiva + variantes + OCR."""
    # [V4] Super-resolución según tamaño de la placa
    roi_sr = super_resolver_placa(roi_original, area_placa_px)

    roi_corr_orig = corregir_perspectiva(roi_original)
    roi_corr_sr   = corregir_perspectiva(roi_sr)

    variantes_orig = generar_variantes(roi_original)
    variantes_sr   = generar_variantes(roi_sr)
    variantes_corr = generar_variantes(roi_corr_orig)
    variantes_corr_sr = generar_variantes(roi_corr_sr)

    todas = variantes_sr + variantes_corr_sr + variantes_orig + variantes_corr

    mejor_texto, mejor_conf, imagen_usada = "", 0.0, roi_original

    for img in todas:
        if img is None or img.size == 0:
            continue
        try:
            resultados = reader.readtext(
                img,
                allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                paragraph=False,
                decoder='beamsearch',
                beamWidth=10
            )
        except Exception:
            continue
        if not resultados:
            continue

        resultados_ord = sorted(resultados, key=lambda r: r[0][0][0])
        texto_concat, conf_prom = "", 0.0
        for r in resultados_ord:
            texto_concat += r[1].strip().upper().replace(" ", "").replace("-", "")
            conf_prom += float(r[2])
        if resultados_ord:
            conf_prom /= len(resultados_ord)

        texto_concat = limpiar_placa_mexicana(texto_concat)
        if len(texto_concat) >= 4 and conf_prom > mejor_conf:
            mejor_texto, mejor_conf, imagen_usada = texto_concat, conf_prom, img

    return mejor_texto, mejor_conf, imagen_usada

# ─────────────────────────────────────────────────────────────────────
# SISTEMA DE VOTOS MULTI-FRAME (Heredado de V3)
# ─────────────────────────────────────────────────────────────────────

class VotadorPlaca:
    def __init__(self, ventana=10):
        self.historial = []
        self.ventana = ventana

    def agregar(self, texto, confianza):
        if texto and len(texto) >= 4:
            self.historial.append((texto, confianza))
            if len(self.historial) > self.ventana:
                self.historial.pop(0)

    def mejor(self):
        if not self.historial:
            return "", 0.0
        votos = {}
        for txt, conf in self.historial:
            votos[txt] = votos.get(txt, 0) + conf
        ganador = max(votos, key=votos.get)
        conf_ganador = max(c for t, c in self.historial if t == ganador)
        return ganador, conf_ganador

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def initialize_model(model_path):
    return YOLO(model_path)

def initialize_reader():
    import torch
    usar_gpu = torch.cuda.is_available()
    print(f"⚡ GPU para OCR: {'Sí (CUDA)' if usar_gpu else 'No (CPU)'}")
    return easyocr.Reader(['en'], gpu=usar_gpu)

def initialize_video_writer(cap, path):
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    return cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (fw, fh))

def write_csv_header(path):
    with open(path, mode='w', newline='') as f:
        csv.writer(f).writerow(['frame', 'object_type', 'confidence', 'tracking_id',
                                 'x1', 'y1', 'x2', 'y2', 'plate_confidence',
                                 'mx1', 'my1', 'mx2', 'my2', 'license_plate_text',
                                 'area_placa_px', 'reid_aplicado'])

def put_text(frame, text, pos, color=(0, 255, 0), font_scale=0.6, thickness=2, bg=(0, 0, 0)):
    ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    tx, ty = pos
    cv2.rectangle(frame, (tx, ty - ts[1] - 5), (tx + ts[0] + 5, ty + 5), bg, cv2.FILLED)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

# ─────────────────────────────────────────────────────────────────────
# BUCLE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────

def main():
    video_path    = 0
    model_path    = 'yolo11n.pt'
    lp_model_path = 'runs/detect/license_plate_detector/weights/best.pt'
    output_video  = 'output_video_v4.mp4'
    csv_path      = 'detection_log_v4.csv'
    classes_to_detect = [0, 1, 2, 3, 5]

    print("🤖 Cargando modelos de IA (V4 - ReID + Super-Resolución)...")
    model       = initialize_model(model_path)
    lp_detector = YOLO(lp_model_path)
    reader      = initialize_reader()
    db          = DatabasePlacas()
    reider      = ReidentificadorVehiculos(max_frames_perdido=90, umbral_similitud=0.72)

    class_names  = {0: "person", 1: "bicycle", 2: "car", 3: "motorbike", 5: "bus"}
    class_colors = {0: (255,255,255), 1: (0,255,0), 2: (0,0,255), 3: (255,255,0), 5: (0,255,255)}

    vehicle_plates   = {}   # track_id → dict placa
    votadores        = {}   # track_id → VotadorPlaca
    mejor_area_placa = {}   # track_id → area máxima de placa vista (para captura óptima)
    total_class_count = Counter()
    seen_ids         = defaultdict(set)
    frame_number     = 0
    blur_enabled     = True
    paused           = False

    print("📹 Intentando abrir la cámara...")
    cap = None
    for backend, nombre in [(cv2.CAP_MSMF, "MSMF"), (cv2.CAP_DSHOW, "DSHOW"), (cv2.CAP_ANY, "ANY")]:
        c = cv2.VideoCapture(video_path, backend)
        if c.isOpened():
            ret, fot = c.read()
            if ret and fot is not None:
                print(f"   ✅ Backend {nombre} funcionó.")
                cap = c
                break
            c.release()

    if cap is None or not cap.isOpened():
        print("❌ No se pudo abrir la cámara.")
        sys.exit(1)

    out = initialize_video_writer(cap, output_video)
    write_csv_header(csv_path)
    print("🎥 Ejecutando V4. ESPACIO=pausar, b=desenfoque, ESC=salir.")

    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ No se pudo leer el fotograma. Saliendo...")
                break

            start_time = time.time()
            frame_number += 1

            results = model.track(frame, persist=True, classes=classes_to_detect, verbose=False)
            current_frame_count = Counter()
            ids_vistos_este_frame = set()

            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    confidence = round(float(box.conf[0]), 2)

                    if box.id is None:
                        continue
                    track_id = int(box.id[0].tolist())
                    ids_vistos_este_frame.add(track_id)

                    if track_id not in seen_ids[cls]:
                        seen_ids[cls].add(track_id)
                        total_class_count[class_names[cls]] += 1

                    license_plate_text = ""
                    plate_confidence   = None
                    mx1 = my1 = mx2 = my2 = None
                    area_placa_px = 0
                    reid_aplicado = False

                    if class_names[cls] in ["car", "motorbike", "bus"]:
                        vehicle_img = frame[y1:y2, x1:x2]
                        if vehicle_img.shape[0] < 50 or vehicle_img.shape[1] < 50:
                            continue
                        if confidence < 0.50:
                            continue

                        # [V4] Re-identificación: actualizar estado y obtener placa heredada si aplica
                        placa_actual = vehicle_plates.get(track_id)
                        placa_reid = reider.actualizar(track_id, cls, (x1, y1, x2, y2),
                                                        vehicle_img, placa_actual)
                        if placa_reid is not None and placa_reid is not placa_actual:
                            vehicle_plates[track_id] = placa_reid
                            reid_aplicado = True

                        plate_results = lp_detector.predict(vehicle_img, verbose=False)

                        if plate_results and len(plate_results[0].boxes) > 0:
                            for plate_box in plate_results[0].boxes:
                                lpx1, lpy1, lpx2, lpy2 = map(int, plate_box.xyxy[0])

                                ph, pw = lpy2 - lpy1, lpx2 - lpx1
                                area_placa_px = ph * pw
                                margin_h = max(int(ph * 0.25), 4)
                                margin_w = max(int(pw * 0.25), 6)
                                lpx1c = max(0, lpx1 - margin_w)
                                lpy1c = max(0, lpy1 - margin_h)
                                lpx2c = min(vehicle_img.shape[1], lpx2 + margin_w)
                                lpy2c = min(vehicle_img.shape[0], lpy2 + margin_h)

                                px1g, py1g = lpx1c + x1, lpy1c + y1
                                px2g, py2g = lpx2c + x1, lpy2c + y1

                                # Color del rectángulo de la placa según tamaño:
                                # Blanco=cerca, Amarillo=mediana, Naranja=lejos
                                if area_placa_px >= 3000:
                                    rect_color = (255, 255, 255)
                                elif area_placa_px >= 800:
                                    rect_color = (0, 255, 255)
                                else:
                                    rect_color = (0, 165, 255)  # naranja = modo SR activo

                                cv2.rectangle(frame, (px1g, py1g), (px2g, py2g), rect_color, 2)

                                roi_placa = vehicle_img[lpy1c:lpy2c, lpx1c:lpx2c].copy()
                                if roi_placa.size == 0:
                                    continue

                                # [V4] OCR con super-resolución adaptativa
                                texto, conf, img_usada = leer_placa_ocr(reader, roi_placa, area_placa_px)

                                if track_id not in votadores:
                                    votadores[track_id] = VotadorPlaca(ventana=10)
                                votadores[track_id].agregar(texto, conf)
                                texto_final, conf_final = votadores[track_id].mejor()

                                if conf_final >= 0.15 and texto_final:
                                    license_plate_text = texto_final
                                    plate_confidence   = conf_final
                                    mx1, my1, mx2, my2 = px1g, py1g, px2g, py2g

                                    previo = vehicle_plates.get(track_id)
                                    if previo is None or conf_final > previo.get('confidence', 0.0):
                                        vehicle_plates[track_id] = {
                                            'plate': texto_final, 'confidence': conf_final,
                                            'checked_db': False, 'es_robado': False,
                                            'notified': False, 'info': None
                                        }
                                        # [V4] Guardar captura del mejor frame (mayor área de placa)
                                        area_previa = mejor_area_placa.get(track_id, 0)
                                        os.makedirs('plates', exist_ok=True)
                                        if area_placa_px >= area_previa:
                                            mejor_area_placa[track_id] = area_placa_px
                                            tag = "SR" if area_placa_px < 800 else "OK"
                                            cv2.imwrite(
                                                f'plates/{frame_number}_{track_id}_{texto_final}_{tag}.png',
                                                img_usada
                                            )

                                assigned_plate = vehicle_plates.get(track_id)
                                if assigned_plate:
                                    if not assigned_plate.get('checked_db', False):
                                        es_robado, info = db.consultar_placa(assigned_plate['plate'])
                                        assigned_plate['checked_db'] = True
                                        assigned_plate['es_robado'] = es_robado
                                        assigned_plate['info'] = info

                                    if assigned_plate.get('es_robado') and not assigned_plate.get('notified'):
                                        assigned_plate['notified'] = True
                                        info = assigned_plate['info']
                                        os.makedirs('alertas', exist_ok=True)
                                        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        ruta_v = f"alertas/{sello}_{assigned_plate['plate']}_vehiculo.jpg"
                                        ruta_p = f"alertas/{sello}_{assigned_plate['plate']}_placa.jpg"
                                        cv2.imwrite(ruta_v, frame)
                                        cv2.imwrite(ruta_p, img_usada)
                                        db.registrar_alerta(
                                            info['placa'], assigned_plate['plate'],
                                            info['similitud'], ruta_v, ruta_p
                                        )
                                        threading.Thread(
                                            target=enviar_telegram_hilo,
                                            args=(assigned_plate['plate'], info, [ruta_v, ruta_p]),
                                            daemon=True
                                        ).start()

                                    bg = (255, 255, 255)
                                    fg = (0, 0, 255) if assigned_plate.get('es_robado') else (0, 0, 0)
                                    prefix = "⚠ ROBADO: " if assigned_plate.get('es_robado') else "Plate: "
                                    reid_str = " [ReID]" if reid_aplicado else ""
                                    put_text(frame,
                                             f"{prefix}{assigned_plate['plate']}{reid_str}",
                                             (x1, y2 + 40), color=fg, bg=bg)
                                    license_plate_text = assigned_plate['plate']
                                    plate_confidence   = assigned_plate['confidence']

                    color = (0, 0, 255) if vehicle_plates.get(track_id, {}).get('es_robado') \
                            else class_colors.get(cls, (0, 0, 0))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                    put_text(frame, f"{class_names[cls]} {confidence}", (x1, y1 - 10), color=color)
                    put_text(frame, f"ID: {track_id}", (x1, y2 + 20), color=color)

                    if class_names[cls] == "person" and blur_enabled:
                        p_roi = frame[y1:y2, x1:x2]
                        if p_roi.size > 0:
                            frame[y1:y2, x1:x2] = cv2.GaussianBlur(p_roi, (51, 51), 30)

                    with open(csv_path, mode='a', newline='') as f:
                        csv.writer(f).writerow([
                            frame_number, class_names[cls], confidence, track_id,
                            x1, y1, x2, y2, plate_confidence,
                            mx1, my1, mx2, my2, license_plate_text,
                            area_placa_px, reid_aplicado
                        ])
                    current_frame_count[class_names[cls]] += 1

            # [V4] Notificar al re-identificador qué IDs se vieron en este frame
            reider.marcar_ids_actuales(ids_vistos_este_frame)

            y_off = 30
            for cls_name, count in total_class_count.items():
                put_text(frame, f"Total {cls_name}: {count}", (10, y_off))
                y_off += 20
            for cls_name, count in current_frame_count.items():
                put_text(frame, f"Frame {cls_name}: {count}", (10, y_off), color=(255, 255, 255))
                y_off += 20
            fps_calc = 1.0 / (time.time() - start_time)
            put_text(frame, f"FPS: {fps_calc:.2f}", (10, y_off), color=(0, 255, 255))
            put_text(frame, "V4: ReID+SR", (10, y_off + 20), color=(200, 200, 0), font_scale=0.5)
            out.write(frame)

        cv2.imshow('Detection and Tracking V4', frame)
        key = cv2.waitKey(1 if not paused else 0) & 0xFF
        if key == 27:
            break
        elif key == ord(' '):
            paused = not paused
        elif key == ord('b'):
            blur_enabled = not blur_enabled
            print(f"Desenfoque {'habilitado' if blur_enabled else 'deshabilitado'}")

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("✅ V4 — Procesamiento terminado.")

if __name__ == "__main__":
    main()
