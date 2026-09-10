# app/display/period_utils.py
# 月前半後半ソートキー

def classify_period(date_key: str):
    """'10/15' → '10月前半' のように period を返す"""
    m, d = map(int, date_key.split('/'))
    return f"{m}月{'前半' if d <= 15 else '後半'}"


def sort_period_key(period: str):
    """'10月前半' → (10, 0) のようにソートキーを返す"""
    m = int(period.replace("月前半", "").replace("月後半", ""))
    half = 0 if "前半" in period else 1
    return (m, half)

