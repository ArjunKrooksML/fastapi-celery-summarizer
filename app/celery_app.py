from celery import Celery
from app.core.config import settings

celery = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["worker.tasks"]
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,#expire results
    task_track_started=True,
)

if __name__ == "__main__":
    celery.start()