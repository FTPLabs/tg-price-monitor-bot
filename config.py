import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")

CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "1800"))
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/tracks.db")
