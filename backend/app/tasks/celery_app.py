from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "invoice_reminder",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.reminder_dispatch"],
)

celery_app.conf.beat_schedule = {
    "dispatch-reminders": {
        "task": "app.tasks.reminder_dispatch.dispatch_due_reminders",
        "schedule": crontab(minute="*/5"),
    }
}
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.timezone = "UTC"
