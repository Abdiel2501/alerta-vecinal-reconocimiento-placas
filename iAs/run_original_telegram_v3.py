# -*- coding: utf-8 -*-
"""
run_original_telegram_v3.py — Motor de IA V3
Mejoras clave:
  - Perspectiva/Deskew: Corrección automática de ángulo de la placa
  - Margen amplio: El recorte de la placa incluye un 25% de padding
  - Concatenación completa de OCR: Combina todos los fragmentos detectados
  - Acumulación multi-frame: Sistema de votos entre frames para la mejor lectura
  - Limpiador de placa mexicana: Elimina caracteres de ruido del guión
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
# Lógica de Base de Datos y Telegram (Autocontenida)
# ─────────────────────────────────────────────────────────────────────

def _get_appdata_dir():
    appdata = os.getenv('APPDATA')
    if not appdata:
        appdata = os.path.expanduser('~')
    app_dir = os.path.join(appdata, 'AlertaVecinal', 'System')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

DB_PATH = os.path.join(_get_appdata_dir(), "secure_placas.db")

TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""

rutas_env = ["config.env", "../yolo-plate-recognition/config.env"]
for r in rutas_env:
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
            mejor_coincidencia = None
            mejor_similitud = 0.0
            for fila in todas:
                placa_bd = fila["placa"]
                similitud = difflib.SequenceMatcher(None, texto_detectado, placa_bd).ratio()
                if similitud > mejor_similitud:
                    mejor_similitud = similitud
                    mejor_coincidencia = fila
            if mejor_similitud >= umbral_similitud and mejor_coincidencia:
                return True, {**dict(mejor_coincidencia), "similitud": round(mejor_similitud * 100, 1)}
        except Exception as e:
            print(f"Error al consultar base de datos: {e}")
        return False, None

    def registrar_alerta(self, placa_bd: str, placa_detectada: str, similitud: float, ruta_v: str, ruta_p: str):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO historial_alertas (placa, placa_detectada, similitud, ruta_foto_vehiculo, ruta_foto_placa)
                VALUES (?, ?, ?, ?, ?)
            """, (placa_bd, placa_detectada, similitud, ruta_v, ruta_p))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error al registrar alerta: {e}")

def enviar_telegram_hilo(placa_detectada: str, info: dict, rutas_imagenes: list):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] [Simulacion] Alerta generada:")
        print(f"   Vehiculo: {info.get('modelo')} - Placa: {placa_detectada}")
        return
    placa_bd = info.get("placa", placa_detectada)
    modelo = info.get("modelo", "Desconocido")
    color = info.get("color", "Desconocido")
    propietario = info.get("propietario", "Desconocido")
    fecha_reporte = info.get("fecha_reporte", "N/A")
    descripcion = info.get("descripcion", "")
    similitud = info.get("similitud", 100)
    hora_deteccion = datetime.now().strftime("%H:%M:%S  %d/%m/%Y")
    coincidencia_str = f"\nDetectada por OCR: {placa_detectada} ({similitud}% similitud)" if placa_detectada != placa_bd else ""
    desc_str = f"\nNota: {descripcion}" if descripcion else ""
    mensaje = (
        f"🚨 *ALERTA DE VEHICULO ROBADO (IA V3)* 🚨\n\n"
        f"📋 Placa en BD: *{placa_bd}*{coincidencia_str}\n"
        f"🚗 Vehiculo: {modelo} -- {color}\n"
        f"👤 Propietario: {propietario}\n"
        f"📅 Fecha del reporte: {fecha_reporte}{desc_str}\n"
        f"🕐 Hora de deteccion: {hora_deteccion}\n\n"
        f"⚠️ *ATENCION:* Llame al 911."
    )
    url_texto = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    url_foto = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        requests.post(url_texto, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
        for ruta in rutas_imagenes:
            if os.path.exists(ruta):
                with open(ruta, "rb") as foto:
                    requests.post(url_foto, data={"chat_id": TELEGRAM_CHAT_ID}, files={"photo": foto}, timeout=15)
        print(f"[Telegram] Alerta enviada para la placa {placa_bd}.")
    except Exception as e:
        print(f"Error al enviar Telegram: {e}")

# ─────────────────────────────────────────────────────────────────────
# PIPELINE DE PREPROCESAMIENTO AVANZADO
# ─────────────────────────────────────────────────────────────────────

def corregir_perspectiva(roi):
    """Intenta detectar el cuadrilátero de la placa y aplica corrección de perspectiva.
    Si no es posible (placa muy distorsionada), devuelve el ROI original."""
    try:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return roi
            
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for cnt in contours[:3]:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            if len(approx) == 4:
                pts = approx.reshape(4, 2).astype(np.float32)
                # Ordenar puntos: top-left, top-right, bottom-right, bottom-left
                s = pts.sum(axis=1)
                diff = np.diff(pts, axis=1)
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
                M = cv2.getPerspectiveTransform(ordered, dst)
                warped = cv2.warpPerspective(roi, M, (int(w), int(h)))
                return warped
    except Exception:
        pass
    return roi

def generar_variantes(roi):
    """Genera múltiples variantes del recorte de la placa para maximizar las
    posibilidades de que el OCR lea correctamente en cualquier condición."""
    h, w = roi.shape[:2]
    if h == 0 or w == 0:
        return []

    # 1. Escalar a resolución alta manteniendo la relación de aspecto
    target_h = 180.0
    scale = target_h / h
    # Evitar escala enorme en placas muy pequeñas para no generar ruido
    scale = min(scale, 12.0)
    rw = max(1, int(w * scale))
    rh = max(1, int(h * scale))
    base = cv2.resize(roi, (rw, rh), interpolation=cv2.INTER_LANCZOS4)

    variantes = []

    # ── Variante 1: Color con Unsharp Masking (buena para placas cercanas limpias)
    g = cv2.GaussianBlur(base, (5, 5), 1.5)
    v1 = cv2.addWeighted(base, 1.5, g, -0.5, 0)
    variantes.append(v1)

    # ── Variante 2: Escala de grises + CLAHE + Filtro Bilateral (excelente para ángulos)
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(6, 6))
    eq = clahe.apply(gray)
    bil = cv2.bilateralFilter(eq, d=11, sigmaColor=80, sigmaSpace=80)
    variantes.append(bil)

    # ── Variante 3: Ecualización adaptativa + umbral local adaptativo (buena para sombras)
    eq2 = cv2.equalizeHist(gray)
    thresh_adapt = cv2.adaptiveThreshold(eq2, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                          cv2.THRESH_BINARY, 25, 8)
    # Invertir si el fondo es oscuro
    if cv2.mean(thresh_adapt)[0] < 128:
        thresh_adapt = cv2.bitwise_not(thresh_adapt)
    variantes.append(thresh_adapt)

    # ── Variante 4: Canal de valor (Value) de espacio HSV (muy robusto a brillos y reflejos)
    hsv = cv2.cvtColor(base, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    v_clahe = clahe.apply(v_channel)
    variantes.append(v_clahe)

    return variantes

def limpiar_placa_mexicana(texto):
    """Post-proceso para corregir errores comunes en el formato de placa mexicana."""
    # Eliminar todo lo que no sea letra o número
    texto = re.sub(r'[^A-Z0-9]', '', texto.upper())

    # Corregir confusión común O↔0, I↔1, S↔5 solo en posiciones numéricas esperadas
    # Formato mexicano típico: 3 letras + 4 números = 7 chars (ej: XKR3865)
    # O bien 3 letras + 2 nums + letra + 2 nums = 8 chars (antes del limpiador)

    # Si tiene 8 chars con el patrón AAA##X## (ruido del guión en pos 5)
    if re.match(r'^[A-Z]{3}[0-9]{2}[A-Z0-9][0-9]{2}$', texto):
        # El carácter en posición 5 es el ruido del guión central → eliminarlo
        texto = texto[:5] + texto[6:]

    # Aplicar correcciones posicionales una vez normalizado a 7 caracteres:
    # Pos 0-2: deben ser letras → convertir 0→O, 1→I, 5→S
    # Pos 3-6: deben ser números → convertir O→0, I→1, S→5, Z→2
    if len(texto) == 7:
        def fix_letra(c):
            return {'0': 'O', '1': 'I', '5': 'S', '8': 'B'}.get(c, c)
        def fix_num(c):
            return {'O': '0', 'I': '1', 'S': '5', 'Z': '2', 'B': '8', 'G': '6'}.get(c, c)
        texto = (fix_letra(texto[0]) + fix_letra(texto[1]) + fix_letra(texto[2]) +
                 fix_num(texto[3]) + fix_num(texto[4]) + fix_num(texto[5]) + fix_num(texto[6]))

    return texto

def leer_placa_ocr(reader, roi_original):
    """Pipeline completo de lectura de placa. Retorna (texto, confianza, imagen_usada)."""
    # 1. Intentar corrección de perspectiva (muy útil para ángulos)
    roi_corr = corregir_perspectiva(roi_original)

    # 2. Generar variantes de preprocesamiento
    variantes_orig = generar_variantes(roi_original)
    variantes_corr = generar_variantes(roi_corr)
    todas_variantes = variantes_orig + variantes_corr

    mejor_texto = ""
    mejor_conf = 0.0
    imagen_usada = roi_original

    for i, img in enumerate(todas_variantes):
        if img is None or img.size == 0:
            continue
        try:
            # Leer TODO el texto detectado, no solo el primero
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

        # Concatenar todos los fragmentos detectados ordenados por posición horizontal
        resultados_ordenados = sorted(resultados, key=lambda r: r[0][0][0])  # sort by x

        texto_concat = ""
        conf_promedio = 0.0
        for r in resultados_ordenados:
            t = r[1].strip().upper().replace(" ", "").replace("-", "")
            texto_concat += t
            conf_promedio += float(r[2])
        if len(resultados_ordenados) > 0:
            conf_promedio /= len(resultados_ordenados)

        texto_concat = limpiar_placa_mexicana(texto_concat)

        if len(texto_concat) >= 4 and conf_promedio > mejor_conf:
            mejor_texto = texto_concat
            mejor_conf = conf_promedio
            imagen_usada = img

    return mejor_texto, mejor_conf, imagen_usada

# ─────────────────────────────────────────────────────────────────────
# SISTEMA DE VOTOS MULTI-FRAME
# ─────────────────────────────────────────────────────────────────────

class VotadorPlaca:
    """Acumula lecturas de OCR de múltiples frames y elige la más consistente."""
    def __init__(self, ventana=8):
        self.historial = []  # lista de (texto, confianza)
        self.ventana = ventana

    def agregar(self, texto, confianza):
        if texto and len(texto) >= 4:
            self.historial.append((texto, confianza))
            if len(self.historial) > self.ventana:
                self.historial.pop(0)

    def mejor(self):
        if not self.historial:
            return "", 0.0
        # Votar por el texto más frecuente ponderado por confianza
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

def initialize_video_writer(cap, output_video_path):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    return cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

def write_csv_header(csv_file_path):
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['frame', 'object_type', 'confidence', 'tracking_id',
                         'x1', 'y1', 'x2', 'y2', 'plate_confidence',
                         'mx1', 'my1', 'mx2', 'my2', 'license_plate_text'])

def put_text(frame, text, position, color=(0, 255, 0), font_scale=0.6, thickness=2, bg_color=(0, 0, 0)):
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    tx, ty = position
    cv2.rectangle(frame, (tx, ty - text_size[1] - 5), (tx + text_size[0] + 5, ty + 5), bg_color, cv2.FILLED)
    cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

# ─────────────────────────────────────────────────────────────────────
# BUCLE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────

def main():
    video_path = 0
    model_path = 'yolo11n.pt'
    lp_model_path = 'runs/detect/license_plate_detector/weights/best.pt'
    output_video_path = 'output_video.mp4'
    csv_file_path = 'detection_tracking_log.csv'
    classes_to_detect = [0, 1, 2, 3, 5]

    print("🤖 Cargando modelos de IA (V3 - Alta Precisión)...")
    model = initialize_model(model_path)
    lp_detector = YOLO(lp_model_path)
    reader = initialize_reader()
    db = DatabasePlacas()

    class_names = {0: "person", 1: "bicycle", 2: "car", 3: "motorbike", 5: "bus"}
    class_colors = {0: (255, 255, 255), 1: (0, 255, 0), 2: (0, 0, 255), 3: (255, 255, 0), 5: (0, 255, 255)}

    vehicle_plates = {}   # track_id → dict con datos de la mejor placa
    votadores = {}        # track_id → VotadorPlaca
    total_class_count = Counter()
    seen_ids = defaultdict(set)
    frame_number = 0
    blur_enabled = True
    paused = False

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
        print("❌ Error: No se pudo abrir la cámara.")
        sys.exit(1)

    out = initialize_video_writer(cap, output_video_path)
    write_csv_header(csv_file_path)
    print("🎥 Ejecutando V3 Alta Precisión. ESPACIO=pausar, b=desenfoque, ESC=salir.")

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

            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    confidence = round(float(box.conf[0]), 2)

                    if box.id is None:
                        continue

                    track_id = int(box.id[0].tolist())
                    if track_id not in seen_ids[cls]:
                        seen_ids[cls].add(track_id)
                        total_class_count[class_names[cls]] += 1

                    license_plate_text = ""
                    plate_confidence = None
                    mx1, my1, mx2, my2 = None, None, None, None

                    if class_names[cls] in ["car", "motorbike", "bus"]:
                        vehicle_img = frame[y1:y2, x1:x2]

                        # Umbral reducido para detectar vehículos lejanos
                        if vehicle_img.shape[0] < 50 or vehicle_img.shape[1] < 50:
                            continue
                        if confidence < 0.50:
                            continue

                        plate_results = lp_detector.predict(vehicle_img, verbose=False)

                        if plate_results and len(plate_results[0].boxes) > 0:
                            for plate_box in plate_results[0].boxes:
                                lpx1, lpy1, lpx2, lpy2 = map(int, plate_box.xyxy[0])

                                # ── MARGEN AMPLIO (25%): evita cortar el primer o último carácter
                                ph = lpy2 - lpy1
                                pw = lpx2 - lpx1
                                margin_h = max(int(ph * 0.25), 4)
                                margin_w = max(int(pw * 0.25), 6)
                                lpx1c = max(0, lpx1 - margin_w)
                                lpy1c = max(0, lpy1 - margin_h)
                                lpx2c = min(vehicle_img.shape[1], lpx2 + margin_w)
                                lpy2c = min(vehicle_img.shape[0], lpy2 + margin_h)

                                px1g = lpx1c + x1
                                py1g = lpy1c + y1
                                px2g = lpx2c + x1
                                py2g = lpy2c + y1

                                cv2.rectangle(frame, (px1g, py1g), (px2g, py2g), (255, 255, 255), 2)

                                roi_placa = vehicle_img[lpy1c:lpy2c, lpx1c:lpx2c].copy()
                                if roi_placa.size == 0:
                                    continue

                                # ── OCR CON PIPELINE COMPLETO (perspectiva + variantes + votos)
                                texto, conf, img_usada = leer_placa_ocr(reader, roi_placa)

                                # Agregar al votador multi-frame
                                if track_id not in votadores:
                                    votadores[track_id] = VotadorPlaca(ventana=10)
                                votadores[track_id].agregar(texto, conf)
                                texto_final, conf_final = votadores[track_id].mejor()

                                if conf_final >= 0.15 and texto_final:
                                    license_plate_text = texto_final
                                    plate_confidence = conf_final
                                    mx1, my1, mx2, my2 = px1g, py1g, px2g, py2g

                                    # Guardar solo si supera la confianza actual
                                    previo = vehicle_plates.get(track_id)
                                    if previo is None or conf_final > previo.get('confidence', 0.0):
                                        vehicle_plates[track_id] = {
                                            'plate': texto_final,
                                            'confidence': conf_final,
                                            'checked_db': False,
                                            'es_robado': False,
                                            'notified': False,
                                            'info': None
                                        }
                                        os.makedirs('plates', exist_ok=True)
                                        cv2.imwrite(f'plates/{frame_number}_{track_id}_{texto_final}.png', img_usada)

                                assigned_plate = vehicle_plates.get(track_id)
                                if assigned_plate:
                                    if not assigned_plate.get('checked_db', False):
                                        es_robado, info = db.consultar_placa(assigned_plate['plate'])
                                        assigned_plate['checked_db'] = True
                                        assigned_plate['es_robado'] = es_robado
                                        assigned_plate['info'] = info

                                    if assigned_plate.get('es_robado', False) and not assigned_plate.get('notified', False):
                                        assigned_plate['notified'] = True
                                        info = assigned_plate['info']
                                        os.makedirs('alertas', exist_ok=True)
                                        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        ruta_v = f"alertas/{sello}_{assigned_plate['plate']}_vehiculo.jpg"
                                        ruta_p = f"alertas/{sello}_{assigned_plate['plate']}_placa.jpg"
                                        cv2.imwrite(ruta_v, frame)
                                        cv2.imwrite(ruta_p, img_usada)
                                        db.registrar_alerta(
                                            placa_bd=info['placa'],
                                            placa_detectada=assigned_plate['plate'],
                                            similitud=info['similitud'],
                                            ruta_v=ruta_v, ruta_p=ruta_p
                                        )
                                        threading.Thread(
                                            target=enviar_telegram_hilo,
                                            args=(assigned_plate['plate'], info, [ruta_v, ruta_p]),
                                            daemon=True
                                        ).start()

                                    bg = (255, 255, 255)
                                    fg = (0, 0, 255) if assigned_plate.get('es_robado') else (0, 0, 0)
                                    prefix = "ROBADO: " if assigned_plate.get('es_robado') else "Plate: "
                                    put_text(frame, f"{prefix}{assigned_plate['plate']}", (x1, y2 + 40), color=fg, bg_color=bg)
                                    license_plate_text = assigned_plate['plate']
                                    plate_confidence = assigned_plate['confidence']

                    color = (0, 0, 255) if vehicle_plates.get(track_id, {}).get('es_robado') else class_colors.get(cls, (0, 0, 0))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                    put_text(frame, f"{class_names[cls]} {confidence}", (x1, y1 - 10), color=color)
                    put_text(frame, f"ID: {track_id}", (x1, y2 + 20), color=color)

                    if class_names[cls] == "person" and blur_enabled:
                        person_roi = frame[y1:y2, x1:x2]
                        if person_roi.size > 0:
                            frame[y1:y2, x1:x2] = cv2.GaussianBlur(person_roi, (51, 51), 30)

                    with open(csv_file_path, mode='a', newline='') as f:
                        csv.writer(f).writerow([frame_number, class_names[cls], confidence,
                                                track_id, x1, y1, x2, y2,
                                                plate_confidence, mx1, my1, mx2, my2,
                                                license_plate_text])
                    current_frame_count[class_names[cls]] += 1

            y_offset = 30
            for cls_name, count in total_class_count.items():
                put_text(frame, f"Total {cls_name}: {count}", (10, y_offset))
                y_offset += 20
            for cls_name, count in current_frame_count.items():
                put_text(frame, f"Frame {cls_name}: {count}", (10, y_offset), color=(255, 255, 255))
                y_offset += 20
            fps_calc = 1.0 / (time.time() - start_time)
            put_text(frame, f"FPS: {fps_calc:.2f}", (10, y_offset), color=(255, 255, 255))
            out.write(frame)

        cv2.imshow('Detection and Tracking', frame)
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
    print("Procesamiento terminado.")

if __name__ == "__main__":
    main()
