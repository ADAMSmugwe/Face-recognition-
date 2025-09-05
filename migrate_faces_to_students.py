#!/usr/bin/env python3
"""
One-time migration: copy all encodings from Faces → Students so attendance mode can recognize them.
Student ID is generated from name or a sequential index.
"""

import argparse
import re
import numpy as np

from database import (
    get_engine, init_db, get_session_maker,
    FaceRepository, StudentRepository,
)


def slugify(name: str) -> str:
    s = (name or "student").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return s or "student"


def parse_args():
    p = argparse.ArgumentParser(description="Migrate Faces to Students")
    p.add_argument("--db-url", default="sqlite:///data/faces.db")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    engine = get_engine(args.db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    face_repo = FaceRepository(Session)
    student_repo = StudentRepository(Session)

    encs, names = face_repo.get_all_faces()
    if not encs:
        print("No faces found to migrate.")
        return 0

    count = 0
    for idx, (enc, name) in enumerate(zip(encs, names), 1):
        sid = f"{slugify(name)}_{idx:03d}"
        student_repo.add_student(sid, name or sid, np.asarray(enc))
        count += 1

    print(f"Migrated {count} face encodings into students table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


