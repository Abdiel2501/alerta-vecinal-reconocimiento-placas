# -*- coding: utf-8 -*-
"""
test_database_telegram.py - Programa de prueba interactivo y autocontenido.
Testea la base de datos y la conexion directa con el Bot de Telegram.

Placas con reporte de robo en la base de datos de ejemplo:
- XYZ1234 (Toyota Corolla, Blanco, Propietario: Carlos Mendoza, Reporte: 2025-01-10)
- ABC5678 (Honda Civic, Rojo, Propietario: Maria Rodriguez, Reporte: 2025-02-20)
- REPORTE12 (Nissan Sentra, Negro, Propietario: Juan Garcia, Reporte: 2025-03-05)
"""

import os
import requests
from datetime import datetime
from database import DatabasePlacas

# Cargar variables desde config.env de manera segura sin dependencias externas obligatorias
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""

if os.path.exists("config.env"):
    with open("config.env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("TELEGRAM_TOKEN="):
                TELEGRAM_TOKEN = line.split("=", 1)[1].strip()
            elif line.startswith("TELEGRAM_CHAT_ID="):
                TELEGRAM_CHAT_ID = line.split("=", 1)[1].strip()

# Si no se leyeron del archivo, intentar obtenerlas de las variables de entorno
if not TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def enviar_mensaje_telegram(mensaje: str):
    """Envia un mensaje de texto formateado en Markdown a Telegram usando las credenciales locales."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Simulación: No se configuraron credenciales reales (Token o Chat ID).")
        print("Mensaje que se habria enviado:\n", mensaje)
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    
    try:
        res = requests.post(url, data=payload, timeout=10)
        if res.ok:
            print(f"[SUCCESS] [Telegram] Mensaje enviado exitosamente al Chat ID: {TELEGRAM_CHAT_ID}")
            return True
        else:
            print(f"[ERROR] [Telegram] Error al enviar mensaje: {res.text}")
            return False
    except Exception as e:
        print(f"[ERROR] [Telegram] Error de conexion: {e}")
        return False


def construir_mensaje_alerta(placa_detectada: str, info: dict) -> str:
    """Construye el cuerpo del mensaje de alerta de prueba."""
    placa_bd = info.get("placa", placa_detectada)
    modelo = info.get("modelo", "Desconocido")
    color = info.get("color", "Desconocido")
    propietario = info.get("propietario", "Desconocido")
    fecha_reporte = info.get("fecha_reporte", "N/A")
    descripcion = info.get("descripcion", "")
    similitud = info.get("similitud", 100)
    hora_deteccion = datetime.now().strftime("%H:%M:%S  %d/%m/%Y")

    coincidencia_str = ""
    if placa_detectada != placa_bd:
        coincidencia_str = f"\n🔍 Detectada por OCR: {placa_detectada} ({similitud}% similitud)"

    desc_str = f"\n📝 Nota: {descripcion}" if descripcion else ""

    return (
        f"🚨 *¡PRUEBA DE ALERTA DE SEGURIDAD!* 🚨\n"
        f"Se detectó un vehículo con reporte de *ROBO* activo.\n"
        f"\n"
        f"📋 Placa en BD: *{placa_bd}*{coincidencia_str}\n"
        f"🚗 Vehículo: {modelo} — {color}\n"
        f"👤 Propietario: {propietario}\n"
        f"📅 Fecha del reporte: {fecha_reporte}{desc_str}\n"
        f"🕐 Hora de detección: {hora_deteccion}\n"
        f"\n"
        f"⚠️ *¡TENGA MUCHO CUIDADO!*\n"
        f"NO confronte al conductor. Llame a las autoridades al *911* de inmediato."
    )


def main():
    print("=====================================================================")
    print("      TEST AUTOCONTENIDO DE BASE DE DATOS Y BOT DE TELEGRAM")
    print("=====================================================================")
    
    # Validar credenciales cargadas
    if TELEGRAM_TOKEN:
        print(f"Bot de Telegram detectado (Token: {TELEGRAM_TOKEN[:10]}...)")
        print(f"ID de Chat Destino: {TELEGRAM_CHAT_ID}")
    else:
        print("⚠️ Advertencia: No se detecto TELEGRAM_TOKEN en config.env. Modo simulacion activo.")
    
    # Inicializar la base de datos
    db = DatabasePlacas()
    
    # Mostrar las placas con reporte en la BD actual
    print("\n[DB] Placas actualmente registradas con reporte de robo:")
    placas_list = db.listar_placas(solo_activas=True)
    for p in placas_list:
        print(f"  * Placa: {p['placa']} | {p['modelo']} ({p['color']}) | Reporto: {p['propietario']}")
    
    print("\n---------------------------------------------------------------------")
    try:
        placa_ingresada = input("Ingresa la placa que deseas probar: ").strip().upper()
    except Exception:
        print("Error al leer la entrada.")
        return
    
    if not placa_ingresada:
        print("Error: Debes ingresar una placa valida.")
        return

    print(f"\nConsultando placa '{placa_ingresada}' en la base de datos (con busqueda difusa)...")
    es_robado, info = db.consultar_placa(placa_ingresada)
    
    if es_robado and info:
        print("\n*** COINCIDENCIA ENCONTRADA! VEHICULO DETECTADO COMO ROBADO ***")
        print(f"  * Placa en BD:   {info['placa']}")
        print(f"  * Similitud:     {info['similitud']}%")
        print(f"  * Vehiculo:      {info['modelo']} -- {info['color']}")
        print(f"  * Propietario:   {info['propietario']}")
        print(f"  * Fecha Reporte: {info['fecha_reporte']}")
        print(f"  * Descripcion:   {info['descripcion']}")
        
        # Registrar alerta en el historial
        db.registrar_alerta(
            placa_bd=info['placa'],
            placa_detectada=placa_ingresada,
            similitud=info['similitud']
        )
        
        # Enviar mensaje a Telegram
        print("\n[Telegram] Generando alerta y enviando mensaje al Bot...")
        mensaje = construir_mensaje_alerta(placa_ingresada, info)
        enviar_mensaje_telegram(mensaje)
    else:
        print(f"\nLa placa '{placa_ingresada}' NO coincide con ninguna placa robada activa.")

if __name__ == "__main__":
    main()
