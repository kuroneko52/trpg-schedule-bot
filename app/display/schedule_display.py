# app/display/schedule_display.py
import os
import asyncio
import discord

# -----------------------------
# Discord 表示更新
# -----------------------------
async def refresh_display(bot, data):
    channel_id = int(os.environ.get("CHANNEL_ID"))
    channel = bot.get_channel(channel_id)
    if not channel:
        return False

    schedules = data.get("schedules", {})
    groups = {}

    # 月前半・後半の分類
    for date_key in schedules.keys():
        try:
            m, d = map(int, date_key.split('/'))
            period = f"{m}月{'前半' if d <= 15 else '後半'}"
            groups.setdefault(period, []).append(date_key)
        except:
            continue

    # Bot の過去メッセージ取得
    bot_messages = []
    async for msg in channel.history(limit=50):
        if msg.author == bot.user:
            bot_messages.append(msg)

    # 各期間のメッセージ更新
    for period, dates in sorted(groups.items()):
        text = f"**{period}の予定一覧**\n"
        for d in sorted(dates, key=lambda x: int(x.split('/')[1])):
            text += f"**【{d}】**\n"
            for i, e in enumerate(schedules[d], 1):
                text += f" {i}. {e}\n"

        target_msg = next((m for m in bot_messages if f"**{period}の予定一覧**" in m.content), None)

        if target_msg:
            if target_msg.content != text:
                await target_msg.edit(content=text)
            bot_messages.remove(target_msg)
        else:
            await channel.send(text)

        await asyncio.sleep(1)

    # 不要メッセージ削除
    for msg in bot_messages:
        await msg.delete()

    return True

