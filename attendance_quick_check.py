#!/usr/bin/env python3
"""
Quick Attendance Check - Auto-Close After Verification

This script:
1. Opens webcam and recognizes faces
2. Logs attendance to SQLAlchemy database when a match is found
3. Automatically closes after successful verification

Usage:
    python attendance_quick_check.py

Controls:
    - Press 'q' to quit manually
    - Automatically closes after attendance verified
"""

import cv2
import sys
import time
from datetime import datetime, date
from pathlib import Path

try:
    import face_recognition
    import numpy as np
    from sqlalchemy.orm import Session
    from database import get_engine, get_session_maker, init_db, Student, AttendancePresent
    print("✓ All libraries loaded successfully")
except ImportError as e:
    print(f"Error: Could not import required library: {e}")
    print("Please install: pip install face-recognition sqlalchemy")
    sys.exit(1)


def load_student_encodings(session: Session):
    """Load all student encodings from database"""
    students = session.query(Student).all()
    
    known_encodings = []
    known_names = []
    known_ids = []
    
    for student in students:
        # Deserialize the encoding from binary
        encoding = np.frombuffer(student.encoding, dtype=student.dtype).reshape(student.length)
        known_encodings.append(encoding)
        known_names.append(student.name)
        known_ids.append(student.id)
    
    print(f"✓ Loaded {len(known_encodings)} student encodings from database")
    return known_encodings, known_names, known_ids


def mark_attendance(session: Session, student_id: int, student_name: str):
    """Mark student as present in the database"""
    today = date.today()
    
    # Check if already marked present today
    existing = session.query(AttendancePresent).filter(
        AttendancePresent.student_id == student_id,
        AttendancePresent.date == today
    ).first()
    
    if existing:
        print(f"⚠️  {student_name} already marked present today at {existing.time.strftime('%H:%M:%S')}")
        return False
    
    # Create new attendance record
    attendance = AttendancePresent(
        student_id=student_id,
        date=today
    )
    
    session.add(attendance)
    session.commit()
    
    print(f"✓ ATTENDANCE VERIFIED: {student_name}")
    print(f"  Date: {today}")
    print(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
    
    return True


def main():
    """Main function for quick attendance check"""
    print("=" * 60)
    print("QUICK ATTENDANCE CHECK - AUTO-CLOSE MODE")
    print("=" * 60)
    
    # Initialize database
    db_url = os.environ.get("DATABASE_URL", "sqlite:///faces.db")
    print(f"\nConnecting to database: {db_url}")
    
    engine = get_engine(db_url)
    init_db(engine)
    SessionMaker = get_session_maker(engine)
    
    # Load student encodings
    with SessionMaker() as session:
        known_encodings, known_names, known_ids = load_student_encodings(session)
    
    if not known_encodings:
        print("\n❌ No students found in database!")
        print("Please register students first.")
        return
    
    # Initialize camera
    print("\nInitializing camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Could not open camera!")
        return
    
    print("✓ Camera opened successfully")
    print("\n" + "=" * 60)
    print("READY - Please look at the camera")
    print("=" * 60)
    
    # Recognition parameters
    TOLERANCE = 0.6  # Face matching tolerance (lower = stricter)
    CONFIDENCE_THRESHOLD = 70  # Minimum confidence % to verify
    FRAMES_REQUIRED = 5  # Number of consecutive frames needed for verification
    
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
            
            # Convert to RGB for face_recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if not face_locations:
                # No face detected - reset counter
                if current_person is not None:
                    frame_count = 0
                    current_person = None
                
                # Display status
                cv2.putText(frame, "No face detected", (10, 30),
                           cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 255), 2)
                cv2.imshow('Attendance Check', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            # Process first face only
            if face_encodings:
                face_encoding = face_encodings[0]
                top, right, bottom, left = face_locations[0]
                
                # Compare with known faces
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                
                if len(distances) > 0:
                    min_idx = np.argmin(distances)
                    min_distance = distances[min_idx]
                    
                    if min_distance <= TOLERANCE:
                        # Match found!
                        name = known_names[min_idx]
                        student_id = known_ids[min_idx]
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
                                # Mark attendance in database
                                with SessionMaker() as session:
                                    success = mark_attendance(session, student_id, name)
                                
                                if success:
                                    # Display verification message
                                    cv2.rectangle(frame, (0, 0), (frame.shape[1], 100), (0, 255, 0), -1)
                                    cv2.putText(frame, "ATTENDANCE VERIFIED!", (50, 60),
                                               cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 3)
                                    cv2.imshow('Attendance Check', frame)
                                    cv2.waitKey(2000)  # Show for 2 seconds
                                    
                                    attendance_verified = True
                                    break  # ✅ EXIT AFTER SUCCESSFUL VERIFICATION
                                else:
                                    # Already marked - show message and continue
                                    cv2.rectangle(frame, (0, 0), (frame.shape[1], 100), (0, 165, 255), -1)
                                    cv2.putText(frame, "Already marked today", (50, 60),
                                               cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)
                                    cv2.imshow('Attendance Check', frame)
                                    cv2.waitKey(2000)
                                    
                                    attendance_verified = True
                                    break  # ✅ EXIT AFTER DUPLICATE CHECK
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
        else:
            print("\n⚠️  No attendance marked")


if __name__ == "__main__":
    import os
    main()
