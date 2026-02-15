import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)

celery_app = Celery(
    "armistead",
    broker=CELERY_BROKER_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.notification_tasks",
        "app.tasks.portal_tasks",
        "app.tasks.compliance_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    # Phase 2: Nudge Engine
    "check-milestone-reminders": {
        "task": "app.tasks.notification_tasks.check_milestone_reminders",
        "schedule": crontab(minute=0),  # Every hour
    },
    "send-queued-emails": {
        "task": "app.tasks.notification_tasks.send_queued_emails",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "expire-stale-drafts": {
        "task": "app.tasks.notification_tasks.expire_stale_drafts",
        "schedule": crontab(hour=0, minute=30),  # Daily 12:30 AM UTC
    },
    # Phase 3: Portal cleanup
    "cleanup-portal-access-logs": {
        "task": "app.tasks.portal_tasks.cleanup_access_logs",
        "schedule": crontab(hour=2, minute=0),  # Daily 2 AM UTC
    },
    # Phase 7: Compliance & performance
    "nightly-compliance-evaluation": {
        "task": "app.tasks.compliance_tasks.evaluate_all_compliance",
        "schedule": crontab(hour=3, minute=0),  # Daily 3 AM UTC
    },
    "nightly-performance-snapshots": {
        "task": "app.tasks.compliance_tasks.compute_performance_snapshots",
        "schedule": crontab(hour=4, minute=0),  # Daily 4 AM UTC
    },
}
