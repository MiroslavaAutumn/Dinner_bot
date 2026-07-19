"""
Слой работы с базой данных.

Таблицы:
- items      — мясные заготовки с остатками (name, quantity)
- meat_garnishes — связь мясо <-> гарниры (разрешённые гарниры для каждого мяса)
- garnishes  — гарниры, без учёта количества (всегда "в наличии")
- salads     — салаты, без учёта количества (всегда "в наличии")
- settings   — произвольные настройки (например, время рассылки)
- meal_log   — история того, что выбрал муж (для истории/отладки)
"""

from __future__ import annotations

import aiosqlite
from datetime import datetime, timedelta
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meat_garnishes (
    meat_id INTEGER NOT NULL,
    garnish_id INTEGER NOT NULL,
    PRIMARY KEY (meat_id, garnish_id),
    FOREIGN KEY (meat_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (garnish_id) REFERENCES garnishes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS garnishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS salads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS meal_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    meat_name TEXT,
    garnish_name TEXT,
    salad_name TEXT,
    is_delivery INTEGER DEFAULT 0,
    delivery_request TEXT,
    meat_id INTEGER,
    selected_at TEXT,
    is_finalized INTEGER DEFAULT 1
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

    await migrate_default_garnishes()
    await migrate_meal_log()


async def migrate_meal_log():
    """Добавляет новые колонки в meal_log, если их нет."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(meal_log)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        if "meat_id" not in column_names:
            await db.execute("ALTER TABLE meal_log ADD COLUMN meat_id INTEGER")

        if "selected_at" not in column_names:
            await db.execute("ALTER TABLE meal_log ADD COLUMN selected_at TEXT")

        if "is_finalized" not in column_names:
            await db.execute("ALTER TABLE meal_log ADD COLUMN is_finalized INTEGER DEFAULT 1")

        await db.commit()


async def migrate_default_garnishes():
    """Переносит старые default_garnish в новую таблицу meat_garnishes."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(items)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        if "default_garnish" not in column_names:
            return

        cursor = await db.execute(
            "SELECT id, default_garnish FROM items WHERE default_garnish IS NOT NULL"
        )
        rows = await cursor.fetchall()

        for item_id, garnish_name in rows:
            cursor = await db.execute(
                "SELECT id FROM garnishes WHERE name = ?", (garnish_name,)
            )
            garnish_row = await cursor.fetchone()
            if garnish_row:
                garnish_id = garnish_row[0]
                await db.execute(
                    "INSERT OR IGNORE INTO meat_garnishes (meat_id, garnish_id) VALUES (?, ?)",
                    (item_id, garnish_id),
                )

        await db.execute("ALTER TABLE items DROP COLUMN default_garnish")
        await db.commit()


# ---------- items (мясо) ----------

async def add_meat_item(name: str, quantity: int, garnish_ids: list[int] | None = None):
    """Добавляет мясную заготовку с возможными гарнирами."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO items (name, quantity) VALUES (?, ?)",
            (name, quantity),
        )
        item_id = cursor.lastrowid

        if garnish_ids:
            for g_id in garnish_ids:
                await db.execute(
                    "INSERT INTO meat_garnishes (meat_id, garnish_id) VALUES (?, ?)",
                    (item_id, g_id),
                )

        await db.commit()
        return item_id


async def get_meats_in_stock() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM items WHERE quantity > 0 ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_items() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM items ORDER BY name")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_item_by_id(item_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_meat_garnishes(meat_id: int) -> list[dict]:
    """Возвращает список гарниров, разрешённых для данного мяса."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT g.* FROM garnishes g
            JOIN meat_garnishes mg ON mg.garnish_id = g.id
            WHERE mg.meat_id = ?
            ORDER BY g.name
            """,
            (meat_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def set_meat_garnishes(meat_id: int, garnish_ids: list[int]):
    """Заменяет список разрешённых гарниров для мяса."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM meat_garnishes WHERE meat_id = ?", (meat_id,))

        for g_id in garnish_ids:
            await db.execute(
                "INSERT INTO meat_garnishes (meat_id, garnish_id) VALUES (?, ?)",
                (meat_id, g_id),
            )

        await db.commit()


async def decrement_item(item_id: int, amount: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE items SET quantity = MAX(quantity - ?, 0) WHERE id = ?",
            (amount, item_id),
        )
        await db.commit()


async def set_item_quantity(item_id: int, quantity: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE items SET quantity = ? WHERE id = ?", (quantity, item_id)
        )
        await db.commit()


async def rename_item(item_id: int, new_name: str):
    """Переименовывает мясную заготовку."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE items SET name = ? WHERE id = ?",
            (new_name, item_id)
        )
        await db.commit()


async def delete_item(item_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await db.commit()


# ---------- garnishes ----------

async def add_garnish(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO garnishes (name) VALUES (?)", (name,)
        )
        await db.commit()


async def get_garnishes() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM garnishes ORDER BY name")
        return [dict(row) for row in await cursor.fetchall()]


async def rename_garnish(garnish_id: int, new_name: str):
    """Переименовывает гарнир."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE garnishes SET name = ? WHERE id = ?",
            (new_name, garnish_id)
        )
        await db.commit()


async def delete_garnish(garnish_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM garnishes WHERE id = ?", (garnish_id,))
        await db.commit()


# ---------- salads ----------

async def add_salad(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO salads (name) VALUES (?)", (name,))
        await db.commit()


async def get_salads() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM salads ORDER BY name")
        return [dict(row) for row in await cursor.fetchall()]


async def rename_salad(salad_id: int, new_name: str):
    """Переименовывает салат."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE salads SET name = ? WHERE id = ?",
            (new_name, salad_id)
        )
        await db.commit()


async def delete_salad(salad_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM salads WHERE id = ?", (salad_id,))
        await db.commit()


# ---------- settings ----------

async def get_setting(key: str, default: str | None = None) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


CANCEL_WINDOW_KEY = "cancel_window_minutes"

REMINDER_TIME_KEY = "reminder_time"

async def get_reminder_time() -> str:
    """Возвращает время отправки напоминания. По умолчанию '14:00'."""
    value = await get_setting(REMINDER_TIME_KEY, "14:00")
    return value


async def set_reminder_time(time_str: str):
    """Устанавливает время отправки напоминания."""
    await set_setting(REMINDER_TIME_KEY, time_str)


async def has_todays_choice() -> bool:
    """Проверяет, сделал ли муж выбор сегодня (независимо от статуса)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT 1 FROM meal_log 
            WHERE date(created_at) = date(?)
            AND is_delivery = 0
            LIMIT 1
            """,
            (datetime.now().isoformat(),)
        )
        row = await cursor.fetchone()
        return row is not None

async def get_cancel_window_minutes() -> int:
    """Возвращает время на изменение выбора в минутах. По умолчанию 240 (4 часа)."""
    value = await get_setting(CANCEL_WINDOW_KEY, "240")
    try:
        return int(value)
    except ValueError:
        return 240


async def set_cancel_window_minutes(minutes: int):
    """Устанавливает время на изменение выбора в минутах."""
    await set_setting(CANCEL_WINDOW_KEY, str(minutes))


# ---------- meal log ----------

async def log_meal(
    meat_name: str | None = None,
    garnish_name: str | None = None,
    salad_name: str | None = None,
    is_delivery: bool = False,
    delivery_request: str | None = None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO meal_log (created_at, meat_name, garnish_name, salad_name, "
            "is_delivery, delivery_request) VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                meat_name,
                garnish_name,
                salad_name,
                int(is_delivery),
                delivery_request,
            ),
        )
        await db.commit()


async def get_last_unfinalized_choice() -> dict | None:
    """Получает последний незафиксированный выбор мужа за сегодня."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM meal_log 
            WHERE is_finalized = 0 
            AND date(selected_at) = date(?)
            ORDER BY selected_at DESC 
            LIMIT 1
            """,
            (datetime.now().isoformat(),)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def cancel_choice(choice_id: int):
    """Отменяет выбор и возвращает остатки."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT meat_id FROM meal_log WHERE id = ?",
            (choice_id,)
        )
        row = await cursor.fetchone()
        if row and row[0]:
            meat_id = row[0]
            await db.execute(
                "UPDATE items SET quantity = quantity + 1 WHERE id = ?",
                (meat_id,)
            )
        await db.execute(
            "UPDATE meal_log SET is_finalized = 1 WHERE id = ?",
            (choice_id,)
        )
        await db.commit()


async def save_choice_with_meat_id(
    meat_id: int,
    meat_name: str,
    garnish_name: str | None,
    salad_name: str,
    is_delivery: bool = False,
    delivery_request: str | None = None,
) -> int:
    """Сохраняет выбор с meat_id для возможности возврата."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO meal_log 
            (created_at, meat_name, garnish_name, salad_name, is_delivery, 
             delivery_request, meat_id, selected_at, is_finalized) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                meat_name,
                garnish_name,
                salad_name,
                int(is_delivery),
                delivery_request,
                meat_id,
                datetime.now().isoformat(timespec="seconds"),
                0
            )
        )
        await db.commit()
        return cursor.lastrowid


async def finalize_expired_choices():
    """Фиксирует выборы, срок которых истёк."""
    cancel_minutes = await get_cancel_window_minutes()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id FROM meal_log 
            WHERE is_finalized = 0 
            AND datetime(selected_at) < datetime('now', '-' || ? || ' minutes')
            """,
            (cancel_minutes,)
        )
        rows = await cursor.fetchall()

        for row in rows:
            await db.execute(
                "UPDATE meal_log SET is_finalized = 1 WHERE id = ?",
                (row[0],)
            )
        await db.commit()

async def has_todays_meal_choice() -> bool:
    """Проверяет, сделал ли муж выбор БЛЮДА сегодня (не доставку)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT 1 FROM meal_log 
            WHERE date(created_at) = date(?)
            AND is_delivery = 0
            LIMIT 1
            """,
            (datetime.now().isoformat(),)
        )
        row = await cursor.fetchone()
        return row is not None


async def has_todays_any_choice() -> bool:
    """Проверяет, сделал ли муж любой выбор сегодня (блюдо или доставка)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT 1 FROM meal_log 
            WHERE date(created_at) = date(?)
            LIMIT 1
            """,
            (datetime.now().isoformat(),)
        )
        row = await cursor.fetchone()
        return row is not None