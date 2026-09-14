# app/display/schedule_display.py
import os
import discord
from datetime import datetime

# ============================================================
# period 分類
# ============================================================

def classify_period(date_key: str):
    # YYYY/MM/DD → MM/DD に変換して月と日だけ使う
    _, m, d = date_key.split('/')
    m = int(m)
    d = int(d)
    return f"{m}月{'前半' if d <= 15 else '後半'}"


def sort_period_key(period: str):
    m = int(period.replace("月前半", "").replace("月後半", ""))
    half = 0 if "前半" in period else 1
    return (m, half)


# ============================================================
# メッセージ本文生成
# ============================================================

def build_message(period: str, groups: dict, schedules: dict):
    text = f"**{period}の予定一覧**\n"

    # groups[period] は YYYY/MM/DD のリスト
    # 日付ソートは「日だけ」で OK（同月内なので）
    for full_date in sorted(groups[period], key=lambda x: int(x.split('/')[2])):
        # 表示は MM/DD に戻す
        _, m, d = full_date.split('/')
        text += f"**【{m}/{d}】**\n"

        for i, e in enumerate(schedules[full_date], 1):
            text += f" {i}. {e}\n"

    return text


# ============================================================
# Discord メッセージ取得
# ============================================================

async def fetch_existing_messages(channel, message_ids: dict):
    # 逆引きマップ（message_id → period）
    id_to_period = {mid: period for period, mid in message_ids.items()}

    messages = []
    async for m in channel.history(limit=50):
        messages.append(m)

    existing = {}
    for m in messages:
        period = id_to_period.get(m.id)
        if period:
            existing[period] = m

    return existing


# ============================================================
# 表示更新（DELETE → SEND）
# ============================================================

from data.schedule_store import save_all

async def refresh_display(bot, data):
    channel_id = int(os.environ.get("CHANNEL_ID"))
    channel = bot.get_channel(channel_id)
    if not channel:
        return False

    schedules = data["schedules"]      # YYYY/MM/DD → [events]
    message_ids = data["message_ids"]  # {period: message_id}

    # period 分類
    groups = {}
    for date_key in schedules:
        try:
            period = classify_period(date_key)
            groups.setdefault(period, []).append(date_key)
        except:
            continue

    # 既存メッセージ取得
    existing = await fetch_existing_messages(channel, message_ids)

    # 不要 period の削除
    for period in list(message_ids):
        if period not in groups:
            msg = existing.get(period)
            if msg:
                try:
                    await msg.delete()
                except discord.NotFound:
                    pass
            del message_ids[period]

    # period ソート
    periods_sorted = sorted(groups.keys(), key=sort_period_key)

    # 全 period を DELETE → SEND
    new_message_ids = {}
    for period in periods_sorted:
        old_msg = existing.get(period)
        if old_msg:
            try:
                await old_msg.delete()
            except discord.NotFound:
                pass

        text = build_message(period, groups, schedules)
        new_msg = await channel.send(text)
        new_message_ids[period] = new_msg.id

    data["message_ids"] = new_message_ids

    save_all(data)
    return True

