# tests/test_schedule_display.py

"""
display.schedule_display のユニットテスト。
- classify_period(): YYYY/MM/DD → internal period
- sort_period_key(): period のソートキー
- group_by_period(): period ごとの date_key グループ化
- build_message(): Discord 表示文生成
"""

from display.schedule_display import (
    classify_period,
    sort_period_key,
    group_by_period,
    build_message
)


def test_classify_period():
    """
    日付から internal period が正しく生成されるか。
    """
    assert classify_period("2026/09/10") == "2026年9月前半"
    assert classify_period("2026/09/20") == "2026年9月後半"
    assert classify_period("bad") is None


def test_sort_period_key():
    """
    前半(half=0) → 後半(half=1) の順でソートされるか。
    """
    p1 = "2026年9月前半"
    p2 = "2026年9月後半"
    assert sort_period_key(p1) < sort_period_key(p2)


def test_group_by_period():
    """
    schedules を period ごとに正しくグループ化できるか。
    """
    schedules = {
        "2026/09/10": ["A"],
        "2026/09/20": ["B"],
    }
    groups = group_by_period(schedules)
    assert groups["2026年9月前半"] == ["2026/09/10"]
    assert groups["2026年9月後半"] == ["2026/09/20"]


def test_build_message():
    """
    Discord 表示メッセージが正しく生成されるか。
    """
    schedules = {"2026/09/10": ["A", "B"]}
    groups = {"2026年9月前半": ["2026/09/10"]}

    msg = build_message("2026年9月前半", groups, schedules)

    assert "【9/10】" in msg
    assert "1. A" in msg
    assert "2. B" in msg

