#!/usr/bin/env python3
"""
Enhanced Face Recognition with Name Display
Shows names prominently when people are recognized
"""

import cv2
import pickle
import sys
from pathlib import Path

try:
    import face_recognition
except ImportError:
    print("❌ face_recognition not installed!")
    sys.exit(1)

print("=" * 60)
print("🎥 ENHANCED FACE RECOGNITION")
print("=" * 60)

# Load encodings
encodings_file = Path("encodings/known_faces.pkl")
if not encodings_file.exists():
    print("❌ No encodings found!")
    print("Run auto_test.py first to add students.")
    sys.exit(1)

with open(encodings_file, 'rb') as f:
    data = pickle.load(f)

known_encodings = data.get('encodings', [])
known_names = data.get('names', [])

print(f"✅ Loaded {len(known_encodings)} face encoding(s)")
print(f"📋 Students: {', '.join(set(known_names))}")
print("\n" + "=" * 60)
print("Press 'q' to quit")
print("=" * 60 + "\n")

# Open webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Could not open webcam!")
    sys.exit(1)

# For tracking recognized people
recognized_people = set()

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Make a copy for drawing
        display_frame = frame.copy()
        
        # Convert to RGB for face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        current_frame_people = []
        
        # Process each face
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            if len(known_encodings) > 0:
                # Compare with known faces
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                min_idx = distances.argmin()
                min_distance = distances[min_idx]
                
                if min_distance <= 0.6:  # Recognized
                    name = known_names[min_idx]
                    confidence = (1.0 - min_distance) * 100
                    
                    recognized_people.add(name)
                    current_frame_people.append(name)
                    
                    # Draw GREEN box for recognized
                    cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
                    
                    # Draw name background (larger)
                    cv2.rectangle(display_frame, (left, bottom - 45), (right, bottom), 
                                (0, 255, 0), cv2.FILLED)
                    
                    # Draw name (BIGGER)
                    text = f"{name}"
                    cv2.putText(display_frame, text, (left + 6, bottom - 25),
                               cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
                    
                    # Draw confidence
                    conf_text = f"{confidence:.1f}%"
                    cv2.putText(display_frame, conf_text, (left + 6, bottom - 8),
                               cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
                    
                    # BIG name at top of screen
                    cv2.putText(display_frame, f"RECOGNIZED: {name}!", (50, 80),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 4)
                    
                else:  # Unknown
                    name = "Unknown"
                    current_frame_people.append(name)
                    
                    # Draw RED box
                    cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 0, 255), 3)
                    cv2.rectangle(display_frame, (left, bottom - 35), (right, bottom), 
                                (0, 0, 255), cv2.FILLED)
                    cv2.putText(display_frame, name, (left + 6, bottom - 10),
                               cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
        
        # Show instructions
        cv2.putText(display_frame, "Press 'Q' to quit", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show list of all people recognized in this session (on the side)
        if recognized_people:
            y_pos = display_frame.shape[0] - 100
            cv2.putText(display_frame, "Recognized Today:", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            for idx, person in enumerate(sorted(recognized_people), 1):
                y_pos += 30
                cv2.putText(display_frame, f"{idx}. {person}", (10, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Display
        cv2.imshow('Face Recognition - Names Displayed', display_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "=" * 60)
    print("✅ Face Recognition Ended")
    if recognized_people:
        print(f"📋 People recognized: {', '.join(sorted(recognized_people))}")
    else:
        print("📋 No one was recognized")
    print("=" * 60)
