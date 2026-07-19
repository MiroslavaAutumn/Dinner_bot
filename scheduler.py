from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from config import DEFAULT_SCHEDULE_TIME

scheduler = AsyncIOScheduler()
JOB_ID = "daily_question"
FINALIZE_JOB_ID = "finalize_choices"
REMINDER_JOB_ID = "reminder"


async def setup_scheduler(bot: Bot):
    import database as db
    from handlers.daily import send_daily_question

    time_str = await db.get_setting("schedule_time", DEFAULT_SCHEDULE_TIME)
    _add_daily_job(bot, time_str)

    # Добавляем джоб для фиксации выборов (каждый час)
    scheduler.add_job(
        db.finalize_expired_choices,
        CronTrigger(minute=0),
        id=FINALIZE_JOB_ID,
        replace_existing=True,
    )

    # Добавляем джоб для напоминания
    reminder_time = await db.get_reminder_time()
    _add_reminder_job(bot, reminder_time)

    scheduler.start()


def reschedule_daily_job(bot: Bot, time_str: str):
    if scheduler.get_job(JOB_ID):
        scheduler.remove_job(JOB_ID)
    _add_daily_job(bot, time_str)


def reschedule_reminder_job(bot: Bot, time_str: str):
    if scheduler.get_job(REMINDER_JOB_ID):
        scheduler.remove_job(REMINDER_JOB_ID)
    _add_reminder_job(bot, time_str)


def _add_daily_job(bot: Bot, time_str: str):
    from handlers.daily import send_daily_question_with_check

    hour, minute = map(int, time_str.split(":"))
    scheduler.add_job(
        send_daily_question_with_check,
        CronTrigger(hour=hour, minute=minute),
        args=[bot],
        id=JOB_ID,
        replace_existing=True,
    )


def _add_reminder_job(bot: Bot, time_str: str):
    from handlers.daily import send_reminder

    hour, minute = map(int, time_str.split(":"))
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=hour, minute=minute),
        args=[bot],
        id=REMINDER_JOB_ID,
        replace_existing=True,
    )