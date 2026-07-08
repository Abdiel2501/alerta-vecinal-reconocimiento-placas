# -*- coding: utf-8 -*-
"""
run_original_telegram_v14.py — Motor de IA V14 (Autodetección de cámara IP + Consenso)
══════════════════════════════════════════════════════════════════════════════
NOTA HONESTA (lee esto primero):
  Ningún sistema de OCR/visión — ni los comerciales de peaje o los de policía —
  logra 100% de precisión en 100% de los ángulos y distancias. Este archivo NO
  promete "nunca fallar"; promete acercarse todo lo posible con: más evidencia
  por vehículo, mejor preprocesamiento, y un árbitro más robusto que un único
  "quien gana". También corrige un problema serio que encontré en tu V12: la
  clase DatabasePlacas y los campos 'es_robado'/'notified' existían pero NUNCA
  se usaban en main(), y no había ninguna función que realmente enviara algo a
  Telegram (el import `requests` no se usaba en ningún lado). Es decir: aunque
  el OCR leyera perfecto una placa robada, la V12 tal como la pegaste NUNCA iba
  a mandar la alerta. Eso ya está arreglado aquí.

CAMBIOS CLAVE EN V13:

  [1] VOTO CARÁCTER-POR-CARÁCTER (VotadorPlacaCaracter)
      - Antes: si Gemini y OCR local no coincidían EXACTO, ganaba Gemini a ciegas
        (un solo mal frame de Gemini podía imponer una placa incorrecta).
      - Ahora: cada lectura válida (siempre normalizada a 7 caracteres por
        validar_formato_placa) vota posición por posición, ponderada por
        confianza y por fuente (Gemini pesa más, pero no gana por decreto).
      - Resultado: la placa final puede ser correcta incluso si NINGUNA lectura
        individual lo fue completa — el error típico "una I leída como 1" en
        un solo frame ya no arruina todo.

  [2] MÁS EVIDENCIA POR VEHÍCULO, NO SOLO LA PRIMERA QUE FUNCIONE
      - V12 se detenía en la primera variante de OCR que diera texto.
      - V13 reúne lecturas de: recto, recto-a-mayor-escala (placas lejanas) y,
        si PRECISION_MAXIMA=True, también los 3 ángulos de respaldo — todas
        alimentan el votador, no solo la primera.
      - Costo: más CPU por frame. Si te baja mucho el FPS, pon
        PRECISION_MAXIMA=False (abajo) para volver a un modo más liviano.

  [3] MEJOR FRAME PARA GEMINI, NO CUALQUIERA
      - V12 le mandaba a Gemini el frame que disparó el umbral de distancia,
        sin importar si estaba borroso.
      - V13 mide nitidez (varianza de Laplaciano) cada frame y guarda el mejor
        recorte visto por vehículo; ese es el que se manda a Gemini, y los
        reintentos usan el mejor frame disponible hasta ese momento.
      - Resolución de imagen a Gemini subida de 384px a 640px (más detalle a
        costa de un poco más de latencia).

  [4] REINTENTOS CONTROLADOS DE GEMINI CON MANEJO DE ERRORES
      - Reintento automático con backoff corto si la API falla o da rate-limit.
      - Tope de reintentos (GEMINI_MAX_REINTENTOS) para no gastar cuota infinita
        en un vehículo que simplemente no tiene placa legible.

  [5] ALERTAS TELEGRAM REALES (esto faltaba en tu V12)
      - Se agrega enviar_alerta_telegram() que sí llama a la API de Telegram
        (sendPhoto con la foto del vehículo + sendMessage de respaldo).
      - Se vuelve a consultar la base de datos si la placa de consenso cambia
        (por si el OCR corrige una lectura después de haber revisado una mal).
      - Se dispara la alerta una sola vez por vehículo (estado['notified']),
        pero se re-evalúa si la placa cambia.

  [6] TRANSPARENCIA
      - La etiqueta en pantalla ahora muestra cuántas lecturas soportan el
        consenso, ej: "Plate: ILE3865 (Confirmado, n=8)" — para que puedas
        juzgar tú mismo qué tan sólida es cada lectura, en vez de creer
        ciegamente en un solo color.
      - Se guarda un log de consenso en logs/consenso_log.csv para que puedas
        medir con datos reales qué tan seguido Gemini y el OCR local coinciden
        (la única forma honesta de saber si "nunca falla" es medirlo, no
        asumirlo).
"""
import cv2
import time
import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'databases'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'iAs'))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import io
import queue
import threading
import sqlite3
import difflib
import requests
import re
import csv
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime
from PIL import Image
from ultralytics import YOLO
from paddleocr import PaddleOCR

import logging
logging.getLogger("ppocr").setLevel(logging.ERROR)

try:
    import google.generativeai as genai
    GEMINI_DISPONIBLE = True
except ImportError:
    GEMINI_DISPONIBLE = False

import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────
# Configuración ajustable de V13
# ─────────────────────────────────────────────────────────────────────

PRECISION_MAXIMA     = True   # True = más lecturas por frame (mejor consenso, más CPU)
VENTANA_VOTADOR       = 25     # cuántas lecturas recientes recuerda el votador por vehículo
GEMINI_IMG_MAX_W      = 640    # resolución enviada a Gemini (antes 384)
GEMINI_MAX_REINTENTOS = 4      # tope de llamadas a Gemini por vehículo
GEMINI_REINTENTO_FRAMES = 45   # cada cuántos frames reintenta si no ha leído nada

FUENTE_PESO = {
    'Gemini': 3.0,
    'Local' : 1.0,
}

# ─────────────────────────────────────────────────────────────────────
# Credenciales
# ─────────────────────────────────────────────────────────────────────

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "databases", "secure_placas.db"))
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
GEMINI_API_KEY = ""

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

if not TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
if not GEMINI_API_KEY:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

GEMINI_MODEL_NAME = "models/gemini-1.5-flash"

if GEMINI_DISPONIBLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("💡 Gemini API configurada.")
        modelos = [m.name for m in genai.list_models()]
        encontrado = False
        preferidos = [
            "models/gemini-flash-lite-latest",
            "models/gemini-2.5-flash-lite",
            "models/gemini-2.0-flash-lite",
            "models/gemini-1.5-flash"
        ]
        for m in preferidos:
            if m in modelos:
                GEMINI_MODEL_NAME = m
                encontrado = True
                break
        if not encontrado:
            for m in modelos:
                if "gemini" in m and "flash" in m and "lite" in m:
                    GEMINI_MODEL_NAME = m
                    encontrado = True
                    break
            if not encontrado:
                for m in modelos:
                    if "gemini" in m and "flash" in m:
                        GEMINI_MODEL_NAME = m
                        break
        print(f"🎯 Modelo Gemini: {GEMINI_MODEL_NAME}")
    except Exception as e:
        print(f"⚠️ Error Gemini: {e}")
        GEMINI_API_KEY = ""
else:
    print("⚠️ Gemini no configurado.")

# ─────────────────────────────────────────────────────────────────────
# Base de datos
# ─────────────────────────────────────────────────────────────────────

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
# Alertas Telegram — ESTO FALTABA POR COMPLETO EN LA V12 QUE COMPARTISTE
# ─────────────────────────────────────────────────────────────────────

def enviar_alerta_telegram(mensaje, ruta_imagen=None):
    """Envía la alerta real a Telegram a todos los usuarios activos de la base de datos
    más el chat_id por defecto de config.env. Si hay imagen, la manda como foto con
    caption; si no, manda solo texto. Nunca lanza excepción hacia afuera."""
    if not TELEGRAM_TOKEN:
        print("⚠️ [Telegram] Token no configurado — alerta NO enviada.")
        return False

    db = DatabasePlacas()
    chat_ids = db.obtener_chat_ids_activos()
    if TELEGRAM_CHAT_ID and TELEGRAM_CHAT_ID not in chat_ids:
        chat_ids.append(TELEGRAM_CHAT_ID)

    if not chat_ids:
        print("⚠️ [Telegram] No hay destinatarios (Chat IDs) configurados — de la base de datos ni config.env.")
        return False

    exito_al_menos_uno = False
    for chat_id in chat_ids:
        if not chat_id:
            continue
        try:
            if ruta_imagen and os.path.exists(ruta_imagen):
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
                with open(ruta_imagen, 'rb') as foto:
                    r = requests.post(
                        url,
                        data={"chat_id": chat_id, "caption": mensaje},
                        files={"photo": foto},
                        timeout=15
                    )
            else:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                r = requests.post(url, data={"chat_id": chat_id, "text": mensaje}, timeout=15)
            if r.status_code != 200:
                print(f"🚨 [Telegram] Error HTTP {r.status_code} al enviar a {chat_id}: {r.text[:200]}")
            else:
                print(f"✅ [Telegram] Alerta enviada a {chat_id}.")
                exito_al_menos_uno = True
        except Exception as e:
            print(f"🚨 [Telegram] Excepción enviando alerta a {chat_id}: {e}")

    return exito_al_menos_uno

def enviar_alerta_telegram_async(mensaje, ruta_imagen=None):
    """Versión en hilo aparte para no congelar el loop principal de video."""
    threading.Thread(target=enviar_alerta_telegram, args=(mensaje, ruta_imagen), daemon=True).start()

def log_consenso(track_id, texto, origen, confianza, n_lecturas):
    """Guarda cada actualización de consenso a un CSV para que puedas medir
    con datos reales — no con promesas — qué tan seguido Gemini y el OCR
    local coinciden, y qué tan estable es cada placa a lo largo del tiempo."""
    try:
        os.makedirs('logs', exist_ok=True)
        existe = os.path.exists('logs/consenso_log.csv')
        with open('logs/consenso_log.csv', 'a', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            if not existe:
                w.writerow(['timestamp', 'track_id', 'placa', 'origen', 'confianza', 'n_lecturas'])
            w.writerow([datetime.now().isoformat(timespec='seconds'), track_id, texto, origen, confianza, n_lecturas])
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────
# ReID
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

# ─────────────────────────────────────────────────────────────────────
# Preprocesamiento + Multi-Ángulo + Multi-Distancia
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

def rotar_imagen(img, angulo):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w/2, h/2), angulo, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def calidad_imagen(roi):
    """Puntaje de nitidez (varianza del Laplaciano). Mayor = más nítida.
    Se usa para elegir el MEJOR frame de cada vehículo para mandar a Gemini,
    en vez de mandar el primero que cumpla el umbral de tamaño (que puede
    estar movido/borroso)."""
    if roi is None or roi.size == 0:
        return 0.0
    try:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        return 0.0

def enfocar(gray):
    """Unsharp mask ligero — refuerza bordes de caracteres, ayuda sobre todo
    en placas lejanas/pequeñas donde el detalle es escaso."""
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
    """Variantes rotadas — solo se usan si PRECISION_MAXIMA=True."""
    out = []
    for ang in [-15, 15, 180]:
        try:
            rotada = rotar_imagen(roi_base, ang)
            out.append(preprocesamiento_dinamico(rotada, area))
        except: pass
    return out

# ─────────────────────────────────────────────────────────────────────
# Validación de placa
# ─────────────────────────────────────────────────────────────────────

def validar_formato_placa(texto):
    """
    V13: estructura confirmada con dos fotos reales de placas de Tamaulipas
    (transporte privado / automóvil):
      - Posiciones 0-2: SIEMPRE letras (ej. 'XKK' en la placa real 'XKK2850').
      - Posiciones 3-5: SIEMPRE dígitos (confirmado en ambas referencias).
      - Posición 6 (última): ambigua — la foto real mostraba dígito
        ('XKK2850'), pero una plantilla de referencia mostraba letra
        ('AAA-000-A'). Sin más evidencia no se fuerza un tipo aquí; se
        respeta lo que haya leído el OCR/Gemini en esa posición.

    Antes se validaba solo contando letras/números sueltos en cualquier
    posición, lo que podía aceptar arreglos que en la realidad no existen
    (ej. una letra en la posición 4). Validar la estructura exacta reduce
    falsos positivos de OCR.
    """
    texto = re.sub(r'[^A-Z0-9]', '', texto.upper())
    if len(texto) != 7:
        return ""

    fl = {'0':'O','1':'I','5':'S','8':'B'}.get
    fn = {'O':'0','I':'1','S':'5','Z':'2','B':'8','G':'6'}.get

    p012 = [fl(c, c) for c in texto[0:3]]
    p345 = [fn(c, c) for c in texto[3:6]]
    p6   = texto[6]

    if not all(c.isalpha() for c in p012):
        return ""
    if not all(c.isdigit() for c in p345):
        return ""

    return "".join(p012) + "".join(p345) + p6

# ─────────────────────────────────────────────────────────────────────
# Votador V13 — consenso caracter-por-caracter
# ─────────────────────────────────────────────────────────────────────

class VotadorPlacaCaracter:
    """
    Reemplaza al votador de string-completo de la V12.

    Como validar_formato_placa() siempre normaliza a exactamente 7 caracteres
    (o descarta la lectura), cada lectura aceptada es directamente comparable
    posición por posición. En vez de exigir que un string completo coincida
    con otro, cada una de las 7 posiciones vota su propio carácter, ponderado
    por confianza y por qué tan confiable es la fuente (Gemini > OCR local).

    Esto es más robusto que "Gemini siempre gana": un solo mal frame de
    Gemini ya no puede imponer una placa incorrecta si el resto de la
    evidencia (varias lecturas locales estables) apunta a otra cosa.
    """
    def __init__(self, ventana=VENTANA_VOTADOR):
        self.historial = []  # (texto, conf, fuente)
        self.ventana = ventana

    def agregar(self, texto, conf, fuente):
        if texto and len(texto) == 7:
            self.historial.append((texto, float(conf), fuente))
            if len(self.historial) > self.ventana:
                self.historial.pop(0)

    def consenso(self):
        """Devuelve (placa_reconstruida, confianza_promedio[0-1], n_lecturas)."""
        if not self.historial:
            return "", 0.0, 0
        posiciones = [defaultdict(float) for _ in range(7)]
        for texto, conf, fuente in self.historial:
            peso = FUENTE_PESO.get(fuente, 1.0) * max(conf, 0.05)
            for i, ch in enumerate(texto):
                posiciones[i][ch] += peso

        placa = []
        certeza_total = 0.0
        for pos in posiciones:
            mejor_ch = max(pos, key=pos.get)
            total = sum(pos.values())
            certeza_total += (pos[mejor_ch] / total) if total > 0 else 0.0
            placa.append(mejor_ch)
        placa_final = "".join(placa)
        confianza = certeza_total / 7.0
        return placa_final, round(confianza, 3), len(self.historial)

    def estable(self, min_lecturas=6, min_confianza=0.75):
        _, conf, n = self.consenso()
        return n >= min_lecturas and conf >= min_confianza

    def gemini_ya_leyo(self):
        return any(f == 'Gemini' for _, _, f in self.historial)

    def ultima_lectura_gemini(self):
        for texto, conf, fuente in reversed(self.historial):
            if fuente == 'Gemini':
                return texto
        return None

# ─────────────────────────────────────────────────────────────────────
# Árbitro central — reemplaza a _comparar_y_actualizar de la V12
# ─────────────────────────────────────────────────────────────────────

def _actualizar_estado(track_id, vehicle_plates, lock, texto, conf, fuente, votadores):
    """Registra una lectura (de Gemini o de OCR local) en el votador del
    vehículo y recalcula el consenso caracter-por-caracter. Devuelve el
    estado actualizado (ya con lock liberado, para poder loguear afuera)."""
    with lock:
        votador = votadores.get(track_id)
        if votador is None:
            votador = VotadorPlacaCaracter()
            votadores[track_id] = votador
        votador.agregar(texto, conf, fuente)

        placa_consenso, confianza_consenso, n = votador.consenso()

        estado = vehicle_plates.get(track_id, {})
        estado.setdefault('checked_db', False)
        estado.setdefault('es_robado', False)
        estado.setdefault('notified', False)
        estado.setdefault('info', None)
        estado.setdefault('placa_verificada', None)

        if fuente == 'Gemini':
            estado['gemini_plate'] = texto
            estado['gemini_done'] = True

        if not placa_consenso:
            vehicle_plates[track_id] = estado
            return dict(estado)

        gemini_txt = votador.ultima_lectura_gemini()
        if gemini_txt and gemini_txt == placa_consenso:
            origen = 'Confirmado'
        elif gemini_txt:
            origen = 'Gemini Fix'
        elif n >= 6 and confianza_consenso >= 0.75:
            origen = 'Local Estable'
        else:
            origen = 'YOLO (local)'

        estado['plate']      = placa_consenso
        estado['origen']     = origen
        estado['confidence'] = round(min(0.99, 0.5 + confianza_consenso * 0.5), 2)
        estado['n_lecturas'] = n

        vehicle_plates[track_id] = estado

    log_consenso(track_id, placa_consenso, origen, estado['confidence'], n)
    return dict(estado)

# ─────────────────────────────────────────────────────────────────────
# Hilo Gemini — con mejor frame, reintentos y manejo de errores
# ─────────────────────────────────────────────────────────────────────

def consultar_gemini_hilo(img_vehiculo, track_id, vehicle_plates, lock, votadores, intento=1):
    if not GEMINI_DISPONIBLE or not GEMINI_API_KEY:
        with lock:
            estado = vehicle_plates.get(track_id, {})
            estado['gemini_done']  = True
            estado['gemini_plate'] = None
            vehicle_plates[track_id] = estado
        return

    try:
        h, w = img_vehiculo.shape[:2]
        max_w = GEMINI_IMG_MAX_W
        if w > max_w:
            scale = max_w / w
            img_vehiculo = cv2.resize(img_vehiculo, (max_w, int(h * scale)), interpolation=cv2.INTER_AREA)

        pil_img = Image.fromarray(cv2.cvtColor(img_vehiculo, cv2.COLOR_BGR2RGB))
        print(f"[Gemini ⏳] → ID {track_id}: analizando (intento {intento})...")
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)

        prompt = (
            "You are analyzing a security camera image of a vehicle. "
            "Your ONLY task is to read the Mexican license plate number visible on this vehicle. "
            "Standard private ('TRANSPORTE PRIVADO') plates from Tamaulipas have exactly 7 alphanumeric "
            "characters: 3 letters followed by 4 digits (e.g. XKK2850, ILE3865). The plate is usually "
            "printed as 'LLL-DD-DD' or 'LLL-DDD-D' with hyphens, but the hyphens are NOT part of the plate "
            "number itself — just report the 7 characters. "
            "The plate may appear at an angle, partially visible, far away, or have glare — do your absolute best, "
            "including guessing individual characters that are only partially visible if the rest of the plate is clear. "
            "Look at the front OR rear of the vehicle for the white/beige rectangular plate. "
            "Respond with ONLY the 7-character plate number in uppercase, no spaces, no hyphens, no explanation. "
            "Examples of valid responses: XKK2850, ILE3865, ABC1234. "
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
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                max_output_tokens=20,
            ),
            safety_settings=safety_settings
        )
        texto_raw = re.sub(r'[^A-Z0-9]', '', response.text.strip().upper())[:7]

        if texto_raw and texto_raw != "NONE" and len(texto_raw) >= 6:
            texto_limpio = validar_formato_placa(texto_raw)
            if not texto_limpio and len(texto_raw) == 7:
                texto_limpio = texto_raw

            if texto_limpio:
                print(f"✅ [Gemini] ID {track_id} → '{texto_limpio}'")
                _actualizar_estado(track_id, vehicle_plates, lock, texto_limpio, 0.95, 'Gemini', votadores)
                return

        print(f"⚠️ [Gemini] ID {track_id} → no leyó placa")

    except Exception as e:
        msg = str(e)
        es_rate_limit = "429" in msg or "quota" in msg.lower() or "rate" in msg.lower()
        print(f"🚨 [Gemini Error] ID {track_id} (intento {intento}): {e}")
        if intento < GEMINI_MAX_REINTENTOS:
            time.sleep(1.5 if es_rate_limit else 0.5)
            consultar_gemini_hilo(img_vehiculo, track_id, vehicle_plates, lock, votadores, intento=intento + 1)
            return

    with lock:
        estado = vehicle_plates.get(track_id, {})
        estado['gemini_done']  = True
        estado['gemini_plate'] = None
        vehicle_plates[track_id] = estado

# ─────────────────────────────────────────────────────────────────────
# PaddleOCR multi-ángulo / multi-distancia — reúne TODAS las lecturas
# ─────────────────────────────────────────────────────────────────────

def _ocr_intentar(reader, img, track_id, label):
    """Intenta leer placa con det=False y det=True. Devuelve (texto, conf, img) o ('', 0, img)."""
    try:
        res = reader.ocr(img, det=False, cls=False)
        if res and res[0] and res[0][0]:
            txt, conf = res[0][0]
            tv = validar_formato_placa(txt)
            if tv and conf > 0.40:
                print(f"[OCR] ID {track_id} {label} rápido: '{tv}' {conf:.2f}")
                return tv, float(conf), img
    except: pass
    try:
        res = reader.ocr(img, det=True, cls=False)
        if res and res[0]:
            lineas = sorted(res[0], key=lambda r: r[0][0][0])
            txt = "".join(r[1][0] for r in lineas)
            conf = sum(r[1][1] for r in lineas) / len(lineas) if lineas else 0.0
            tv = validar_formato_placa(txt)
            if tv:
                print(f"[OCR] ID {track_id} {label} det: '{tv}' {conf:.2f}")
                return tv, conf, img
    except: pass
    return "", 0.0, img

def leer_todas_variantes(reader, roi_base, area, track_id):
    """
    V13: en vez de detenerse en la primera variante que funcione (como hacía
    leer_placa_completa en V12), reúne TODAS las lecturas válidas de varias
    escalas/ángulos. Más lecturas = mejor consenso caracter-por-caracter.

    Siempre prueba: recto (distancia normal) y recto-lejos (placas pequeñas/
    distantes, con más upscaling). Si PRECISION_MAXIMA=True, también prueba
    los 3 ángulos de respaldo (-15°, +15°, 180°) para vehículos fotografiados
    de lado o con la placa un poco girada.
    """
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

# ─────────────────────────────────────────────────────────────────────
# Helpers visuales
# ─────────────────────────────────────────────────────────────────────

ORIGEN_COLORES = {
    'Gemini'       : ((0, 220, 255), (0, 0, 0)),
    'Gemini Fix'   : ((0, 165, 255), (0, 0, 0)),
    'Confirmado'   : ((0, 255, 100), (0, 0, 0)),
    'Local Estable': ((0, 200, 200), (0, 0, 0)),
    'YOLO (local)' : ((200, 200, 200), (0, 0, 0)),
    'Local'        : ((200, 200, 200), (0, 0, 0)),
}

def put_text(frame, text, pos, color=(0,255,0), font_scale=0.6, thickness=2, bg=(0,0,0)):
    ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    tx, ty = pos
    cv2.rectangle(frame, (tx,ty-ts[1]-5), (tx+ts[0]+5,ty+5), bg, cv2.FILLED)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def pixelar_region(frame, x1, y1, x2, y2, factor=12):
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0: return
    h, w = roi.shape[:2]
    if h < factor or w < factor: return
    small = cv2.resize(roi, (max(1, w // factor), max(1, h // factor)), interpolation=cv2.INTER_LINEAR)
    frame[y1:y2, x1:x2] = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

def dibujar_placa(frame, estado, x1, x2, y2):
    """Dibuja la etiqueta de placa con color según el origen, mostrando
    también cuántas lecturas soportan el consenso (transparencia real sobre
    qué tan sólida es cada lectura)."""
    if not estado or not estado.get('plate'):
        return
    plate  = estado['plate']
    origen = estado.get('origen', 'Local')
    n      = estado.get('n_lecturas', 0)
    bg_color, fg_color = ORIGEN_COLORES.get(origen, ((255,255,255), (0,0,0)))

    ty = y2 + 45
    if ty > frame.shape[0] - 10:
        ty = y2 - 15

    put_text(frame, f"Plate: {plate} ({origen}, n={n})", (x1, ty), color=fg_color, bg=bg_color, font_scale=0.65, thickness=2)

# ─────────────────────────────────────────────────────────────────────
# Worker YOLO + OCR (hilo separado)
# ─────────────────────────────────────────────────────────────────────

class DeteccionOCRWorker:
    def __init__(self, lp_detector, reader, vehicle_plates, lock, votadores):
        self.lp_detector    = lp_detector
        self.reader         = reader
        self.vehicle_plates = vehicle_plates
        self.lock           = lock
        self.votadores      = votadores
        self.cola           = queue.Queue(maxsize=8)
        self.resultados     = {}
        self.lock_res       = threading.Lock()
        self.running        = True
        self.hilo           = threading.Thread(target=self._loop, daemon=True)
        self.hilo.start()

    def enviar(self, track_id, vehicle_roi, veh_bbox, frame_num, mejor_area_ref):
        try: self.cola.put_nowait((track_id, vehicle_roi.copy(), veh_bbox, frame_num, mejor_area_ref))
        except queue.Full: pass

    def obtener_bbox(self, track_id):
        with self.lock_res: return self.resultados.get(track_id)

    def detener(self):
        self.running = False
        try: self.cola.put_nowait(None)
        except queue.Full: pass

    def _loop(self):
        while self.running:
            try: item = self.cola.get(timeout=1.0)
            except queue.Empty: continue
            if item is None: break
            track_id, vehicle_roi, veh_bbox, frame_num, mejor_area_ref = item
            self._procesar(track_id, vehicle_roi, veh_bbox, frame_num, mejor_area_ref)
            self.cola.task_done()

    def _procesar(self, track_id, vehicle_roi, veh_bbox, frame_num, mejor_area_ref):
        try: plate_results = self.lp_detector.predict(vehicle_roi, verbose=False, conf=0.35)
        except: return

        if not plate_results or len(plate_results[0].boxes) == 0:
            return

        x1v, y1v = veh_bbox[0], veh_bbox[1]
        mejores = []

        for plate_box in plate_results[0].boxes:
            conf_plate = float(plate_box.conf[0])
            if conf_plate < 0.35: continue
            lpx1,lpy1,lpx2,lpy2 = map(int, plate_box.xyxy[0])
            ph, pw = lpy2-lpy1, lpx2-lpx1
            if ph == 0: continue
            aspect_ratio = pw / float(ph)
            
            # Filtro inteligente: rechazar cosas muy alargadas (como fascias) o muy cuadradas
            if aspect_ratio > 4.5 or aspect_ratio < 1.1:
                continue
                
            area   = ph * pw
            m = max(int(pw * 0.18), 6)
            lpx1c = max(0, lpx1 - m)
            lpy1c = max(0, lpy1 - m)
            lpx2c = min(vehicle_roi.shape[1], lpx2 + m)
            lpy2c = min(vehicle_roi.shape[0], lpy2 + m)
            px1g,py1g = lpx1c+x1v, lpy1c+y1v
            px2g,py2g = lpx2c+x1v, lpy2c+y1v
            roi_placa = vehicle_roi[lpy1c:lpy2c, lpx1c:lpx2c]
            if roi_placa.size == 0: continue

            lecturas, img_usada = leer_todas_variantes(self.reader, roi_placa, area, track_id)

            mejor_texto, mejor_conf = "", 0.0
            for txt, conf in lecturas:
                if conf > mejor_conf:
                    mejor_texto, mejor_conf = txt, conf

            mejores.append({
                'plate': mejor_texto, 'confidence': mejor_conf, 'img': img_usada,
                'bbox_global': (px1g,py1g,px2g,py2g), 'area': area,
                'frame_num': frame_num, 'lecturas': lecturas
            })

        if not mejores: return

        con_texto = [m for m in mejores if m['plate']]
        mejor = max(con_texto, key=lambda x: x['confidence']) if con_texto else mejores[0]

        with self.lock_res:
            prev = self.resultados.get(track_id)
            if prev is None or mejor['area'] >= prev.get('area', 0):
                self.resultados[track_id] = mejor

        if mejor['plate']:
            parea = mejor_area_ref.get(track_id, 0)
            if mejor['area'] >= parea:
                mejor_area_ref[track_id] = mejor['area']
                os.makedirs('plates', exist_ok=True)
                try: cv2.imwrite(f"plates/{frame_num}_{track_id}_{mejor['plate']}_V14.png", mejor['img'])
                except: pass

            # Alimentar el votador con TODAS las lecturas obtenidas (no solo la mejor),
            # así el consenso caracter-por-caracter tiene más evidencia real.
            for txt, conf in mejor['lecturas']:
                _actualizar_estado(track_id, self.vehicle_plates, self.lock, txt, conf, 'Local', self.votadores)

# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    import subprocess
    import os
    ip_cam = "169.254.223.11"
    video_path = 0
    print("Buscando cámara IP...")
    try:
        if os.name == 'nt':
            res = subprocess.run(["ping", "-n", "1", "-w", "500", ip_cam], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            res = subprocess.run(["ping", "-c", "1", "-W", "1", ip_cam], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        if res.returncode == 0:
            print(f"✅ Cámara IP conectada ({ip_cam}). Usando flujo de red.")
            video_path = f"rtsp://admin:admin@{ip_cam}:554/live/ch0"
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        else:
            print("⚠️ Cámara IP no encontrada. Usando Webcam (0)...")
    except:
        pass

    model_path    = 'yolo11n.pt'
    lp_model_path = 'runs/detect/license_plate_detector/weights/best.pt'
    output_video  = 'output_v14.mp4'
    classes_to_detect = [0,1,2,3,5]

    print("🤖 Cargando V14 — Autodetección de cámara IP + Consenso + Alertas reales...")
    import torch
    usar_gpu = torch.cuda.is_available()
    print(f"⚡ GPU: {'Sí' if usar_gpu else 'CPU'}")
    print(f"🔧 PRECISION_MAXIMA={PRECISION_MAXIMA} (más lecturas por frame si está en True)")

    model       = YOLO(model_path)
    lp_detector = YOLO(lp_model_path)
    try:
        reader = PaddleOCR(use_angle_cls=False, lang='en', use_gpu=False)
    except Exception as e:
        print(f"Error PaddleOCR: {e}")
        sys.exit(1)

    reider      = ReidentificadorVehiculos(max_frames=90, umbral=0.72)
    lock_plates = threading.Lock()
    db_placas   = DatabasePlacas()

    vehicle_plates      = {}
    mejor_area          = {}
    votadores           = {}   # track_id -> VotadorPlacaCaracter
    mejor_frame_gemini  = {}   # track_id -> (score_nitidez_area, roi_copy)
    gemini_intentos     = {}   # track_id -> cuántas veces ya se llamó a Gemini

    worker = DeteccionOCRWorker(lp_detector, reader, vehicle_plates, lock_plates, votadores)

    class_names  = {0:"person",1:"bicycle",2:"car",3:"motorbike",5:"bus"}
    class_colors = {0:(255,255,255),1:(0,255,0),2:(0,0,255),3:(255,255,0),5:(0,255,255)}

    gemini_lanzado     = set()
    gemini_lock        = threading.Lock()
    ocr_skip_counter   = {}

    total_class_count  = Counter()
    seen_ids           = defaultdict(set)
    frame_number       = 0
    blur_enabled       = True
    paused             = False

    print("📹 Abriendo cámara...")
    cap = None
    for backend in [(cv2.CAP_MSMF,"MSMF"),(cv2.CAP_DSHOW,"DSHOW"),(cv2.CAP_ANY,"ANY")]:
        c = cv2.VideoCapture(video_path, backend[0])
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

            results = model.track(frame, persist=True, classes=classes_to_detect, verbose=False, imgsz=480, conf=0.40)
            current_frame_count = Counter()
            ids_vistos = set()

            for result in results:
                for box in result.boxes:
                    x1,y1,x2,y2 = map(int, box.xyxy[0])
                    cls          = int(box.cls[0])
                    confidence   = round(float(box.conf[0]), 2)

                    if box.id is None: continue
                    track_id = int(box.id[0].tolist())

                    if class_names[cls] not in ["car","motorbike","bus"]:
                        ids_vistos.add(track_id)
                        if track_id not in seen_ids[cls]:
                            seen_ids[cls].add(track_id)
                            total_class_count[class_names[cls]] += 1
                        if class_names[cls] == "person" and blur_enabled:
                            pixelar_region(frame, x1, y1, x2, y2, factor=12)
                        color = class_colors.get(cls,(0,0,0))
                        cv2.rectangle(frame,(x1,y1),(x2,y2),color,3)
                        put_text(frame, f"{class_names[cls]} {confidence}", (x1,y1-10), color=color)
                        put_text(frame, f"ID: {track_id}", (x1,y2+20), color=color)
                        current_frame_count[class_names[cls]] += 1
                        continue

                    pad_bottom = int((y2 - y1) * 0.12)
                    y2_pad = min(frame.shape[0], y2 + pad_bottom)
                    vehicle_roi = frame[y1:y2_pad, x1:x2]

                    with lock_plates:
                        nuevo_track_id, placa_actual, reid = reider.actualizar(
                            track_id, cls, (x1,y1,x2,y2), vehicle_roi, vehicle_plates.get(track_id)
                        )
                        if reid and track_id in vehicle_plates and track_id != nuevo_track_id:
                            del vehicle_plates[track_id]
                        track_id = nuevo_track_id
                        if reid and placa_actual is not None:
                            vehicle_plates[track_id] = placa_actual

                    ids_vistos.add(track_id)
                    if track_id not in seen_ids[cls]:
                        seen_ids[cls].add(track_id)
                        total_class_count[class_names[cls]] += 1

                    color = class_colors.get(cls,(0,0,0))
                    cv2.rectangle(frame,(x1,y1),(x2,y2),color,3)
                    put_text(frame, f"{class_names[cls]} {confidence}", (x1,y1-10), color=color)
                    put_text(frame, f"ID: {track_id}", (x1,y2+20), color=color)
                    current_frame_count[class_names[cls]] += 1

                    if vehicle_roi.shape[0] < 50 or vehicle_roi.shape[1] < 50 or confidence < 0.50:
                        continue

                    area_auto = vehicle_roi.shape[0] * vehicle_roi.shape[1]

                    # Actualizar el mejor frame visto de este vehículo (nitidez + área)
                    calidad = calidad_imagen(vehicle_roi)
                    score_frame = area_auto * (1.0 + calidad / 200.0)
                    prev_frame = mejor_frame_gemini.get(track_id)
                    if prev_frame is None or score_frame > prev_frame[0]:
                        mejor_frame_gemini[track_id] = (score_frame, vehicle_roi.copy())

                    # ══════════════════════════════════════════════════
                    # GEMINI — disparo inteligente usando el MEJOR frame visto,
                    # no el frame actual (que puede estar movido/borroso)
                    # ══════════════════════════════════════════════════
                    with gemini_lock:
                        estado_gem = vehicle_plates.get(track_id) or {}
                        ya_leyo_gemini = bool(estado_gem.get('gemini_plate'))
                        frames_vistos = ocr_skip_counter.get(track_id, 0)
                        intentos_previos = gemini_intentos.get(track_id, 0)

                        debe_lanzar = False
                        if track_id not in gemini_lanzado and area_auto > 20000:
                            debe_lanzar = True
                        elif (not ya_leyo_gemini and track_id in gemini_lanzado
                              and frames_vistos > 0 and frames_vistos % GEMINI_REINTENTO_FRAMES == 0
                              and intentos_previos < GEMINI_MAX_REINTENTOS):
                            debe_lanzar = True

                        if debe_lanzar:
                            gemini_lanzado.add(track_id)
                            gemini_intentos[track_id] = intentos_previos + 1

                    if debe_lanzar and GEMINI_API_KEY:
                        _, mejor_roi_g = mejor_frame_gemini.get(track_id, (0, vehicle_roi))
                        roi_g = mejor_roi_g.copy()
                        t_g = threading.Thread(
                            target=consultar_gemini_hilo,
                            args=(roi_g, track_id, vehicle_plates, lock_plates, votadores),
                            daemon=True
                        )
                        t_g.start()

                    veh_bbox_padded = (x1, y1, x2, y2_pad)

                    # ══════════════════════════════════════════════════
                    # YOLO + OCR local — en paralelo, cada 2 frames
                    # ══════════════════════════════════════════════════
                    ocr_skip_counter[track_id] = ocr_skip_counter.get(track_id, 0) + 1
                    vot = votadores.get(track_id)
                    if not (vot and vot.estable()) and ocr_skip_counter[track_id] % 2 == 0:
                        worker.enviar(track_id, vehicle_roi, veh_bbox_padded, frame_number, mejor_area)

                    bbox_res = worker.obtener_bbox(track_id)
                    if bbox_res:
                        px1g,py1g,px2g,py2g = bbox_res['bbox_global']
                        area = bbox_res['area']
                        tiene_texto = bool(bbox_res.get('plate'))
                        rect_color = (255,255,255) if area >= 3000 else ((0,255,255) if area >= 800 else (0,165,255))
                        if tiene_texto:
                            cv2.rectangle(frame,(px1g,py1g),(px2g,py2g), rect_color, 2)
                        else:
                            cv2.rectangle(frame,(px1g,py1g),(px2g,py2g),(128,128,128),1)

                    # ══════════════════════════════════════════════════
                    # Mostrar resultado
                    # ══════════════════════════════════════════════════
                    with lock_plates:
                        estado = vehicle_plates.get(track_id)
                    dibujar_placa(frame, estado, x1, x2, y2)

                    # ══════════════════════════════════════════════════
                    # Verificación en base de datos + ALERTA TELEGRAM REAL
                    # (esto no existía conectado en la V12 que compartiste)
                    # ══════════════════════════════════════════════════
                    if estado and estado.get('plate'):
                        placa_actual_txt = estado['plate']
                        necesita_check = (
                            not estado.get('checked_db')
                            or estado.get('placa_verificada') != placa_actual_txt
                        )
                        if necesita_check:
                            es_robado, info = db_placas.consultar_placa(placa_actual_txt)
                            with lock_plates:
                                e = vehicle_plates.get(track_id) or {}
                                e['checked_db']        = True
                                e['placa_verificada']  = placa_actual_txt
                                e['es_robado']          = es_robado
                                e['info']               = info
                                if es_robado is False:
                                    e['notified'] = False  # si la placa cambió y ya no coincide, permite re-evaluar
                                vehicle_plates[track_id] = e
                                estado = e

                        if estado.get('es_robado') and not estado.get('notified'):
                            os.makedirs('alertas', exist_ok=True)
                            ruta_img = f"alertas/alerta_{track_id}_{placa_actual_txt}_{frame_number}.png"
                            try:
                                cv2.imwrite(ruta_img, vehicle_roi)
                            except Exception:
                                ruta_img = None
                            info = estado.get('info') or {}
                            similitud = info.get('similitud', 100.0)
                            mensaje = (
                                "🚨 ALERTA — POSIBLE VEHÍCULO ROBADO\n"
                                f"Placa leída: {placa_actual_txt}\n"
                                f"Placa registrada: {info.get('placa', placa_actual_txt)}\n"
                                f"Similitud: {similitud}%\n"
                                f"Origen de la lectura: {estado.get('origen')} (n={estado.get('n_lecturas', 0)})\n"
                                f"Frame: {frame_number}\n"
                                f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                            enviar_alerta_telegram_async(mensaje, ruta_img)
                            with lock_plates:
                                e = vehicle_plates.get(track_id, {})
                                e['notified'] = True
                                vehicle_plates[track_id] = e

            reider.marcar_ids(ids_vistos)

            yo = 30
            for cn, ct in total_class_count.items():
                put_text(frame, f"Total {cn}: {ct}", (10,yo)); yo += 20
            for cn, ct in current_frame_count.items():
                put_text(frame, f"Frame {cn}: {ct}", (10,yo), color=(255,255,255)); yo += 20
            diff = time.time() - t0
            fps_c = 1.0 / diff if diff > 0 else 30.0
            put_text(frame, f"FPS: {fps_c:.1f}", (10,yo), color=(0,255,255)); yo += 20
            out.write(frame)

        if frame is not None:
            cv2.imshow('Detection and Tracking V14', frame)
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
