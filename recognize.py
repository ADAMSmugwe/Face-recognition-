#!/usr/bin/env python3
"""
Real-time Face Recognition using webcam
"""

import os
import cv2
import face_recognition
import numpy as np
import sys
import time
import argparse
from db import FaceDatabase
from database import (
    get_engine,
    init_db,
    get_session_maker,
    FaceRepository,
    StudentRepository,
    AttendanceRepository,
    AttendancePresentRepository,
    StudentSampleRepository,
)
from utils import (
    load_encodings,
    draw_face_box,
    load_config,
    save_encodings,
    get_face_encodings_with_locations,
    get_mask_aware_encodings_with_locations,
)


def parse_args(config) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Real-time face recognition from webcam or video source"
    )
    recog_cfg = (config or {}).get("recognizer", {}) if isinstance(config, dict) else {}
    parser.add_argument(
        "--encodings",
        "-e",
        default=recog_cfg.get("encodings_file", "encodings/face_encodings.pkl"),
        help="Path to encodings pickle file",
    )
    parser.add_argument(
        "--camera",
        "-c",
        type=int,
        default=int(recog_cfg.get("camera_index", 0)),
        help="Camera index (0,1,2...)",
    )
    parser.add_argument(
        "--tolerance",
        "-t",
        type=float,
        default=float(recog_cfg.get("tolerance", 0.6)),
        help="Recognition tolerance (lower=more strict)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=recog_cfg.get("model", "hog"),
        choices=["hog", "cnn"],
        help="Face detection model (hog=CPU, cnn=GPU)",
    )
    parser.add_argument(
        "--outputs-dir",
        default=recog_cfg.get("outputs_dir", "outputs/screenshots"),
        help="Directory to save screenshots",
    )
    parser.add_argument(
        "--align",
        action="store_true",
        help="Align faces using landmarks before encoding for better accuracy",
    )
    parser.add_argument(
        "--align-size",
        type=int,
        default=int((recog_cfg.get("align_size") if isinstance(recog_cfg, dict) else 160) or 160),
        help="Aligned face chip size (pixels)",
    )
    parser.add_argument(
        "--mask-aware",
        action="store_true",
        help="Use mask-aware matching (tries masked encodings for occluded faces)",
    )
    parser.add_argument(
        "--mask-ratio",
        type=float,
        default=float((recog_cfg.get("mask_ratio") if isinstance(recog_cfg, dict) else 0.45) or 0.45),
        help="Lower-face coverage ratio for simulated masks (0.35–0.5 typical)",
    )
    # DB is now the default storage
    parser.add_argument(
        "--db-url",
        default=(recog_cfg.get("db_url") if isinstance(recog_cfg, dict) else None) or "sqlite:///data/faces.db",
        help="SQLAlchemy DB URL (e.g., postgresql+psycopg2://user:pass@host/db)",
    )
    parser.add_argument(
        "--refresh-interval",
        type=float,
        default=float((recog_cfg.get("refresh_interval") if isinstance(recog_cfg, dict) else 5.0) or 5.0),
        help="Seconds between auto-refresh of encodings (0 to disable)",
    )
    parser.add_argument(
        "--attendance-mode",
        action="store_true",
        help="Enable class attendance: match against students and mark present",
    )
    # Default to attendance mode enabled
    parser.set_defaults(attendance_mode=True)
    parser.add_argument(
        "--no-attendance-mode",
        dest="attendance_mode",
        action="store_false",
        help="Disable attendance mode (revert to faces table)",
    )
    return parser.parse_args()


def main():
    config = load_config()
    args = parse_args(config)
    encodings_file = args.encodings
    
    print("Face Recognition System - Real-time Recognition")
    print("=" * 50)
    
    # Load known faces
    print("Loading known face encodings...")
    engine = get_engine(args.db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    if args.attendance_mode:
        student_repo = StudentRepository(Session)
        attendance_repo = AttendanceRepository(Session)
        attendance_present_repo = AttendancePresentRepository(Session)
        student_encs, student_meta = student_repo.get_all_encodings()
        # names array will be student names, and we track mapping by index
        known_encodings = student_encs
        known_names = [meta[2] for meta in student_meta]
        print(f"Loaded {len(known_encodings)} student encodings from DB: {args.db_url}")
    else:
        repo = FaceRepository(Session)
        known_encodings, known_names = repo.get_all_faces()
        print(f"Loaded {len(known_encodings)} encodings from DB: {args.db_url}")
    
    # Initialize camera
    print("Initializing camera...")
    video_capture = cv2.VideoCapture(args.camera)
    
    if not video_capture.isOpened():
        print("Error: Could not open camera")
        return False
        
    print("Camera initialized successfully!")
    print("\nControls:")
    print("  'q' or ESC - Quit")
    print("  's' - Save screenshot")
    print("  'a' - Add/enroll a new person")
    print("=" * 50)
    
    # Performance tracking
    frame_count = 0
    start_time = time.time()
    process_this_frame = True
    last_refresh_time = 0.0
    
    # Initialize state for frames processed/ignored
    scaled_face_locations = []
    face_names = []

    # Enrollment mode state
    enroll_mode = False
    typed_name = ""
    enrollment_encodings = []
    enrollment_samples_needed = 5
    last_enroll_time = 0.0

    try:
        while True:
            # Read frame
            ret, frame = video_capture.read()
            if not ret:
                print("Error: Could not read frame")
                break
            
            # Periodically refresh encodings from source
            if args.refresh_interval and (time.time() - last_refresh_time) >= args.refresh_interval:
                try:
                    if args.attendance_mode:
                        student_repo = StudentRepository(Session)
                        student_encs, student_meta = student_repo.get_all_encodings()
                        known_encodings = student_encs
                        known_names = [meta[2] for meta in student_meta]
                    else:
                        repo = FaceRepository(Session)
                        known_encodings, known_names = repo.get_all_faces()
                    last_refresh_time = time.time()
                except Exception:
                    # Ignore refresh errors; continue with existing encodings
                    last_refresh_time = time.time()

            # Process every other frame for better performance
            if process_this_frame:
                # Resize frame for faster processing
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                # Find faces
                face_locations = face_recognition.face_locations(rgb_small_frame, model=args.model)
                
                face_names = []
                if getattr(args, "mask_aware", False):
                    enc_pairs = get_mask_aware_encodings_with_locations(
                        rgb_small_frame,
                        face_locations,
                        align=True if args.align else False,
                        align_size=args.align_size,
                        mask_ratio=getattr(args, "mask_ratio", 0.45),
                    )
                    for normal_enc, masked_enc in enc_pairs:
                        candidate_encs = [e for e in (normal_enc, masked_enc) if e is not None]
                        if not candidate_encs:
                            face_names.append(("Unknown", 0.0))
                            continue
                        name = "Unknown"
                        confidence = 0.0
                        if len(known_encodings) > 0:
                            best_name = "Unknown"
                            best_conf = 0.0
                            for enc in candidate_encs:
                                dists = face_recognition.face_distance(known_encodings, enc)
                                if dists.size == 0:
                                    continue
                                idx = int(np.argmin(dists))
                                if dists[idx] <= args.tolerance:
                                    conf = 1.0 - float(dists[idx])
                                    if conf > best_conf:
                                        best_conf = conf
                                        best_name = known_names[idx]
                            name, confidence = best_name, best_conf
                        face_names.append((name, confidence))
                else:
                    face_encodings = get_face_encodings_with_locations(
                        rgb_small_frame, face_locations, align=args.align, align_size=args.align_size
                    )
                    for face_encoding in face_encodings:
                        # Compare with known faces if available
                        if len(known_encodings) == 0:
                            name = "Unknown"
                            confidence = 0.0
                        else:
                            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                            if face_distances.size == 0:
                                name = "Unknown"
                                confidence = 0.0
                            else:
                                best_match_index = np.argmin(face_distances)
                                if face_distances[best_match_index] <= args.tolerance:
                                    name = known_names[best_match_index]
                                    confidence = 1 - face_distances[best_match_index]
                                else:
                                    name = "Unknown"
                                    confidence = 0.0
                        
                        face_names.append((name, confidence))
                
                # Scale back up face locations
                scaled_face_locations = []
                for (top, right, bottom, left) in face_locations:
                    scaled_face_locations.append((top * 4, right * 4, bottom * 4, left * 4))
                    
            process_this_frame = not process_this_frame
            
            # Draw results
            for (top, right, bottom, left), (name, confidence) in zip(scaled_face_locations, face_names):
                frame = draw_face_box(frame, (top, right, bottom, left), name, confidence)
                if args.attendance_mode and name != "Unknown":
                    # Mark present once per student per day
                    try:
                        from datetime import date as date_cls
                        # Find student_db_id by name mapping
                        # Reload mapping snapshot to keep it simple
                        student_repo = StudentRepository(Session)
                        _, student_meta = student_repo.get_all_encodings()
                        # meta: (id, student_id, name)
                        student_db_id = None
                        for sid, student_id_code, student_name in student_meta:
                            if student_name == name:
                                student_db_id = sid
                                break
                        if student_db_id is not None:
                            if not attendance_present_repo.has_marked_today(student_db_id, date_cls.today()):
                                attendance_present_repo.mark_present(student_db_id, date_cls.today())
                                cv2.putText(frame, "Marked Present", (left, min(bottom + 30, frame.shape[0]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            # Store high-confidence sample for continuous learning
                            try:
                                if confidence and confidence >= 0.65:
                                    sample_repo = StudentSampleRepository(Session)
                                    # Use the encoding that matched (first encoding corresponds to current face)
                                    # We approximate by taking the closest encoding among current frame's encodings
                                    sample_repo.add_sample(student_db_id, face_encoding, confidence=float(confidence), source="recognize")
                            except Exception:
                                pass
                    except Exception:
                        pass
            
            # Calculate and display FPS
            frame_count += 1
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                fps = frame_count / elapsed_time
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # HUD overlays
            if enroll_mode:
                status_text = f"Enroll: type name -> {typed_name}_  ({len(enrollment_encodings)}/{enrollment_samples_needed})"
                cv2.putText(frame, status_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(frame, "Hold face steady; samples auto-capture", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

            # Display frame
            cv2.imshow('Face Recognition System', frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' or ESC
                break
            elif key == ord('s'):  # 's' - screenshot
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                os.makedirs(args.outputs_dir, exist_ok=True)
                filename = os.path.join(args.outputs_dir, f"screenshot_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                print(f"Screenshot saved: {filename}")
            elif key == ord('a'):
                # Toggle enrollment mode
                enroll_mode = not enroll_mode
                typed_name = ""
                enrollment_encodings = []
                last_enroll_time = 0.0
                state = "ON" if enroll_mode else "OFF"
                print(f"Enrollment mode: {state}")
            elif enroll_mode:
                # Capture typed name in enroll mode
                if key == 8 or key == 127:  # Backspace
                    typed_name = typed_name[:-1]
                elif key in (13, 10):
                    pass  # Enter ignored; we auto-complete when enough samples
                elif 32 <= key <= 126:
                    typed_name += chr(key)

            # If in enrollment mode, auto-capture encodings
            if enroll_mode and process_this_frame is False:
                # Use last computed face_encodings from the prior processed frame
                # Only if we have a name and at least one face
                if typed_name.strip() and 'face_encodings' in locals() and face_encodings:
                    now = time.time()
                    if now - last_enroll_time >= 0.4:
                        # Take the first face encoding (closest one would be better; first is fine)
                        enrollment_encodings.append(face_encodings[0])
                        last_enroll_time = now
                        print(f"Captured enrollment sample {len(enrollment_encodings)}/{enrollment_samples_needed}")

                # When enough samples, save and exit enroll mode
                if len(enrollment_encodings) >= enrollment_samples_needed:
                    person_name = typed_name.strip() or "Unknown"
                    # Extend in-memory lists
                    for enc in enrollment_encodings:
                        known_encodings.append(enc)
                        known_names.append(person_name)

                    # Persist to DB or file
                    for enc in enrollment_encodings:
                        repo.add_face(person_name, enc)
                    print(f"✓ Enrolled '{person_name}' with {len(enrollment_encodings)} samples to DB.")
                    known_encodings, known_names = repo.get_all_faces()

                    # Also save a cropped example image to known_faces
                    try:
                        os.makedirs("known_faces", exist_ok=True)
                        # Use last scaled_face_locations and frame to crop best effort
                        if 'scaled_face_locations' in locals() and scaled_face_locations:
                            t, r, b, l = scaled_face_locations[0]
                            crop = frame[t:b, l:r]
                            ts = time.strftime("%Y%m%d_%H%M%S")
                            safe_name = person_name.lower().replace(' ', '_')
                            cv2.imwrite(os.path.join("known_faces", f"{safe_name}_{ts}.jpg"), crop)
                    except Exception:
                        pass

                    # Reset enrollment state
                    enroll_mode = False
                    typed_name = ""
                    enrollment_encodings = []
                
    except KeyboardInterrupt:
        print("\nStopping face recognition...")
        
    finally:
        video_capture.release()
        cv2.destroyAllWindows()
        print("Camera released and windows closed.")
        
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)