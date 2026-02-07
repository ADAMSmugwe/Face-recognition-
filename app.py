#!/usr/bin/env python3
"""
Face Recognition Web Dashboard
A complete web interface for student management and face recognition
"""

from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import cv2
import face_recognition
import numpy as np
import pickle
import os
from pathlib import Path
from werkzeug.utils import secure_filename
import base64
import json
from datetime import datetime
import shutil

app = Flask(__name__)
app.config['SECRET_KEY'] = 'face-recognition-dashboard-2026'
app.config['UPLOAD_FOLDER'] = 'images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Paths
IMAGES_DIR = Path("images")
ENCODINGS_DIR = Path("encodings")
ENCODINGS_FILE = ENCODINGS_DIR / "known_faces.pkl"

# Ensure directories exist
IMAGES_DIR.mkdir(exist_ok=True)
ENCODINGS_DIR.mkdir(exist_ok=True)

# Global variables for video stream
camera = None
known_encodings = []
known_names = []
recognition_active = False

# Attendance tracking
from datetime import date, timedelta
attendance_records = {}  # {date: {student_name: timestamp}}
current_session_attendance = set()  # Students marked present in current session
last_recognition_time = {}  # {student_name: timestamp} - for duplicate prevention

# Real-time recognition status for sound/voice feedback
current_recognition_status = {
    'faces_detected': [],  # List of {name, confidence}
    'no_face': False,
    'too_dark': False,
    'brightness': 0,
    'last_update': None
}

# Enhanced settings
SETTINGS = {
    'confidence_threshold': 0.6,  # Adjustable recognition sensitivity (0-1, default 0.6)
    'duplicate_cooldown': 0,  # Seconds before same student can be recognized again (0 = disabled)
    'enable_sound': True,  # Play sound on recognition
    'enable_welcome_msg': True,  # Show welcome banner
    'enable_emotion': False,  # Emotion detection (requires additional setup)
    'dark_mode': False,  # Dark mode theme
    'auto_face_detection': True,  # Reject photos without faces (set to False to allow all photos)
    'min_face_size': 0.02  # Minimum face size relative to image (0.02 = 2% of image)
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def load_encodings():
    """Load face encodings from file"""
    global known_encodings, known_names
    
    if ENCODINGS_FILE.exists():
        try:
            with open(ENCODINGS_FILE, 'rb') as f:
                data = pickle.load(f)
                known_encodings = data.get('encodings', [])
                known_names = data.get('names', [])
                return True
        except Exception as e:
            print(f"Error loading encodings: {e}")
            return False
    return False

def save_encodings():
    """Save face encodings to file"""
    data = {
        'encodings': known_encodings,
        'names': known_names,
        'num_faces': len(known_names)
    }
    with open(ENCODINGS_FILE, 'wb') as f:
        pickle.dump(data, f)

def encode_faces_for_student(student_name):
    """Encode all faces for a specific student"""
    student_dir = IMAGES_DIR / student_name
    if not student_dir.exists():
        return 0
    
    encodings = []
    for img_file in student_dir.glob("*.*"):
        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            try:
                image = face_recognition.load_image_file(str(img_file))
                face_locations = face_recognition.face_locations(image)
                if face_locations:
                    face_encodings = face_recognition.face_encodings(image, face_locations)
                    if face_encodings:
                        encodings.append(face_encodings[0])
            except Exception as e:
                print(f"Error encoding {img_file}: {e}")
    
    return len(encodings)

def rebuild_all_encodings():
    """Rebuild all encodings from scratch"""
    global known_encodings, known_names
    
    known_encodings = []
    known_names = []
    
    total_encoded = 0
    
    for student_dir in IMAGES_DIR.iterdir():
        if student_dir.is_dir():
            student_name = student_dir.name
            
            for img_file in student_dir.glob("*.*"):
                if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    try:
                        image = face_recognition.load_image_file(str(img_file))
                        face_locations = face_recognition.face_locations(image)
                        
                        if face_locations:
                            face_encodings = face_recognition.face_encodings(image, face_locations)
                            if face_encodings:
                                known_encodings.append(face_encodings[0])
                                known_names.append(student_name)
                                total_encoded += 1
                    except Exception as e:
                        print(f"Error encoding {img_file}: {e}")
    
    if known_encodings:
        save_encodings()
    
    return total_encoded

def get_all_students():
    """Get list of all students with their info"""
    students = []
    
    for student_dir in IMAGES_DIR.iterdir():
        if student_dir.is_dir():
            images = list(student_dir.glob("*.*"))
            images = [img for img in images if img.suffix.lower() in ['.jpg', '.jpeg', '.png']]
            
            students.append({
                'name': student_dir.name,
                'image_count': len(images),
                'images': [img.name for img in images]
            })
    
    return sorted(students, key=lambda x: x['name'])

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/students')
def api_students():
    """Get all students"""
    students = get_all_students()
    return jsonify({'students': students, 'total': len(students)})

@app.route('/api/student/<student_name>')
def api_student_detail(student_name):
    """Get details of a specific student"""
    student_dir = IMAGES_DIR / student_name
    
    if not student_dir.exists():
        return jsonify({'error': 'Student not found'}), 404
    
    images = list(student_dir.glob("*.*"))
    images = [img for img in images if img.suffix.lower() in ['.jpg', '.jpeg', '.png']]
    
    return jsonify({
        'name': student_name,
        'image_count': len(images),
        'images': [img.name for img in images]
    })

@app.route('/api/student/add', methods=['POST'])
def api_add_student():
    """Add a new student with auto face detection"""
    data = request.form
    student_name = data.get('name', '').strip()
    
    if not student_name:
        return jsonify({'error': 'Student name is required'}), 400
    
    student_dir = IMAGES_DIR / student_name
    
    if student_dir.exists():
        return jsonify({'error': 'Student already exists'}), 400
    
    student_dir.mkdir(parents=True)
    
    # Handle uploaded files with auto face detection
    files = request.files.getlist('photos')
    saved_count = 0
    rejected_count = 0
    rejected_files = []
    face_quality_info = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            
            # Save temporarily to check for faces
            temp_path = student_dir / f"temp.{ext}"
            file.save(temp_path)
            
            # Check if auto face detection is enabled
            if SETTINGS.get('auto_face_detection', True):
                # Check if face exists in image
                try:
                    image = face_recognition.load_image_file(str(temp_path))
                    face_locations = face_recognition.face_locations(image)
                    
                    if face_locations:
                        # Face detected - check quality
                        img_height, img_width = image.shape[:2]
                        top, right, bottom, left = face_locations[0]
                        face_width = right - left
                        face_height = bottom - top
                        face_ratio = (face_width * face_height) / (img_width * img_height)
                        
                        if face_ratio >= SETTINGS.get('min_face_size', 0.02):
                            # Good quality - keep the file
                            new_filename = f"{student_name}_{saved_count + 1:03d}.{ext}"
                            temp_path.rename(student_dir / new_filename)
                            saved_count += 1
                            quality = "Good" if face_ratio > 0.1 else "Acceptable"
                            face_quality_info.append(f"{filename}: {quality} (face size: {face_ratio*100:.1f}%)")
                        else:
                            # Face too small
                            temp_path.unlink()
                            rejected_count += 1
                            rejected_files.append(f"{filename} (face too small)")
                    else:
                        # No face detected - reject
                        temp_path.unlink()
                        rejected_count += 1
                        rejected_files.append(f"{filename} (no face detected)")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    if temp_path.exists():
                        temp_path.unlink()
                    rejected_count += 1
                    rejected_files.append(f"{filename} (processing error)")
            else:
                # Auto detection disabled - save all files
                new_filename = f"{student_name}_{saved_count + 1:03d}.{ext}"
                temp_path.rename(student_dir / new_filename)
                saved_count += 1
    
    if saved_count == 0:
        student_dir.rmdir()
        error_msg = 'No valid images with faces detected'
        if rejected_files:
            error_msg += f'. Rejected: {", ".join(rejected_files[:3])}'
            if len(rejected_files) > 3:
                error_msg += f' and {len(rejected_files) - 3} more'
        error_msg += '. Tips: Use clear photos with visible faces, good lighting, and face looking at camera.'
        if SETTINGS.get('auto_face_detection', True):
            error_msg += ' Or disable auto-face-detection in settings.'
        
        return jsonify({
            'error': error_msg,
            'rejected': rejected_files,
            'help': 'Make sure photos have clear, visible faces with good lighting'
        }), 400
    
    # Encode faces
    encoded = encode_faces_for_student(student_name)
    rebuild_all_encodings()
    
    message = f'✅ Added {student_name} with {saved_count} image{"s" if saved_count != 1 else ""}'
    if rejected_count > 0:
        message += f' ({rejected_count} rejected)'
    
    return jsonify({
        'success': True,
        'message': message,
        'encoded': encoded,
        'saved': saved_count,
        'rejected': rejected_count,
        'rejected_files': rejected_files,
        'quality_info': face_quality_info
    })

@app.route('/api/student/<student_name>/delete', methods=['DELETE'])
def api_delete_student(student_name):
    """Delete a student"""
    student_dir = IMAGES_DIR / student_name
    
    if not student_dir.exists():
        return jsonify({'error': 'Student not found'}), 404
    
    shutil.rmtree(student_dir)
    rebuild_all_encodings()
    
    return jsonify({'success': True, 'message': f'Deleted {student_name}'})

@app.route('/api/student/<student_name>/rename', methods=['PUT'])
def api_rename_student(student_name):
    """Rename a student"""
    data = request.get_json()
    new_name = data.get('new_name', '').strip()
    
    if not new_name:
        return jsonify({'error': 'New name is required'}), 400
    
    student_dir = IMAGES_DIR / student_name
    new_dir = IMAGES_DIR / new_name
    
    if not student_dir.exists():
        return jsonify({'error': 'Student not found'}), 404
    
    if new_dir.exists():
        return jsonify({'error': 'New name already exists'}), 400
    
    student_dir.rename(new_dir)
    rebuild_all_encodings()
    
    return jsonify({'success': True, 'message': f'Renamed {student_name} to {new_name}'})

@app.route('/api/student/<student_name>/add-photos', methods=['POST'])
def api_add_photos(student_name):
    """Add more photos to existing student"""
    student_dir = IMAGES_DIR / student_name
    
    if not student_dir.exists():
        return jsonify({'error': 'Student not found'}), 404
    
    files = request.files.getlist('photos')
    
    # Get current image count
    existing_images = list(student_dir.glob("*.*"))
    current_count = len([img for img in existing_images if img.suffix.lower() in ['.jpg', '.jpeg', '.png']])
    
    saved_count = 0
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            new_filename = f"{student_name}_{current_count + saved_count + 1:03d}.{ext}"
            file.save(student_dir / new_filename)
            saved_count += 1
    
    if saved_count == 0:
        return jsonify({'error': 'No valid images uploaded'}), 400
    
    rebuild_all_encodings()
    
    return jsonify({
        'success': True,
        'message': f'Added {saved_count} photos for {student_name}'
    })

@app.route('/api/student/<student_name>/photo/<photo_name>/delete', methods=['DELETE'])
def api_delete_photo(student_name, photo_name):
    """Delete a specific photo"""
    photo_path = IMAGES_DIR / student_name / photo_name
    
    if not photo_path.exists():
        return jsonify({'error': 'Photo not found'}), 404
    
    photo_path.unlink()
    rebuild_all_encodings()
    
    return jsonify({'success': True, 'message': f'Deleted {photo_name}'})

@app.route('/api/encodings/rebuild', methods=['POST'])
def api_rebuild_encodings():
    """Rebuild all face encodings"""
    total = rebuild_all_encodings()
    return jsonify({
        'success': True,
        'message': f'Rebuilt encodings for {total} faces'
    })

@app.route('/images/<student_name>/<photo_name>')
def serve_image(student_name, photo_name):
    """Serve student images"""
    return send_from_directory(IMAGES_DIR / student_name, photo_name)

def generate_frames():
    """Generate video frames with MULTI-STUDENT face recognition"""
    global camera, known_encodings, known_names, current_session_attendance
    
    camera = cv2.VideoCapture(0)
    
    # Load encodings
    load_encodings()
    
    recognized_today = set()
    today = str(date.today())
    
    # Initialize today's attendance if needed
    if today not in attendance_records:
        attendance_records[today] = {}
    
    # Track confidence for auto-attendance
    attendance_tracking = {}  # {name: frames_seen_count}
    ATTENDANCE_THRESHOLD = 10  # Need to see student for 10 frames to confirm
    
    try:
        while recognition_active:
            success, frame = camera.read()
            if not success:
                break
            
            # Resize for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Detect ALL faces in frame
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            # Check brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            
            # Draw guidance
            height, width = frame.shape[:2]
            
            # Info panel at top
            cv2.rectangle(frame, (0, 0), (width, 80), (0, 0, 0), -1)
            
            # Show face count and status
            face_count_text = f"👥 Faces Detected: {len(face_locations)}"
            cv2.putText(frame, face_count_text, (20, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            if brightness < 60:
                cv2.putText(frame, "⚠️  WARNING: TOO DARK!", (20, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            elif len(face_locations) == 0:
                cv2.putText(frame, "❌ No faces detected", (20, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(frame, "✅ Multi-Student Recognition Active", (20, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Recognize ALL faces with enhanced features
            current_time = datetime.now()
            
            # Update recognition status for sound/voice feedback
            global current_recognition_status
            current_recognition_status['faces_detected'] = []
            current_recognition_status['no_face'] = len(face_locations) == 0
            current_recognition_status['too_dark'] = brightness < 60
            current_recognition_status['brightness'] = float(brightness)
            current_recognition_status['last_update'] = current_time
            
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Scale back up
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                name = "Unknown"
                confidence = 0
                color = (0, 0, 255)  # Red by default
                is_duplicate = False
                cooldown_remaining = 0
                
                if known_encodings:
                    distances = face_recognition.face_distance(known_encodings, face_encoding)
                    if len(distances) > 0:
                        min_idx = distances.argmin()
                        min_distance = distances[min_idx]
                        
                        # Use configurable confidence threshold
                        threshold = 1.0 - SETTINGS['confidence_threshold']
                        
                        if min_distance <= threshold:  # Recognized!
                            name = known_names[min_idx]
                            confidence = (1.0 - min_distance) * 100
                            recognized_today.add(name)
                            
                            # Add to status for sound/voice feedback
                            current_recognition_status['faces_detected'].append({
                                'name': name,
                                'confidence': confidence
                            })
                            
                            # 🚫 DUPLICATE DETECTION - Check cooldown period
                            if name in last_recognition_time:
                                time_diff = (current_time - last_recognition_time[name]).total_seconds()
                                if time_diff < SETTINGS['duplicate_cooldown']:
                                    is_duplicate = True
                                    cooldown_remaining = int(SETTINGS['duplicate_cooldown'] - time_diff)
                                    color = (0, 165, 255)  # Orange for duplicate
                                else:
                                    last_recognition_time[name] = current_time
                            else:
                                last_recognition_time[name] = current_time
                            
                            # Track for auto-attendance (only if not duplicate)
                            if not is_duplicate:
                                if name not in attendance_tracking:
                                    attendance_tracking[name] = 0
                                attendance_tracking[name] += 1
                                
                                # AUTO-MARK ATTENDANCE after threshold! 🎯
                                if attendance_tracking[name] >= ATTENDANCE_THRESHOLD:
                                    if name not in attendance_records[today]:
                                        attendance_records[today][name] = current_time.strftime('%H:%M:%S')
                                        current_session_attendance.add(name)
                            
                            # 🎨 Color based on status
                            if is_duplicate:
                                color = (0, 165, 255)  # Orange - duplicate warning
                            elif confidence > 80:
                                color = (0, 255, 0)  # Bright green - excellent match
                            elif confidence > 70:
                                color = (50, 205, 50)  # Lime green - good match
                            else:
                                color = (0, 200, 200)  # Cyan - acceptable match
                        else:
                            # Unknown face - add to status
                            current_recognition_status['faces_detected'].append({
                                'name': 'Unknown',
                                'confidence': 0
                            })
                else:
                    # No encodings loaded - mark as unknown
                    current_recognition_status['faces_detected'].append({
                        'name': 'Unknown',
                        'confidence': 0
                    })
                
                # Draw box with thicker border for recognized students
                thickness = 4 if name != "Unknown" else 2
                cv2.rectangle(frame, (left, top), (right, bottom), color, thickness)
                
                # Calculate label size to fit name
                text = f"{name}"
                if name != "Unknown":
                    text += f" {confidence:.0f}%"
                    # Add checkmark if confirmed
                    if name in attendance_records[today]:
                        text += " ✓"
                    # Show duplicate warning
                    if is_duplicate:
                        text = f"{name} - DUPLICATE! (wait {cooldown_remaining}s)"
                
                (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1)
                
                # Draw name background (adaptive width)
                label_width = max(text_width + 12, right - left)
                cv2.rectangle(frame, (left, bottom - text_height - 20), (left + label_width, bottom), color, -1)
                
                # Draw name
                cv2.putText(frame, text, (left + 6, bottom - 8),
                           cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
                
                # 💡 Add status indicator at top of box
                if name != "Unknown" and not is_duplicate:
                    if attendance_tracking.get(name, 0) >= ATTENDANCE_THRESHOLD:
                        status = "✓ PRESENT"
                        status_color = (0, 255, 0)
                    else:
                        progress = int((attendance_tracking.get(name, 0) / ATTENDANCE_THRESHOLD) * 100)
                        status = f"Confirming {progress}%"
                        status_color = (255, 255, 0)
                    
                    cv2.rectangle(frame, (left, top - 30), (left + 150, top), (0, 0, 0), -1)
                    cv2.putText(frame, status, (left + 5, top - 8),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1)
                
                # 🎊 WELCOME MESSAGE - Big banner when first recognized
                if name != "Unknown" and not is_duplicate:
                    if SETTINGS['enable_welcome_msg'] and attendance_tracking.get(name, 0) == ATTENDANCE_THRESHOLD:
                        # Big welcome banner at top center
                        welcome_text = f"WELCOME, {name.upper()}!"
                        (w_width, w_height), _ = cv2.getTextSize(welcome_text, cv2.FONT_HERSHEY_DUPLEX, 1.5, 3)
                        
                        # Center the banner
                        banner_x = (width - w_width) // 2
                        banner_y = 100
                        
                        # Animated background (pulsing effect)
                        cv2.rectangle(frame, (banner_x - 20, banner_y - 60), 
                                    (banner_x + w_width + 20, banner_y + 20), (0, 255, 0), -1)
                        cv2.rectangle(frame, (banner_x - 20, banner_y - 60), 
                                    (banner_x + w_width + 20, banner_y + 20), (255, 255, 255), 3)
                        
                        # Welcome text
                        cv2.putText(frame, welcome_text, (banner_x, banner_y),
                                   cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 0), 3)
            
            # Show attendance panel at bottom
            if recognized_today:
                # Background panel
                panel_height = min(200, 30 + len(recognized_today) * 30)
                cv2.rectangle(frame, (0, height - panel_height), (350, height), (0, 0, 0), -1)
                
                y_offset = height - panel_height + 25
                present_count = len([p for p in recognized_today if p in attendance_records[today]])
                
                cv2.putText(frame, f"📋 Attendance: {present_count}/{len(recognized_today)}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                y_offset += 30
                
                for person in sorted(recognized_today):
                    # Show status
                    if person in attendance_records[today]:
                        prefix = "✅"
                        time_str = f" - {attendance_records[today][person]}"
                        color_code = (0, 255, 0)
                    else:
                        progress = attendance_tracking.get(person, 0)
                        prefix = f"○ {int((progress/ATTENDANCE_THRESHOLD)*100)}%"
                        time_str = ""
                        color_code = (255, 255, 0)
                    
                    cv2.putText(frame, f"{prefix} {person}{time_str}", (15, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_code, 1)
                    y_offset += 28
            
            # Show current count in top-right
            present_count = len(current_session_attendance)
            total_students = len(get_all_students())
            count_text = f"Present: {present_count}/{total_students}"
            cv2.putText(frame, count_text, (width - 220, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    finally:
        if camera:
            camera.release()

@app.route('/video-feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/recognition/start', methods=['POST'])
def start_recognition():
    """Start face recognition"""
    global recognition_active
    recognition_active = True
    return jsonify({'success': True, 'message': 'Recognition started'})

@app.route('/api/recognition/stop', methods=['POST'])
def stop_recognition():
    """Stop face recognition"""
    global recognition_active, camera
    recognition_active = False
    if camera:
        camera.release()
    return jsonify({'success': True, 'message': 'Recognition stopped'})

@app.route('/api/recognition/status')
def get_recognition_status():
    """Get current recognition status for sound/voice feedback"""
    global current_recognition_status
    
    if not recognition_active:
        return jsonify({'active': False})
    
    # Return copy of current status
    status = {
        'active': True,
        'faces_detected': current_recognition_status.get('faces_detected', []),
        'no_face': bool(current_recognition_status.get('no_face', False)),
        'too_dark': bool(current_recognition_status.get('too_dark', False)),
        'brightness': float(current_recognition_status.get('brightness', 0)),
        'last_update': current_recognition_status.get('last_update').isoformat() if current_recognition_status.get('last_update') else None
    }
    
    return jsonify(status)

@app.route('/api/attendance/today')
def get_today_attendance():
    """Get today's attendance"""
    today = str(date.today())
    attendance = attendance_records.get(today, {})
    
    # Get all students
    all_students = [s['name'] for s in get_all_students()]
    
    # Mark who's present and absent
    present = list(attendance.keys())
    absent = [s for s in all_students if s not in present]
    
    return jsonify({
        'date': today,
        'present': present,
        'absent': absent,
        'total_students': len(all_students),
        'present_count': len(present),
        'absent_count': len(absent),
        'attendance_details': attendance
    })

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    """Manually mark a student present"""
    data = request.get_json()
    student_name = data.get('student_name')
    
    if not student_name:
        return jsonify({'error': 'Student name required'}), 400
    
    today = str(date.today())
    
    if today not in attendance_records:
        attendance_records[today] = {}
    
    attendance_records[today][student_name] = datetime.now().strftime('%H:%M:%S')
    current_session_attendance.add(student_name)
    
    return jsonify({
        'success': True,
        'message': f'{student_name} marked present',
        'time': attendance_records[today][student_name]
    })

@app.route('/api/attendance/unmark', methods=['POST'])
def unmark_attendance():
    """Unmark a student (mark as absent)"""
    data = request.get_json()
    student_name = data.get('student_name')
    
    if not student_name:
        return jsonify({'error': 'Student name required'}), 400
    
    today = str(date.today())
    
    if today in attendance_records and student_name in attendance_records[today]:
        del attendance_records[today][student_name]
        current_session_attendance.discard(student_name)
    
    return jsonify({
        'success': True,
        'message': f'{student_name} marked absent'
    })

@app.route('/api/attendance/clear', methods=['POST'])
def clear_today_attendance():
    """Clear today's attendance"""
    today = str(date.today())
    
    if today in attendance_records:
        del attendance_records[today]
    
    current_session_attendance.clear()
    
    return jsonify({
        'success': True,
        'message': 'Today\'s attendance cleared'
    })

@app.route('/api/attendance/history')
def get_attendance_history():
    """Get attendance history"""
    return jsonify({
        'records': attendance_records,
        'total_days': len(attendance_records)
    })

@app.route('/api/attendance/export')
def export_attendance():
    """Export attendance as CSV-like data"""
    all_students = [s['name'] for s in get_all_students()]
    dates = sorted(attendance_records.keys())
    
    # Build export data
    export_data = {
        'students': all_students,
        'dates': dates,
        'attendance': {}
    }
    
    for student in all_students:
        export_data['attendance'][student] = {}
        for date_str in dates:
            export_data['attendance'][student][date_str] = student in attendance_records.get(date_str, {})
    
    return jsonify(export_data)

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    return jsonify(SETTINGS)

@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    """Update settings"""
    data = request.get_json()
    
    for key, value in data.items():
        if key in SETTINGS:
            SETTINGS[key] = value
    
    return jsonify({
        'success': True,
        'settings': SETTINGS
    })

@app.route('/api/search/students/<query>')
def search_students(query):
    """Search students by name"""
    all_students = get_all_students()
    query_lower = query.lower()
    
    results = [s for s in all_students if query_lower in s['name'].lower()]
    
    return jsonify({
        'results': results,
        'count': len(results)
    })

@app.route('/api/stats')
def get_stats():
    """Get system statistics"""
    students = get_all_students()
    total_photos = sum(s['image_count'] for s in students)
    
    today = str(date.today())
    present_today = len(attendance_records.get(today, {}))
    
    # Load encodings count
    encodings_count = len(known_encodings) if known_encodings else 0
    
    return jsonify({
        'total_students': len(students),
        'total_photos': total_photos,
        'total_encodings': encodings_count,
        'present_today': present_today,
        'absent_today': len(students) - present_today,
        'attendance_percentage': (present_today / len(students) * 100) if students else 0
    })

if __name__ == '__main__':
    import os
    
    print("\n" + "="*60)
    print("🎓 FACE RECOGNITION WEB DASHBOARD")
    print("="*60)
    print("\n📱 Open in your browser:")
    print("   http://localhost:5001")
    print("\n🎯 Features:")
    print("   ✅ Add/Delete/Edit students")
    print("   ✅ Upload photos")
    print("   ✅ Live face recognition")
    print("   ✅ Real-time guidance")
    print("\n" + "="*60 + "\n")
    
    # Load initial encodings
    load_encodings()
    
    # Get port from environment variable (for deployment) or use 5001
    port = int(os.environ.get('PORT', 5001))
    
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)
