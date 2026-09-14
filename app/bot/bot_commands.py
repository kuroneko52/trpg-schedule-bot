import asyncio
import discord
import os
import json
from discord.ext import commands

# Redis 永続化
from data.schedule_store import (
    load_data_from_redis,
    save_all,
    normalize_date_key,
    save_data_to_redis
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
    if "/" not in date_str:
        return False
    try:
        m, d = map(int, date_str.split("/"))
        return 1 <= m <= 12 and 1 <= d <= 31
    except:
        return False

# -----------------------------
# Bot 起動時
# -----------------------------
@bot.event
async def on_ready():
    print(f"Bot Ready: {bot.user}")

    data = load_data_from_redis()

    # schedules/message_ids が壊れていたら「操作を拒否するだけ」
    if not isinstance(data.get("schedules"), dict):
        print("⚠ schedules が壊れています。initjson を実行してください。")
        data["schedules"] = {}  # ← ここは空にするだけ（初期化ではない）

    if not isinstance(data.get("message_ids"), dict):
        print("⚠ message_ids が壊れています。initjson を実行してください。")
        data["message_ids"] = {}

    save_all(data)
    await refresh_display(bot, data)

# -----------------------------
# 予定追加
# -----------------------------
@bot.command(name="add")
async def add_command(ctx, date_str: str, *, event_info: str):
    async with data_lock:
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        data = load_data_from_redis()

        if not isinstance(data.get("schedules"), dict):
            await ctx.send("⚠️ データ形式が壊れています。initjson を実行してください。")
            return

        normalized_key = normalize_date_key(date_str)
        if not normalized_key:
            await ctx.send("⚠️ 日付形式が不正です")
            return

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

        if not isinstance(data.get("schedules"), dict):
            await ctx.send("⚠️ データ形式が壊れています。initjson を実行してください。")
            return

        normalized_key = normalize_date_key(date_str)
        if not normalized_key:
            await ctx.send("⚠️ 日付形式が不正です")
            return

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
# Redis Dump
# -----------------------------
@bot.command(name="dump")
async def dump(ctx):
    data = load_data_from_redis()
    await ctx.send(f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```")

# -----------------------------
# Redis 初期化
# -----------------------------
@bot.command(name="initjson")
async def initjson(ctx):
    data = {"schedules": {}, "message_ids": {}}
    save_data_to_redis(data)
    await ctx.send("✅ Redis のデータを初期化したよ")

