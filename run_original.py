import cv2
import time
import math
import csv
import os
import sys
from collections import defaultdict, Counter
from ultralytics import YOLO
import easyocr

def initialize_model(model_path):
    """Initialize the YOLO model for detection."""
    return YOLO(model_path)

def initialize_reader():
    """Initialize the EasyOCR reader."""
    # Intentar usar GPU si está disponible
    import torch
    usar_gpu = torch.cuda.is_available()
    print(f"⚡ GPU para OCR: {'Sí (CUDA)' if usar_gpu else 'No (CPU)'}")
    return easyocr.Reader(['en'], gpu=usar_gpu)  

def initialize_video_writer(cap, output_video_path):
    """Set up the video writer for the processed video."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    return cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

def write_csv_header(csv_file_path):
    """Prepare CSV file for logging."""
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['frame', 'object_type', 'confidence', 'tracking_id', 'x1', 'y1', 'x2', 'y2',
                         'license_plate_confidence', 'mx1', 'my1', 'mx2', 'my2', 'license_plate_text'])

def put_text(frame, text, position, color=(0, 255, 0), font_scale=0.6, thickness=2, bg_color=(0, 0, 0)):
    """Helper function to put text with background on the frame."""
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    text_x, text_y = position
    box_coords = ((text_x, text_y - text_size[1] - 5), (text_x + text_size[0] + 5, text_y + 5))
    cv2.rectangle(frame, box_coords[0], box_coords[1], bg_color, cv2.FILLED)
    cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def main():
    # Parameters 
    video_path = 0  # Usamos la cámara por defecto (0) para pruebas en vivo
    model_path = 'yolo11n.pt'  # Path to YOLO model
    license_plate_detector_model_path = 'runs/detect/license_plate_detector/weights/best.pt'  # Path to license plate detector model
    
    output_video_path = 'output_video.mp4'  # Path to save the annotated output video
    csv_file_path = 'detection_tracking_log.csv'  # Path to save the CSV log file
    show_video = True  # Set to True to display the video while processing
    classes_to_detect = [0, 1, 2, 3, 5]  # Class IDs to detect (person, bicycle, car, motorbike, bus)
    
    print("🤖 Cargando modelos de IA originales...")
    model = initialize_model(model_path)
    license_plate_detector = YOLO(license_plate_detector_model_path)
    reader = initialize_reader()
    
    # Define class names and colors for display
    class_names = {
        0: "person",
        1: "bicycle",
        2: "car",
        3: "motorbike",
        5: "bus"
    }
    class_colors = {
        0: (255, 255, 255),
        1: (0, 255, 0),
        2: (0, 0, 255),
        3: (255, 255, 0),
        5: (0, 255, 255)
    }
    
    # Dictionary to store the best plate and its confidence for each track_id
    vehicle_plates = {}
    
    # Persistent total count of each class across all frames
    total_class_count = Counter()
    # Track unique IDs for each class to count only once
    seen_ids = defaultdict(set)
    frame_number = 0  # Initialize frame counter
    
    blur_enabled = True # Set to True to blur faces
    paused = False
    
    print("📹 Intentando abrir la cámara...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Error: No se pudo abrir la cámara.")
        sys.exit(1)
        
    out = initialize_video_writer(cap, output_video_path)
    write_csv_header(csv_file_path)
    
    print("🎥 Ejecutando reconocimiento. Presiona ESPACIO para pausar, 'b' para alternar desenfoque, 'ESC' para salir.")
    
    # Loop through each frame
    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ No se pudo leer el fotograma. Saliendo...")
                break
    
            start_time = time.time()
            frame_number += 1
    
            # Run YOLO detection and tracking
            results = model.track(frame, persist=True, classes=classes_to_detect, verbose=False)
            current_frame_count = Counter()
    
            # Process detections
            for result in results:
                boxes = result.boxes
    
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    confidence = round(float(box.conf[0]), 2)
    
                    if box.id is not None:
                        track_id = int(box.id[0].tolist())
                        if track_id not in seen_ids[cls]:
                            seen_ids[cls].add(track_id)
                            total_class_count[class_names[cls]] += 1
    
                        # License plate recognition for cars
                        license_plate_text = ""
                        plate_confidence = None
                        mx1, my1, mx2, my2 = None, None, None, None
    
                        # Check if the detected object is a car, then detect license plate within its bounding box
                        if class_names[cls] in ["car", "motorbike", "bus"]:
                            vehicle_img = frame[y1:y2, x1:x2]  # Crop the vehicle area to search for license plate
                            
                            # Check if the cropped image is large enough for license plate detection
                            min_plate_size = 80
                            if vehicle_img.shape[0] < min_plate_size or vehicle_img.shape[1] < min_plate_size:
                                continue
                            
                            # Check if the confidence is high enough for license plate detection
                            if confidence < 0.7:
                                continue
                            
                            # Run license plate detector model on the cropped vehicle image
                            plate_results = license_plate_detector.predict(vehicle_img, verbose=False)
    
                            # Process license plate detection results
                            if plate_results and len(plate_results[0].boxes) > 0:
                                for plate_box in plate_results[0].boxes:
                                    # Get bounding box coordinates for the license plate, adjusted to the frame's coordinates
                                    px1, py1, px2, py2 = map(int, plate_box.xyxy[0])
                                    px1, py1, px2, py2 = px1 + x1, py1 + y1, px2 + x1, py2 + y1  # Adjust to the car's bounding box position
                                                                
                                    # Draw bounding box for license plate
                                    background_color = (255, 255, 255)  # White background for contrast
                                    cv2.rectangle(frame, (px1, py1), (px2, py2), background_color, 2)
                                        
                                    # Extract the license plate text using OCR
                                    license_plate_roi = frame[py1:py2, px1:px2]
                                    
                                    # Resize based on the plate size
                                    plate_height, plate_width = license_plate_roi.shape[:2]
                                    if plate_height == 0 or plate_width == 0:
                                        continue
                                    scale_factor = 100.0 / plate_height
                                    resized_plate = cv2.resize(
                                        license_plate_roi, None, fx=scale_factor, fy=scale_factor,
                                        interpolation=cv2.INTER_CUBIC)
    
                                    # Convert to grayscale
                                    gray_plate = cv2.cvtColor(resized_plate, cv2.COLOR_BGR2GRAY)
    
                                    # Apply CLAHE
                                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                                    equalized_plate = clahe.apply(gray_plate)
    
                                    # Denoise the image
                                    denoised_plate = cv2.fastNlMeansDenoising(equalized_plate, None, 10, 7, 21)
    
                                    # Adaptive thresholding with adjusted parameters
                                    thresh_plate = cv2.adaptiveThreshold(
                                        denoised_plate, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY_INV, 11, 2)
    
                                    # Morphological operations
                                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                                    morph_plate = cv2.morphologyEx(thresh_plate, cv2.MORPH_CLOSE, kernel)
                                    morph_plate = cv2.morphologyEx(morph_plate, cv2.MORPH_OPEN, kernel)
                                    morph_plate = cv2.bitwise_not(morph_plate)
    
                                    plate_ocr_results = reader.readtext(morph_plate, allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                                    
                                    if plate_ocr_results:
                                        license_plate_text = plate_ocr_results[0][-2]
                                        plate_confidence = round(plate_ocr_results[0][-1], 2)
                                        
                                        # Check if confidence is above threshold
                                        if plate_confidence >= 0.2:
                                            # Update the vehicle_plates dictionary
                                            if (track_id not in vehicle_plates) or (plate_confidence > vehicle_plates[track_id]['confidence']):
                                                vehicle_plates[track_id] = {
                                                    'plate': license_plate_text,
                                                    'confidence': plate_confidence
                                                }
                                                # Save the processed license plate image in /plates folder
                                                os.makedirs('plates', exist_ok=True)
                                                cv2.imwrite(f'plates/{frame_number}_{track_id}_{license_plate_text}.png', morph_plate)
    
                                            # Save coordinates for CSV logging
                                            mx1, my1, mx2, my2 = px1, py1, px2, py2
                                        
                                    assigned_plate = vehicle_plates.get(track_id, None)
                                    if assigned_plate:
                                        # Draw the assigned plate on the frame
                                        background_color = (255, 255, 255)  # White background for contrast
                                        high_contrast_color = (0, 0, 0)  # Black text
                                        put_text(frame, f"Plate: {assigned_plate['plate']}", (x1, y2 + 40), color=high_contrast_color, bg_color=background_color)
    
                                        # Update license_plate_text and plate_confidence for CSV logging
                                        license_plate_text = assigned_plate['plate']
                                        plate_confidence = assigned_plate['confidence']
                                    else:
                                        # If no plate assigned yet, set to empty
                                        license_plate_text = ""
                                        plate_confidence = None
                        
                        # Draw bounding box and label for the detected object
                        color = class_colors.get(cls, (0, 0, 0))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                        put_text(frame, f"{class_names[cls]} {confidence}", (x1, y1 - 10), color=color)
                        put_text(frame, f"ID: {track_id}", (x1, y2 + 20), color=color)
                                        
                        # Anonimización condicional de personas
                        if class_names[cls] == "person" and blur_enabled:
                            person_roi = frame[y1:y2, x1:x2]
                            if person_roi.size > 0:
                                blurred_person = cv2.GaussianBlur(person_roi, (51, 51), 30)
                                frame[y1:y2, x1:x2] = blurred_person
                            
                        # Write to CSV
                        with open(csv_file_path, mode='a', newline='') as file:
                            writer = csv.writer(file)
                            writer.writerow([frame_number, class_names[cls], confidence, track_id, x1, y1, x2, y2,
                                            plate_confidence, mx1, my1, mx2, my2, license_plate_text])
    
                        current_frame_count[class_names[cls]] += 1
    
            # Display counts and FPS
            y_offset = 30
            for cls, count in total_class_count.items():
                put_text(frame, f"Total {cls}: {count}", (10, y_offset))
                y_offset += 20
    
            for cls, count in current_frame_count.items():
                put_text(frame, f"Frame {cls}: {count}", (10, y_offset), color=(255, 255, 255))
                y_offset += 20
    
            fps_calc = 1.0 / (time.time() - start_time)
            put_text(frame, f"FPS: {fps_calc:.2f}", (10, y_offset), color=(255, 255, 255))
    
            # Write frame to output video
            out.write(frame)
    
        # Optionally display the frame
        if show_video:
            cv2.imshow('Detection and Tracking', frame)
            key = cv2.waitKey(1 if not paused else 0) & 0xFF
            if key == 27: # Tecla Esc
                break
            elif key == ord(' '):  # Tecla Espacio
                paused = not paused
            elif key == ord('b'):  # Tecla para alternar desenfoque
                blur_enabled = not blur_enabled  # Cambia el estado de desenfoque
                print(f"Desenfoque {'habilitado' if blur_enabled else 'deshabilitado'}")
            
    # Release resources
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("Procesamiento terminado de forma exitosa.")

if __name__ == "__main__":
    main()
