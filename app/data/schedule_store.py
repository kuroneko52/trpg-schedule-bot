# app/data/schedule_store.py
import json
import os
import asyncio
from datetime import datetime

FILE_PATH = os.environ.get("FILE_PATH", "schedule.json")

# ============================================================
# ローカル JSON 読み込み
# ============================================================

async def load_data_from_local():
    if not os.path.exists(FILE_PATH):
        return {"schedules": {}, "message_ids": {}}

    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        return {"schedules": {}, "message_ids": {}}

    if "schedules" not in data:
        data["schedules"] = {}
    if "message_ids" not in data:
        data["message_ids"] = {}

    return data

# ============================================================
# 古いデータ削除
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
# ローカル保存
# ============================================================

async def save_data_to_local(data):
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

from collections import OrderedDict
from datetime import datetime

# ============================================================
# 日付ソート
# ============================================================

def sort_schedules(schedules: dict):
    def parse_date(key):
        m, d = key.split("/")
        return datetime(2026, int(m), int(d))

    sorted_items = sorted(schedules.items(), key=lambda kv: parse_date(kv[0]))
    return OrderedDict(sorted_items)


# ============================================================
# save_all（本体）
# ============================================================

async def save_all(data):
    schedules = data.get("schedules", {})
    data["schedules"] = sort_schedules(schedules)

    cleanup_old_data(data)
    await save_data_to_local(data)

# ============================================================
# save_all のキュー化（ここが今回の本丸）
# ============================================================

save_queue = asyncio.Queue()
save_worker_task = None

async def request_save(data):
    """
    save_all をキュー化して、最新だけ1回保存する
    """

    # キューが空なら入れる
    if save_queue.empty():
        await save_queue.put(data)
    else:
        # 古いデータを捨てて最新だけ入れる
        try:
            save_queue.get_nowait()
        except:
            pass
        await save_queue.put(data)

    # ワーカー起動
    global save_worker_task
    if save_worker_task is None or save_worker_task.done():
        save_worker_task = asyncio.create_task(save_worker())


async def save_worker():
    """
    0.5秒待って最新の data を1回だけ保存する
    """
    while not save_queue.empty():
        data = await save_queue.get()

        await asyncio.sleep(0.5)

        # 最新だけ残す
        while not save_queue.empty():
            data = await save_queue.get()

        await save_all(data)

