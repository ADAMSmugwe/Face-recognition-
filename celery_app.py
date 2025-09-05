import os
from celery import Celery


def make_celery() -> Celery:
    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    backend_url = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    app = Celery("face_recognition", broker=broker_url, backend=backend_url)
    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
    app.conf.accept_content = ["json"]
    app.conf.result_expires = 3600
    return app


celery = make_celery()


