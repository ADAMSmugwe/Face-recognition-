#!/usr/bin/env python3
"""
Simple Flask app to upload images and store face encodings in the database.
"""

import io
import os
from typing import Optional

import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

import face_recognition

from database import get_engine, init_db, get_session_maker, FaceRepository


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

    @app.route("/")
    def index():
        faces = repo.list_faces()
        return render_template("index.html", faces=faces)

    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        if request.method == "POST":
            name: Optional[str] = request.form.get("name") or None
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

                # Save first face encoding
                repo.add_face(name, np.asarray(encs[0]), image_path=filename, image_bytes=image_bytes)
                flash("Face saved successfully", "success")
                return redirect(url_for("index"))
            except Exception as e:
                flash(f"Error processing image: {e}", "error")
                return redirect(request.url)

        return render_template("upload.html")

    return app


if __name__ == "__main__":
    url = os.environ.get("DB_URL", "sqlite:///data/faces.db")
    app = create_app(url)
    app.run(host="127.0.0.1", port=5000, debug=True)


