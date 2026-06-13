"""
alerta_telegram.py — Módulo de alertas por Telegram con fotos directas del vehículo y de la placa.

Modos de operación:
  - SIMULACIÓN (por defecto): Imprime la alerta en consola y guarda las fotos localmente.
  - REAL (Telegram):          Envía el mensaje y las fotos a Telegram cuando config.env
                              tiene un TOKEN y CHAT_ID válidos de Telegram.

No se necesita ngrok ni servidores públicos, las fotos se suben directamente desde el disco.
"""

import os
import requests
import threading
from datetime import datetime
from pathlib import Path
from database import DatabasePlacas

# Intentar cargar python-dotenv para leer las variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv("config.env")
except ImportError:
    pass

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID_ENV = os.getenv("TELEGRAM_CHAT_ID", "")

CARPETA_ALERTAS = Path(os.path.abspath("alertas"))
CARPETA_ALERTAS.mkdir(exist_ok=True, parents=True)

_modo_real = bool(TELEGRAM_TOKEN)

if _modo_real:
    print("[Telegram] Bot configurado — modo REAL de alertas activado.")
else:
    print("[Telegram] Credenciales no configuradas — modo SIMULACIÓN activado.")


def _construir_mensaje(placa_detectada: str, info: dict) -> str:
    """Construye el cuerpo del mensaje de alerta formateado para Telegram."""
    placa_bd        = info.get("placa", placa_detectada)
    modelo          = info.get("modelo", "Desconocido")
    color           = info.get("color", "Desconocido")
    propietario     = info.get("propietario", "Desconocido")
    fecha_reporte   = info.get("fecha_reporte", "N/A")
    descripcion     = info.get("descripcion", "")
    similitud       = info.get("similitud", 100)
    hora_deteccion  = datetime.now().strftime("%H:%M:%S  %d/%m/%Y")

    coincidencia_str = ""
    if placa_detectada != placa_bd:
        coincidencia_str = f"\n🔍 Detectada por OCR: {placa_detectada} ({similitud}% similitud)"

    desc_str = f"\n📝 Nota: {descripcion}" if descripcion else ""

    return (
        f"🚨 *¡ALERTA DE SEGURIDAD!* 🚨\n"
        f"Se detectó un vehículo con reporte de *ROBO* activo.\n"
        f"\n"
        f"📋 Placa en BD: *{placa_bd}*{coincidencia_str}\n"
        f"🚗 Vehículo: {modelo} — {color}\n"
        f"👤 Propietario: {propietario}\n"
        f"📅 Fecha del reporte: {fecha_reporte}{desc_str}\n"
        f"🕐 Hora de detección: {hora_deteccion}\n"
        f"\n"
        f"⚠️ *¡TENGA MUCHO CUIDADO!*\n"
        f"NO confronte al conductor. Llame a las autoridades al *911* de inmediato.\n"
        f"\n"
        f"📸 Se adjuntan imágenes del vehículo y de la placa."
    )


def _enviar_telegram(mensaje: str, rutas_imagenes: list, chat_ids: list):
    """Realiza las peticiones HTTP seguras a la API de Telegram para todos los usuarios activos."""
    try:
        url_texto = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        url_foto = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"

        for chat_id in chat_ids:
            if not chat_id:
                continue

            # 1. Enviar el mensaje de texto formateado en Markdown
            payload = {
                "chat_id": chat_id,
                "text": mensaje,
                "parse_mode": "Markdown"
            }
            res_texto = requests.post(url_texto, data=payload, timeout=10)
            
            if not res_texto.ok:
                print(f"[Telegram] Error al enviar mensaje a {chat_id}: {res_texto.text}")
                continue

            # 2. Enviar las imágenes locales directamente
            for ruta in rutas_imagenes:
                ruta_path = Path(ruta)
                if ruta_path.exists():
                    with open(ruta_path, "rb") as foto:
                        files = {"photo": foto}
                        data = {"chat_id": chat_id}
                        res_foto = requests.post(url_foto, data=data, files=files, timeout=15)
                        if not res_foto.ok:
                            print(f"[Telegram] Error al enviar imagen {ruta_path.name} a {chat_id}: {res_foto.text}")

            print(f"📲 [Telegram] Alerta e imágenes enviadas correctamente a Chat ID {chat_id}.")

    except Exception as e:
        print(f"[Telegram] Excepción al enviar alerta: {e}")


def _simular_envio(mensaje: str, rutas_imagenes: list):
    """Muestra la alerta en consola si no hay credenciales configuradas."""
    linea = "═" * 60
    print(f"\n{linea}")
    print("📱 [SIMULACIÓN Telegram] Mensaje que se enviaría:")
    print(linea)
    print(mensaje)
    print(linea)
    for ruta in rutas_imagenes:
        print(f"   📎 Imagen adjunta guardada localmente: {ruta}")
    print(f"{linea}\n")


def guardar_capturas(frame_vehiculo, frame_placa, placa: str) -> tuple:
    """
    Guarda las imágenes del vehículo y el recorte de la placa en disco.

    Returns:
        (ruta_vehiculo: str, ruta_placa: str)
    """
    import cv2
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    placa_limpia = placa.replace(" ", "_")

    ruta_vehiculo = str(CARPETA_ALERTAS / f"{sello}_placa_{placa_limpia}_vehiculo.jpg")
    ruta_placa    = str(CARPETA_ALERTAS / f"{sello}_placa_{placa_limpia}_recorte.jpg")

    cv2.imwrite(ruta_vehiculo, frame_vehiculo)
    cv2.imwrite(ruta_placa,    frame_placa)

    print(f"[Captura] Vehículo guardado: {ruta_vehiculo}")
    print(f"[Captura] Placa guardada:    {ruta_placa}")

    return ruta_vehiculo, ruta_placa


def enviar_alerta_telegram(placa_detectada: str, info: dict,
                           frame_vehiculo=None, frame_placa=None,
                           rutas_imagenes=None):
    """
    Punto de entrada principal del módulo de alertas.
    Guarda capturas y envía la alerta (real o simulación) de forma no bloqueante.

    Args:
        placa_detectada: Texto leído por el OCR.
        info:            Diccionario con la información de la base de datos.
        frame_vehiculo:  Imagen numpy BGR del vehículo.
        frame_placa:     Imagen numpy BGR del recorte de la placa.
        rutas_imagenes:  Opcional, lista de rutas si las imágenes ya se guardaron.
    """
    mensaje = _construir_mensaje(placa_detectada, info)
    
    if rutas_imagenes is None:
        rutas_imagenes = []
        # Guardar capturas locales si se proporcionaron imágenes
        if frame_vehiculo is not None and frame_placa is not None:
            ruta_v, ruta_p = guardar_capturas(frame_vehiculo, frame_placa, placa_detectada)
            rutas_imagenes = [ruta_v, ruta_p]

    # Obtener IDs de chat de la base de datos
    db = DatabasePlacas()
    chat_ids = db.obtener_chat_ids_activos()
    if TELEGRAM_CHAT_ID_ENV and TELEGRAM_CHAT_ID_ENV not in chat_ids:
        chat_ids.append(TELEGRAM_CHAT_ID_ENV)

    # Si estamos en modo real pero no hay destinatarios, no enviamos
    if _modo_real and not chat_ids:
        print("[Telegram] No hay usuarios de Telegram configurados. No se enviará alerta real.")
        return

    # Ejecutar en segundo plano en un hilo daemon para no congelar el video en tiempo real
    if _modo_real:
        hilo = threading.Thread(
            target=_enviar_telegram,
            args=(mensaje, rutas_imagenes, chat_ids),
            daemon=True
        )
    else:
        hilo = threading.Thread(
            target=_simular_envio,
            args=(mensaje, rutas_imagenes),
            daemon=True
        )

    hilo.start()
