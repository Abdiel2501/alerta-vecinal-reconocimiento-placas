# -*- coding: utf-8 -*-
"""
test_database_telegram.py - Programa de prueba interactivo de base de datos y alertas de Telegram.

Placas con reporte de robo en la base de datos de ejemplo:
- XYZ1234 (Toyota Corolla, Blanco, Propietario: Carlos Mendoza, Reporte: 2025-01-10)
- ABC5678 (Honda Civic, Rojo, Propietario: María Rodríguez, Reporte: 2025-02-20)
- REPORTE12 (Nissan Sentra, Negro, Propietario: Juan García, Reporte: 2025-03-05)
"""

import sys
from database import DatabasePlacas
from alerta_telegram import enviar_alerta_telegram

def main():
    print("=====================================================================")
    print("      TEST DE PLACAS ROBADAS Y ALERTAS TELEGRAM")
    print("=====================================================================")
    
    # Inicializar la base de datos
    db = DatabasePlacas()
    
    # Mostrar las placas con reporte en la BD actual
    print("\n[DB] Placas actualmente registradas con reporte de robo:")
    placas_list = db.listar_placas(solo_activas=True)
    for p in placas_list:
        print(f"  * Placa: {p['placa']} | {p['modelo']} ({p['color']}) | Reporto: {p['propietario']}")
    
    print("\n---------------------------------------------------------------------")
    # Forzar codificacion utf-8 para entrada/salida si es necesario, o evitar acentos en el prompt
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
        
        print("\nEnviando alerta por Telegram (simulacion o real segun tu config.env)...")
        # Registrar alerta en el historial
        db.registrar_alerta(
            placa_bd=info['placa'],
            placa_detectada=placa_ingresada,
            similitud=info['similitud']
        )
        # Enviar la alerta de Telegram
        enviar_alerta_telegram(placa_detectada=placa_ingresada, info=info)
        print("Alerta enviada/simulada correctamente.")
    else:
        print(f"\nLa placa '{placa_ingresada}' NO coincide con ninguna placa robada activa.")

if __name__ == "__main__":
    main()
