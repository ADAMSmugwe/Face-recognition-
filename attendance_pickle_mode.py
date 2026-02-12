#!/usr/bin/env python3
"""
Quick Attendance Check - Works with Pickle-Based Encodings

This version works with your existing system that uses:
- images/ folder for student photos  
- encodings/known_faces.pkl for face encodings

Usage:
    python attendance_pickle_mode.py
    
Or use the shell script:
    ./run_quick_test.sh
"""

import cv2
import sys
import pickle
from datetime import datetime, date
from pathlib import Path

try:
    import face_recognition
    import numpy as np
    print("✓ All libraries loaded successfully")
except ImportError as e:
    print(f"Error: Could not import required library: {e}")
    print("Please install: pip install face-recognition opencv-python numpy")
    sys.exit(1)


# Simple attendance tracking (file-based)
ATTENDANCE_FILE = Path("attendance_log.txt")


def load_pickle_encodings():
    """Load encodings from the pickle file used by your dashboard"""
    encodings_file = Path("encodings/known_faces.pkl")
    
    if not encodings_file.exists():
        print(f"❌ Encodings file not found: {encodings_file}")
        print("Please run the dashboard first to generate encodings, or run:")
        print("  python encode_faces.py")
        return [], []
    
    try:
        with open(encodings_file, 'rb') as f:
            data = pickle.load(f)
            encodings = data.get('encodings', [])
            names = data.get('names', [])
            
        print(f"✓ Loaded {len(encodings)} student encodings from {encodings_file}")
        return encodings, names
    
    except Exception as e:
        print(f"❌ Error loading encodings: {e}")
        return [], []


def mark_attendance_to_file(student_name):
    """Mark student attendance in a text file"""
    today = date.today()
    now = datetime.now()
    
    # Check if already marked today
    if ATTENDANCE_FILE.exists():
        with open(ATTENDANCE_FILE, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if today.isoformat() in line and student_name in line:
                    timestamp = line.split('|')[2].strip()
                    print(f"⚠️  {student_name} already marked present today at {timestamp}")
                    return False
    
    # Write new attendance record
    record = f"{today.isoformat()}|{student_name}|{now.strftime('%H:%M:%S')}\n"
    
    with open(ATTENDANCE_FILE, 'a') as f:
        f.write(record)
    
    print(f"✓ ATTENDANCE VERIFIED: {student_name}")
    print(f"  Date: {today}")
    print(f"  Time: {now.strftime('%H:%M:%S')}")
    
    return True


def main():
    """Main function for quick attendance check"""
    print("=" * 60)
    print("QUICK ATTENDANCE CHECK - AUTO-CLOSE MODE")
    print("(Works with pickle-based encodings)")
    print("=" * 60)
    
    # Load student encodings from pickle file
    known_encodings, known_names = load_pickle_encodings()
    
    if not known_encodings:
        print("\n❌ No students found!")
        print("Please add students using the web dashboard first,")
        print("or run: python encode_faces.py")
        return
    
    print(f"\nStudents loaded: {', '.join(set(known_names))}")
    
    # Initialize camera
    print("\nInitializing camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Could not open camera!")
        return
    
    print("✓ Camera opened successfully")
    print("\n" + "=" * 60)
    print("READY - Please look at the camera")
    print("Press 'q' to quit manually")
    print("=" * 60)
    
    # Recognition parameters
    TOLERANCE = 0.6
    CONFIDENCE_THRESHOLD = 70
    FRAMES_REQUIRED = 5
    
    # Tracking variables
    current_person = None
    frame_count = 0
    attendance_verified = False
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Could not read frame from camera")
                break
            
            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if not face_locations:
                # No face detected
                if current_person is not None:
                    frame_count = 0
                    current_person = None
                
                cv2.putText(frame, "No face detected", (10, 30),
                           cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 255), 2)
                cv2.imshow('Attendance Check', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            if face_encodings:
                face_encoding = face_encodings[0]
                top, right, bottom, left = face_locations[0]
                
                # Compare with known faces
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                
                if len(distances) > 0:
                    min_idx = np.argmin(distances)
                    min_distance = distances[min_idx]
                    
                    if min_distance <= TOLERANCE:
                        # Match found
                        name = known_names[min_idx]
                        confidence = (1.0 - min_distance) * 100
                        
                        if confidence >= CONFIDENCE_THRESHOLD:
                            # Check if same person
                            if current_person == name:
                                frame_count += 1
                            else:
                                current_person = name
                                frame_count = 1
                            
                            # Draw green box
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 3)
                            
                            # Display name and confidence
                            text = f"{name} - {confidence:.1f}%"
                            cv2.putText(frame, text, (left, top - 10),
                                       cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 255, 0), 2)
                            
                            # Display progress
                            progress = f"Verifying... {frame_count}/{FRAMES_REQUIRED}"
                            cv2.putText(frame, progress, (10, frame.shape[0] - 20),
                                       cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 255, 255), 2)
                            
                            # Check if verified
                            if frame_count >= FRAMES_REQUIRED:
                                # Mark attendance
                                success = mark_attendance_to_file(name)
                                
                                # Display verification message
                                cv2.rectangle(frame, (0, 0), (frame.shape[1], 100), (0, 255, 0), -1)
                                cv2.putText(frame, "ATTENDANCE VERIFIED!", (50, 60),
                                           cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 3)
                                cv2.imshow('Attendance Check', frame)
                                cv2.waitKey(2000)  # Show for 2 seconds
                                
                                attendance_verified = True
                                break  # ✅ EXIT AFTER VERIFICATION
                        else:
                            # Low confidence
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 165, 255), 2)
                            cv2.putText(frame, f"Low confidence: {confidence:.1f}%", (left, top - 10),
                                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 165, 255), 2)
                            frame_count = 0
                            current_person = None
                    else:
                        # Unknown face
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                        cv2.putText(frame, "Unknown", (left, top - 10),
                                   cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 0, 255), 2)
                        frame_count = 0
                        current_person = None
            
            # Display frame
            cv2.imshow('Attendance Check', frame)
            
            # Check for quit key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n⚠️  Manually quit - no attendance marked")
                break
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    
    finally:
        # Clean up
        cap.release()
        cv2.destroyAllWindows()  # ✅ CLOSE ALL WINDOWS
        
        if attendance_verified:
            print("\n" + "=" * 60)
            print("✓ Session complete - Window closed")
            print("=" * 60)
            print(f"\nAttendance log saved to: {ATTENDANCE_FILE}")
            print("\nView attendance:")
            print(f"  cat {ATTENDANCE_FILE}")
        else:
            print("\n⚠️  No attendance marked")


if __name__ == "__main__":
    main()
