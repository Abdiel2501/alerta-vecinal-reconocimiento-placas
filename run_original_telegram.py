# -*- coding: utf-8 -*-
import cv2
import time
import math
import csv
import os
import sys
import threading
import sqlite3
import difflib
import requests
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

# Intentar cargar credenciales desde el config.env del proyecto principal
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Rutas posibles del archivo config.env
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
    def consultar_placa(self, texto_detectado: str, umbral_similitud: float = 0.80):
        if not os.path.exists(DB_PATH):
            return False, None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Búsqueda exacta
            cursor.execute("SELECT * FROM placas_robadas WHERE placa = ? AND activo = 1", (texto_detectado,))
            fila = cursor.fetchone()
            if fila:
                conn.close()
                return True, {**dict(fila), "similitud": 1.0}
            
            # 2. Búsqueda difusa
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
    """Realiza el envío de alertas y fotos a Telegram en segundo plano."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] [Simulacion] Alerta generada (Credenciales no configuradas):")
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
        f"🚨 *ALERTA DE VEHICULO ROBADO (IA ORIGINAL)* 🚨\n\n"
        f"📋 Placa en BD: *{placa_bd}*{coincidencia_str}\n"
        f"🚗 Vehiculo: {modelo} -- {color}\n"
        f"👤 Propietario: {propietario}\n"
        f"📅 Fecha del reporte: {fecha_reporte}{desc_str}\n"
        f"🕐 Hora de deteccion: {hora_deteccion}\n\n"
        f"⚠️ *ATENCION:* Llame al 911. Verifique visualmente antes de actuar."
    )

    url_texto = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    url_foto = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    try:
        # 1. Enviar mensaje de texto
        requests.post(url_texto, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}, timeout=10)
        
        # 2. Enviar fotos
        for ruta in rutas_imagenes:
            if os.path.exists(ruta):
                with open(ruta, "rb") as foto:
                    requests.post(url_foto, data={"chat_id": TELEGRAM_CHAT_ID}, files={"photo": foto}, timeout=15)
        print(f"[Telegram] Alerta enviada con éxito para la placa {placa_bd}.")
    except Exception as e:
        print(f"Error al enviar Telegram: {e}")

# ─────────────────────────────────────────────────────────────────────
# Código Principal de la IA
# ─────────────────────────────────────────────────────────────────────

def initialize_model(model_path):
    """Initialize the YOLO model for detection."""
    return YOLO(model_path)

def initialize_reader():
    """Initialize the EasyOCR reader."""
    import torch
    usar_gpu = torch.cuda.is_available()
    print(f"⚡ GPU para OCR: {'Sí (CUDA)' if usar_gpu else 'No (CPU)'}")
    return easyocr.Reader(['en'], gpu=usar_gpu)  

def initialize_video_writer(cap, output_video_path):
    """Set up the video writer for the processed video."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    return cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

def write_csv_header(csv_file_path):
    """Prepare CSV file for logging."""
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['frame', 'object_type', 'confidence', 'tracking_id', 'x1', 'y1', 'x2', 'y2',
                         'license_plate_confidence', 'mx1', 'my1', 'mx2', 'my2', 'license_plate_text'])

def put_text(frame, text, position, color=(0, 255, 0), font_scale=0.6, thickness=2, bg_color=(0, 0, 0)):
    """Helper function to put text with background on the frame."""
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    text_x, text_y = position
    box_coords = ((text_x, text_y - text_size[1] - 5), (text_x + text_size[0] + 5, text_y + 5))
    cv2.rectangle(frame, box_coords[0], box_coords[1], bg_color, cv2.FILLED)
    cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def main():
    # Parameters 
    video_path = 0  # Usamos la cámara por defecto (0) para pruebas en vivo
    model_path = 'yolo11n.pt'  # Path to YOLO model
    license_plate_detector_model_path = 'runs/detect/license_plate_detector/weights/best.pt'
    
    output_video_path = 'output_video.mp4'
    csv_file_path = 'detection_tracking_log.csv'
    show_video = True
    classes_to_detect = [0, 1, 2, 3, 5]
    
    print("🤖 Cargando modelos de IA con integración de alertas...")
    model = initialize_model(model_path)
    license_plate_detector = YOLO(license_plate_detector_model_path)
    reader = initialize_reader()
    db = DatabasePlacas()
    
    class_names = {0: "person", 1: "bicycle", 2: "car", 3: "motorbike", 5: "bus"}
    class_colors = {0: (255, 255, 255), 1: (0, 255, 0), 2: (0, 0, 255), 3: (255, 255, 0), 5: (0, 255, 255)}
    
    # Dictionary to store the best plate and its confidence for each track_id
    vehicle_plates = {}
    
    total_class_count = Counter()
    seen_ids = defaultdict(set)
    frame_number = 0
    
    blur_enabled = True
    paused = False
    
    print("📹 Intentando abrir la cámara...")
    # Probar diferentes backends de captura para evitar errores de lectura
    cap = None
    for backend, nombre in [(cv2.CAP_MSMF, "MSMF"), (cv2.CAP_DSHOW, "DSHOW"), (cv2.CAP_ANY, "ANY")]:
        c = cv2.VideoCapture(video_path, backend)
        if c.isOpened():
            ret, fot = c.read()
            if ret and fot is not None:
                print(f"   ✅ Backend {nombre} funcionó y lee fotogramas correctamente.")
                cap = c
                break
            c.release()
    
    if cap is None or not cap.isOpened():
        print("❌ Error: No se pudo abrir la cámara con ningún backend.")
        sys.exit(1)
        
    out = initialize_video_writer(cap, output_video_path)
    write_csv_header(csv_file_path)
    
    print("🎥 Ejecutando reconocimiento. Presiona ESPACIO para pausar, 'b' para alternar desenfoque, 'ESC' para salir.")
    
    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ No se pudo leer el fotograma. Saliendo...")
                break
    
            start_time = time.time()
            frame_number += 1
    
            # Run YOLO detection and tracking
            results = model.track(frame, persist=True, classes=classes_to_detect, verbose=False)
            current_frame_count = Counter()
    
            # Process detections
            for result in results:
                boxes = result.boxes
    
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    confidence = round(float(box.conf[0]), 2)
    
                    if box.id is not None:
                        track_id = int(box.id[0].tolist())
                        if track_id not in seen_ids[cls]:
                            seen_ids[cls].add(track_id)
                            total_class_count[class_names[cls]] += 1
    
                        license_plate_text = ""
                        plate_confidence = None
                        mx1, my1, mx2, my2 = None, None, None, None
    
                        if class_names[cls] in ["car", "motorbike", "bus"]:
                            vehicle_img = frame[y1:y2, x1:x2]
                            
                            min_plate_size = 80
                            if vehicle_img.shape[0] < min_plate_size or vehicle_img.shape[1] < min_plate_size:
                                continue
                            
                            if confidence < 0.7:
                                continue
                            
                            plate_results = license_plate_detector.predict(vehicle_img, verbose=False)
    
                            if plate_results and len(plate_results[0].boxes) > 0:
                                for plate_box in plate_results[0].boxes:
                                    px1, py1, px2, py2 = map(int, plate_box.xyxy[0])
                                    px1, py1, px2, py2 = px1 + x1, py1 + y1, px2 + x1, py2 + y1
                                                                
                                    cv2.rectangle(frame, (px1, py1), (px2, py2), (255, 255, 255), 2)
                                        
                                    license_plate_roi = frame[py1:py2, px1:px2]
                                    
                                    plate_height, plate_width = license_plate_roi.shape[:2]
                                    if plate_height == 0 or plate_width == 0:
                                        continue
                                    scale_factor = 100.0 / plate_height
                                    resized_plate = cv2.resize(
                                        license_plate_roi, None, fx=scale_factor, fy=scale_factor,
                                        interpolation=cv2.INTER_CUBIC)
    
                                    gray_plate = cv2.cvtColor(resized_plate, cv2.COLOR_BGR2GRAY)
    
                                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                                    equalized_plate = clahe.apply(gray_plate)
    
                                    denoised_plate = cv2.fastNlMeansDenoising(equalized_plate, None, 10, 7, 21)
    
                                    thresh_plate = cv2.adaptiveThreshold(
                                        denoised_plate, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY_INV, 11, 2)
    
                                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                                    morph_plate = cv2.morphologyEx(thresh_plate, cv2.MORPH_CLOSE, kernel)
                                    morph_plate = cv2.morphologyEx(morph_plate, cv2.MORPH_OPEN, kernel)
                                    morph_plate = cv2.bitwise_not(morph_plate)
    
                                    plate_ocr_results = reader.readtext(morph_plate, allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                                    
                                    if plate_ocr_results:
                                        license_plate_text = plate_ocr_results[0][-2]
                                        plate_confidence = round(plate_ocr_results[0][-1], 2)
                                        
                                        if plate_confidence >= 0.2:
                                            if (track_id not in vehicle_plates) or (plate_confidence > vehicle_plates[track_id]['confidence']):
                                                vehicle_plates[track_id] = {
                                                    'plate': license_plate_text,
                                                    'confidence': plate_confidence,
                                                    'checked_db': False,
                                                    'es_robado': False,
                                                    'notified': False,
                                                    'info': None
                                                }
                                                os.makedirs('plates', exist_ok=True)
                                                cv2.imwrite(f'plates/{frame_number}_{track_id}_{license_plate_text}.png', morph_plate)
    
                                            mx1, my1, mx2, my2 = px1, py1, px2, py2
                                        
                                    assigned_plate = vehicle_plates.get(track_id, None)
                                    if assigned_plate:
                                        # Comparación con Base de Datos de Placas Robadas
                                        if not assigned_plate.get('checked_db', False):
                                            es_robado, info = db.consultar_placa(assigned_plate['plate'])
                                            assigned_plate['checked_db'] = True
                                            assigned_plate['es_robado'] = es_robado
                                            assigned_plate['info'] = info
                                            
                                        # Si coincide y es robado, y no ha sido notificado
                                        if assigned_plate.get('es_robado', False) and not assigned_plate.get('notified', False):
                                            assigned_plate['notified'] = True
                                            info = assigned_plate['info']
                                            
                                            # Guardar fotos locales de la alerta
                                            os.makedirs('alertas', exist_ok=True)
                                            sello = datetime.now().strftime("%Y%m%d_%H%M%S")
                                            ruta_v = f"alertas/{sello}_placa_{assigned_plate['plate']}_vehiculo.jpg"
                                            ruta_p = f"alertas/{sello}_placa_{assigned_plate['plate']}_recorte.jpg"
                                            cv2.imwrite(ruta_v, frame)
                                            cv2.imwrite(ruta_p, morph_plate)
                                            
                                            # Registrar en historial
                                            db.registrar_alerta(
                                                placa_bd=info['placa'],
                                                placa_detectada=assigned_plate['plate'],
                                                similitud=info['similitud'],
                                                ruta_v=ruta_v,
                                                ruta_p=ruta_p
                                            )
                                            
                                            # Enviar por Telegram en segundo plano
                                            hilo = threading.Thread(
                                                target=enviar_telegram_hilo,
                                                args=(assigned_plate['plate'], info, [ruta_v, ruta_p]),
                                                daemon=True
                                            )
                                            hilo.start()

                                        background_color = (255, 255, 255)
                                        high_contrast_color = (0, 0, 255) if assigned_plate.get('es_robado', False) else (0, 0, 0)
                                        label_prefix = "ROBADO: " if assigned_plate.get('es_robado', False) else "Plate: "
                                        put_text(frame, f"{label_prefix}{assigned_plate['plate']}", (x1, y2 + 40), color=high_contrast_color, bg_color=background_color)
    
                                        license_plate_text = assigned_plate['plate']
                                        plate_confidence = assigned_plate['confidence']
                                    else:
                                        license_plate_text = ""
                                        plate_confidence = None
                        
                        color = (0, 0, 255) if vehicle_plates.get(track_id, {}).get('es_robado', False) else class_colors.get(cls, (0, 0, 0))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                        put_text(frame, f"{class_names[cls]} {confidence}", (x1, y1 - 10), color=color)
                        put_text(frame, f"ID: {track_id}", (x1, y2 + 20), color=color)
                                        
                        if class_names[cls] == "person" and blur_enabled:
                            person_roi = frame[y1:y2, x1:x2]
                            if person_roi.size > 0:
                                blurred_person = cv2.GaussianBlur(person_roi, (51, 51), 30)
                                frame[y1:y2, x1:x2] = blurred_person
                            
                        with open(csv_file_path, mode='a', newline='') as file:
                            writer = csv.writer(file)
                            writer.writerow([frame_number, class_names[cls], confidence, track_id, x1, y1, x2, y2,
                                             plate_confidence, mx1, my1, mx2, my2, license_plate_text])
    
                        current_frame_count[class_names[cls]] += 1
    
            y_offset = 30
            for cls, count in total_class_count.items():
                put_text(frame, f"Total {cls}: {count}", (10, y_offset))
                y_offset += 20
    
            for cls, count in current_frame_count.items():
                put_text(frame, f"Frame {cls}: {count}", (10, y_offset), color=(255, 255, 255))
                y_offset += 20
    
            fps_calc = 1.0 / (time.time() - start_time)
            put_text(frame, f"FPS: {fps_calc:.2f}", (10, y_offset), color=(255, 255, 255))
    
            out.write(frame)
    
        if show_video:
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
    print("Procesamiento terminado de forma exitosa.")

if __name__ == "__main__":
    main()
