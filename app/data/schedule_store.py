import os
import json
from upstash_redis import Redis
from datetime import datetime
from collections import OrderedDict

# ============================================================
# Upstash Redis 接続設定
# ============================================================

UPSTASH_REDIS_URL = os.environ.get("UPSTASH_REDIS_URL")
UPSTASH_REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_TOKEN")

r = Redis(
    url=UPSTASH_REDIS_URL,
    token=UPSTASH_REDIS_TOKEN
)

REDIS_KEY = "bot_schedule_data"


# ============================================================
# MM/DD → YYYY/MM/DD 正規化
# ============================================================

def normalize_date_key(key: str):
    """
    MM/DD を YYYY/MM/DD に正規化する。
    - MM/DD形式でなければ None
    - 存在しない月日は None
    - 月が現在より前なら翌年扱い
    """
    if "/" not in key:
        return None

    try:
        m, d = map(int, key.split("/"))
    except:
        return None

    try:
        datetime(datetime.now().year, m, d)
    except:
        return None

    today = datetime.now()
    year = today.year

    # 今日より前の月は翌年扱い
    if m < today.month:
        year += 1

    return f"{year}/{m:02d}/{d:02d}"


# ============================================================
# Redis 読み込み（壊れていてもクラッシュしない）
# ============================================================

def load_data_from_redis():
    """
    Redis から schedules / message_ids を読み込む。
    壊れた JSON や欠損があっても dict を返す防御入り。
    """
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
# 過去日付の削除（cleanup）
# ============================================================

def cleanup_schedules(schedules: dict):
    """
    今日より前の日付を削除する。
    壊れたキーは無視して安全に進める。
    """
    if not isinstance(schedules, dict):
        return {}

    today = datetime.now().date()
    new_schedules = {}

    for date_key, events in schedules.items():
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
# 日付ソート（YYYY/MM/DD）
# ============================================================

def sort_schedules(schedules: dict):
    """
    YYYY/MM/DD を datetime に変換してソートする。
    壊れたキーは最後尾へ送る。
    """
    if not isinstance(schedules, dict):
        return OrderedDict()

    def parse_date(key):
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
    """
    dict を JSON 化して Redis に保存する。
    """
    r.set(REDIS_KEY, json.dumps(data, ensure_ascii=False))


# ============================================================
# save_all（PIPELINE による整形処理）
# ============================================================

PIPELINE = [
    ("sort",    sort_schedules),
    ("cleanup", cleanup_schedules),
]

def save_all(data):
    """
    schedules を整形して保存する統合処理。
    - add/del 側で正規化済みの YYYY/MM/DD を受け取る
    - PIPELINE（sort → cleanup）で整形
    - Redis に保存
    """
    schedules = data.get("schedules", {})

    # パイプライン実行（処理順序を明示）
    for name, func in PIPELINE:
        schedules = func(schedules)

    data["schedules"] = schedules

    # 保存
    save_data_to_redis(data)

