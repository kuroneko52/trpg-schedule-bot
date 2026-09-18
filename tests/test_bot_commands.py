# tests/test_bot_commands.py

"""
bot.bot_commands のユニットテスト。
- normalize_date_key(): MM/DD → YYYY/MM/DD 正規化
"""

from datetime import datetime
from unittest.mock import patch
from bot.bot_commands import normalize_date_key


def test_normalize_date_key_current_year():
    """
    今日と同じ月の場合：
    → 同じ年で正規化される
    """
    fake_today = datetime(2026, 9, 10)

    with patch("bot.bot_commands.datetime") as mock_dt:
        mock_dt.now.return_value = fake_today
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        assert normalize_date_key("09/10") == "2026/09/10"


def test_normalize_date_key_next_year():
    """
    今日より前の月の場合：
    → 翌年扱いになる
    """
    fake_today = datetime(2026, 9, 10)

    with patch("bot.bot_commands.datetime") as mock_dt:
        mock_dt.now.return_value = fake_today
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        assert normalize_date_key("08/10") == "2027/08/10"

