import asyncio
import socket
import aiohttp
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import uvicorn

import bot_instance
from config import BOT_TOKEN, OWNER_ID
from database import (
    init_db,
    get_tasks, get_task, create_task, update_task,
    complete_task, delete_task, reset_reminder,
    get_pending_reminders, mark_reminder_sent
)
from handlers import user, owner, shop

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ── Telegram reminder sender ───────────────────────────────

async def send_tg_reminder(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        await session.post(url, json={
            "chat_id": OWNER_ID, "text": text, "parse_mode": "HTML"
        })

async def check_reminders():
    from datetime import datetime, timedelta
    tasks = get_pending_reminders()
    now = datetime.now()
    for task in tasks:
        try:
            deadline = datetime.strptime(task["deadline"], "%Y-%m-%dT%H:%M")
        except Exception:
            continue
        remind_at = deadline - timedelta(minutes=task["remind_minutes"])
        if now >= remind_at:
            total_min = int((deadline - now).total_seconds() / 60)
            if total_min <= 0:
                time_str = "срок уже истёк"
            elif total_min < 60:
                time_str = f"через {total_min} мин"
            else:
                h, m = divmod(total_min, 60)
                time_str = f"через {h} ч {m} мин" if m else f"через {h} ч"

            priority_label = {"low": "Низкий", "normal": "Средний", "high": "Высокий"}.get(task["priority"], "Средний")
            text = f"<b>Напоминание</b>\n\n<b>{task['title']}</b>\n"
            if task["description"]:
                text += f"{task['description']}\n"
            text += f"\nПриоритет: {priority_label}\nДедлайн: {deadline.strftime('%d.%m.%Y %H:%M')}\nОсталось: {time_str}"
            try:
                await send_tg_reminder(text)
                mark_reminder_sent(task["id"])
            except Exception as e:
                log.error(f"Reminder error: {e}")

async def reminder_loop():
    while True:
        await check_reminders()
        await asyncio.sleep(30)

# ── FastAPI app ────────────────────────────────────────────

app = FastAPI()

# Папка static и templates лежат рядом с main.py
import os
BASE = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "tasks_active": get_tasks("active"),
        "tasks_done":   get_tasks("done"),
    })

@app.post("/task/create")
async def task_create(
    title:          str = Form(...),
    description:    str = Form(""),
    deadline:       str = Form(""),
    priority:       str = Form("normal"),
    remind_minutes: int = Form(0),
):
    create_task(title, description, deadline or None, priority, remind_minutes)
    return RedirectResponse("/", status_code=303)

@app.post("/task/{task_id}/complete")
async def task_complete(task_id: int):
    complete_task(task_id)
    return JSONResponse({"ok": True})

@app.post("/task/{task_id}/delete")
async def task_delete(task_id: int):
    delete_task(task_id)
    return JSONResponse({"ok": True})

@app.get("/task/{task_id}/edit", response_class=HTMLResponse)
async def task_edit_page(request: Request, task_id: int):
    task = get_task(task_id)
    if not task:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "edit.html", {"task": task})

@app.post("/task/{task_id}/edit")
async def task_edit_save(
    task_id:        int,
    title:          str = Form(...),
    description:    str = Form(""),
    deadline:       str = Form(""),
    priority:       str = Form("normal"),
    remind_minutes: int = Form(0),
):
    update_task(task_id, title, description, deadline or None, priority, remind_minutes)
    return RedirectResponse("/", status_code=303)

@app.post("/task/{task_id}/reset-reminder")
async def task_reset_reminder(task_id: int):
    reset_reminder(task_id)
    return JSONResponse({"ok": True})


# ── Entry point — запускает бот + веб одновременно ────────

async def run_bot():
    # Принудительно IPv4 для PythonAnywhere и др.
    original_init = aiohttp.TCPConnector.__init__
    def patched_init(self, *args, **kwargs):
        kwargs.setdefault("family", socket.AF_INET)
        original_init(self, *args, **kwargs)
    aiohttp.TCPConnector.__init__ = patched_init

    bot_instance.bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(owner.router)
    dp.include_router(shop.router)
    dp.include_router(user.router)

    try:
        await bot_instance.bot.send_message(
            OWNER_ID,
            "<b>Бот запущен.</b>\n\n"
            "/history — последние 20 сообщений\n"
            "/clear — очистить БД\n"
            "/banlist — забаненные\n"
            "/shop — управление магазином\n\n"
            "Сайт задач: http://localhost:8000",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await dp.start_polling(bot_instance.bot)


async def run_web():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    init_db()
    await asyncio.gather(
        run_bot(),
        run_web(),
        reminder_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())