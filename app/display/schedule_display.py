import os
import discord
from datetime import datetime

# ============================================================
# 1. period 分類（internal period 生成）
# ============================================================

def classify_period(date_key: str):
    """
    YYYY/MM/DD → internal period（例：2026年10月前半）に変換する。
    ソートや message_ids のキーとして使用する。
    壊れたキーは None を返す。
    """
    parts = date_key.split('/')
    if len(parts) != 3:
        return None

    try:
        y, m, d = map(int, parts)
    except:
        return None

    half = "前半" if d <= 15 else "後半"
    return f"{y}年{m}月{half}"


def sort_period_key(period: str):
    """
    internal period を (年, 月, 前半/後半) のタプルに変換してソートする。
    壊れた period は最後尾へ送る。
    """
    try:
        year_part, rest = period.split("年", 1)
        month_part = rest.replace("月前半", "").replace("月後半", "")
        y = int(year_part)
        m = int(month_part)
        half = 0 if "前半" in period else 1
        return (y, m, half)
    except:
        return (9999, 12, 1)


# ============================================================
# 2. period → date_key のグループ化
# ============================================================

def group_by_period(schedules: dict):
    """
    schedules を internal period ごとにまとめる。
    壊れた日付キーは無視する。
    """
    groups = {}
    for date_key in schedules:
        period = classify_period(date_key)
        if not period:
            continue
        groups.setdefault(period, []).append(date_key)
    return groups


# ============================================================
# 3. Discord 表示メッセージ生成
# ============================================================

def build_message(period: str, groups: dict, schedules: dict):
    """
    internal period を使って Discord に送る本文を生成する。
    日付は safe_day_sort で日付順に並べる。
    """
    lines = [f"**{period}の予定一覧**"]

    for full_date in sorted(groups[period], key=lambda x: safe_day_sort(x)):
        parts = full_date.split('/')
        if len(parts) != 3:
            continue

        _, m, d = parts
        m = int(m)
        d = int(d)
        lines.append(f"**【{m}/{d}】**")

        for i, e in enumerate(schedules.get(full_date, []), 1):
            lines.append(f" {i}. {e}")

    return "\n".join(lines)


def safe_day_sort(date_key: str):
    """
    YYYY/MM/DD の日付部分だけでソートする。
    壊れたキーは最後尾へ送る。
    """
    try:
        return int(date_key.split('/')[2])
    except:
        return 999


# ============================================================
# 4. Discord メッセージ取得（逆引き）
# ============================================================

async def fetch_existing_messages(channel, message_ids: dict):
    """
    message_ids（period → message_id）を逆引きし、
    チャンネル内の既存メッセージを period と紐付けて返す。
    """
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
    """
    groups に存在しない period のメッセージを削除する。
    message_ids からも削除する。
    """
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
    """
    period ごとにメッセージを再構築する。
    順序のため、既存メッセージは必ず DELETE → SEND する。
    """
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
# 7. 表示更新（orchestrator）
# ============================================================

from data.schedule_store import save_all

async def refresh_display(bot, data):
    """
    表示更新の統合処理。
    - period 分類
    - 既存メッセージ取得
    - 不要 period 削除
    - period ソート
    - メッセージ再構築
    - Redis 保存
    """
    channel_id = int(os.environ.get("CHANNEL_ID"))
    channel = bot.get_channel(channel_id)
    if not channel:
        return False

    schedules = data["schedules"]
    message_ids = data["message_ids"]

    groups = group_by_period(schedules)
    existing = await fetch_existing_messages(channel, message_ids)
    await delete_unused_periods(existing, message_ids, groups)

    periods_sorted = sorted(groups.keys(), key=sort_period_key)

    new_message_ids = await rebuild_period_messages(
        channel, periods_sorted, groups, schedules, existing
    )

    data["message_ids"] = new_message_ids
    save_all(data)
    return True

