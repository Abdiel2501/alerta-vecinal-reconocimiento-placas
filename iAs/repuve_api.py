# -*- coding: utf-8 -*-
"""
repuve_api.py — Cliente para la API de Información de Vehículos de México (REPUVE) en RapidAPI.
"""

import os
import time
import requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "d025b6a541mshd06eb6ef830e7d7p1249dajsn0244c75332de")
RAPIDAPI_HOST = "informacion-vehiculos-de-mexico.p.rapidapi.com"
USE_REPUVE = os.getenv("USE_REPUVE", "False").lower() in ("true", "1", "yes")

def consultar_repuve(placa: str) -> dict | None:
    """
    Consulta la API de REPUVE en RapidAPI para verificar si el vehículo tiene reporte de robo.
    Retorna un diccionario estructurado si es robado o tiene datos del vehículo, o None si no.
    """
    if not USE_REPUVE or not RAPIDAPI_KEY:
        return None
    
    url_post = f"https://{RAPIDAPI_HOST}/consulta"
    headers = {
        "content-type": "application/json",
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    # Limpiar caracteres especiales de la placa
    placa_clean = ''.join(c for c in placa.upper() if c.isalnum())
    if len(placa_clean) < 5:
        return None
    
    payload = {
        "placas": placa_clean,
        "niv": ""
    }
    
    try:
        print(f"[REPUVE] Solicitando consulta en RapidAPI para la placa: {placa_clean}")
        res = requests.post(url_post, json=payload, headers=headers, timeout=12)
        if res.status_code != 200:
            print(f"[REPUVE] Error al iniciar consulta (Código HTTP {res.status_code}): {res.text}")
            return None
        
        data = res.json()
        query_id = data.get("id")
        if not query_id:
            # A veces la API retorna el resultado directamente si ya existe en caché
            if "result" in data and isinstance(data["result"], dict) and len(data["result"]) > 0:
                return _parsear_resultado_repuve(placa_clean, data["result"])
            print(f"[REPUVE] Respuesta inválida de inicio de consulta: {data}")
            return None
        
        # Polling: Consultar el endpoint GET hasta obtener la información
        url_get = f"https://{RAPIDAPI_HOST}/consulta/{query_id}"
        max_intentos = 6
        for intento in range(max_intentos):
            time.sleep(2.0)  # Esperar 2 segundos para dar tiempo de procesamiento
            print(f"[REPUVE] Consultando estado del ID {query_id} (Intento {intento + 1}/{max_intentos})...")
            res_get = requests.get(url_get, headers=headers, timeout=12)
            if res_get.status_code == 200:
                result_data = res_get.json()
                if "result" in result_data and isinstance(result_data["result"], dict) and len(result_data["result"]) > 0:
                    return _parsear_resultado_repuve(placa_clean, result_data["result"])
        
        print(f"[REPUVE] Excedido el tiempo de espera de consulta para ID {query_id}")
        return None
    except Exception as e:
        print(f"[REPUVE] Error durante la consulta de la placa {placa_clean}: {e}")
        return None

def _parsear_resultado_repuve(placa_clean: str, result: dict) -> dict | None:
    try:
        repuve_status = result.get("repuve", {})
        pgj_status = result.get("pgj", {})
        ocra_status = result.get("ocra", {})
        
        es_robado = False
        origen_robo = ""
        detalles = ""
        
        # Validar en OCRA
        if ocra_status and (ocra_status.get("reporte", {}).get("estatus") == "CON REPORTE DE ROBO" or ocra_status.get("conReporteRoboRecuperacion") == "true"):
            es_robado = True
            origen_robo = "OCRA"
            detalles = f"OCRA: {ocra_status.get('reporte', {}).get('estatus', 'ROBO')}. Fecha: {ocra_status.get('reporteRobo', {}).get('fechaRobo', '')}"
        
        # Validar en PGJ
        elif pgj_status and pgj_status.get("ESTATUS_VHI_ROBO") == "ROBADO":
            es_robado = True
            origen_robo = pgj_status.get("FTE_VHI_ROBO", "PGJ")
            detalles = f"PGJ: ROBADO. Fecha Robo: {pgj_status.get('FECHA_ROBO', '')}"
            
        marca = repuve_status.get("MARCA") or ocra_status.get("vehiculo", {}).get("marca") or "Desconocido"
        modelo = repuve_status.get("MODELO") or ocra_status.get("vehiculo", {}).get("tipoSubmarca") or "Desconocido"
        color = ocra_status.get("vehiculo", {}).get("color") or "Desconocido"
        propietario = repuve_status.get("NOMBRE") or "Desconocido"
        anio = repuve_status.get("ANIO_MODELO") or ocra_status.get("vehiculo", {}).get("modelo") or "Desconocido"
        vin = repuve_status.get("VIN") or ocra_status.get("vehiculo", {}).get("numeroSerie") or ""
        
        return {
            "placa": placa_clean,
            "es_robado": es_robado,
            "origen_repuve": origen_robo,
            "detalles_repuve": detalles,
            "modelo": f"{marca} {modelo} ({anio})".strip(),
            "color": color,
            "propietario": propietario,
            "vin": vin,
            "fecha_reporte": pgj_status.get("FECHA_ROBO") or ocra_status.get("reporteRobo", {}).get("fechaRobo") or ""
        }
    except Exception as e:
        print(f"[REPUVE] Error al parsear resultado: {e}")
        return None
