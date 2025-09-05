#!/usr/bin/env python3
"""
Multi-camera real-time recognition with periodic DB refresh.
"""

import os
import sys
import time
import threading
import argparse
from typing import List, Tuple

import cv2
import numpy as np
import face_recognition

from database import get_engine, init_db, get_session_maker, FaceRepository


def load_known(db_url: str) -> Tuple[List[np.ndarray], List[str]]:
    engine = get_engine(db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    repo = FaceRepository(Session)
    return repo.get_all_faces()


class SharedEncodings:
    def __init__(self, db_url: str, refresh_interval: float = 5.0):
        self.db_url = db_url
        self.refresh_interval = refresh_interval
        self.known_encodings: List[np.ndarray] = []
        self.known_names: List[str] = []
        self._lock = threading.Lock()
        self._last_refresh = 0.0
        self.refresh(force=True)

    def refresh(self, force: bool = False):
        now = time.time()
        if not force and (now - self._last_refresh) < self.refresh_interval:
            return
        try:
            enc, names = load_known(self.db_url)
            with self._lock:
                self.known_encodings = enc
                self.known_names = names
            self._last_refresh = now
        except Exception:
            self._last_refresh = now

    def snapshot(self) -> Tuple[List[np.ndarray], List[str]]:
        with self._lock:
            return list(self.known_encodings), list(self.known_names)


def camera_worker(index: int, shared: SharedEncodings, tolerance: float, model: str):
    window_name = f"Camera {index}"
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"[Cam {index}] Error: Could not open camera")
        return
    process_this_frame = True
    start_time = time.time()
    frames = 0
    scaled_face_locations = []
    face_names = []
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"[Cam {index}] Error: Could not read frame")
                break

            shared.refresh()

            if process_this_frame:
                small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                locs = face_recognition.face_locations(rgb, model=model)
                encs = face_recognition.face_encodings(rgb, locs)

                known_encodings, known_names = shared.snapshot()
                face_names = []
                for enc in encs:
                    if len(known_encodings) == 0:
                        face_names.append(("Unknown", 0.0))
                        continue
                    dists = face_recognition.face_distance(known_encodings, enc)
                    if dists.size == 0:
                        face_names.append(("Unknown", 0.0))
                        continue
                    idx = int(np.argmin(dists))
                    if dists[idx] <= tolerance:
                        face_names.append((known_names[idx], float(1.0 - dists[idx])))
                    else:
                        face_names.append(("Unknown", 0.0))

                scaled_face_locations = [(t*4, r*4, b*4, l*4) for (t, r, b, l) in locs]

            process_this_frame = not process_this_frame

            # Draw
            for (top, right, bottom, left), (name, conf) in zip(scaled_face_locations, face_names):
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                label = f"{name} ({conf:.2f})" if conf else name
                cv2.putText(frame, label, (left, max(0, top - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

            # FPS
            frames += 1
            elapsed = time.time() - start_time
            if elapsed > 0:
                fps = frames / elapsed
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

    finally:
        cap.release()
        cv2.destroyWindow(window_name)


def parse_args():
    p = argparse.ArgumentParser(description="Multi-camera face recognition")
    p.add_argument("--cameras", type=int, nargs="+", default=[0], help="Camera indices, e.g. 0 1 2")
    p.add_argument("--db-url", default="sqlite:///data/faces.db")
    p.add_argument("--tolerance", type=float, default=0.6)
    p.add_argument("--model", default="hog", choices=["hog", "cnn"])
    p.add_argument("--refresh-interval", type=float, default=5.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    shared = SharedEncodings(args.db_url, refresh_interval=args.refresh_interval)

    threads: List[threading.Thread] = []
    for idx in args.cameras:
        t = threading.Thread(target=camera_worker, args=(idx, shared, args.tolerance, args.model), daemon=True)
        t.start()
        threads.append(t)

    print("Multi-camera recognition running. Press Ctrl+C to stop.")
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())


