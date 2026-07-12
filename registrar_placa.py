import sys
import os

# Asegurar que se pueda importar databases
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from databases.database import DatabasePlacas

db = DatabasePlacas()

print("========================================")
print(" 🛡️  REGISTRO DE PLACAS SOSPECHOSAS — ALERTAVECINAL")
print("========================================")
placa = input("Introduce la placa (ej. XYZ1234): ").strip()
if not placa:
    print("❌ La placa no puede estar vacía.")
    sys.exit(1)

modelo = input("Modelo del vehículo: ").strip()
color = input("Color del vehículo: ").strip()
propietario = input("Nombre del propietario: ").strip()
descripcion = input("Detalles del reporte (ej. Robado ayer): ").strip()

exito = db.agregar_placa(
    placa=placa,
    modelo=modelo,
    color=color,
    propietario=propietario,
    descripcion=descripcion
)

if exito:
    print(f"\n🎉 ¡Placa '{placa.upper()}' registrada exitosamente en la base de datos de Alertas!")
    print("Ya puedes mostrar esta placa a la cámara para activar la alarma.")
else:
    print("\n❌ Error al registrar la placa (es posible que ya exista).")
print("========================================")
