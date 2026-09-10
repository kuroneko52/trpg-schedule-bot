import discord
from discord.ext import commands
import json
import base64
import os
import asyncio
import aiohttp
import time
from datetime import datetime
from flask import Flask
from threading import Thread


TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = 1158360743578701854
FILE_PATH = 'schedule.json'
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO_NAME = 'sibu810/ie-'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
data_lock = asyncio.Lock()


app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))


async def get_github_sha(session):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        async with session.get(url, headers=headers) as res:
            if res.status == 200:
                data = await res.json()
                return data.get('sha'), data.get('content')
    except: pass
    return None, None

async def download_data():
    if not GITHUB_TOKEN: return
    async with aiohttp.ClientSession() as session:
        _, content = await get_github_sha(session)
        if content:
            file_data = base64.b64decode(content).decode('utf-8')
            with open(FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(file_data)

async def push_data(data):
    if not GITHUB_TOKEN: return True
    async with aiohttp.ClientSession() as session:
        sha, _ = await get_github_sha(session)
        if not sha: return True
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        payload = {
            "message": "Update schedule",
            "content": base64.b64encode(json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8')).decode('utf-8'),
            "sha": sha
        }
        async with session.put(url, headers=headers, json=payload) as res:
            return res.status in (200, 201)


def load_data():
    if not os.path.exists(FILE_PATH): return {"schedules": {}}
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return {"schedules": {}}

async def sync_and_refresh_display(data, save_to_github=False):
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return False
    
    schedules = data.get("schedules", {})
    groups = {}
    for date_key in schedules.keys():
        try:
            m, d = map(int, date_key.split('/'))
            period = f"{m}月{'前半' if d <= 15 else '後半'}"
            if period not in groups: groups[period] = []
            groups[period].append(date_key)
        except: continue

   
    bot_messages = []
    async for msg in channel.history(limit=50):
        if msg.author == bot.user:
            bot_messages.append(msg)

    
    for period, dates in sorted(groups.items()):
        text = f"**{period}の予定一覧**\n"
        for d in sorted(dates, key=lambda x: int(x.split('/')[1])):
            text += f"**【{d}】**\n"
            for i, e in enumerate(schedules[d], 1):
                text += f" {i}. {e}\n"
        
        target_msg = next((m for m in bot_messages if f"**{period}の予定一覧**" in m.content), None)
        
        if target_msg:
            if target_msg.content != text:
                await target_msg.edit(content=text)
            bot_messages.remove(target_msg)
        else:
            await channel.send(text)
        await asyncio.sleep(1)

    
    for msg in bot_messages:
        await msg.delete()

    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    return await push_data(data) if save_to_github else True

@bot.event
async def on_ready():
    print(f'Bot Ready: {bot.user}')
    await download_data()
    data = await asyncio.to_thread(load_data)
    
    await sync_and_refresh_display(data, save_to_github=False)

@bot.command()
async def add(ctx, date_str: str, *, event_info: str):
    async with data_lock:
        data = await asyncio.to_thread(load_data)
        if date_str not in data["schedules"]: data["schedules"][date_str] = []
        data["schedules"][date_str].append(event_info.strip())
        
        success = await sync_and_refresh_display(data, save_to_github=True)
        await ctx.message.add_reaction('✅' if success else '⚠️')

@bot.command(name="del")
async def del_command(ctx, date_str: str, num: int):
    async with data_lock:
        data = await asyncio.to_thread(load_data)
        if date_str in data["schedules"]:
            try:
                data["schedules"][date_str].pop(num - 1)
                if not data["schedules"][date_str]: del data["schedules"][date_str]
                success = await sync_and_refresh_display(data, save_to_github=True)
                await ctx.message.add_reaction('🗑️' if success else '⚠️')
            except:
                await ctx.send("⚠️ 番号が正しくありません")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    while True: