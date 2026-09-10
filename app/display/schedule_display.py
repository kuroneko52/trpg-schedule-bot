# app/display/schedule_display.py
# 司令塔

import os
import discord

from data.schedule_store import save_all

from display.period_utils import classify_period, sort_period_key
from display.message_builder import build_message
from display.discord_utils import fetch_existing_messages
from display.order_utils import is_mismatched

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

    # -----------------------------
    # period 分類
    # -----------------------------
    groups = {}
    for date_key in schedules.keys():
        try:
            period = classify_period(date_key)
            groups.setdefault(period, []).append(date_key)
        except:
            continue

    updated = False

    # -----------------------------
    # 整合性チェック（ID壊れてる？）
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
    # 不要な period の削除
    # -----------------------------
    for period in list(message_ids.keys()):
        if period not in groups:
            del message_ids[period]
            updated = True

    # -----------------------------
    # period ソート順
    # -----------------------------
    periods_sorted = sorted(groups.keys(), key=sort_period_key)

    # -----------------------------
    # Discord 上の既存メッセージ取得
    # -----------------------------
    existing = await fetch_existing_messages(channel, message_ids)

    # -----------------------------
    # ズレ判定用の辞書順
    # -----------------------------
    actual_order = list(message_ids.keys())

    # -----------------------------
    # 再投稿 or 編集
    # -----------------------------
    new_message_ids = {}

    for period in periods_sorted:

        msg_obj = existing.get(period)
        text = build_message(period, groups, schedules)

        if is_mismatched(period, actual_order, periods_sorted):
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
                new_msg = await channel.send(text)
                new_message_ids[period] = new_msg.id
                updated = True

    # -----------------------------
    # message_ids を正しい順番で再構築
    # -----------------------------
    data["message_ids"] = new_message_ids

    if updated:
        await save_all(bot, data)

    return True

