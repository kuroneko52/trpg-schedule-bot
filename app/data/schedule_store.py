# app/data/schedule_store.py
import json
import os
import asyncio
import tempfile
from datetime import datetime

FILE_PATH = os.environ.get("FILE_PATH")

# ============================================================
# JSON 読み書き
# ============================================================

def load_data():
    """schedule.json を読み込む（壊れていたら復旧）"""
    if not os.path.exists(FILE_PATH):
        return {"schedules": {}, "message_ids": {}}

    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "message_ids" not in data:
            data["message_ids"] = {}

        return data

    except Exception as e:
        print(f"[Local] JSON 読み込み失敗 → 初期化: {e}")
        return {"schedules": {}, "message_ids": {}}


# ============================================================
# 古いデータ削除（昨日以前）
# ============================================================

def cleanup_old_data(data):
    """昨日以前の schedule を削除する"""
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
# 原子的保存
# ============================================================

def save_data_atomic(data):
    """schedule.json を原子的に安全保存する"""
    dir_name = os.path.dirname(FILE_PATH) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        temp_name = tmp.name

    os.replace(temp_name, FILE_PATH)


# ============================================================
# 保存処理の共通化
# ============================================================

async def save_all(data):
    cleanup_old_data(data)
    await asyncio.to_thread(save_data_atomic, data)

