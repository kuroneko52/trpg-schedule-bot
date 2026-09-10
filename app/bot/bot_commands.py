# app/bot/bot_commands.py
import asyncio
import discord
import os
from discord.ext import commands

# データ層
from data.schedule_store import load_data_from_discord, save_all

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
# 日付ヴァリデーション関数
# -----------------------------
def validate_date(date_str: str):
    try:
        m, d = map(int, date_str.split("/"))
        if not (1 <= m <= 12 and 1 <= d <= 31):
            return False
        return True
    except:
        return False

# -----------------------------
# Bot 起動時処理
# -----------------------------
@bot.event
async def on_ready():
    print(f"Bot Ready: {bot.user}")
    data = await load_data_from_discord(bot)
    await refresh_display(bot, data)
    await save_all(bot, data)  # 初期表示も保存

# -----------------------------
# 予定追加コマンド
# -----------------------------
@bot.command()
async def add(ctx, date_str: str, *, event_info: str):
    async with data_lock:
        # 日付ヴァリデーション
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        # Json読み込み
        data = await load_data_from_discord(bot)

        # 日付がなければJson作成
        if date_str not in data["schedules"]:
            data["schedules"][date_str] = []

        # 予定追加
        data["schedules"][date_str].append(event_info.strip())

        # 共通保存処理
        await save_all(bot, data)

        # Discord表示を更新してリアクションを追加
        success = await refresh_display(bot, data)
        await ctx.message.add_reaction('✅' if success else '⚠️')

# -----------------------------
# 予定削除コマンド
# -----------------------------
@bot.command(name="del")
async def del_command(ctx, date_str: str, num: int):
    async with data_lock:
        # 日付ヴァリデーション
        if not validate_date(date_str):
            await ctx.send("⚠️ 日付は 9/10 の形式で入力してください")
            return

        # Json読み込み
        data = await load_data_from_discord(bot)

        # 削除処理
        if date_str in data["schedules"]:
            try:
                # 指定された予定を削除
                data["schedules"][date_str].pop(num - 1)

                # 予定が空なら日付ごと削除
                if not data["schedules"][date_str]:
                    del data["schedules"][date_str]

                # 共通保存処理
                await save_all(bot, data)

                # Discord表示を更新してリアクションを追加
                success = await refresh_display(bot, data)
                await ctx.message.add_reaction('🗑️' if success else '⚠️')

            except:
                await ctx.send("⚠️ 番号が正しくありません")
        else:
            await ctx.send("⚠️ 指定された日付の予定がありません")

# -----------------------------
# 予定削除コマンド
# -----------------------------
@bot.command()
async def initjson(ctx):
    """schedule-json の初期化（保存メッセージを bot が作成）"""
    channel_id = int(os.environ.get("JSON_STORAGE_CHANNEL_ID"))
    channel = bot.get_channel(channel_id)

    if not channel:
        await ctx.send("⚠️ JSON_STORAGE_CHANNEL_ID が不正です")
        return

    # 新しい保存メッセージを bot が送る
    new_msg = await channel.send('{"schedules": {}, "message_ids": {}}')

    # 新しいメッセージIDを .env に書き込むのはできないので
    # data に保存しておいて、save_all で永続化する
    data = {
            "schedules": {},
            "message_ids": {}
            }

    # 保存メッセージの ID をセット
    data["storage_message_id"] = new_msg.id

    # JSON_STORAGE_ID を使う構造なので、ここで上書き
    os.environ["JSON_STORAGE_ID"] = str(new_msg.id)

    # Discord に保存
    await save_all(bot, data)

    await ctx.send(f"✅ 初期化完了！ 新しい JSON_STORAGE_ID は `{new_msg.id}` だよ")

