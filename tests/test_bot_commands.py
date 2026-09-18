# tests/test_bot_commands.py

"""
app.bot.bot_commands のユニットテスト。
- normalize_date_key(): MM/DD → YYYY/MM/DD 正規化
"""

from datetime import datetime
from unittest.mock import patch
from app.bot.bot_commands import normalize_date_key


def test_normalize_date_key_current_year():
    fake_today = datetime(2026, 9, 10)

    with patch("app.bot.bot_commands.datetime") as mock_dt:
        mock_dt.now.return_value = fake_today
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        assert normalize_date_key("09/10") == "2026/09/10"


def test_normalize_date_key_next_year():
    fake_today = datetime(2026, 9, 10)

    with patch("app.bot.bot_commands.datetime") as mock_dt:
        mock_dt.now.return_value = fake_today
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        assert normalize_date_key("08/10") == "2027/08/10"

