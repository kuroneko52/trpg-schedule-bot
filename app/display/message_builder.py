# app/display/message_builder.py
# メッセージ本文生成

def build_message(period: str, groups: dict, schedules: dict):
    """period の本文を生成する"""
    text = f"**{period}の予定一覧**\n"

    # 日付昇順
    for d in sorted(groups[period], key=lambda x: int(x.split('/')[1])):
        text += f"**【{d}】**\n"
        for i, e in enumerate(schedules[d], 1):
            text += f" {i}. {e}\n"

    return text

