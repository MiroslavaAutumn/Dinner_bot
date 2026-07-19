import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from config import BOT_TOKEN, WIFE_CHAT_ID, HUSBAND_CHAT_ID
import database as db
from scheduler import setup_scheduler
from handlers import admin, daily

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _set_commands_safe(bot: Bot, commands: list[BotCommand], chat_id: int, label: str):
    """Устанавливает меню команд для конкретного чата.
    Если чат ещё не 'известен' Telegram (человек ни разу не писал боту) —
    не роняем весь бот, а просто предупреждаем в лог и пробуем в следующий раз."""
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id))
    except TelegramBadRequest as e:
        logger.warning(
            "Не удалось настроить меню команд для %s (chat_id=%s): %s. "
            "Это нормально, если человек ещё ни разу не писал боту — "
            "попробуй ещё раз после того, как он отправит /start.",
            label, chat_id, e,
        )


async def setup_commands(bot: Bot):
    # По умолчанию (на случай, если кто-то посторонний напишет боту) — пусто
    await bot.set_my_commands([], scope=BotCommandScopeDefault())

    # Админские команды видны только в чате жены
    admin_commands = [
        BotCommand(command="add", description="Добавить заготовку"),
        BotCommand(command="list", description="Показать остатки"),
        BotCommand(command="edit", description="Изменить количество или переименовать"),
        BotCommand(command="delete", description="Удалить позицию"),
        BotCommand(command="setgarnish", description="Изменить гарниры для мяса"),
        BotCommand(command="settime", description="Установить время ежедневного вопроса"),
        BotCommand(command="setreminder", description="Установить время напоминания"),
        BotCommand(command="setcancel", description="Установить время на изменение выбора"),
        BotCommand(command="showcancel", description="Показать время на изменение выбора"),
        BotCommand(command="ask", description="Спросить мужа прямо сейчас"),
        BotCommand(command="help", description="Список всех команд"),
        BotCommand(command="start", description="Приветственное сообщение"),
    ]

    await _set_commands_safe(bot, admin_commands, WIFE_CHAT_ID, "жены")

    # Команды мужа видны только в его чате
    husband_commands = [
        BotCommand(command="food", description="Что приготовить сегодня?"),
        BotCommand(command="help", description="Список команд"),
        BotCommand(command="start", description="Приветственное сообщение"),
        BotCommand(command="cancel", description="Отменить выбор"),
    ]
    await _set_commands_safe(bot, husband_commands, HUSBAND_CHAT_ID, "мужа")


async def main():
    await db.init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(daily.router)

    await setup_commands(bot)
    await setup_scheduler(bot)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())