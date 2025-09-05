#!/usr/bin/env python3
"""
Export attendance records to CSV (and optionally XLSX if openpyxl is available).
"""

import csv
import argparse
from datetime import date

try:
    import openpyxl  # type: ignore
except Exception:
    openpyxl = None

from database import get_engine, init_db, get_session_maker, AttendanceRepository


def parse_args():
    p = argparse.ArgumentParser(description="Export attendance records")
    p.add_argument("--start", help="Start date YYYY-MM-DD", default=str(date.today()))
    p.add_argument("--end", help="End date YYYY-MM-DD", default=str(date.today()))
    p.add_argument("--db-url", default="sqlite:///data/faces.db")
    p.add_argument("--out", default="attendance.csv")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    engine = get_engine(args.db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    repo = AttendanceRepository(Session)
    rows = repo.export_range(args.start, args.end)

    # CSV export
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["student_id", "name", "date", "status"])
        for r in rows:
            writer.writerow(list(r))
    print(f"CSV exported to {args.out} ({len(rows)} rows)")

    # Optional XLSX
    if openpyxl and args.out.lower().endswith(".xlsx"):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Attendance"
        ws.append(["student_id", "name", "date", "status"])
        for r in rows:
            ws.append(list(r))
        wb.save(args.out)
        print(f"XLSX exported to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


