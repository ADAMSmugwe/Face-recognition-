#!/usr/bin/env python3
"""
List faces stored in the database using SQLAlchemy.
"""

import argparse
from database import get_engine, init_db, get_session_maker, FaceRepository


def parse_args():
    p = argparse.ArgumentParser(description="List faces in the database")
    p.add_argument(
        "--db-url",
        default="sqlite:///data/faces.db",
        help="SQLAlchemy DB URL (e.g., postgresql+psycopg2://user:pass@host/db)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    engine = get_engine(args.db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    repo = FaceRepository(Session)
    faces = repo.list_faces()
    if not faces:
        print("No faces found.")
        return 0
    print(f"Found {len(faces)} face(s):")
    for f in faces:
        print(f"- id={f.id} name={f.name} created_at={f.created_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


