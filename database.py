import sqlite3
from datetime import datetime

DB = "messages.db"


def get_db():
    return sqlite3.connect(DB)


def init_db():
    conn = get_db()
    c = conn.cursor()

    # ── Бот ──────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT,
            message_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'ru',
            is_active INTEGER DEFAULT 1,
            is_banned INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pending_messages (
            user_id INTEGER PRIMARY KEY,
            owner_message_id INTEGER,
            accumulated_text TEXT,
            has_media INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_status_msg (
            user_id INTEGER PRIMARY KEY,
            status_message_id INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            price TEXT NOT NULL,
            payment_info TEXT,
            photo_id TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS shop_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    c.execute("INSERT OR IGNORE INTO shop_settings (key, value) VALUES ('visible', '0')")
    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_messages (
            user_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payment_messages (
            user_id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            title TEXT,
            lang TEXT
        )
    """)

    # ── Todo (только для владельца) ───────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            deadline TEXT,
            priority TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'active',
            remind_minutes INTEGER DEFAULT 0,
            remind_sent INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ════════════════════════════════════════════════
#  БОТ — пользователи
# ════════════════════════════════════════════════

def save_message(user_id, username, full_name, text):
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (user_id, username, full_name, message_text, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, username or "", full_name or "", text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def set_user_lang(user_id, lang):
    conn = get_db()
    conn.execute(
        "INSERT INTO user_settings (user_id, language, is_active, is_banned) VALUES (?, ?, 1, 0) "
        "ON CONFLICT(user_id) DO UPDATE SET language=excluded.language",
        (user_id, lang)
    )
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = get_db()
    row = conn.execute("SELECT language FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else None

def is_user_active(user_id):
    conn = get_db()
    row = conn.execute("SELECT is_active FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] == 1 if row else False

def set_user_active(user_id, active):
    conn = get_db()
    conn.execute("UPDATE user_settings SET is_active=? WHERE user_id=?", (1 if active else 0, user_id))
    conn.commit()
    conn.close()

def is_banned(user_id):
    conn = get_db()
    row = conn.execute("SELECT is_banned FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] == 1 if row else False

def set_banned(user_id, banned):
    conn = get_db()
    conn.execute(
        "INSERT INTO user_settings (user_id, language, is_active, is_banned) VALUES (?, 'ru', 0, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET is_banned=excluded.is_banned",
        (user_id, 1 if banned else 0)
    )
    conn.commit()
    conn.close()

def get_pending(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT owner_message_id, accumulated_text, has_media FROM pending_messages WHERE user_id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    return row

def set_pending(user_id, owner_message_id, accumulated_text, has_media=False):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO pending_messages (user_id, owner_message_id, accumulated_text, has_media) VALUES (?, ?, ?, ?)",
        (user_id, owner_message_id, accumulated_text, 1 if has_media else 0)
    )
    conn.commit()
    conn.close()

def clear_pending(user_id):
    conn = get_db()
    conn.execute("DELETE FROM pending_messages WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_status_msg(user_id):
    conn = get_db()
    row = conn.execute("SELECT status_message_id FROM user_status_msg WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else None

def set_status_msg(user_id, msg_id):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO user_status_msg (user_id, status_message_id) VALUES (?, ?)",
        (user_id, msg_id)
    )
    conn.commit()
    conn.close()

def clear_status_msg(user_id):
    conn = get_db()
    conn.execute("DELETE FROM user_status_msg WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def save_bot_message(user_id, message_id):
    conn = get_db()
    conn.execute("INSERT INTO bot_messages (user_id, message_id) VALUES (?, ?)", (user_id, message_id))
    conn.commit()
    conn.close()

def get_bot_messages(user_id):
    conn = get_db()
    rows = conn.execute("SELECT message_id FROM bot_messages WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows]

def clear_bot_messages(user_id):
    conn = get_db()
    conn.execute("DELETE FROM bot_messages WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# ── Магазин ──────────────────────────────────────────

def get_shop_items():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, description, price, payment_info, photo_id "
        "FROM shop_items WHERE is_active=1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows

def get_shop_item(item_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, title, description, price, payment_info, photo_id "
        "FROM shop_items WHERE id=? AND is_active=1", (item_id,)
    ).fetchone()
    conn.close()
    return row

def add_shop_item(title, description, price, payment_info, photo_id):
    conn = get_db()
    conn.execute(
        "INSERT INTO shop_items (title, description, price, payment_info, photo_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (title, description, price, payment_info, photo_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def delete_shop_item(item_id):
    conn = get_db()
    conn.execute("UPDATE shop_items SET is_active=0 WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def is_shop_visible():
    conn = get_db()
    row = conn.execute("SELECT value FROM shop_settings WHERE key='visible'").fetchone()
    conn.close()
    return row[0] == '1' if row else False

def set_shop_visible(visible: bool):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO shop_settings (key, value) VALUES ('visible', ?)",
        ('1' if visible else '0',)
    )
    conn.commit()
    conn.close()

def save_payment_msg(user_id, message_id, title, lang):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO payment_messages (user_id, message_id, title, lang) VALUES (?, ?, ?, ?)",
        (user_id, message_id, title, lang)
    )
    conn.commit()
    conn.close()

def get_payment_msg(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT message_id, title, lang FROM payment_messages WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row

def clear_payment_msg(user_id):
    conn = get_db()
    conn.execute("DELETE FROM payment_messages WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


# ════════════════════════════════════════════════
#  TODO — задачи владельца
# ════════════════════════════════════════════════

def get_tasks(status=None):
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status=? ORDER BY deadline ASC, id DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY deadline ASC, id DESC"
        ).fetchall()
    conn.close()
    return [_task_dict(r) for r in rows]

def get_task(task_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    return _task_dict(row) if row else None

def create_task(title, description, deadline, priority, remind_minutes):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO tasks (title, description, deadline, priority, remind_minutes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (title, description, deadline, priority, remind_minutes, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return task_id

def update_task(task_id, title, description, deadline, priority, remind_minutes):
    conn = get_db()
    conn.execute(
        "UPDATE tasks SET title=?, description=?, deadline=?, priority=?, remind_minutes=?, remind_sent=0 WHERE id=?",
        (title, description, deadline, priority, remind_minutes, task_id)
    )
    conn.commit()
    conn.close()

def complete_task(task_id):
    conn = get_db()
    conn.execute("UPDATE tasks SET status='done' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def reset_reminder(task_id):
    conn = get_db()
    conn.execute("UPDATE tasks SET remind_sent=0 WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def get_pending_reminders():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status='active' AND remind_minutes > 0 "
        "AND remind_sent=0 AND deadline IS NOT NULL AND deadline != ''"
    ).fetchall()
    conn.close()
    return [_task_dict(r) for r in rows]

def mark_reminder_sent(task_id):
    conn = get_db()
    conn.execute("UPDATE tasks SET remind_sent=1 WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def _task_dict(row):
    if not row:
        return None
    return {
        "id": row[0], "title": row[1], "description": row[2],
        "deadline": row[3], "priority": row[4], "status": row[5],
        "remind_minutes": row[6], "remind_sent": row[7], "created_at": row[8],
    }
