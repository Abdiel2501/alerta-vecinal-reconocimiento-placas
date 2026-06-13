"""Script rápido para detectar qué cámaras están disponibles en la PC."""
import cv2
import json
import sys

available = []
for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap.isOpened():
        available.append(i)
        cap.release()

print(json.dumps(available))
sys.exit(0)
