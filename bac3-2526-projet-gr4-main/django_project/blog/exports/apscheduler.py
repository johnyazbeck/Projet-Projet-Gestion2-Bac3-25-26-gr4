from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone
from .scheduler import run_scheduled_exports

scheduler = None

def start_safe():
    global scheduler

    if scheduler is not None:
        return  # empêche double lancement

    scheduler = BackgroundScheduler(timezone=timezone.get_current_timezone())
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        run_scheduled_exports,
        trigger="cron",
        minute="*",
        args=["daily"],
        id="daily_exports",
        replace_existing=True,
    )

    scheduler.add_job(
        run_scheduled_exports,
        trigger="cron",
        minute="*",
        args=["weekly"],
        id="weekly_exports",
        replace_existing=True,
    )

    scheduler.add_job(
        run_scheduled_exports,
        trigger="cron",
        minute="*",
        args=["monthly"],
        id="monthly_exports",
        replace_existing=True,
    )

    scheduler.start()
    print("✅ APScheduler started")
