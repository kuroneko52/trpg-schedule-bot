# app/data/schedule_store.py
import os
import json
import redis
from datetime import datetime
from collections import OrderedDict

# ============================================================
# Redis 接続
# ============================================================

REDIS_URL = os.environ.get("REDIS_URL")
r = redis.from_url(REDIS_URL, decode_responses=True)

REDIS_KEY = "bot_schedule_data"  # 1キーに全部まとめて保存する

# ============================================================
# Redis 読み込み
# ============================================================

def load_data_from_redis():
    raw = r.get(REDIS_KEY)
    if not raw:
        return {"schedules": {}, "message_ids": {}}

    try:
        data = json.loads(raw)
    except:
        return {"schedules": {}, "message_ids": {}}

    # 必須キーの補完
    data.setdefault("schedules", {})
    data.setdefault("message_ids", {})

    return data

# ============================================================
# 古いデータ削除（昨日以前のデータを消す）
# ============================================================

def cleanup_old_data(data):
    today = datetime.now().date()
    schedules = data["schedules"]

    new_schedules = {}
    for date_key, events in schedules.items():
        try:
            m, d = map(int, date_key.split("/"))
            dt = datetime(today.year, m, d).date()
            if dt >= today:
                new_schedules[date_key] = events
        except:
            continue

    data["schedules"] = new_schedules

# ============================================================
# 日付ソート（今年の正しい年でソート）
# ============================================================

def sort_schedules(schedules: dict):
    today_year = datetime.now().year

    def parse_date(key):
        m, d = key.split("/")
        return datetime(today_year, int(m), int(d))

    sorted_items = sorted(schedules.items(), key=lambda kv: parse_date(kv[0]))
    return OrderedDict(sorted_items)

# ============================================================
# Redis 保存
# ============================================================

def save_data_to_redis(data):
    r.set(REDIS_KEY, json.dumps(data, ensure_ascii=False))

# ============================================================
# save_all（ソート → 古いデータ削除 → 保存）
# ============================================================

def save_all(data):
    # ソート
    data["schedules"] = sort_schedules(data["schedules"])

    # 古いデータ削除
    cleanup_old_data(data)

    # 保存
    save_data_to_redis(data)

