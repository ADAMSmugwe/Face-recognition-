#!/usr/bin/env python3
"""
Real-time Face Recognition Script

This script loads pre-computed face encodings and performs real-time face recognition
using a webcam feed. It detects faces, matches them against known faces, and displays
the results with bounding boxes and names.

Usage:
    python recognize.py

Controls:
    - Press 'q' to quit
    - Press 's' to save current frame
    - Press 'c' to clear the console output

Requirements:
    - Run encode_faces.py first to generate the encodings file
    - Webcam/camera connected and accessible
"""

import cv2
import sys
import time
from utils import (
    load_encodings_from_file,
    draw_bounding_box,
    preprocess_frame,
    get_video_properties,
    create_status_display_text,
    save_frame
)

# Import face_recognition at the top level
try:
    import face_recognition
    print("✓ face_recognition library loaded successfully")
except ImportError as e:
    print(f"Error: Could not import face_recognition: {e}")
    print("Please install the required packages: pip install -r requirements.txt")
    sys.exit(1)


def initialize_camera(camera_index=0):
    """
    Initialize the camera/webcam.

    Args:
        camera_index (int): Camera device index (0 = default camera)

    Returns:
        cv2.VideoCapture: Camera capture object
    """
    print("Initializing camera...")
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print(f"Error: Could not open camera {camera_index}")
        print("Make sure your webcam is connected and not being used by another application.")
        return None

    # Get camera properties
    width, height, fps = get_video_properties(cap)
    print(f"Camera initialized: {width}x{height} @ {fps} FPS")

    return cap


def process_frame(frame, known_encodings, known_names, tolerance=0.6, show_confidence=True):
    """
    Process a single frame for face recognition.

    Args:
        frame: Input video frame
        known_encodings: List of known face encodings
        known_names: List of known person names
        tolerance (float): Face matching tolerance
        show_confidence (bool): Whether to show confidence scores

    Returns:
        tuple: (processed_frame, num_faces_detected, num_faces_recognized)
    """
    # Preprocess frame for face recognition
    rgb_frame = preprocess_frame(frame)

    # Find all faces in the current frame
    face_locations = face_recognition.face_locations(rgb_frame)

    if not face_locations:
        # No faces detected
        return frame, 0, 0

    # Encode faces in the current frame
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    num_faces_detected = len(face_locations)
    num_faces_recognized = 0

    # Process each detected face
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        # Compare with known faces
        distances = face_recognition.face_distance(known_encodings, face_encoding)

        if len(distances) > 0:
            # Find best match
            min_distance_idx = distances.argmin()
            min_distance = distances[min_distance_idx]

            # Check if match is within tolerance
            if min_distance <= tolerance:
                name = known_names[min_distance_idx]
                confidence = 1.0 - min_distance  # Convert distance to confidence
                num_faces_recognized += 1

                if show_confidence:
                    draw_bounding_box(frame, top, right, bottom, left, name, confidence)
                else:
                    draw_bounding_box(frame, top, right, bottom, left, name)
            else:
                # Unknown face
                draw_bounding_box(frame, top, right, bottom, left, "Unknown")
        else:
            # No known faces to compare against
            draw_bounding_box(frame, top, right, bottom, left, "Unknown")

    return frame, num_faces_detected, num_faces_recognized


def display_status_info(frame, status_text, position=(10, 30)):
    """
    Display status information on the frame.

    Args:
        frame: Video frame to draw on
        status_text (str): Status text to display
        position (tuple): Position to display text (x, y)
    """
    # Split status text into lines
    lines = status_text.split('\n')

    # Draw each line
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    font_thickness = 2
    line_height = 30

    for i, line in enumerate(lines):
        y_position = position[1] + (i * line_height)
        cv2.putText(frame, line, (position[0], y_position),
                   font, font_scale, (255, 255, 255), font_thickness)
        # Add shadow for better readability
        cv2.putText(frame, line, (position[0] + 2, y_position + 2),
                   font, font_scale, (0, 0, 0), font_thickness)


def main():
    """
    Main function to run the real-time face recognition system.
    """
    print("Real-time Face Recognition System")
    print("=" * 40)

    # Load known face encodings
    print("Loading face encodings...")
    known_encodings, known_names = load_encodings_from_file()

    if not known_encodings:
        print("No face encodings found. Please run encode_faces.py first.")
        return

    # Initialize camera
    cap = initialize_camera()
    if cap is None:
        return

    print("\nStarting real-time recognition...")
    print("Controls:")
    print("  'q' - Quit")
    print("  's' - Save current frame")
    print("  'c' - Clear console")
    print("  'h' - Toggle help display")
    print("\nPress any key to continue...")
    cv2.waitKey(0)

    # Recognition parameters
    tolerance = 0.6  # Lower = more strict matching
    show_confidence = True
    show_help = False

    # Performance tracking
    frame_count = 0
    start_time = time.time()
    fps = 0

    try:
        while True:
            # Capture frame
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame from camera")
                break

            # Process frame for face recognition
            processed_frame, num_detected, num_recognized = process_frame(
                frame, known_encodings, known_names, tolerance, show_confidence
            )

            # Update FPS calculation
            frame_count += 1
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                fps = frame_count / elapsed_time

            # Create status text
            status_text = create_status_display_text(num_detected, num_recognized, fps)

            # Display status information
            display_status_info(processed_frame, status_text)

            # Show help if requested
            if show_help:
                help_text = "q: quit | s: save | c: clear | h: help"
                cv2.putText(processed_frame, help_text, (10, processed_frame.shape[0] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Display the frame
            cv2.imshow('Face Recognition', processed_frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("Quitting...")
                break
            elif key == ord('s'):
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"captured_frame_{timestamp}.jpg"
                save_frame(frame, filename)
            elif key == ord('c'):
                print("\033c", end="")  # Clear console (Unix/Linux/Mac)
            elif key == ord('h'):
                show_help = not show_help
                print(f"Help display: {'ON' if show_help else 'OFF'}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    finally:
        # Clean up
        cap.release()
        cv2.destroyAllWindows()
        print("Camera released and windows closed.")


if __name__ == "__main__":
    main()
