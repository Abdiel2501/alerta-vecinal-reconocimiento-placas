import cv2
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

capture = None

class CamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('.mjpg') or self.path == '/' or '/stream' in self.path:
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            while True:
                try:
                    rc, img = capture.read()
                    if not rc:
                        time.sleep(0.01)
                        continue
                    # Reducir un poco la resolución para optimizar el ancho de banda del túnel
                    img_resized = cv2.resize(img, (640, 480))
                    _, jpeg = cv2.imencode('.jpg', img_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    img_bytes = jpeg.tobytes()
                    
                    self.wfile.write(b"--jpgboundary\r\n")
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', str(len(img_bytes)))
                    self.end_headers()
                    self.wfile.write(img_bytes)
                    self.wfile.write(b"\r\n")
                    time.sleep(0.05)  # Aprox 20 FPS
                except Exception as e:
                    break

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

def main():
    global capture
    # Intentar abrir la webcam principal
    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        print("❌ Error: No se detectó ninguna webcam conectada a esta laptop.")
        return
        
    server = ThreadedHTTPServer(('0.0.0.0', 8090), CamHandler)
    print("\n========================================================")
    print("🟢 Servidor de Webcam Iniciado Localmente")
    print("Dirección local: http://localhost:8090/stream.mjpg")
    print("========================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando servidor...")
        capture.release()
        server.socket.close()

if __name__ == '__main__':
    main()
