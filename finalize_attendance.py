#!/usr/bin/env python3
"""
Finalize daily attendance by marking all students who were not present as absent.
Run this once at the end of the day.
"""

import argparse
from datetime import date as date_cls

from database import (
    get_engine,
    init_db,
    get_session_maker,
    StudentRepository,
    AttendancePresentRepository,
    AttendanceAbsentRepository,
)


def parse_args():
    p = argparse.ArgumentParser(description="Finalize attendance and mark absentees")
    p.add_argument("--db-url", default="sqlite:///data/faces.db")
    p.add_argument("--date", default=str(date_cls.today()), help="YYYY-MM-DD (defaults to today)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    engine = get_engine(args.db_url)
    init_db(engine)
    Session = get_session_maker(engine)

    student_repo = StudentRepository(Session)
    present_repo = AttendancePresentRepository(Session)
    absent_repo = AttendanceAbsentRepository(Session)

    _, meta = student_repo.get_all_encodings()  # (id, student_id, name)
    total = 0
    marked_absent = 0
    for sid, code, name in meta:
        total += 1
        if not present_repo.has_marked_today(sid, args.date):
            absent_repo.mark_absent(sid, args.date)
            marked_absent += 1

    print(f"Finalized attendance for {args.date}: total students={total}, marked absent={marked_absent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


