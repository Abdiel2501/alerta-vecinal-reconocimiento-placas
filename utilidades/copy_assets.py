import os
import shutil

dist_dir = os.path.join("dist", "MotorIA")
if not os.path.exists(dist_dir):
    print(f"Error: {dist_dir} no existe aún.")
    exit(1)

# Copiar modelo de vehículos
shutil.copy("yolo11n.pt", os.path.join(dist_dir, "yolo11n.pt"))
print("Copiado yolo11n.pt")

# Copiar modelo de placas
os.makedirs(os.path.join(dist_dir, "runs", "detect", "license_plate_detector", "weights"), exist_ok=True)
shutil.copy(
    os.path.join("runs", "detect", "license_plate_detector", "weights", "best.pt"),
    os.path.join(dist_dir, "runs", "detect", "license_plate_detector", "weights", "best.pt")
)
print("Copiado best.pt")

print("Todos los assets copiados al empaquetado de IA.")
