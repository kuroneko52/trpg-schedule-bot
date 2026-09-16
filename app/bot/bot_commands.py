import asyncio
import discord
import os
import json
from discord.ext import commands

# ============================================================
# データ層（Redis 永続化）
# ============================================================

from data.schedule_store import (
    load_data_from_redis,
    save_all,
    normalize_date_key,
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
# 日付バリデーション（MM/DD）
# ============================================================

def validate_date(date_str: str):
    """
    MM/DD の形式かどうかを判定する。
    月・日が数値として妥当でなければ False を返す。
    """
    if "/" not in date_str:
        return False
    try:
        m, d = map(int, date_str.split("/"))
        return 1 <= m <= 12 and 1 <= d <= 31
    except:
        return False


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
    await refresh_display(bot, data)


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
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        data = load_data_from_redis()

        if not isinstance(data.get("schedules"), dict):
            await ctx.send("⚠️ データ形式が壊れています。")
            return

        normalized_key = normalize_date_key(date_str)
        if not normalized_key:
            await ctx.send("⚠️ 日付形式が不正です")
            return

        try:
            y, m, d = map(int, normalized_key.split("/"))
            dt = datetime(y, m, d).date()
        except:
            await ctx.send("⚠️ 日付形式が不正です")
            return

        if dt < datetime.now().date():
            await ctx.send("⚠️ 同月過去日付の予定は追加できません")
            return

        data["schedules"].setdefault(normalized_key, [])
        data["schedules"][normalized_key].append(event_info.strip())

        save_all(data)
        await refresh_display(bot, data)
        await ctx.message.add_reaction('✅')


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
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        data = load_data_from_redis()

        if not isinstance(data.get("schedules"), dict):
            await ctx.send("⚠️ データ形式が壊れています。")
            return

        normalized_key = normalize_date_key(date_str)
        if not normalized_key:
            await ctx.send("⚠️ 日付形式が不正です")
            return

        try:
            y, m, d = map(int, normalized_key.split("/"))
            dt = datetime(y, m, d).date()
        except:
            await ctx.send("  日付形式が不正です")
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

