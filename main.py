# main.py
# -----------------------------
# .env 読み込み（最優先）
# -----------------------------
try:
    from app.config.loadenv import load_env
    load_env()
except ModuleNotFoundError:
    pass

from app.server.server import run_flask
from app.bot.bot_commands import bot
from threading import Thread
import os

# -----------------------------
# 起動処理
# -----------------------------
if __name__ == "__main__":
    # Flask サーバー起動
    Thread(target=run_flask).start()

    # Discord Bot 起動
    bot.run(os.getenv("DISCORD_TOKEN"))

