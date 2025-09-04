#!/usr/bin/env python3
"""
Face Encoding Script - Processes known face images and creates encodings
"""

import os
import sys
import argparse
from db import FaceDatabase
from database import get_engine, init_db, get_session_maker, FaceRepository
from utils import (
    load_image_safely, 
    get_person_name_from_filename,
    get_face_encodings_from_image,
    save_encodings,
    validate_image_file,
    load_config,
)


def parse_args(config) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Encode known faces into embeddings for recognition"
    )
    encoder_cfg = (config or {}).get("encoder", {}) if isinstance(config, dict) else {}
    parser.add_argument(
        "--input", "-i", default=encoder_cfg.get("input_dir", "known_faces"), help="Directory of known face images"
    )
    parser.add_argument(
        "--output", "-o", default=encoder_cfg.get("output_file", "encodings/face_encodings.pkl"), help="Output pickle file for encodings"
    )
    parser.add_argument(
        "--model",
        "-m",
        default=encoder_cfg.get("model", "hog"),
        choices=["hog", "cnn"],
        help="Face detection model (hog=CPU, cnn=GPU)",
    )
    parser.add_argument(
        "--use-db",
        action="store_true",
        help="Save encodings into SQLite database instead of pickle",
    )
    parser.add_argument(
        "--db-path",
        default=encoder_cfg.get("db_path", "data/faces.db"),
        help="SQLite database path (when --use-db)",
    )
    parser.add_argument(
        "--db-url",
        default=encoder_cfg.get("db_url", "sqlite:///data/faces.db"),
        help="SQLAlchemy DB URL (e.g., postgresql+psycopg2://user:pass@host/db)",
    )
    return parser.parse_args()


def main():
    config = load_config()
    args = parse_args(config)
    input_dir = args.input
    output_file = args.output
    
    print("Face Recognition - Encoding Known Faces")
    print("=" * 50)
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Directory '{input_dir}' does not exist.")
        return False
        
    # Get image files
    image_files = []
    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if os.path.isfile(file_path) and validate_image_file(file_path):
            image_files.append(file_path)
    
    if not image_files:
        print(f"No valid image files found in '{input_dir}'.")
        print("Please add some face images and try again.")
        return False
    
    print(f"Found {len(image_files)} image files")
    
    known_encodings = []
    known_names = []
    
    # Process each image
    for image_path in image_files:
        print(f"Processing: {os.path.basename(image_path)}")
        
        # Load image
        image = load_image_safely(image_path)
        if image is None:
            continue
            
        # Get person name
        person_name = get_person_name_from_filename(image_path)
        
        # Get face encodings
        face_encodings = get_face_encodings_from_image(image, model=args.model)
        
        if not face_encodings:
            print(f"  Warning: No faces detected in {os.path.basename(image_path)}")
            continue
            
        if len(face_encodings) > 1:
            print(f"  Warning: Multiple faces detected, using first face for {person_name}")
            
        # Store encoding
        encoding = face_encodings[0]
        known_encodings.append(encoding)
        known_names.append(person_name)
        
        print(f"  Successfully encoded: {person_name}")
    
    if not known_encodings:
        print("No face encodings were created.")
        return False
    
    if args.use_db:
        engine = get_engine(args.db_url)
        init_db(engine)
        Session = get_session_maker(engine)
        repo = FaceRepository(Session)
        added = 0
        for enc, name in zip(known_encodings, known_names):
            repo.add_face(name, enc)
            added += 1
        print(f"\n✓ Saved {added} encodings into database: {args.db_url}")
        print("You can now run 'python3 recognize.py --use-db --db-url ...' to start recognition.")
        return True
    else:
        # Save to pickle file
        encodings_data = {
            "encodings": known_encodings,
            "names": known_names,
            "total_faces": len(known_encodings)
        }
        success = save_encodings(encodings_data, output_file)
        
        if success:
            print(f"\n✓ Successfully encoded {len(known_encodings)} faces!")
            print(f"Recognized individuals:")
            for i, name in enumerate(set(known_names), 1):
                count = known_names.count(name)
                print(f"  {i}. {name} ({count} encoding{'s' if count > 1 else ''})")
            print(f"\nYou can now run 'python3 recognize.py' to start recognition.")
            return True
        else:
            print("Failed to save encodings.")
            return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)