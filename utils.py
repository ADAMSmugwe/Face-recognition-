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


def get_face_encodings_from_image(image: np.ndarray, model: str = "hog") -> List[np.ndarray]:
    """Extract face encodings from an image."""
    try:
        face_locations = face_recognition.face_locations(image, model=model)
        if face_locations:
            face_encodings = face_recognition.face_encodings(image, face_locations)
            return face_encodings
        else:
            return []
    except Exception as e:
        print(f"Error extracting face encodings: {str(e)}")
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