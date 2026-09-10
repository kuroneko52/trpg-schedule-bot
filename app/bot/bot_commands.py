# app/bot/bot_commands.py
import asyncio
import discord
from discord.ext import commands

# データ層
from data.schedule_store import load_data, queue_save, github_worker

# 表示層
from display.schedule_display import refresh_display

data_lock = asyncio.Lock()

# -----------------------------
# Discord Bot 初期化
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True

# -----------------------------
# discord.py v2 正式対応 Bot クラス
# -----------------------------
class MyBot(commands.Bot):
    # Bot 初期化時に呼ばれる（v2 の正しい worker 起動場所）
    async def setup_hook(self):
        # GitHub 保存 worker をバックグラウンドで起動
        self.loop.create_task(github_worker())
        print("GitHub worker started.")

# Bot インスタンス生成
bot = MyBot(command_prefix='!', intents=intents)

# -----------------------------
# Bot 起動時処理
# -----------------------------
@bot.event
async def on_ready():
    print(f"Bot Ready: {bot.user}")
    # ローカル JSON 読み込み
    data = await asyncio.to_thread(load_data)
    # Discord 表示更新
    await refresh_display(bot, data)

# -----------------------------
# 予定追加コマンド
# -----------------------------
@bot.command()
async def add(ctx, date_str: str, *, event_info: str):
    async with data_lock:
        # ローカル JSON 読み込み
        data = await asyncio.to_thread(load_data)

        # 日付がなければ作成
        if date_str not in data["schedules"]:
            data["schedules"][date_str] = []

        # 予定追加
        data["schedules"][date_str].append(event_info.strip())

        # GitHub 保存要求（キュー化）
        await queue_save()

        # Discord 表示更新
        success = await refresh_display(bot, data)

        # 成功リアクション
        await ctx.message.add_reaction('✅' if success else '⚠️')

# -----------------------------
# 予定削除コマンド
# -----------------------------
@bot.command(name="del")
async def del_command(ctx, date_str: str, num: int):
    async with data_lock:
        # ローカル JSON 読み込み
        data = await asyncio.to_thread(load_data)

        if date_str in data["schedules"]:
            try:
                # 指定番号の予定削除
                data["schedules"][date_str].pop(num - 1)

                # 予定が空なら日付ごと削除
                if not data["schedules"][date_str]:
                    del data["schedules"][date_str]

                # GitHub 保存要求（キュー化）
                await queue_save()

                # Discord 表示更新
                success = await refresh_display(bot, data)

                # 成功リアクション
                await ctx.message.add_reaction('🗑️' if success else '⚠️')

            except:
                await ctx.send("⚠️ 番号が正しくありません")

