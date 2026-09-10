# app/display/schedule_display.py
import os
import asyncio
import discord

# データ保存（ID方式のため追加）
from data.schedule_store import save_all

# -----------------------------
# Discord 表示更新
# -----------------------------
async def refresh_display(bot, data):
    channel_id = int(os.environ.get("CHANNEL_ID"))
    channel = bot.get_channel(channel_id)
    if not channel:
        return False

    schedules = data.get("schedules", {})
    message_ids = data.get("message_ids", {})

    groups = {}

    # 月前半・後半の分類
    for date_key in schedules.keys():
        try:
            m, d = map(int, date_key.split('/'))
            period = f"{m}月{'前半' if d <= 15 else '後半'}"
            groups.setdefault(period, []).append(date_key)
        except:
            continue

    updated = False  # ← save_all 最適化用フラグ

    # -----------------------------
    # ID方式：履歴を読まず、message_ids を使う
    # -----------------------------
    for period, dates in sorted(groups.items()):
        text = f"**{period}の予定一覧**\n"
        for d in sorted(dates, key=lambda x: int(x.split('/')[1])):
            text += f"**【{d}】**\n"
            for i, e in enumerate(schedules[d], 1):
                text += f" {i}. {e}\n"

        msg_id = message_ids.get(period)

        if msg_id:
            # 既存メッセージを取得して更新
            try:
                target_msg = await channel.fetch_message(msg_id)
                if target_msg.content != text:
                    await target_msg.edit(content=text)
            except discord.NotFound:
                # メッセージが消えていた場合は新規作成
                new_msg = await channel.send(text)
                message_ids[period] = new_msg.id
                updated = True
        else:
            # 初回作成
            new_msg = await channel.send(text)
            message_ids[period] = new_msg.id
            updated = True

        await asyncio.sleep(1)

    # -----------------------------
    # save_all はここで 1 回だけ
    # -----------------------------
    if updated:
        await save_all(data)

    return True

