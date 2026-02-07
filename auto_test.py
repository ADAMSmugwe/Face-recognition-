#!/usr/bin/env python3
"""
Auto Face Recognition Test - No typing needed!
Just look at the camera and press SPACE to capture, then 'q' to continue
"""

import os
import sys
import cv2
import pickle
from pathlib import Path

# Auto name - no input needed!
name = "Student"

print("=" * 60)
print("🎥 FACE RECOGNITION - AUTO TEST")
print("=" * 60)
print(f"\nStudent name: {name}")
print("\nThis will:")
print("1. Capture your face using webcam (press SPACE 3-5 times)")
print("2. Encode it")
print("3. Run face recognition to recognize you!")
print("\n" + "=" * 60)

# Create folders
images_dir = Path("images") / name
images_dir.mkdir(parents=True, exist_ok=True)

print(f"\n📷 Opening webcam to capture {name}...")
print("Instructions:")
print("  - Press SPACE to capture (take 3-5 photos)")
print("  - Press 'q' when done")

# Capture images
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Could not open webcam!")
    sys.exit(1)

image_count = 0
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Display
        cv2.putText(frame, f"Capturing for: {name}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Images: {image_count}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "SPACE: Capture | Q: Done", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow('Capture Your Face - Press SPACE', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):  # Space
            filename = images_dir / f"{name}_{image_count + 1:03d}.jpg"
            cv2.imwrite(str(filename), frame)
            image_count += 1
            print(f"✓ Captured image {image_count}")
        
        elif key == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()

if image_count == 0:
    print("\n⚠️  No images captured! Please run again and press SPACE to capture.")
    sys.exit(1)

print(f"\n✅ Captured {image_count} images!")

# Now encode
print("\n🔄 Encoding face...")

try:
    import face_recognition
    
    known_encodings = []
    known_names = []
    
    for img_file in images_dir.glob("*.jpg"):
        image = face_recognition.load_image_file(str(img_file))
        face_locations = face_recognition.face_locations(image)
        
        if len(face_locations) > 0:
            face_encodings = face_recognition.face_encodings(image, face_locations)
            if len(face_encodings) > 0:
                known_encodings.append(face_encodings[0])
                known_names.append(name)
                print(f"✓ Encoded: {img_file.name}")
    
    if not known_encodings:
        print("❌ No faces found in images!")
        sys.exit(1)
    
    # Save encodings
    encodings_dir = Path("encodings")
    encodings_dir.mkdir(exist_ok=True)
    
    data = {
        'encodings': known_encodings,
        'names': known_names,
        'num_faces': len(known_names)
    }
    
    with open(encodings_dir / "known_faces.pkl", 'wb') as f:
        pickle.dump(data, f)
    
    print(f"\n✅ Encoded {len(known_encodings)} face(s)!")
    
    # Now run recognition
    print("\n" + "=" * 60)
    print("🎥 STARTING FACE RECOGNITION...")
    print("=" * 60)
    print("Look at the camera - you should see 'Student' appear!")
    print("Press 'q' to quit")
    print("=" * 60 + "\n")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open webcam!")
        sys.exit(1)
    
    recognized_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Find faces
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            # Recognize
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                
                if len(distances) > 0:
                    min_idx = distances.argmin()
                    min_distance = distances[min_idx]
                    
                    if min_distance <= 0.6:
                        recognized_name = known_names[min_idx]
                        confidence = 1.0 - min_distance
                        recognized_count += 1
                        
                        # Draw box (GREEN for recognized)
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 3)
                        
                        # Draw name
                        text = f"{recognized_name} ({confidence:.2f})"
                        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
                        cv2.putText(frame, text, (left + 6, bottom - 6),
                                   cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
                        
                        # Success message
                        if recognized_count == 1:
                            cv2.putText(frame, "SUCCESS! Face Recognized!", (10, 120),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
                    else:
                        # Unknown (RED box)
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 3)
                        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                        cv2.putText(frame, "Unknown", (left + 6, bottom - 6),
                                   cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
            
            # Show instructions
            cv2.putText(frame, "Press 'q' to quit", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('Face Recognition - WORKING! Press Q to quit', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    print("\n" + "=" * 60)
    print("✅ FACE RECOGNITION TEST COMPLETE!")
    print("=" * 60)
    if recognized_count > 0:
        print(f"✅ Your face was recognized {recognized_count} times!")
        print("🎉 The system is working perfectly!")
    else:
        print("⚠️  Face was captured but not recognized during test.")
        print("   This might happen if you moved away from camera.")
    print("\nYou can now use manage_students.py to:")
    print("  - Add more students with custom names")
    print("  - Delete students")
    print("  - Rename students")
    print("  - Run recognition anytime")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
