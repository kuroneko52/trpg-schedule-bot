# app/display/discord_utils.py
# Discord メッセージ取得

async def fetch_existing_messages(channel, message_ids: dict):
    """Discord 上の既存メッセージを {period: msg_obj} にする"""
    messages = []
    async for m in channel.history(limit=50):
        messages.append(m)

    existing = {}
    for m in messages:
        for period, mid in message_ids.items():
            if m.id == mid:
                existing[period] = m

    return existing

