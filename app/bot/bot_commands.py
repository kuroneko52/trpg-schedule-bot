# app/bot/bot_commands.py
import asyncio
import discord
import os
from discord.ext import commands

# Redis 永続化
from data.schedule_store import (
    load_data_from_redis,
    save_all,
    normalize_date_key
)

# 表示更新
from display.schedule_display import refresh_display

data_lock = asyncio.Lock()

# -----------------------------
# Discord Bot 初期化
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    async def setup_hook(self):
        print("Bot setup completed.")

bot = MyBot(command_prefix='!', intents=intents)

# -----------------------------
# 日付ヴァリデーション
# -----------------------------
def validate_date(date_str: str):
    try:
        m, d = map(int, date_str.split("/"))
        return 1 <= m <= 12 and 1 <= d <= 31
    except:
        return False

# -----------------------------
# Bot 起動時（順序修正済み）
# -----------------------------
@bot.event
async def on_ready():
    print(f"Bot Ready: {bot.user}")

    data = load_data_from_redis()
    save_all(data)  # ★ 正規化 → ソート → cleanup
    await refresh_display(bot, data)  # ★ 表示更新

# -----------------------------
# 予定追加
# -----------------------------
@bot.command()
async def add_command(ctx, date_str: str, *, event_info: str):
    async with data_lock:
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        data = load_data_from_redis()

        normalized_key = normalize_date_key(date_str)

        data["schedules"].setdefault(normalized_key, [])
        data["schedules"][normalized_key].append(event_info.strip())

        save_all(data)
        await refresh_display(bot, data)
        await ctx.message.add_reaction('✅')

# -----------------------------
# 予定削除
# -----------------------------
@bot.command(name="del")
async def delete_command(ctx, date_str: str, num: int):
    async with data_lock:
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        data = load_data_from_redis()

        normalized_key = normalize_date_key(date_str)

        if normalized_key not in data["schedules"]:
            await ctx.send("⚠️ 指定された日付の予定がありません")
            return

        try:
            data["schedules"][normalized_key].pop(num - 1)
        except:
            await ctx.send("⚠️ 番号が正しくありません")
            return

        if not data["schedules"][normalized_key]:
            del data["schedules"][normalized_key]

        save_all(data)
        await refresh_display(bot, data)
        await ctx.message.add_reaction('🗑️')

# -----------------------------
# Redis 初期化
# -----------------------------
@bot.command()
async def initjson(ctx):
    data = {"schedules": {}, "message_ids": {}}
    save_all(data)
    await ctx.send("✅ Redis のデータを初期化したよ")

