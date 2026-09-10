# app/data/schedule_store.py
import json
import os
import asyncio
from datetime import datetime
import discord

# ============================================================
# 環境変数
# ============================================================

JSON_STORAGE_ID = int(os.environ.get("JSON_STORAGE_ID"))
JSON_STORAGE_CHANNEL_ID = int(os.environ.get("JSON_STORAGE_CHANNEL_ID"))

# ============================================================
# Discord メッセージから JSON を読み込む
# ============================================================

async def load_data_from_discord(bot):
    """Discord の保存メッセージから JSON を読み込む"""
    try:
        channel = bot.get_channel(JSON_STORAGE_CHANNEL_ID)
        msg = await channel.fetch_message(JSON_STORAGE_ID)

        raw = msg.content.strip()

        # JSON デコード安全化
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print("[Discord] JSON が壊れているため初期化します")
            return {"schedules": {}, "message_ids": {}}

        # 安全性のための最低限の補完
        if "schedules" not in data:
            data["schedules"] = {}
        if "message_ids" not in data:
            data["message_ids"] = {}

        return data

    except Exception as e:
        print(f"[Discord] JSON 読み込み失敗 → 初期化: {e}")
        return {"schedules": {}, "message_ids": {}}


# ============================================================
# 古いデータ削除（昨日以前）
# ============================================================

def cleanup_old_data(data):
    today = datetime.now().date()
    new_schedules = {}

    for date_key, events in data["schedules"].items():
        try:
            m, d = map(int, date_key.split("/"))
            dt = datetime(today.year, m, d).date()
            if dt >= today:
                new_schedules[date_key] = events
        except:
            continue

    data["schedules"] = new_schedules


# ============================================================
# Discord メッセージに JSON を保存（上書き）
# ============================================================

async def save_data_to_discord(bot, data):
    """Discord の保存メッセージを edit して永続化"""
    try:
        channel = bot.get_channel(JSON_STORAGE_CHANNEL_ID)
        msg = await channel.fetch_message(JSON_STORAGE_ID)

        text = json.dumps(data, ensure_ascii=False, indent=2)
        await msg.edit(content=text)

    except Exception as e:
        print(f"[Discord] JSON 保存失敗: {e}")


# ============================================================
# 保存処理の共通化
# ============================================================

async def save_all(bot, data):
    cleanup_old_data(data)
    await save_data_to_discord(bot, data)

