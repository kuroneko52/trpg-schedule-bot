import asyncio
import discord
import os
import json
from datetime import datetime
from discord.ext import commands


# ============================================================
# データ層（Redis 永続化）
# ============================================================

from data.schedule_store import (
    load_data_from_redis,
    save_all,
    save_data_to_redis
)

# ============================================================
# 表示層（Discord メッセージ更新）
# ============================================================

from display.schedule_display import refresh_display

data_lock = asyncio.Lock()

# ============================================================
# Discord Bot 初期化
# ============================================================

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    """
    Discord Bot の初期化クラス。
    setup_hook は起動時に一度だけ呼ばれる。
    """
    async def setup_hook(self):
        print("Bot setup completed.")

bot = MyBot(command_prefix='!', intents=intents)


# ============================================================
# Bot 起動時（壊れたデータは操作拒否）
# ============================================================

@bot.event
async def on_ready():
    """
    Bot 起動時に Redis のデータを読み込み、
    schedules / message_ids が壊れていれば操作を拒否する。
    正常なら save_all → refresh_display を実行する。
    """
    print(f"Bot Ready: {bot.user}")

    data = load_data_from_redis()
    broken = False

    if not isinstance(data.get("schedules"), dict):
        print("⚠ schedules が壊れています。")
        broken = True

    if not isinstance(data.get("message_ids"), dict):
        print("⚠ message_ids が壊れています。")
        broken = True

    if broken:
        return

    save_all(data)
    new_ids = await refresh_display(bot, data)
    data["message_ids"] = new_ids
    save_data_to_redis(data)


# ============================================================
# 予定追加コマンド
# ============================================================

@bot.command(name="add")
async def add_command(ctx, date_str: str, *, event_info: str):
    """
    MM/DD の予定を追加する。
    正規化後は YYYY/MM/DD で保存される。
    同月過去日付の防止
    """
    async with data_lock:
        data = load_data_from_redis()

        normalized_key = normalize_date_key(date_str)
        if not normalized_key:
            await ctx.send("⚠️ 日付形式が不正です")
            return

        _, m, d = map(int, normalized_key.split("/"))

        today = datetime.now().date()
        if m == today.month and d < today.day:
            await ctx.send("⚠️ 同月内過去日付の予定は追加できません")
            return

        data["schedules"].setdefault(normalized_key, [])
        data["schedules"][normalized_key].append(event_info.strip())

        save_all(data)
        new_ids = await refresh_display(bot, data)
        data["message_ids"] = new_ids
        await ctx.message.add_reaction('✅')


# ============================================================
# MM/DD → YYYY/MM/DD 正規化
# ============================================================

def normalize_date_key(key: str):
    """
    MM/DD を YYYY/MM/DD に正規化する。
    - MM/DD形式でなければ None
    - 存在しない月日は None
    - 月が現在より前なら翌年扱い
    """
    if "/" not in key:
        return None

    try:
        m, d = map(int, key.split("/"))
    except:
        return None

    try:
        datetime(datetime.now().year, m, d)
    except:
        return None

    today = datetime.now()
    year = today.year

    # 今日より前の月は翌年扱い
    if m < today.month:
        year += 1

    return f"{year}/{m:02d}/{d:02d}"


# ============================================================
# 予定削除コマンド
# ============================================================

@bot.command(name="del")
async def delete_command(ctx, date_str: str, num: int):
    """
    指定した MM/DD の予定を削除する。
    番号が不正・日付が存在しない場合は警告を返す。
    """
    async with data_lock:
        data = load_data_from_redis()

        normalized_key = normalize_date_key(date_str)
        if not normalized_key:
            await ctx.send("⚠️ 日付形式が不正です")
            return

        if normalized_key not in data["schedules"]:
            await ctx.send("⚠️ 指定された日付の予定がありません")
            return

        events = data["schedules"][normalized_key]

        if not (1 <= num <= len(events)):
            await ctx.send("  番号が正しくありません")
            return

        events.pop(num - 1)

        if not data["schedules"][normalized_key]:
            del data["schedules"][normalized_key]

        save_all(data)
        await refresh_display(bot, data)
        await ctx.message.add_reaction('🗑️')


# ============================================================
# Redis Dump（デバッグ用）
# ============================================================

@bot.command(name="dump")
async def dump(ctx):
    """
    Redis の schedules / message_ids をそのまま表示する。
    デバッグ用コマンド。
    """
    data = load_data_from_redis()
    await ctx.send(f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```")


# ============================================================
# Redis 初期化
# ============================================================

@bot.command(name="initjson")
async def initjson(ctx):
    """
    schedules / message_ids を完全初期化する。
    """
    data = {"schedules": {}, "message_ids": {}}
    save_data_to_redis(data)
    await ctx.send("✅ Redis のデータを初期化したよ")

