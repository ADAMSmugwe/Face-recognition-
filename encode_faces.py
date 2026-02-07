#!/usr/bin/env python3
"""
Face Encoding Script

This script loads images from the 'images' folder, encodes the faces using
the face_recognition library, and saves the encodings along with the names
to a pickle file for later use in recognition.

Usage:
    python encode_faces.py

Requirements:
    - Images should be placed in the 'images' folder
    - Each image filename should be the person's name (e.g., "john_doe.jpg")
    - Only one face per image is recommended for best results
"""

import os
import pickle
import face_recognition
import numpy as np
from pathlib import Path


def load_images_from_folder(folder_path):
    """
    Load all images from a folder and return a dictionary of image paths.
    Supports both:
    1. Direct images in the folder (filename = person name)
    2. Subdirectories (folder name = person name, containing multiple images)

    Args:
        folder_path (str): Path to the folder containing images

    Returns:
        dict: Dictionary with person names as keys and lists of image paths as values
    """
    images = {}
    folder = Path(folder_path)

    # Supported image extensions
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}

    if not folder.exists():
        print(f"Warning: Images folder '{folder_path}' does not exist.")
        print("Please create the folder and add images before running this script.")
        return images

    # Check for subdirectories (student folders)
    has_subdirs = any(item.is_dir() for item in folder.iterdir())
    
    if has_subdirs:
        # Mode 1: Each person has their own folder with multiple images
        print("📁 Detected folder-based organization (each student has their own folder)")
        for person_folder in folder.iterdir():
            if person_folder.is_dir():
                person_name = person_folder.name
                person_images = []
                
                for image_file in person_folder.iterdir():
                    if image_file.is_file() and image_file.suffix.lower() in valid_extensions:
                        person_images.append(str(image_file))
                
                if person_images:
                    images[person_name] = person_images
                    print(f"Found {len(person_images)} image(s) for: {person_name}")
    else:
        # Mode 2: Direct image files (legacy mode)
        print("📄 Detected file-based organization (one image per student)")
        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                # Use filename (without extension) as the person's name
                person_name = file_path.stem
                images[person_name] = [str(file_path)]
                print(f"Found image: {person_name} -> {file_path.name}")

    return images


def encode_faces(images_dict):
    """
    Encode faces from the provided images.
    Now supports multiple images per person.

    Args:
        images_dict (dict): Dictionary with person names as keys and lists of image paths as values

    Returns:
        tuple: (encodings_list, names_list) where encodings_list contains face encodings
               and names_list contains corresponding person names
    """
    known_encodings = []
    known_names = []

    total_images = sum(len(paths) if isinstance(paths, list) else 1 for paths in images_dict.values())
    print(f"\nEncoding faces for {len(images_dict)} people ({total_images} total images)...")

    for person_name, image_paths in images_dict.items():
        # Ensure image_paths is a list
        if not isinstance(image_paths, list):
            image_paths = [image_paths]
        
        person_encodings = 0
        
        for image_path in image_paths:
            try:
                # Load the image using face_recognition
                image = face_recognition.load_image_file(image_path)

                # Find all face locations in the image
                face_locations = face_recognition.face_locations(image)

                if len(face_locations) == 0:
                    print(f"⚠️  No faces found in {Path(image_path).name}")
                    continue
                elif len(face_locations) > 1:
                    print(f"⚠️  Multiple faces found in {Path(image_path).name}. Using the first face.")

                # Encode the face(s) - get the encoding for the first face
                face_encodings = face_recognition.face_encodings(image, face_locations)

                if len(face_encodings) > 0:
                    # Add the encoding and name to our lists
                    known_encodings.append(face_encodings[0])
                    known_names.append(person_name)
                    person_encodings += 1
                else:
                    print(f"⚠️  Could not encode face in {Path(image_path).name}")

            except Exception as e:
                print(f"❌ Error processing {Path(image_path).name}: {str(e)}")
                continue
        
        if person_encodings > 0:
            print(f"✓ Encoded {person_encodings} image(s) for: {person_name}")
        else:
            print(f"❌ Failed to encode any images for: {person_name}")

    return known_encodings, known_names


def save_encodings_to_file(encodings, names, output_file="encodings/known_faces.pkl"):
    """
    Save the face encodings and names to a pickle file.

    Args:
        encodings (list): List of face encodings
        names (list): List of corresponding person names
        output_file (str): Path to save the pickle file
    """
    # Create encodings directory if it doesn't exist
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a dictionary to store the data
    data = {
        'encodings': encodings,
        'names': names,
        'num_faces': len(names)
    }

    # Save to pickle file
    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    print(f"\n✓ Saved {len(names)} face encodings to {output_file}")


def main():
    """
    Main function to orchestrate the face encoding process.
    """
    print("Face Recognition System - Face Encoder")
    print("=" * 40)

    # Define paths
    images_folder = "images"

    # Load images from folder
    images_dict = load_images_from_folder(images_folder)

    if not images_dict:
        print("No images found. Please add images to the 'images' folder.")
        print("Each image filename should be the person's name (e.g., 'john_doe.jpg')")
        return

    # Encode the faces
    known_encodings, known_names = encode_faces(images_dict)

    if not known_encodings:
        print("No faces could be encoded. Please check your images.")
        return

    # Save encodings to file
    save_encodings_to_file(known_encodings, known_names)

    print("\nFace encoding completed successfully!")
    print("You can now run 'python recognize.py' to start real-time recognition.")


def encode_all_faces(images_folder="images", output_file="encodings/known_faces.pkl"):
    """
    Encode all faces from a folder and save to file.
    This function can be called from other scripts.
    
    Args:
        images_folder (str): Path to folder containing images
        output_file (str): Path to save encodings file
    
    Returns:
        bool: True if encoding was successful, False otherwise
    """
    # Load images from folder
    images_dict = load_images_from_folder(images_folder)

    if not images_dict:
        print("❌ No images found in the images folder.")
        return False

    # Encode the faces
    known_encodings, known_names = encode_faces(images_dict)

    if not known_encodings:
        print("❌ No faces could be encoded. Please check your images.")
        return False

    # Save encodings to file
    save_encodings_to_file(known_encodings, known_names, output_file)
    
    return True


if __name__ == "__main__":
    main()
