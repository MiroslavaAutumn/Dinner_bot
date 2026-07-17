from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from config import DEFAULT_SCHEDULE_TIME

scheduler = AsyncIOScheduler()
JOB_ID = "daily_question"


async def setup_scheduler(bot: Bot):
    import database as db
    from handlers.daily import send_daily_question

    time_str = await db.get_setting("schedule_time", DEFAULT_SCHEDULE_TIME)
    _add_job(bot, time_str, send_daily_question)
    scheduler.start()


def reschedule_daily_job(bot: Bot, time_str: str):
    from handlers.daily import send_daily_question
    if scheduler.get_job(JOB_ID):
        scheduler.remove_job(JOB_ID)
    _add_job(bot, time_str, send_daily_question)


def _add_job(bot: Bot, time_str: str, callback):
    hour, minute = map(int, time_str.split(":"))
    scheduler.add_job(
        callback,
        CronTrigger(hour=hour, minute=minute),
        args=[bot],
        id=JOB_ID,
        replace_existing=True,
    )