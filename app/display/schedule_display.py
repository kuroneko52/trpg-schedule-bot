# app/display/schedule_display.py
import os
import discord
from datetime import datetime

# ============================================================
# 1. period 分類
# ============================================================

def classify_period(date_key: str):
    _, m, d = date_key.split('/')
    m = int(m)
    d = int(d)
    return f"{m}月{'前半' if d <= 15 else '後半'}"


def sort_period_key(period: str):
    m = int(period.replace("月前半", "").replace("月後半", ""))
    half = 0 if "前半" in period else 1
    return (m, half)


# ============================================================
# 2. period → date_key のグループ化
# ============================================================

def group_by_period(schedules: dict):
    groups = {}
    for date_key in schedules:
        try:
            period = classify_period(date_key)
            groups.setdefault(period, []).append(date_key)
        except:
            continue
    return groups


# ============================================================
# 3. メッセージ本文生成（join 化）
# ============================================================

def build_message(period: str, groups: dict, schedules: dict):
    lines = [f"**{period}の予定一覧**"]

    for full_date in sorted(groups[period], key=lambda x: int(x.split('/')[2])):
        _, m, d = full_date.split('/')
        lines.append(f"**【{m}/{d}】**")

        for i, e in enumerate(schedules[full_date], 1):
            lines.append(f" {i}. {e}")

    return "\n".join(lines)


# ============================================================
# 4. Discord メッセージ取得
# ============================================================

async def fetch_existing_messages(channel, message_ids: dict):
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
# 5. 不要 period の削除
# ============================================================

async def delete_unused_periods(existing: dict, message_ids: dict, groups: dict):
    for period in list(message_ids):
        if period not in groups:
            msg = existing.get(period)
            if msg:
                try:
                    await msg.delete()
                except discord.NotFound:
                    pass
            del message_ids[period]


# ============================================================
# 6. period メッセージ再構築（DELETE → SEND）
# ============================================================

async def rebuild_period_messages(channel, periods_sorted, groups, schedules, existing):
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

    return new_message_ids


# ============================================================
# 7. 表示更新（本体）
# ============================================================

from data.schedule_store import save_all

async def refresh_display(bot, data):
    channel_id = int(os.environ.get("CHANNEL_ID"))
    channel = bot.get_channel(channel_id)
    if not channel:
        return False

    schedules = data["schedules"]
    message_ids = data["message_ids"]

    # 1. period 分類
    groups = group_by_period(schedules)

    # 2. 既存メッセージ取得
    existing = await fetch_existing_messages(channel, message_ids)

    # 3. 不要 period の削除
    await delete_unused_periods(existing, message_ids, groups)

    # 4. period ソート
    periods_sorted = sorted(groups.keys(), key=sort_period_key)

    # 5. メッセージ再構築
    new_message_ids = await rebuild_period_messages(
        channel, periods_sorted, groups, schedules, existing
    )

    data["message_ids"] = new_message_ids

    # 6. 保存
    save_all(data)
    return True

