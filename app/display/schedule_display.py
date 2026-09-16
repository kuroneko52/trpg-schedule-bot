import os
import discord

# ============================================================
# 1. period 分類（internal period 生成）
# ============================================================

def classify_period(date_key: str):
    """
    YYYY/MM/DD を internal period（例：2026年10月前半）に変換する。
    不正な形式の場合は None を返す。
    """
    parts = date_key.split('/')
    if len(parts) != 3:
        return None

    try:
        y, m, d = map(int, parts)
    except ValueError:
        return None

    half = "前半" if d <= 15 else "後半"
    return f"{y}年{m}月{half}"


def sort_period_key(period: str):
    """
    internal period を (年, 月, 前半/後半) のタプルに変換してソート順を決める。
    不正な period は最後尾に送る。
    """
    try:
        year_part, rest = period.split("年", 1)
        month_part = rest.replace("月前半", "").replace("月後半", "")
        y = int(year_part)
        m = int(month_part)
        half = 0 if "前半" in period else 1
        return (y, m, half)
    except Exception:
        return (9999, 12, 1)


# ============================================================
# 2. period → date_key のグループ化
# ============================================================

def group_by_period(schedules: dict):
    """
    schedules（YYYY/MM/DD → [予定]）を internal period ごとにまとめる。
    不正な日付キーは無視する。
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
    1つの period に対応する Discord メッセージ本文を生成する。
    日付順は data 層で既に YYYY/MM/DD 昇順に整形済み。
    """
    lines = [f"**{period}の予定一覧**"]

    # groups[period] は data 層でソート済みの挿入順を保持している
    for full_date in groups[period]:
        parts = full_date.split('/')
        if len(parts) != 3:
            continue

        _, m, d = parts
        lines.append(f"**【{int(m)}/{int(d)}】**")

        for i, e in enumerate(schedules.get(full_date, []), 1):
            lines.append(f" {i}. {e}")

    return "\n".join(lines)


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
# 6. period メッセージ再構築（DELETE → SEND）
# ============================================================

async def rebuild_period_messages(channel, periods_sorted, groups, schedules, existing):
    """
    period ごとに Discord メッセージを再構築する。
    表示順を維持するため、既存メッセージは DELETE → SEND で置き換える。
    """
    new_message_ids = {}

    for period in periods_sorted:
        old_msg = existing.get(period)
        if old_msg:
            try:
                await old_msg.delete()
            except discord.NotFound:
                pass  # 既に削除されている場合

        text = build_message(period, groups, schedules)
        new_msg = await channel.send(text)
        new_message_ids[period] = new_msg.id

    return new_message_ids


# ============================================================
# 7. 表示更新（orchestrator）
# ============================================================

from data.schedule_store import save_data_to_redis

async def refresh_display(bot, data):
    """
    表示更新の統合処理。

    処理内容:
        1. period 分類
        2. 既存メッセージの逆引き
        3. period のソート
        4. メッセージ再構築
        5. message_ids の保存
    """
    channel_id = int(os.environ.get("CHANNEL_ID"))
    channel = bot.get_channel(channel_id)
    if not channel:
        return False

    schedules = data["schedules"]
    message_ids = data["message_ids"]

    groups = group_by_period(schedules)
    existing = await fetch_existing_messages(channel, message_ids)

    periods_sorted = sorted(groups.keys(), key=sort_period_key)

    new_message_ids = await rebuild_period_messages(
        channel, periods_sorted, groups, schedules, existing
    )

    data["message_ids"] = new_message_ids
    save_data_to_redis(data)

    return True

