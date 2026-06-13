"""
bot_listener.py — Demonio en segundo plano para registrar automáticamente usuarios de Telegram.
Escucha el comando /start usando Long Polling.
"""

import os
import time
import requests
from dotenv import load_dotenv
from database import DatabasePlacas

load_dotenv("config.env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

if not TELEGRAM_TOKEN:
    print("❌ Error: TELEGRAM_TOKEN no encontrado en config.env")
    exit(1)

API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def main():
    print("🤖 Iniciando Escucha del Bot de Telegram (Long Polling)...")
    print("Presiona Ctrl+C para detener.")
    
    db = DatabasePlacas()
    offset = None

    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset

            response = requests.get(f"{API_URL}/getUpdates", params=params, timeout=40)
            if not response.ok:
                print(f"⚠️ Error al conectar con Telegram: {response.text}")
                time.sleep(5)
                continue

            data = response.json()
            for update in data.get("result", []):
                offset = update["update_id"] + 1

                if "message" in update and "text" in update["message"]:
                    msg = update["message"]
                    chat_id = str(msg["chat"]["id"])
                    text = msg["text"].strip()
                    
                    if text.startswith("/start"):
                        # Extraer nombre del usuario
                        first_name = msg["chat"].get("first_name", "Usuario")
                        last_name = msg["chat"].get("last_name", "")
                        nombre_completo = f"{first_name} {last_name}".strip()

                        print(f"📥 Nueva solicitud de registro de: {nombre_completo} (ID: {chat_id})")
                        
                        # Registrar en la base de datos
                        if db.agregar_usuario(nombre_completo, chat_id):
                            # Enviar mensaje de bienvenida
                            bienvenida = (
                                f"👋 ¡Hola {first_name}!\n\n"
                                f"✅ *Registro Exitoso*\n"
                                f"Tu cuenta ha sido vinculada al Sistema de Vigilancia de Placas.\n\n"
                                f"A partir de ahora recibirás alertas automáticas cuando se detecte un vehículo con reporte de robo."
                            )
                            requests.post(f"{API_URL}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": bienvenida,
                                "parse_mode": "Markdown"
                            })
                            print(f"✅ Usuario {first_name} registrado y notificado exitosamente.\n")

        except requests.exceptions.RequestException as e:
            print(f"📡 Error de red: {e}. Reintentando en 5 segundos...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo el listener...")
            break
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
