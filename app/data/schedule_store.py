import os
import json
from datetime import datetime
from upstash_redis import Redis
from collections import OrderedDict
from app.display.schedule_display import classify_period, sort_period_key

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
    period ベースで cleanup する。
    今日が属する period より前の period を削除し、
    今日の period と未来の period を残す。
    """
    if not isinstance(schedules, dict):
        return {}

    today = datetime.now().date()
    today_key = f"{today.year}/{today.month:02d}/{today.day:02d}"
    today_period = classify_period(today_key)
    today_period_sort = sort_period_key(today_period)

    new_schedules = {}

    for date_key, events in schedules.items():
        if "/" not in date_key:
            continue

        period = classify_period(date_key)
        if not period:
            continue

        # period のソートキーを比較
        if sort_period_key(period) >= today_period_sort:
            new_schedules[date_key] = events

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
    dict を検証して JSON 化し、 Redis に保存する。
    """

    if not isinstance(data, dict):
        print("⚠️ Redis保存中止: data が dict ではありません")
        return False

    if not isinstance(data.get("schedules"), dict):
        print("⚠️ Redis保存中止: schedules が dict ではありません")
        return False

    if not isinstance(data.get("message_ids"), dict):
        print("⚠️ Redis保存中止: message_ids が dict ではありません")
        return False

    try:
        payload = json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        print(f"⚠️ Redis保存中止: JSON 化に失敗しました: {e}")
        return False

    try:
        r.set(REDIS_KEY, payload)
    except Exception as e:
        print(f"⚠️ Redis保存失敗: {e}")
        return False

    return True


# ============================================================
# cleanup_sort_schedules（PIPELINE による整形処理）
# ============================================================

PIPELINE = [
    ("cleanup", cleanup_schedules),
    ("sort",    sort_schedules),
]

def cleanup_sort_schedules(data):
    """
    data["schedules"] をcleanup・sort する。
    - add/del 側で正規化済みの YYYY/MM/DD を受け取る
    - PIPELINE（cleanup → sort）で整形
    """
    schedules = data.get("schedules", {})

    # パイプライン実行（処理順序を明示）
    for _, func in PIPELINE:
        schedules = func(schedules)

    data["schedules"] = schedules

    return data

