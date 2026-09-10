# app/data/schedule_store.py
import json
import os
import base64
import aiohttp
import asyncio

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO_NAME = os.environ.get("REPO_NAME")
FILE_PATH = os.environ.get("FILE_PATH")

# -----------------------------
# GitHub API
# -----------------------------
async def get_github_sha(session):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
            }
    async with session.get(url, headers=headers) as res:
        if res.status == 200:
            data = await res.json()
            return data.get('sha'), data.get('content')
    return None, None


async def download_data():
    if not GITHUB_TOKEN:
        return
    async with aiohttp.ClientSession() as session:
        _, content = await get_github_sha(session)
        if content:
            file_data = base64.b64decode(content).decode('utf-8')
            with open(FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(file_data)


async def push_data(data):
    if not GITHUB_TOKEN:
        return True
    async with aiohttp.ClientSession() as session:
        sha, _ = await get_github_sha(session)
        if not sha:
            return True

        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
        headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
                }
        payload = {
                "message": "Update schedule",
                "content": base64.b64encode(
                    json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8')
                    ).decode('utf-8'),
                "sha": sha
                }

        async with session.put(url, headers=headers, json=payload) as res:
            return res.status in (200, 201)

# -----------------------------
# JSON 読み書き
# -----------------------------
def load_data():
    if not os.path.exists(FILE_PATH):
        return {"schedules": {}}
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"schedules": {}}

# -----------------------------
# GitHub 保存キュー
# -----------------------------
pending_save = False
save_lock = asyncio.Lock()

async def queue_save():
    """保存要求だけ出す（GitHub APIは叩かない）"""
    global pending_save
    pending_save = True

async def github_worker():
    """10秒に1回だけ GitHub 保存を実行する"""
    global pending_save
    while True:
        if pending_save:
            async with save_lock:
                pending_save = False
                data = load_data()
                await push_data(data)
        await asyncio.sleep(10)

