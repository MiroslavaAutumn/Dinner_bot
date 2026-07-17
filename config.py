import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WIFE_CHAT_ID = int(os.getenv("WIFE_CHAT_ID", "0"))
HUSBAND_CHAT_ID = int(os.getenv("HUSBAND_CHAT_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "foodbot.db")

DEFAULT_SCHEDULE_TIME = "16:00"  # используется, если время ещё не задано через /settime

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден. Скопируй .env.example в .env и заполни значения."
    )
if not WIFE_CHAT_ID or not HUSBAND_CHAT_ID:
    raise RuntimeError(
        "WIFE_CHAT_ID и HUSBAND_CHAT_ID должны быть заполнены в .env. "
        "Узнать свой chat_id можно, написав боту @userinfobot."
    )
