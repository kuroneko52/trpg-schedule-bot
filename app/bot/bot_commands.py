# app/bot/bot_commands.py
import asyncio
import discord
import os
from discord.ext import commands

# ローカル永続化
from data.schedule_store import load_data_from_local, save_all

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
# Bot 起動時
# -----------------------------
@bot.event
async def on_ready():
    print(f"Bot Ready: {bot.user}")

    data = load_data_from_local()
    await refresh_display(bot, data)
    save_all(data)

# -----------------------------
# 予定追加
# -----------------------------
@bot.command()
async def add(ctx, date_str: str, *, event_info: str):
    async with data_lock:
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        data = load_data_from_local()

        data["schedules"].setdefault(date_str, [])
        data["schedules"][date_str].append(event_info.strip())

        save_all(data)
        await refresh_display(bot, data)
        await ctx.message.add_reaction('✅')

# -----------------------------
# 予定削除
# -----------------------------
@bot.command(name="del")
async def del_command(ctx, date_str: str, num: int):
    async with data_lock:
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        data = load_data_from_local()

        if date_str not in data["schedules"]:
            await ctx.send("⚠️ 指定された日付の予定がありません")
            return

        try:
            data["schedules"][date_str].pop(num - 1)
        except:
            await ctx.send("⚠️ 番号が正しくありません")
            return

        if not data["schedules"][date_str]:
            del data["schedules"][date_str]

        save_all(data)
        await refresh_display(bot, data)
        await ctx.message.add_reaction('🗑️')

# -----------------------------
# JSON 初期化
# -----------------------------
@bot.command()
async def initjson(ctx):
    data = {"schedules": {}, "message_ids": {}}
    save_all(data)
    await ctx.send("✅ ローカル schedule.json を初期化したよ")

