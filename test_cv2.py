import cv2
import sys
import time

print("Testing OpenCV VideoCapture...")

for backend_name, backend in [("CAP_DSHOW", cv2.CAP_DSHOW), ("CAP_MSMF", cv2.CAP_MSMF), ("DEFAULT", None)]:
    print(f"\n--- Trying backend: {backend_name} ---")
    try:
        if backend is not None:
            cap = cv2.VideoCapture(0, backend)
        else:
            cap = cv2.VideoCapture(0)
            
        print("Created VideoCapture object.")
        
        start_time = time.time()
        is_opened = cap.isOpened()
        print(f"cap.isOpened() returned: {is_opened} (took {time.time() - start_time:.2f}s)")
        
        if is_opened:
            print("Reading frame...")
            start_time = time.time()
            ret, frame = cap.read()
            print(f"cap.read() returned: {ret} (took {time.time() - start_time:.2f}s)")
            if ret:
                print(f"Frame shape: {frame.shape}")
                cv2.imwrite("test_backend_frame.jpg", frame)
                print("Saved test_backend_frame.jpg successfully!")
            cap.release()
            print("Released cap.")
        else:
            cap.release()
    except Exception as e:
        print(f"Exception: {e}")

print("\nFinished tests.")
