# app/display/schedule_display.py
import os
import asyncio
import discord

# データ保存
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

    # -----------------------------
    # 月前半・後半の分類
    # -----------------------------
    for date_key in schedules.keys():
        try:
            m, d = map(int, date_key.split('/'))
            period = f"{m}月{'前半' if d <= 15 else '後半'}"
            groups.setdefault(period, []).append(date_key)
        except:
            continue

    updated = False

    # -----------------------------
    # 整合性チェック（ID方式の安全装置）
    # -----------------------------
    for period in groups.keys():
        msg_id = message_ids.get(period)

        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)

                if not msg.content.startswith(f"**{period}の予定一覧**"):
                    new_msg = await channel.send(f"**{period}の予定一覧**\n（自動修正）")
                    message_ids[period] = new_msg.id
                    updated = True

            except discord.NotFound:
                new_msg = await channel.send(f"**{period}の予定一覧**\n（自動修正）")
                message_ids[period] = new_msg.id
                updated = True

        else:
            new_msg = await channel.send(f"**{period}の予定一覧**\n（自動修正）")
            message_ids[period] = new_msg.id
            updated = True

    # -----------------------------
    # 不要な period の message_id を削除
    # -----------------------------
    for period in list(message_ids.keys()):
        if period not in groups:
            del message_ids[period]
            updated = True

    # -----------------------------
    # 並び順ソートキー（前半→後半）
    # -----------------------------
    def sort_period_key(period: str):
        m = int(period.replace("月前半", "").replace("月後半", ""))
        half = 0 if "前半" in period else 1
        return (m, half)

    periods_sorted = sorted(groups.keys(), key=sort_period_key)

    # -----------------------------
    # Discord 上の既存メッセージを取得
    # -----------------------------
    messages = []
    async for m in channel.history(limit=50):
        messages.append(m)

    existing = {}
    for m in messages:
        for period, mid in message_ids.items():
            if m.id == mid:
                existing[period] = m

    # -----------------------------
    # ズレ判定（created_at は使わない）
    # message_ids のキー順を「実際の順番」として扱う
    # -----------------------------
    actual_order = list(message_ids.keys())

    # -----------------------------
    # 並び順修正（ズレてるものだけ再投稿）
    # -----------------------------
    new_message_ids = {}

    for correct_index, period in enumerate(periods_sorted):

        # メッセージ本文生成
        text = f"**{period}の予定一覧**\n"
        for d in sorted(groups[period], key=lambda x: int(x.split('/')[1])):
            text += f"**【{d}】**\n"
            for i, e in enumerate(schedules[d], 1):
                text += f" {i}. {e}\n"

        msg_obj = existing.get(period)

        # 正しい順番
        correct_index = periods_sorted.index(period)

        # 実際の順番（辞書順）
        actual_index = actual_order.index(period)

        if actual_index != correct_index:
            # ズレてる → 再投稿
            if msg_obj:
                try:
                    await msg_obj.delete()
                except discord.NotFound:
                    pass

            new_msg = await channel.send(text)
            new_message_ids[period] = new_msg.id
            updated = True

        else:
            # 正しい → 編集だけ
            if msg_obj:
                if msg_obj.content != text:
                    await msg_obj.edit(content=text)
                    updated = True
                new_message_ids[period] = msg_obj.id
            else:
                # 存在しない場合は新規作成
                new_msg = await channel.send(text)
                new_message_ids[period] = new_msg.id
                updated = True

    # -----------------------------
    # message_ids を正しい順番で再構築
    # -----------------------------
    data["message_ids"] = new_message_ids

    # -----------------------------
    # save_all はここで 1 回だけ
    # -----------------------------
    if updated:
        await save_all(bot, data)

    return True
