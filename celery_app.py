import os
from celery import Celery
from celery.schedules import crontab


def make_celery() -> Celery:
    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    backend_url = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    app = Celery("face_recognition", broker=broker_url, backend=backend_url)
    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
    app.conf.accept_content = ["json"]
    app.conf.result_expires = 3600
    # Optional: Celery beat schedule for daily absentee finalization (defaults 17:00)
    hour = int(os.environ.get("FINALIZE_HOUR", "17"))
    minute = int(os.environ.get("FINALIZE_MINUTE", "0"))
    app.conf.beat_schedule = {
        "finalize-absentees-daily": {
            "task": "finalize_absentees_task",
            "schedule": crontab(hour=hour, minute=minute),
        }
    }
    return app


celery = make_celery()


