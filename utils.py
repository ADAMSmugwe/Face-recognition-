"""
Utility functions for face recognition system.
"""

import os
import cv2
import face_recognition
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import pickle


def validate_image_file(file_path: str) -> bool:
    """Validate if a file is a supported image format."""
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    _, ext = os.path.splitext(file_path.lower())
    return ext in valid_extensions


def load_image_safely(image_path: str) -> Optional[np.ndarray]:
    """Safely load an image file with error handling."""
    try:
        if not os.path.exists(image_path):
            print(f"Warning: Image file not found: {image_path}")
            return None
            
        if not validate_image_file(image_path):
            print(f"Warning: Unsupported image format: {image_path}")
            return None
            
        image = face_recognition.load_image_file(image_path)
        return image
    except Exception as e:
        print(f"Error loading image {image_path}: {str(e)}")
        return None


def get_person_name_from_filename(file_path: str) -> str:
    """Extract person's name from image filename."""
    filename = os.path.basename(file_path)
    name = os.path.splitext(filename)[0]
    name = name.replace('_', ' ').replace('-', ' ')
    return name.title()


def save_encodings(encodings_data: Dict[str, Any], file_path: str) -> bool:
    """Save face encodings to a pickle file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            pickle.dump(encodings_data, f)
        print(f"Encodings saved successfully to: {file_path}")
        return True
    except Exception as e:
        print(f"Error saving encodings: {str(e)}")
        return False


def load_encodings(file_path: str) -> Optional[Dict[str, Any]]:
    """Load face encodings from a pickle file."""
    try:
        if not os.path.exists(file_path):
            print(f"Encodings file not found: {file_path}")
            return None
            
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        print(f"Encodings loaded successfully from: {file_path}")
        return data
    except Exception as e:
        print(f"Error loading encodings: {str(e)}")
        return None


def draw_face_box(frame: np.ndarray, face_location: Tuple[int, int, int, int], 
                  name: str, confidence: float = None) -> np.ndarray:
    """Draw bounding box and label on detected face."""
    top, right, bottom, left = face_location
    
    # Choose color based on recognition status
    if name.lower() == "unknown":
        color = (0, 0, 255)  # Red for unknown
        text_color = (255, 255, 255)
    else:
        color = (0, 255, 0)  # Green for known person
        text_color = (255, 255, 255)
    
    # Draw bounding box
    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
    
    # Prepare label text
    if confidence is not None:
        label = f"{name} ({confidence:.2f})"
    else:
        label = name
    
    # Draw label background
    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1)[0]
    cv2.rectangle(frame, (left, bottom - 35), (left + label_size[0] + 10, bottom), color, cv2.FILLED)
    
    # Draw label text
    cv2.putText(frame, label, (left + 5, bottom - 10), cv2.FONT_HERSHEY_DUPLEX, 0.6, text_color, 1)
    
    return frame


def _compute_eye_centers(landmarks: Dict[str, List[Tuple[int, int]]]) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Compute centers of left and right eyes from landmarks."""
    try:
        left_eye_pts = landmarks.get("left_eye") or []
        right_eye_pts = landmarks.get("right_eye") or []
        if not left_eye_pts or not right_eye_pts:
            return None
        left_eye = (float(np.mean([p[0] for p in left_eye_pts])), float(np.mean([p[1] for p in left_eye_pts])))
        right_eye = (float(np.mean([p[0] for p in right_eye_pts])), float(np.mean([p[1] for p in right_eye_pts])))
        return left_eye, right_eye
    except Exception:
        return None


def align_face_chip(image: np.ndarray, face_location: Tuple[int, int, int, int], output_size: int = 160,
                    desired_left_eye_x: float = 0.35, desired_eye_y: float = 0.35) -> Optional[np.ndarray]:
    """
    Align a face to a canonical pose using eye landmarks and return an aligned face chip.

    Returns an image of shape (output_size, output_size, 3) or None if alignment fails.
    """
    try:
        landmarks_list = face_recognition.face_landmarks(image, [face_location], model="small")
        if not landmarks_list:
            return None
        eyes = _compute_eye_centers(landmarks_list[0])
        if eyes is None:
            return None
        (lX, lY), (rX, rY) = eyes

        dY = rY - lY
        dX = rX - lX
        angle = np.degrees(np.arctan2(dY, dX))

        desired_right_eye_x = 1.0 - desired_left_eye_x
        dist = np.sqrt((dX ** 2) + (dY ** 2))
        desired_dist = (desired_right_eye_x - desired_left_eye_x) * float(output_size)
        if dist == 0:
            return None
        scale = desired_dist / dist

        eyes_center = (float((lX + rX) / 2.0), float((lY + rY) / 2.0))

        M = cv2.getRotationMatrix2D(eyes_center, angle, scale)
        tX = float(output_size) * 0.5
        tY = float(output_size) * desired_eye_y
        M[0, 2] += (tX - eyes_center[0])
        M[1, 2] += (tY - eyes_center[1])

        aligned = cv2.warpAffine(image, M, (int(output_size), int(output_size)), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return aligned
    except Exception:
        return None


def get_face_encodings_from_image(image: np.ndarray, model: str = "hog", align: bool = False,
                                  align_size: int = 160) -> List[np.ndarray]:
    """Extract face encodings from an image. Optionally align faces before encoding."""
    try:
        face_locations = face_recognition.face_locations(image, model=model)
        if not face_locations:
            return []

        if not align:
            return face_recognition.face_encodings(image, face_locations)

        encodings: List[np.ndarray] = []
        for loc in face_locations:
            chip = align_face_chip(image, loc, output_size=align_size)
            if chip is None:
                # Fallback to non-aligned for this face
                try:
                    enc = face_recognition.face_encodings(image, [loc])
                    if enc:
                        encodings.append(enc[0])
                except Exception:
                    continue
                continue
            # Compute encoding on the aligned chip
            enc = face_recognition.face_encodings(chip)
            if enc:
                encodings.append(enc[0])
        return encodings
    except Exception as e:
        print(f"Error extracting face encodings: {str(e)}")
        return []


def get_face_encodings_with_locations(image: np.ndarray, face_locations: List[Tuple[int, int, int, int]],
                                      align: bool = False, align_size: int = 160) -> List[np.ndarray]:
    """Compute encodings for provided face locations with optional alignment."""
    try:
        if not face_locations:
            return []
        if not align:
            return face_recognition.face_encodings(image, face_locations)

        encodings: List[np.ndarray] = []
        for loc in face_locations:
            chip = align_face_chip(image, loc, output_size=align_size)
            if chip is None:
                try:
                    enc = face_recognition.face_encodings(image, [loc])
                    if enc:
                        encodings.append(enc[0])
                except Exception:
                    continue
                continue
            enc = face_recognition.face_encodings(chip)
            if enc:
                encodings.append(enc[0])
        return encodings
    except Exception as e:
        print(f"Error computing encodings with locations: {str(e)}")
        return []


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load optional YAML configuration file.

    Returns empty dict when file is missing or cannot be parsed.
    """
    try:
        if not os.path.exists(config_path):
            return {}

        try:
            import yaml  # type: ignore
        except Exception:
            print("Warning: PyYAML not installed; skipping config load.")
            return {}

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        return data
    except Exception as e:
        print(f"Warning: Failed to load config '{config_path}': {str(e)}")
        return {}