import os
import requests
from dotenv import load_dotenv

load_dotenv("config.env")

token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print("[System] Enviando mensaje de prueba a tu bot de Telegram...")
print(f"[System] Token: {token[:10]}... (oculto por seguridad)")
print(f"[System] Chat ID: {chat_id}")

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": (
        "🎉 *¡CONEXIÓN EXITOSA!* 🎉\n"
        "\n"
        "Tu Bot de Telegram *AlertaVecinal* ha sido enlazado y configurado correctamente para el sistema de reconocimiento de placas.\n"
        "\n"
        "Ahora, cuando ejecutes `main.py` y detecte un carro robado, recibirás de inmediato el reporte detallado y las **fotos reales** directamente aquí.\n"
        "\n"
        "🤖 _¡Excelente trabajo! Todo listo para funcionar._"
    ),
    "parse_mode": "Markdown"
}

try:
    res = requests.post(url, json=payload, timeout=10)
    resultado = res.json()
    if resultado.get("ok"):
        print("[SUCCESS] Mensaje enviado con éxito! Revisa tu Telegram.")
    else:
        print(f"[ERROR] Error al enviar: {resultado}")
except Exception as e:
    print(f"[EXCEPTION] Excepción al conectar con Telegram: {e}")
