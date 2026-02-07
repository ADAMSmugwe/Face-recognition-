"""
SQLite-backed storage for face encodings and optional image metadata.
"""

import os
import sqlite3
from typing import List, Tuple, Optional
import numpy as np


class FaceDatabase:
    def __init__(self, db_path: str = "data/faces.db") -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                encoding BLOB NOT NULL,
                length INTEGER NOT NULL,
                dtype TEXT NOT NULL,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.commit()

    def add_face(self, name: str, encoding: np.ndarray, image_path: Optional[str] = None) -> int:
        if not isinstance(encoding, np.ndarray):
            raise ValueError("encoding must be a numpy.ndarray")
        encoding = np.asarray(encoding)
        length = int(encoding.size)
        dtype = str(encoding.dtype)
        blob = encoding.tobytes()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO faces (name, encoding, length, dtype, image_path) VALUES (?, ?, ?, ?, ?)",
            (name, blob, length, dtype, image_path),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_all_faces(self) -> Tuple[List[np.ndarray], List[str]]:
        cur = self.conn.cursor()
        cur.execute("SELECT name, encoding, length, dtype FROM faces")
        rows = cur.fetchall()
        names: List[str] = []
        encodings: List[np.ndarray] = []
        for name, blob, length, dtype in rows:
            arr = np.frombuffer(blob, dtype=dtype)
            if arr.size != length:
                # Fallback if metadata mismatch
                arr = np.frombuffer(blob, dtype=np.float64)
            encodings.append(arr.reshape(-1))
            names.append(name)
        return encodings, names

    def delete_face(self, face_id: int) -> None:
        self.conn.execute("DELETE FROM faces WHERE id = ?", (face_id,))
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


