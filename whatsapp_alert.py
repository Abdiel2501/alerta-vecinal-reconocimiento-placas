"""
whatsapp_alert.py — Módulo de alertas por WhatsApp con foto del vehículo.

Modos de operación:
  - SIMULACIÓN (por defecto): Imprime el mensaje en consola y guarda las fotos localmente.
  - REAL (Twilio):            Envía el mensaje y las fotos por WhatsApp cuando config.env
                              está configurado con credenciales válidas de Twilio.

Para el modo real con imágenes, Twilio necesita una URL pública para descargar las fotos.
Opciones:
  1. Configura SERVIDOR_PUBLICO_URL en config.env con tu URL de ngrok (recomendado).
  2. O sube las imágenes a un hosting (Imgur, S3, etc.) y provee la URL.
"""

import os
import threading
from datetime import datetime
from pathlib import Path

# Intentar cargar python-dotenv (opcional)
try:
    from dotenv import load_dotenv
    load_dotenv("config.env")
except ImportError:
    pass

TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM          = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
WHATSAPP_DESTINO     = os.getenv("WHATSAPP_DESTINO", "")
SERVIDOR_PUBLICO_URL = os.getenv("SERVIDOR_PUBLICO_URL", "").rstrip("/")

CARPETA_ALERTAS = Path("alertas")
CARPETA_ALERTAS.mkdir(exist_ok=True)

_modo_real = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and WHATSAPP_DESTINO)

if _modo_real:
    try:
        from twilio.rest import Client as TwilioClient
        _twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("✅ [WhatsApp] Twilio configurado — modo REAL activado.")
    except ImportError:
        print("⚠️ [WhatsApp] twilio no instalado. Ejecuta: pip install twilio")
        _modo_real = False
        _twilio_client = None
else:
    _twilio_client = None
    print("ℹ️ [WhatsApp] Credenciales no configuradas — modo SIMULACIÓN activado.")


def _construir_mensaje(placa_detectada: str, info: dict) -> str:
    """Construye el cuerpo del mensaje de alerta."""
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
        f"🚨 ¡ALERTA DE SEGURIDAD! 🚨\n"
        f"Se detectó un vehículo con reporte de ROBO activo.\n"
        f"\n"
        f"📋 Placa en BD: *{placa_bd}*{coincidencia_str}\n"
        f"🚗 Vehículo: {modelo} — {color}\n"
        f"👤 Propietario: {propietario}\n"
        f"📅 Fecha del reporte: {fecha_reporte}{desc_str}\n"
        f"🕐 Hora de detección: {hora_deteccion}\n"
        f"\n"
        f"⚠️ ¡TENGA MUCHO CUIDADO!\n"
        f"NO confronte al conductor. Llame a las autoridades al *911* de inmediato.\n"
        f"\n"
        f"📸 Se adjuntan imágenes del vehículo y de la placa."
    )


def _enviar_twilio(mensaje: str, rutas_imagenes: list):
    """Envía el mensaje y las imágenes por WhatsApp usando Twilio (hilo separado)."""
    try:
        # Mensaje de texto
        _twilio_client.messages.create(
            from_=TWILIO_FROM,
            to=WHATSAPP_DESTINO,
            body=mensaje
        )

        # Imágenes (solo si hay URL pública configurada)
        if SERVIDOR_PUBLICO_URL:
            for ruta in rutas_imagenes:
                nombre = Path(ruta).name
                url_imagen = f"{SERVIDOR_PUBLICO_URL}/alertas/{nombre}"
                _twilio_client.messages.create(
                    from_=TWILIO_FROM,
                    to=WHATSAPP_DESTINO,
                    media_url=[url_imagen]
                )
            print(f"📲 [WhatsApp] Mensaje + {len(rutas_imagenes)} imagen(es) enviadas correctamente.")
        else:
            print("📲 [WhatsApp] Mensaje de texto enviado. (Configura SERVIDOR_PUBLICO_URL para enviar imágenes)")

    except Exception as e:
        print(f"❌ [WhatsApp] Error al enviar por Twilio: {e}")


def _simular_envio(mensaje: str, rutas_imagenes: list, placa: str):
    """Muestra la alerta en consola cuando no hay credenciales Twilio."""
    linea = "─" * 55
    print(f"\n{linea}")
    print("📱 [SIMULACIÓN WhatsApp] Mensaje que se enviaría:")
    print(linea)
    print(mensaje)
    print(linea)
    for ruta in rutas_imagenes:
        print(f"   📎 Imagen adjunta guardada: {ruta}")
    print(f"{linea}\n")


def guardar_capturas(frame_vehiculo, frame_placa, placa: str) -> tuple:
    """
    Guarda las imágenes del vehículo y la placa en la carpeta de alertas.

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

    print(f"📸 [Captura] Vehículo guardado: {ruta_vehiculo}")
    print(f"📸 [Captura] Placa guardada:    {ruta_placa}")

    return ruta_vehiculo, ruta_placa


def enviar_alerta_whatsapp(placa_detectada: str, info: dict,
                           frame_vehiculo=None, frame_placa=None):
    """
    Punto de entrada principal.
    Guarda las capturas y envía la alerta (real o simulada) en un hilo separado
    para no bloquear el procesamiento de video.

    Args:
        placa_detectada: Texto detectado por el OCR.
        info:            Dict con datos del vehículo de la BD.
        frame_vehiculo:  Imagen numpy del vehículo recortado (BGR).
        frame_placa:     Imagen numpy del recorte de la placa (BGR).
    """
    mensaje = _construir_mensaje(placa_detectada, info)
    rutas_imagenes = []

    # Guardar capturas si se proporcionaron imágenes
    if frame_vehiculo is not None and frame_placa is not None:
        ruta_v, ruta_p = guardar_capturas(frame_vehiculo, frame_placa, placa_detectada)
        rutas_imagenes = [ruta_v, ruta_p]

    # Enviar en hilo separado para no bloquear el loop de video
    if _modo_real and _twilio_client:
        hilo = threading.Thread(
            target=_enviar_twilio,
            args=(mensaje, rutas_imagenes),
            daemon=True
        )
    else:
        hilo = threading.Thread(
            target=_simular_envio,
            args=(mensaje, rutas_imagenes, placa_detectada),
            daemon=True
        )

    hilo.start()
