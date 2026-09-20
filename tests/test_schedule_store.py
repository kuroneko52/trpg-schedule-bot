# tests/test_schedule_store.py

"""
app.data.schedule_store のユニットテスト。
- cleanup_schedules(): period の削除ロジックの本体
- sort_schedules(): YYYY/MM/DD の昇順ソート
"""

from datetime import datetime
from unittest.mock import patch
from app.data.schedule_store import cleanup_schedules, sort_schedules, cleanup_sort_schedules


def test_cleanup_front_half_today():
    """
    今日が「前半」の場合：
    - 今日の period = 前半
    - 前半 period → 残る
    - 後半 period → 残る
    """
    fake_today = datetime(2026, 9, 10)

    with patch("app.data.schedule_store.datetime") as mock_dt:
        mock_dt.now.return_value = fake_today
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        schedules = {
            "2026/09/10": ["A"],
            "2026/09/20": ["B"],
        }

        cleaned = cleanup_schedules(schedules)
        assert "2026/09/10" in cleaned
        assert "2026/09/20" in cleaned


def test_cleanup_back_half_today():
    """
    今日が「後半」の場合：
    - 今日の period = 後半
    - 前半 period → 削除される
    - 後半 period → 残る
    """
    fake_today = datetime(2026, 9, 18)

    with patch("app.data.schedule_store.datetime") as mock_dt:
        mock_dt.now.return_value = fake_today
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        schedules = {
            "2026/09/10": ["A"],
            "2026/09/20": ["B"],
        }

        cleaned = cleanup_schedules(schedules)
        assert "2026/09/10" not in cleaned
        assert "2026/09/20" in cleaned


def test_sort_schedules():
    """
    YYYY/MM/DD の昇順ソートが正しく動くか確認。
    """
    schedules = {
        "2026/09/20": ["B"],
        "2026/09/10": ["A"],
    }
    sorted_s = sort_schedules(schedules)
    assert list(sorted_s.keys()) == ["2026/09/10", "2026/09/20"]


def test_cleanup_sort_schedules():
    fake_today = datetime(2026, 9, 18)

    with patch("app.data.schedule_store.datetime") as mock_dt:
        mock_dt.now.return_value = fake_today
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        data = {
            "schedules": {
                "2026/10/01": ["B"],
                "2026/09/20": ["A"],
            },
            "message_ids": {},
        }

        cleanup_sort_schedules(data)

        assert list(data["schedules"].keys()) == [
            "2026/09/20",
            "2026/10/01",
        ]










