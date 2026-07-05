import os
import torch
from ultralytics import YOLO

def main():
    # 1. Definir rutas del dataset
    # Asegúrate de que la carpeta 'VLP' y el archivo 'VLP/data.yaml' existan
    dataset_yaml = r"D:\License Plate.yolov8\data.yaml"
    
    if not os.path.exists(dataset_yaml):
        print(f"❌ Error: No se encontró el archivo de configuración en {dataset_yaml}")
        print("Asegúrate de haber extraído el dataset 'VLP.v2i.yolov11.zip' en la raíz.")
        return

    # 2. Seleccionar dispositivo (GPU CUDA si está disponible, de lo contrario CPU)
    dispositivo = "0" if torch.cuda.is_available() else "cpu"
    print(f"🖥️  Entrenamiento configurado en: {'GPU (CUDA:0)' if dispositivo == '0' else 'CPU'}")

    # 3. Cargar el modelo base preentrenado de YOLOv11
    # Usamos 'yolo11n.pt' (modelo nano) por velocidad y bajo consumo de memoria.
    print("🤖 Cargando modelo base YOLOv11...")
    model = YOLO("yolo11n.pt")

    # 4. Configurar e iniciar el entrenamiento
    print("🚀 Iniciando el entrenamiento del detector de placas...")
    model.train(
        data=dataset_yaml,       # Ruta al data.yaml del dataset
        epochs=50,               # Número de épocas a entrenar (ajustable)
        imgsz=640,               # Tamaño de imagen de entrada (estándar para YOLO)
        batch=8,                 # Tamaño del lote (reducir a 4 u 8 si te da error de memoria en GPU)
        device=dispositivo,      # GPU o CPU
        workers=2,               # Hilos para cargar imágenes
        name="detector_placas",  # Nombre de la carpeta de salida
        exist_ok=True            # Sobrescribir carpeta si ya existe
    )

    print("\n✅ ¡Entrenamiento completado!")
    print("Los resultados y el modelo entrenado ('best.pt') se guardaron en la carpeta:")
    print("📂 runs/detect/detector_placas/weights/best.pt")

if __name__ == "__main__":
    main()
