"""
SQLAlchemy database models and helpers for face recognition storage.

Supports PostgreSQL (preferred) and SQLite (default for local testing).
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

import numpy as np
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    LargeBinary,
    String,
    Date,
    create_engine,
    func,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session


Base = declarative_base()


class Face(Base):
    __tablename__ = "faces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    encoding = Column(LargeBinary, nullable=False)
    length = Column(Integer, nullable=False)
    dtype = Column(String, nullable=False)
    image_path = Column(String, nullable=True)
    image_data = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    encoding = Column(LargeBinary, nullable=False)
    length = Column(Integer, nullable=False)
    dtype = Column(String, nullable=False)
    image_path = Column(String, nullable=True)
    image_data = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    time = Column(DateTime, server_default=func.now(), nullable=False)
    status = Column(String, nullable=False, default="Present")


class AttendancePresent(Base):
    __tablename__ = "attendance_present"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    time = Column(DateTime, server_default=func.now(), nullable=False)


class AttendanceAbsent(Base):
    __tablename__ = "attendance_absent"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)


def get_engine(db_url: str):
    if db_url.startswith("sqlite"):
        # Ensure directory exists for SQLite file paths like sqlite:///data/faces.db
        try:
            tail = db_url.split("sqlite:///", 1)[-1]
            if tail and "/" in tail:
                os.makedirs(os.path.dirname(tail), exist_ok=True)
        except Exception:
            pass
    return create_engine(db_url, future=True)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def get_session_maker(engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class FaceRepository:
    """Repository for reading/writing faces in the database."""

    def __init__(self, session_maker: sessionmaker):
        self._session_maker = session_maker

    def add_face(
        self,
        name: Optional[str],
        encoding: np.ndarray,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
    ) -> int:
        if not isinstance(encoding, np.ndarray):
            raise ValueError("encoding must be a numpy.ndarray")
        arr = np.asarray(encoding)
        face = Face(
            name=name,
            encoding=arr.tobytes(),
            length=int(arr.size),
            dtype=str(arr.dtype),
            image_path=image_path,
            image_data=image_bytes,
        )
        with self._session_maker() as session:  # type: Session
            session.add(face)
            session.commit()
            session.refresh(face)
            return int(face.id)

    def get_all_faces(self) -> Tuple[List[np.ndarray], List[Optional[str]]]:
        with self._session_maker() as session:  # type: Session
            rows = session.query(Face).all()
            names: List[Optional[str]] = []
            encodings: List[np.ndarray] = []
            for r in rows:
                arr = np.frombuffer(r.encoding, dtype=r.dtype).reshape(-1)
                if arr.size != r.length:
                    arr = np.frombuffer(r.encoding, dtype=np.float64).reshape(-1)
                encodings.append(arr)
                names.append(r.name or "Unknown")
            return encodings, names

    def list_faces(self) -> List[Face]:
        with self._session_maker() as session:  # type: Session
            return session.query(Face).order_by(Face.created_at.desc()).all()


class StudentRepository:
    def __init__(self, session_maker: sessionmaker):
        self._session_maker = session_maker

    def add_student(self, student_id: str, name: str, encoding: np.ndarray, image_path: Optional[str] = None, image_bytes: Optional[bytes] = None) -> int:
        arr = np.asarray(encoding)
        row = Student(
            student_id=student_id,
            name=name,
            encoding=arr.tobytes(),
            length=int(arr.size),
            dtype=str(arr.dtype),
            image_path=image_path,
            image_data=image_bytes,
        )
        with self._session_maker() as session:  # type: Session
            session.add(row)
            session.commit()
            session.refresh(row)
            return int(row.id)

    def get_all_students(self) -> List[Student]:
        with self._session_maker() as session:
            return session.query(Student).order_by(Student.created_at.desc()).all()

    def get_all_encodings(self) -> Tuple[List[np.ndarray], List[Tuple[int, str, str]]]:
        with self._session_maker() as session:
            rows = session.query(Student).all()
            encodings: List[np.ndarray] = []
            meta: List[Tuple[int, str, str]] = []  # (id, student_id, name)
            for r in rows:
                arr = np.frombuffer(r.encoding, dtype=r.dtype).reshape(-1)
                if arr.size != r.length:
                    arr = np.frombuffer(r.encoding, dtype=np.float64).reshape(-1)
                encodings.append(arr)
                meta.append((int(r.id), r.student_id, r.name))
            return encodings, meta


class AttendanceRepository:
    def __init__(self, session_maker: sessionmaker):
        self._session_maker = session_maker

    def mark_present(self, student_db_id: int, on_date) -> int:
        from datetime import date as date_cls
        if not hasattr(on_date, "year"):
            on_date = date_cls.today()
        with self._session_maker() as session:
            # Prevent duplicate for day
            existing = session.query(Attendance).filter(Attendance.student_id == student_db_id, Attendance.date == on_date).first()
            if existing:
                return int(existing.id)
            row = Attendance(student_id=student_db_id, date=on_date, status="Present")
            session.add(row)
            session.commit()
            session.refresh(row)
            return int(row.id)

    def has_marked_today(self, student_db_id: int, on_date) -> bool:
        with self._session_maker() as session:
            existing = session.query(Attendance).filter(Attendance.student_id == student_db_id, Attendance.date == on_date).first()
            return existing is not None

    def export_range(self, start_date, end_date) -> List[Tuple[str, str, str]]:
        # returns (student_id, name, date)
        with self._session_maker() as session:
            # Join via manual fetch to avoid ORM complexity
            rows = session.execute(
                text(
                    """
                    SELECT s.student_id, s.name, a.date, a.status
                    FROM attendance a
                    JOIN students s ON s.id = a.student_id
                    WHERE a.date BETWEEN :start AND :end
                    ORDER BY a.date DESC
                    """
                ),
                {"start": start_date, "end": end_date},
            ).fetchall()
            return [(r[0], r[1], str(r[2]), r[3]) for r in rows]


class AttendancePresentRepository:
    def __init__(self, session_maker: sessionmaker):
        self._session_maker = session_maker

    def has_marked_today(self, student_db_id: int, on_date) -> bool:
        with self._session_maker() as session:
            existing = session.execute(
                text(
                    "SELECT 1 FROM attendance_present WHERE student_id=:sid AND date=:d LIMIT 1"
                ),
                {"sid": student_db_id, "d": on_date},
            ).fetchone()
            return existing is not None

    def mark_present(self, student_db_id: int, on_date) -> int:
        from datetime import date as date_cls
        if not hasattr(on_date, "year"):
            on_date = date_cls.today()
        with self._session_maker() as session:
            session.execute(
                text(
                    "INSERT INTO attendance_present (student_id, date) SELECT :sid, :d WHERE NOT EXISTS (SELECT 1 FROM attendance_present WHERE student_id=:sid AND date=:d)"
                ),
                {"sid": student_db_id, "d": on_date},
            )
            session.commit()
            rowid = session.execute(text("SELECT last_insert_rowid()")).scalar() if session.bind.dialect.name == "sqlite" else 0
            return int(rowid or 0)

    def export_range(self, start_date, end_date) -> List[Tuple[str, str, str]]:
        with self._session_maker() as session:
            rows = session.execute(
                text(
                    """
                    SELECT s.student_id, s.name, p.date
                    FROM attendance_present p
                    JOIN students s ON s.id = p.student_id
                    WHERE p.date BETWEEN :start AND :end
                    ORDER BY p.date DESC
                    """
                ),
                {"start": start_date, "end": end_date},
            ).fetchall()
            return [(r[0], r[1], str(r[2])) for r in rows]


class AttendanceAbsentRepository:
    def __init__(self, session_maker: sessionmaker):
        self._session_maker = session_maker

    def mark_absent(self, student_db_id: int, on_date) -> None:
        with self._session_maker() as session:
            session.execute(
                text(
                    "INSERT INTO attendance_absent (student_id, date) SELECT :sid, :d WHERE NOT EXISTS (SELECT 1 FROM attendance_absent WHERE student_id=:sid AND date=:d)"
                ),
                {"sid": student_db_id, "d": on_date},
            )
            session.commit()

    def export_range(self, start_date, end_date) -> List[Tuple[str, str, str]]:
        with self._session_maker() as session:
            rows = session.execute(
                text(
                    """
                    SELECT s.student_id, s.name, a.date
                    FROM attendance_absent a
                    JOIN students s ON s.id = a.student_id
                    WHERE a.date BETWEEN :start AND :end
                    ORDER BY a.date DESC
                    """
                ),
                {"start": start_date, "end": end_date},
            ).fetchall()
            return [(r[0], r[1], str(r[2])) for r in rows]


