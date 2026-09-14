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

REDIS_KEY = "bot_schedule_data"


# ============================================================
# MM/DD → YYYY/MM/DD 正規化
# ============================================================

def normalize_date_key(key: str):
    # key が "MM/DD" 形式でない場合は無視
    if "/" not in key:
        return None

    try:
        m, d = map(int, key.split("/"))
    except:
        return None

    today = datetime.now()
    year = today.year

    # 今日より前の月は来年扱い
    if m < today.month:
        year += 1

    return f"{year}/{m:02d}/{d:02d}"


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

    data.setdefault("schedules", {})
    data.setdefault("message_ids", {})

    return data


# ============================================================
# 正規化（MM/DD → YYYY/MM/DD）
# ============================================================

def normalize_schedules(schedules: dict):
    if not isinstance(schedules, dict):
        return {}

    normalized = {}

    for key, events in schedules.items():
        parts = key.split("/")

        # MM/DD → YYYY/MM/DD に正規化
        if len(parts) == 2:
            normalized_key = normalize_date_key(key)
            if not normalized_key:
                continue
        # すでに YYYY/MM/DD ならそのまま使う
        elif len(parts) == 3:
            normalized_key = key
        else:
            continue  # 変なキーは無視

        normalized.setdefault(normalized_key, []).extend(events)

    return normalized


# ============================================================
# 古いデータ削除（今日より前は削除）
# ============================================================

def cleanup_schedules(schedules: dict):
    if not isinstance(schedules, dict):
        return {}

    today = datetime.now().date()
    new_schedules = {}

    for date_key, events in schedules.items():
        # 日付形式でないキーは無視
        if "/" not in date_key:
            continue

        try:
            y, m, d = map(int, date_key.split("/"))
            dt = datetime(y, m, d).date()
            if dt >= today:
                new_schedules[date_key] = events
        except:
            continue

    return new_schedules


# ============================================================
# 日付ソート（YYYY/MM/DD を datetime でソート）
# ============================================================

def sort_schedules(schedules: dict):
    if not isinstance(schedules, dict):
        return OrderedDict()

    def parse_date(key):
        # 壊れたキーは最大値扱い（最後尾へ）
        try:
            y, m, d = map(int, key.split("/"))
            return datetime(y, m, d)
        except:
            return datetime.max

    sorted_items = sorted(schedules.items(), key=lambda kv: parse_date(kv[0]))
    return OrderedDict(sorted_items)


# ============================================================
# Redis 保存
# ============================================================

def save_data_to_redis(data):
    r.set(REDIS_KEY, json.dumps(data, ensure_ascii=False))


# ============================================================
# save_all（パイプライン化）
# ============================================================

PIPELINE = [
    ("sort",      sort_schedules),
    ("cleanup",   cleanup_schedules),
]

def save_all(data):
    schedules = data.get("schedules", {})

    # パイプライン実行
    for name, func in PIPELINE:
        schedules = func(schedules)

    data["schedules"] = schedules

    # 保存
    save_data_to_redis(data)

