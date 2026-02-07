#!/usr/bin/env python3
"""
Register a student by ID and name using a photo file. Saves encoding to DB.
"""

import io
import argparse
import numpy as np
import face_recognition

from database import get_engine, init_db, get_session_maker, StudentRepository


def parse_args():
    p = argparse.ArgumentParser(description="Register a student with a photo")
    p.add_argument("--student-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--photo", required=True, help="Path to student face photo")
    p.add_argument("--db-url", default="sqlite:///data/faces.db")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    engine = get_engine(args.db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    repo = StudentRepository(Session)

    image = face_recognition.load_image_file(args.photo)
    locs = face_recognition.face_locations(image)
    if not locs:
        print("No face found in the provided image.")
        return 2
    encs = face_recognition.face_encodings(image, locs)
    if not encs:
        print("Failed to extract face encoding.")
        return 3
    repo.add_student(args.student_id, args.name, np.asarray(encs[0]), image_path=args.photo)
    print(f"Registered student {args.student_id} - {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


