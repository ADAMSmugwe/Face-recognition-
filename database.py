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
    create_engine,
    func,
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


