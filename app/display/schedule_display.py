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

    # save_all flag
    updated = False

    # -----------------------------
    # 整合性チェック（ID方式の安全装置）
    # -----------------------------
    for period in groups.keys():
        msg_id = message_ids.get(period)

        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)

                # periodと内容一致しているかチェック
                if not msg.content.startswith(f"**{period}の予定一覧**"):
                    # 内容がズレていたら自動修正
                    new_msg = await channel.send(f"**{period}の予定一覧**\n（自動修正）")
                    message_ids[period] = new_msg.id
                    updated = True

            except discord.NotFound:
                # メッセージが消えていたら自動修正
                new_msg = await channel.send(f"**{period}の予定一覧**\n（自動修正）")
                message_ids[period] = new_msg.id
                updated = True

        else:
            # message_idsにperiodが存在しなければ自動修正
            new_msg = await channel.send(f"**{period}の予定一覧**\n（自動修正）")
            message_ids[period] = new_msg.id
            updated = True

    # -----------------------------
    # 不要な period の message_id を自動削除
    # -----------------------------
    for period in list(message_ids.keys()):
        if period not in groups:
            del message_ids[period]
            updated = True

    # -----------------------------
    # ID方式：履歴を読まず、message_ids を使う
    # -----------------------------
    def sort_period_key(period: str):
        m = int(period.replace("月前半", "").replace("月後半", ""))
        half = 0 if "前半" in period else 1
        return (m, half)

    for period, dates in sorted(groups.items(), key=lambda x: sort_period_key(x[0])):

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
                # メッセージが消えていたら新規作成
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
        await save_all(bot, data)

    return True

