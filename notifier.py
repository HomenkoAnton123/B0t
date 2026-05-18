import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp

from database import get_pending_reminders, mark_reminder_sent

log = logging.getLogger(__name__)


async def send_telegram(token: str, chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with aiohttp.ClientSession() as session:
        await session.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


async def check_reminders(token: str, owner_id: int):
    tasks = get_pending_reminders()
    now = datetime.now()
    for task in tasks:
        try:
            deadline = datetime.strptime(task["deadline"], "%Y-%m-%dT%H:%M")
        except Exception:
            continue
        remind_delta = timedelta(minutes=task["remind_minutes"])
        remind_at = deadline - remind_delta
        if now >= remind_at:
            time_left = deadline - now
            total_minutes = int(time_left.total_seconds() / 60)
            if total_minutes <= 0:
                time_str = "срок уже истёк"
            elif total_minutes < 60:
                time_str = f"через {total_minutes} мин"
            else:
                hours = total_minutes // 60
                mins  = total_minutes % 60
                time_str = f"через {hours} ч {mins} мин" if mins else f"через {hours} ч"

            priority_label = {
                "low":    "Низкий",
                "normal": "Средний",
                "high":   "Высокий",
            }.get(task["priority"], "Средний")

            text = (
                f"<b>Напоминание о задаче</b>\n\n"
                f"<b>{task['title']}</b>\n"
            )
            if task["description"]:
                text += f"{task['description']}\n"
            text += (
                f"\nПриоритет: {priority_label}\n"
                f"Дедлайн: {deadline.strftime('%d.%m.%Y %H:%M')}\n"
                f"Осталось: {time_str}"
            )
            try:
                await send_telegram(token, owner_id, text)
                mark_reminder_sent(task["id"])
                log.info(f"Reminder sent for task {task['id']}")
            except Exception as e:
                log.error(f"Failed to send reminder: {e}")


def start_scheduler(app, token: str, owner_id: int):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_reminders,
        "interval",
        seconds=30,
        args=[token, owner_id],
    )
    scheduler.start()
    app.state.scheduler = scheduler
    log.info("Reminder scheduler started (every 30s)")
