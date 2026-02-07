import io
import os
from typing import List, Tuple

import numpy as np
try:
    import face_recognition  # type: ignore
    _HAS_FACE_RECOG = True
except Exception:
    face_recognition = None  # type: ignore
    _HAS_FACE_RECOG = False

from celery_app import celery
from database import get_engine, init_db, get_session_maker, FaceRepository
from database import StudentRepository, AttendancePresentRepository, AttendanceAbsentRepository
from database import StudentSampleRepository


def _get_repo(db_url: str) -> FaceRepository:
    engine = get_engine(db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    return FaceRepository(Session)


@celery.task(name="batch_encode_folder")
def batch_encode_folder(input_dir: str, db_url: str) -> dict:
    if not _HAS_FACE_RECOG:
        return {"added": 0, "failed": [], "error": "face_recognition_unavailable"}
    added = 0
    failed: List[str] = []
    repo = _get_repo(db_url)

    for fname in os.listdir(input_dir):
        path = os.path.join(input_dir, fname)
        if not os.path.isfile(path):
            continue
        try:
            image = face_recognition.load_image_file(path)  # type: ignore
            locs = face_recognition.face_locations(image)  # type: ignore
            if not locs:
                failed.append(fname)
                continue
            encs = face_recognition.face_encodings(image, locs)  # type: ignore
            if not encs:
                failed.append(fname)
                continue
            name = os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").title()
            repo.add_face(name, np.asarray(encs[0]))
            added += 1
        except Exception:
            failed.append(fname)

    return {"added": added, "failed": failed}


@celery.task(name="recognize_image_bytes")
def recognize_image_bytes(image_b64: str, db_url: str, tolerance: float = 0.6) -> dict:
    if not _HAS_FACE_RECOG:
        return {"results": [], "error": "face_recognition_unavailable"}
    import base64

    try:
        if "," in image_b64 and image_b64.strip().startswith("data:"):
            image_b64 = image_b64.split(",", 1)[1]
        image_bytes = base64.b64decode(image_b64)
    except Exception as e:
        return {"error": f"invalid_base64: {e}"}

    repo = _get_repo(db_url)
    image_np = face_recognition.load_image_file(io.BytesIO(image_bytes))  # type: ignore
    locs = face_recognition.face_locations(image_np)  # type: ignore
    encs = face_recognition.face_encodings(image_np, locs)  # type: ignore
    if not encs:
        return {"results": []}

    known_encs, known_names = repo.get_all_faces()
    results = []
    for (top, right, bottom, left), enc in zip(locs, encs):
        if not known_encs:
            results.append({"name": "Unknown", "confidence": 0.0, "box": [top, right, bottom, left]})
            continue
        dists = face_recognition.face_distance(known_encs, enc)
        if dists.size == 0:
            results.append({"name": "Unknown", "confidence": 0.0, "box": [top, right, bottom, left]})
            continue
        idx = int(dists.argmin())
        best = float(dists[idx])
        if best <= tolerance:
            results.append({
                "name": known_names[idx],
                "confidence": round(1.0 - best, 4),
                "box": [top, right, bottom, left],
            })
        else:
            results.append({"name": "Unknown", "confidence": 0.0, "box": [top, right, bottom, left]})
    return {"results": results}


@celery.task(name="recompute_student_encodings")
def recompute_student_encodings(db_url: str, samples_limit: int = 100, min_samples: int = 5) -> dict:
    """Recompute each student's encoding as a centroid of their latest samples (and original)."""
    engine = get_engine(db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    srepo = StudentRepository(Session)
    samp_repo = StudentSampleRepository(Session)

    students = srepo.get_all_students()
    updated = 0
    skipped = 0
    for s in students:
        base = srepo.get_encoding_by_db_id(int(s.id))
        samples = samp_repo.get_samples(int(s.id), limit=int(samples_limit))
        if not samples:
            skipped += 1
            continue
        stack = [base] if base is not None else []
        stack.extend(samples)
        if len(stack) < int(min_samples):
            skipped += 1
            continue
        try:
            arr = np.vstack(stack)
            centroid = arr.mean(axis=0)
            srepo.update_student_encoding(int(s.id), centroid.astype(base.dtype if base is not None else np.float32))
            # Trim to last N samples
            try:
                samp_repo.delete_oldest(int(s.id), keep_last=int(samples_limit))
            except Exception:
                pass
            updated += 1
        except Exception:
            skipped += 1
            continue
    return {"updated": updated, "skipped": skipped}


@celery.task(name="finalize_absentees_task")
def finalize_absentees_task(db_url: str = "sqlite:///data/faces.db", day: str = None) -> dict:
    from datetime import date as date_cls
    engine = get_engine(db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    student_repo = StudentRepository(Session)
    present_repo = AttendancePresentRepository(Session)
    absent_repo = AttendanceAbsentRepository(Session)
    _, meta = student_repo.get_all_encodings()  # (id, student_id, name)
    d = day or str(date_cls.today())
    total = 0
    marked_absent = 0
    for sid, code, name in meta:
        total += 1
        if not present_repo.has_marked_today(sid, d):
            absent_repo.mark_absent(sid, d)
            marked_absent += 1
    return {"date": d, "total": total, "absent": marked_absent}


