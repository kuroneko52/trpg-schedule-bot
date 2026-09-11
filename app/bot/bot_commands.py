# app/bot/bot_commands.py
import asyncio
import discord
import os
from discord.ext import commands

# データ層（ローカル永続化）
from data.schedule_store import load_data_from_local, request_save

# 表示層
from display.schedule_display import refresh_display, schedule_refresh

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
    data = await load_data_from_local()
    await refresh_display(bot, data)
    await request_save(data)

# -----------------------------
# 予定追加
# -----------------------------
@bot.command()
async def add(ctx, date_str: str, *, event_info: str):
    async with data_lock:
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        data = await load_data_from_local()

        if date_str not in data["schedules"]:
            data["schedules"][date_str] = []

        data["schedules"][date_str].append(event_info.strip())

        await request_save(data)
        await schedule_refresh(bot, data)
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

        data = await load_data_from_local()

        if date_str in data["schedules"]:
            try:
                data["schedules"][date_str].pop(num - 1)

                if not data["schedules"][date_str]:
                    del data["schedules"][date_str]

                await request_save(data)
                await schedule_refresh(bot, data)
                await ctx.message.add_reaction('🗑️')

            except:
                await ctx.send("⚠️ 番号が正しくありません")
        else:
            await ctx.send("⚠️ 指定された日付の予定がありません")

# -----------------------------
# JSON 初期化
# -----------------------------
@bot.command()
async def initjson(ctx):
    data = {"schedules": {}, "message_ids": {}}
    await request_save(data)
    await ctx.send("✅ ローカル schedule.json を初期化したよ")

