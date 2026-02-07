#!/usr/bin/env python3
"""
Smart Face Recognition with Real-Time Guidance
Gives live feedback: "Move closer", "Too dark", "Perfect!", etc.
"""

import cv2
import numpy as np
import sys
from pathlib import Path

print("=" * 60)
print("🎥 SMART FACE CAPTURE WITH LIVE GUIDANCE")
print("=" * 60)
print("\nThis will give you real-time feedback:")
print("  ✅ 'Perfect! Press SPACE' - Good face detected")
print("  ⚠️  'Move closer' - Face too small")
print("  ⚠️  'Too dark' - Need more light")
print("  ⚠️  'No face detected' - Position yourself")
print("\n" + "=" * 60)

name = "Student"

# Create folders
images_dir = Path("images") / name
images_dir.mkdir(parents=True, exist_ok=True)

print(f"\n📷 Opening webcam...")
print("Press SPACE when it says 'Perfect!' (need 3-5 good photos)")
print("Press 'q' when done\n")

# Load face detector - use face_recognition instead of cascade
import face_recognition as fr

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Could not open webcam!")
    sys.exit(1)

image_count = 0
good_frames = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Make a copy for display
        display_frame = frame.copy()
        height, width = display_frame.shape[:2]
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Check brightness
        brightness = np.mean(gray)
        
        # Detect faces using face_recognition library
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = fr.face_locations(rgb_frame)
        
        # Analyze and give feedback
        feedback = ""
        feedback_color = (0, 0, 255)  # Red by default
        status = "❌"
        
        if brightness < 60:
            feedback = "⚠️  TOO DARK - Turn on lights!"
            feedback_color = (0, 165, 255)  # Orange
            status = "⚠️"
        elif len(face_locations) == 0:
            feedback = "❌ NO FACE DETECTED - Look at camera"
            feedback_color = (0, 0, 255)  # Red
            status = "❌"
        elif len(face_locations) > 1:
            feedback = "⚠️  MULTIPLE FACES - Only one person"
            feedback_color = (0, 165, 255)  # Orange
            status = "⚠️"
        else:
            # One face detected - face_locations returns (top, right, bottom, left)
            top, right, bottom, left = face_locations[0]
            w = right - left
            h = bottom - top
            face_size = w * h
            frame_size = width * height
            face_ratio = face_size / frame_size
            
            # Draw rectangle around face
            cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
            
            # Check face size
            if face_ratio < 0.05:
                feedback = "⚠️  MOVE CLOSER - Face too small"
                feedback_color = (0, 165, 255)  # Orange
                status = "⚠️"
            elif face_ratio > 0.4:
                feedback = "⚠️  MOVE BACK - Face too close"
                feedback_color = (0, 165, 255)  # Orange
                status = "⚠️"
            elif brightness < 80:
                feedback = "⚠️  A BIT DARK - More light would help"
                feedback_color = (0, 200, 255)  # Yellow
                status = "⚠️"
            else:
                feedback = "✅ PERFECT! Press SPACE to capture"
                feedback_color = (0, 255, 0)  # Green
                status = "✅"
                good_frames += 1
        
        # Display feedback - BIG and PROMINENT
        # Background rectangle for better visibility
        cv2.rectangle(display_frame, (10, 10), (width - 10, 120), (0, 0, 0), -1)
        cv2.rectangle(display_frame, (10, 10), (width - 10, 120), feedback_color, 3)
        
        # Status and feedback text
        cv2.putText(display_frame, feedback, (20, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, feedback_color, 3)
        
        # Instructions
        cv2.putText(display_frame, "SPACE: Capture | Q: Done", (20, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show stats at bottom
        cv2.putText(display_frame, f"Images captured: {image_count}", (20, height - 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(display_frame, f"Brightness: {int(brightness)}/255", (20, height - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Show brightness indicator
        indicator_width = int((brightness / 255) * 200)
        cv2.rectangle(display_frame, (20, height - 15), (220, height - 5), (100, 100, 100), -1)
        indicator_color = (0, 255, 0) if brightness > 80 else (0, 165, 255) if brightness > 60 else (0, 0, 255)
        cv2.rectangle(display_frame, (20, height - 15), (20 + indicator_width, height - 5), indicator_color, -1)
        
        cv2.imshow('Smart Face Capture - Follow the guidance!', display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):  # Space
            if status == "✅":
                filename = images_dir / f"{name}_{image_count + 1:03d}.jpg"
                cv2.imwrite(str(filename), frame)
                image_count += 1
                print(f"✅ Captured GOOD image {image_count}")
            else:
                print(f"❌ Can't capture - {feedback}")
        
        elif key == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()

if image_count == 0:
    print("\n⚠️  No images captured!")
    sys.exit(1)

print(f"\n✅ Captured {image_count} images!")

# Now encode with face_recognition
print("\n🔄 Encoding faces with face_recognition...")

try:
    import face_recognition
    import pickle
    
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
                print(f"✅ Encoded: {img_file.name}")
        else:
            print(f"⚠️  Skipped {img_file.name} - No face found")
    
    if not known_encodings:
        print("❌ No faces could be encoded!")
        print("This shouldn't happen if you captured during 'Perfect!' status")
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
    
    print(f"\n✅ Successfully encoded {len(known_encodings)} face(s)!")
    
    # Now run recognition with SMART FEEDBACK
    print("\n" + "=" * 60)
    print("🎥 STARTING SMART FACE RECOGNITION...")
    print("=" * 60)
    print("Real-time guidance will help you get recognized!")
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
            
            display_frame = frame.copy()
            height, width = display_frame.shape[:2]
            
            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            feedback = ""
            feedback_color = (0, 165, 255)
            
            # Check conditions
            if brightness < 60:
                feedback = "⚠️  TOO DARK - Need more light to recognize"
                feedback_color = (0, 165, 255)
            elif len(face_locations) == 0:
                feedback = "❌ NO FACE DETECTED - Look at camera"
                feedback_color = (0, 0, 255)
            else:
                feedback = "🔍 SEARCHING..."
                feedback_color = (255, 255, 0)
            
            # Recognize faces
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                
                if len(distances) > 0:
                    min_idx = distances.argmin()
                    min_distance = distances[min_idx]
                    
                    if min_distance <= 0.6:
                        # RECOGNIZED!
                        recognized_name = known_names[min_idx]
                        confidence = (1.0 - min_distance) * 100
                        recognized_count += 1
                        
                        feedback = f"✅ RECOGNIZED: {recognized_name}!"
                        feedback_color = (0, 255, 0)
                        
                        # Draw GREEN box
                        cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 4)
                        
                        # Name background
                        cv2.rectangle(display_frame, (left, bottom - 50), (right, bottom), 
                                    (0, 255, 0), -1)
                        
                        # Name - BIG
                        cv2.putText(display_frame, recognized_name, (left + 6, bottom - 28),
                                   cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)
                        
                        # Confidence
                        cv2.putText(display_frame, f"{confidence:.1f}%", (left + 6, bottom - 8),
                                   cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)
                        
                    else:
                        # Unknown but face detected
                        feedback = "❌ UNKNOWN PERSON"
                        feedback_color = (0, 0, 255)
                        
                        cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 0, 255), 4)
                        cv2.rectangle(display_frame, (left, bottom - 40), (right, bottom), 
                                    (0, 0, 255), -1)
                        cv2.putText(display_frame, "Unknown", (left + 6, bottom - 12),
                                   cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
            
            # Display feedback - PROMINENT
            cv2.rectangle(display_frame, (10, 10), (width - 10, 100), (0, 0, 0), -1)
            cv2.rectangle(display_frame, (10, 10), (width - 10, 100), feedback_color, 3)
            cv2.putText(display_frame, feedback, (20, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, feedback_color, 3)
            
            # Instructions
            cv2.putText(display_frame, "Press 'Q' to quit", (20, height - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Brightness indicator
            cv2.putText(display_frame, f"Light: {int(brightness)}", (width - 150, height - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow('Smart Recognition - Live Guidance!', display_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    print("\n" + "=" * 60)
    print("✅ SMART FACE RECOGNITION COMPLETE!")
    print("=" * 60)
    if recognized_count > 0:
        print(f"✅ You were recognized {recognized_count} times!")
        print("🎉 The system is working perfectly!")
    else:
        print("⚠️  Not recognized during test")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
