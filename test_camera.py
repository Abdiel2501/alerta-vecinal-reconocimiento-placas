import cv2
import sys

def main():
    print("Iniciando prueba de cámara...")
    
    # Intentar abrir la cámara por defecto (0)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara.")
        sys.exit(1)
        
    print("Cámara abierta correctamente. Presiona 'q' o 'ESC' en la ventana del video para salir.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: No se pudo recibir frame de la cámara. Saliendo...")
            break
            
        cv2.imshow('Prueba de Camara - Antigravity', frame)
        
        # Esperar tecla 'q' o ESC para salir
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("Prueba finalizada.")

if __name__ == "__main__":
    main()
