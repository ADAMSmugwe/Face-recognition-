#!/usr/bin/env python3
"""
Utility functions for the Face Recognition System

This module contains helper functions used by both the encoding and recognition scripts.
"""

import pickle
import cv2
import numpy as np
from pathlib import Path


def load_encodings_from_file(encodings_file="encodings/known_faces.pkl"):
    """
    Load face encodings and names from a pickle file.

    Args:
        encodings_file (str): Path to the pickle file containing encodings

    Returns:
        tuple: (encodings, names) where encodings is a list of face encodings
               and names is a list of corresponding person names
    """
    encodings_file_path = Path(encodings_file)

    if not encodings_file_path.exists():
        print(f"Error: Encodings file '{encodings_file}' not found.")
        print("Please run 'python encode_faces.py' first to create the encodings.")
        return [], []

    try:
        with open(encodings_file_path, 'rb') as f:
            data = pickle.load(f)

        encodings = data.get('encodings', [])
        names = data.get('names', [])
        num_faces = data.get('num_faces', 0)

        print(f"✓ Loaded {num_faces} face encodings from {encodings_file}")
        return encodings, names

    except Exception as e:
        print(f"Error loading encodings file: {str(e)}")
        return [], []


def draw_bounding_box(frame, top, right, bottom, left, name, confidence=None):
    """
    Draw a bounding box around a detected face with the person's name.

    Args:
        frame: The video frame to draw on
        top, right, bottom, left: Face bounding box coordinates
        name (str): Person's name to display
        confidence (float, optional): Recognition confidence score
    """
    # Draw rectangle around the face
    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

    # Prepare text to display
    if confidence is not None:
        display_text = f"{name} ({confidence:.2f})"
    else:
        display_text = name

    # Calculate text size for background rectangle
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 0.6
    font_thickness = 1
    text_size = cv2.getTextSize(display_text, font, font_scale, font_thickness)[0]

    # Draw background rectangle for text
    text_bg_top = max(0, top - text_size[1] - 10)
    text_bg_bottom = max(0, top)
    text_bg_left = max(0, left)
    text_bg_right = min(frame.shape[1], left + text_size[0] + 10)

    cv2.rectangle(frame, (text_bg_left, text_bg_top), (text_bg_right, text_bg_bottom),
                  (0, 255, 0), cv2.FILLED)

    # Draw text
    text_position = (left + 6, max(top - 6, text_size[1] + 4))
    cv2.putText(frame, display_text, text_position, font, font_scale, (255, 255, 255),
                font_thickness)


def recognize_faces(face_encodings, known_encodings, known_names, tolerance=0.6):
    """
    Recognize faces by comparing encodings against known encodings.

    Args:
        face_encodings: List of face encodings from the current frame
        known_encodings: List of known face encodings
        known_names: List of known person names
        tolerance (float): Tolerance for face matching (lower = stricter)

    Returns:
        list: List of recognized names corresponding to face_encodings
    """
    names = []

    if not known_encodings:
        return ["Unknown"] * len(face_encodings)

    for face_encoding in face_encodings:
        # Calculate distances to all known faces
        distances = face_recognition.face_distance(known_encodings, face_encoding)

        # Find the best match
        min_distance_idx = np.argmin(distances)
        min_distance = distances[min_distance_idx]

        # Check if the match is within tolerance
        if min_distance <= tolerance:
            name = known_names[min_distance_idx]
            confidence = 1 - min_distance  # Convert distance to confidence
        else:
            name = "Unknown"
            confidence = 0.0

        names.append((name, confidence))

    return names


def preprocess_frame(frame):
    """
    Preprocess the video frame for better face detection.

    Args:
        frame: Input video frame

    Returns:
        Processed frame
    """
    # Convert to RGB (face_recognition expects RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Optional: Apply some preprocessing for better detection
    # You can add filters here if needed

    return rgb_frame


def get_video_properties(cap):
    """
    Get video capture properties for display.

    Args:
        cap: OpenCV VideoCapture object

    Returns:
        tuple: (width, height, fps)
    """
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    return width, height, fps


def create_status_display_text(num_faces_detected, num_faces_recognized, fps=None):
    """
    Create status text for display on the video feed.

    Args:
        num_faces_detected (int): Number of faces detected
        num_faces_recognized (int): Number of faces recognized
        fps (float, optional): Current FPS

    Returns:
        str: Status text
    """
    status_lines = [
        f"Faces detected: {num_faces_detected}",
        f"Faces recognized: {num_faces_recognized}"
    ]

    if fps is not None:
        status_lines.append(f"FPS: {fps:.1f}")

    return "\n".join(status_lines)


def save_frame(frame, filename="captured_frame.jpg"):
    """
    Save a frame to disk.

    Args:
        frame: Video frame to save
        filename (str): Output filename
    """
    cv2.imwrite(filename, frame)
    print(f"Frame saved as: {filename}")


# Import face_recognition here to avoid circular imports
try:
    import face_recognition
except ImportError:
    print("Warning: face_recognition library not available")
    face_recognition = None
