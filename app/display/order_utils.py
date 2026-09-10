# app/display/order_utils.py
# 並び順ズレ判定

def is_mismatched(period: str, actual_order: list, periods_sorted: list):
    """period がズレているかどうか判定する"""
    actual_index = actual_order.index(period)
    correct_index = periods_sorted.index(period)
    return actual_index != correct_index

