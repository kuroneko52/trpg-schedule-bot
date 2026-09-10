# app/bot/bot_commands.py
import asyncio
import discord
from discord.ext import commands

# データ層
from data.schedule_store import load_data, save_all

# 表示層
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
# Bot 起動時処理
# -----------------------------
@bot.event
async def on_ready():
    print(f"Bot Ready: {bot.user}")
    data = await asyncio.to_thread(load_data)
    await refresh_display(bot, data)
    await save_all(data)  # 初期表示も保存

# -----------------------------
# 予定追加コマンド
# -----------------------------
@bot.command()
async def add(ctx, date_str: str, *, event_info: str):
    async with data_lock:
        # Json読み込み
        data = await asyncio.to_thread(load_data)

        # 日付がなければJson作成
        if date_str not in data["schedules"]:
            data["schedules"][date_str] = []

        # 予定追加
        data["schedules"][date_str].append(event_info.strip())

        # 共通保存処理
        await save_all(data)

        # Discord表示を更新してリアクションを追加
        success = await refresh_display(bot, data)
        await ctx.message.add_reaction('✅' if success else '⚠️')

# -----------------------------
# 予定削除コマンド
# -----------------------------
@bot.command(name="del")
async def del_command(ctx, date_str: str, num: int):
    async with data_lock:
        # Json読み込み
        data = await asyncio.to_thread(load_data)

        # 削除処理
        if date_str in data["schedules"]:
            try:
                # 指定された予定を削除
                data["schedules"][date_str].pop(num - 1)

                # 予定が空なら日付ごと削除
                if not data["schedules"][date_str]:
                    del data["schedules"][date_str]

                # 共通保存処理
                await save_all(data)

                # Discord表示を更新してリアクションを追加
                success = await refresh_display(bot, data)
                await ctx.message.add_reaction('🗑️' if success else '⚠️')

            except:
                await ctx.send("⚠️ 番号が正しくありません")

