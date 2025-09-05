#!/usr/bin/env python3
"""
Flask web interface for managing and testing the face database.

Features:
- Home page: list faces in DB
- Upload page: add a face by uploading a photo
- Recognize page/API: upload an image and get recognition results
- Delete faces
"""

import io
import os
import base64
from typing import Optional

import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

import face_recognition

from database import (
    get_engine, init_db, get_session_maker,
    FaceRepository, AttendanceRepository,
    AttendancePresentRepository, AttendanceAbsentRepository,
    StudentRepository,
)
from datetime import date as date_cls
from tasks import batch_encode_folder, recognize_image_bytes, finalize_absentees_task
from cloud_storage import S3Client
from monitoring import metrics

DEFAULT_TOLERANCE = float(os.environ.get("TOLERANCE", 0.6))


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def allowed_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def create_app(db_url: str = "sqlite:///data/faces.db") -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("UPLOAD_SECRET", "dev-secret")
    app.config["DB_URL"] = db_url

    engine = get_engine(db_url)
    init_db(engine)
    Session = get_session_maker(engine)
    repo = FaceRepository(Session)
    student_repo = StudentRepository(Session)

    @app.route("/")
    def index():
        metrics.inc("page.index")
        faces = repo.list_faces()
        return render_template("index.html", faces=faces)

    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        metrics.inc("page.upload")
        if request.method == "POST":
            with metrics.timer("upload.process_time"):
                name: Optional[str] = request.form.get("name") or None
                student_id: Optional[str] = request.form.get("student_id") or None
                as_student = request.form.get("as_student") in ("on", "true", "1")
                file = request.files.get("file")
                if not file or file.filename == "":
                    flash("No file selected", "error")
                    return redirect(request.url)
                if not allowed_file(file.filename):
                    flash("Unsupported file type", "error")
                    return redirect(request.url)

                filename = secure_filename(file.filename)
                image_bytes = file.read()
                try:
                    image_np = face_recognition.load_image_file(io.BytesIO(image_bytes))
                    locs = face_recognition.face_locations(image_np)
                    if not locs:
                        flash("No face detected in the uploaded image", "error")
                        return redirect(request.url)
                    encs = face_recognition.face_encodings(image_np, locs)
                    if not encs:
                        flash("Failed to extract encoding", "error")
                        return redirect(request.url)

                    # Optionally store image in S3
                    image_path = filename
                    try:
                        if os.environ.get("S3_BUCKET"):
                            s3 = S3Client()
                            key = s3.put_image(name or "unknown", filename, image_bytes)
                            image_path = f"s3://{s3.bucket}/{key}"
                    except Exception:
                        pass

                    # Save first face encoding (include stored path)
                    if as_student or student_id:
                        sid = student_id or (name or "student").lower().replace(" ", "_")
                        student_repo.add_student(sid, name or sid, np.asarray(encs[0]), image_path=image_path, image_bytes=image_bytes)
                        flash("Student saved successfully", "success")
                    else:
                        repo.add_face(name, np.asarray(encs[0]), image_path=image_path, image_bytes=image_bytes)
                        flash("Face saved successfully", "success")
                    return redirect(url_for("index"))
                except Exception as e:
                    flash(f"Error processing image: {e}", "error")
                    return redirect(request.url)

        return render_template("upload.html")

    @app.route("/faces/<int:face_id>/delete", methods=["POST"]) 
    def delete_face(face_id: int):
        try:
            with Session() as s:
                s.query(type(repo).list_faces.__annotations__.get('return', object)).filter_by(id=face_id)
            # Simpler: direct SQL since we have small scope
            eng = get_engine(app.config["DB_URL"])  # ensure engine
            # Recreate repo to be safe
            _Session = get_session_maker(eng)
            _repo = FaceRepository(_Session)
            # Use session to delete by id
            with _Session() as session:
                session.execute("DELETE FROM faces WHERE id = :id", {"id": face_id})
                session.commit()
            flash("Face deleted", "success")
        except Exception as e:
            flash(f"Failed to delete: {e}", "error")
        return redirect(url_for("index"))

    # -------- REST API Helpers -------- #
    def _read_image_bytes_from_request() -> Optional[bytes]:
        # Multipart file
        file = request.files.get("file")
        if file and file.filename:
            return file.read()
        # JSON base64
        if request.is_json:
            data = request.get_json(silent=True) or {}
            b64 = data.get("image_b64")
            if isinstance(b64, str) and b64:
                try:
                    # Strip data URL prefix if present
                    if "," in b64 and b64.strip().startswith("data:"):
                        b64 = b64.split(",", 1)[1]
                    return base64.b64decode(b64)
                except Exception:
                    return None
        return None

    def _load_known(repo: FaceRepository):
        encodings, names = repo.get_all_faces()
        return encodings, names

    def _recognize_image(image_bytes: bytes, tolerance: float):
        image_np = face_recognition.load_image_file(io.BytesIO(image_bytes))
        locs = face_recognition.face_locations(image_np)
        encs = face_recognition.face_encodings(image_np, locs)
        if not encs:
            return []
        known_encs, known_names = _load_known(repo)
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
        return results

    @app.route("/recognize", methods=["GET", "POST"]) 
    def recognize_page():
        if request.method == "POST":
            file = request.files.get("file")
            tolerance = float(request.form.get("tolerance") or DEFAULT_TOLERANCE)
            if not file or file.filename == "":
                flash("No file selected", "error")
                return redirect(request.url)
            if not allowed_file(file.filename):
                flash("Unsupported file type", "error")
                return redirect(request.url)
            image_bytes = file.read()
            try:
                with metrics.timer("recognize.page_time"):
                    results = _recognize_image(image_bytes, tolerance)
                metrics.inc("recognize.success")
                return render_template("recognize.html", results=results, tolerance=tolerance)
            except Exception as e:
                metrics.inc("recognize.error")
                flash(f"Error processing image: {e}", "error")
                return redirect(request.url)
        return render_template("recognize.html", results=None, tolerance=DEFAULT_TOLERANCE)

    @app.route("/api/recognize", methods=["POST"]) 
    def recognize_api():
        # Accept multipart file or JSON { image_b64 }
        with metrics.timer("api.recognize_time"):
            tolerance = DEFAULT_TOLERANCE
            if request.is_json:
                try:
                    data = request.get_json(silent=True) or {}
                    if "tolerance" in data:
                        tolerance = float(data.get("tolerance", DEFAULT_TOLERANCE))
                except Exception:
                    pass
            else:
                try:
                    tolerance = float(request.form.get("tolerance") or DEFAULT_TOLERANCE)
                except Exception:
                    tolerance = DEFAULT_TOLERANCE

            image_bytes = _read_image_bytes_from_request()
            if not image_bytes:
                return jsonify({"error": "no_image"}), 400
            try:
                results = _recognize_image(image_bytes, tolerance)
                metrics.inc("api.recognize.success")
                return jsonify({"results": results, "tolerance": tolerance})
            except Exception as e:
                metrics.inc("api.recognize.error")
                return jsonify({"error": str(e)}), 500

    @app.get("/api/health")
    def api_health():
        return jsonify({"status": "ok"})

    @app.get("/api/faces")
    def api_list_faces():
        metrics.inc("api.faces.list")
        faces = repo.list_faces()
        payload = [
            {
                "id": f.id,
                "name": f.name,
                "created_at": f.created_at.isoformat() if getattr(f, "created_at", None) else None,
                "image_path": getattr(f, "image_path", None),
            }
            for f in faces
        ]
        return jsonify({"faces": payload})

    @app.get("/api/faces/<int:face_id>")
    def api_get_face(face_id: int):
        metrics.inc("api.faces.get")
        faces = repo.list_faces()
        for f in faces:
            if int(f.id) == face_id:
                return jsonify({
                    "id": f.id,
                    "name": f.name,
                    "created_at": f.created_at.isoformat() if getattr(f, "created_at", None) else None,
                    "image_path": getattr(f, "image_path", None),
                })
        return jsonify({"error": "not_found"}), 404

    @app.post("/api/faces")
    def api_create_face():
        with metrics.timer("api.create_face_time"):
            name = None
            if request.is_json:
                data = request.get_json(silent=True) or {}
                if isinstance(data.get("name"), str):
                    name = data.get("name")
            else:
                name = request.form.get("name") or None

            image_bytes = _read_image_bytes_from_request()
            if not image_bytes:
                return jsonify({"error": "no_image"}), 400
            try:
                image_np = face_recognition.load_image_file(io.BytesIO(image_bytes))
                locs = face_recognition.face_locations(image_np)
                if not locs:
                    return jsonify({"error": "no_face"}), 400
                encs = face_recognition.face_encodings(image_np, locs)
                if not encs:
                    return jsonify({"error": "no_encoding"}), 400
                face_id = repo.add_face(name, np.asarray(encs[0]), image_path=None, image_bytes=image_bytes)
                metrics.inc("api.faces.create.success")
                return jsonify({"id": face_id, "name": name}), 201
            except Exception as e:
                metrics.inc("api.faces.create.error")
                return jsonify({"error": str(e)}), 500

    # Async examples
    @app.post("/api/jobs/batch_encode")
    def api_jobs_batch_encode():
        data = request.get_json(silent=True) or {}
        input_dir = data.get("input_dir")
        if not input_dir or not os.path.isdir(input_dir):
            return jsonify({"error": "invalid_input_dir"}), 400
        job = batch_encode_folder.delay(input_dir, app.config["DB_URL"])
        return jsonify({"task_id": job.id}), 202

    @app.post("/api/jobs/recognize")
    def api_jobs_recognize():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("image_b64")
        tolerance = float(data.get("tolerance") or DEFAULT_TOLERANCE)
        if not image_b64:
            return jsonify({"error": "no_image_b64"}), 400
        job = recognize_image_bytes.delay(image_b64, app.config["DB_URL"], tolerance)
        return jsonify({"task_id": job.id}), 202

    @app.get("/api/jobs/<task_id>")
    def api_job_status(task_id: str):
        from celery_app import celery as celery_client

        res = celery_client.AsyncResult(task_id)
        payload = {
            "id": task_id,
            "state": res.state,
            "ready": res.ready(),
        }
        if res.ready():
            try:
                payload["result"] = res.get(propagate=False)
            except Exception as e:
                payload["error"] = str(e)
        return jsonify(payload)

    @app.post("/api/jobs/finalize_absentees")
    def api_jobs_finalize_absentees():
        data = request.get_json(silent=True) or {}
        day = data.get("date")
        job = finalize_absentees_task.delay(app.config["DB_URL"], day)
        return jsonify({"task_id": job.id}), 202

    @app.delete("/api/faces/<int:face_id>")
    def api_delete_face(face_id: int):
        metrics.inc("api.faces.delete")
        try:
            _Session = get_session_maker(get_engine(app.config["DB_URL"]))
            with _Session() as session:
                session.execute("DELETE FROM faces WHERE id = :id", {"id": face_id})
                session.commit()
            return jsonify({"deleted": face_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/faces/<int:face_id>/presigned")
    def api_presigned(face_id: int):
        metrics.inc("api.faces.presigned")
        key = None
        faces = repo.list_faces()
        for f in faces:
            if int(f.id) == face_id:
                path = getattr(f, "image_path", None)
                if path and path.startswith("s3://"):
                    bucket_key = path.replace("s3://", "", 1)
                    parts = bucket_key.split("/", 1)
                    if len(parts) == 2:
                        bucket, key = parts
                        s3 = S3Client(bucket=bucket)
                        url = s3.presigned_url(key)
                        return jsonify({"url": url})
                return jsonify({"error": "no_s3_path"}), 400
        return jsonify({"error": "not_found"}), 404

    # -------- Attendance Web & API -------- #
    @app.route("/attendance", methods=["GET"]) 
    def attendance_page():
        start = request.args.get("start") or str(date_cls.today())
        end = request.args.get("end") or str(date_cls.today())
        repo_att = AttendanceRepository(Session)
        rows = repo_att.export_range(start, end)  # (student_id, name, date, status)
        repo_present = AttendancePresentRepository(Session)
        repo_absent = AttendanceAbsentRepository(Session)
        present = repo_present.export_range(start, end)
        absent = repo_absent.export_range(start, end)
        return render_template("attendance.html", rows=rows, present=present, absent=absent, start=start, end=end)

    @app.get("/api/attendance")
    def api_attendance():
        start = request.args.get("start") or str(date_cls.today())
        end = request.args.get("end") or str(date_cls.today())
        repo_att = AttendanceRepository(Session)
        rows = repo_att.export_range(start, end)
        payload = [
            {"student_id": r[0], "name": r[1], "date": r[2], "status": r[3]}
            for r in rows
        ]
        return jsonify({"start": start, "end": end, "attendance": payload})

    @app.get("/api/attendance.csv")
    def api_attendance_csv():
        import csv
        from io import StringIO
        start = request.args.get("start") or str(date_cls.today())
        end = request.args.get("end") or str(date_cls.today())
        repo_att = AttendanceRepository(Session)
        rows = repo_att.export_range(start, end)
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["student_id", "name", "date", "status"])
        for r in rows:
            w.writerow(list(r))
        from flask import Response
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=attendance_{start}_to_{end}.csv"
            },
        )

    @app.get("/api/metrics")
    def api_metrics():
        return jsonify(metrics.export())

    return app


if __name__ == "__main__":
    url = os.environ.get("DB_URL", "sqlite:///data/faces.db")
    app = create_app(url)
    app.run(host="127.0.0.1", port=5000, debug=True)


