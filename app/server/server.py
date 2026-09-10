# app/server/server.py
from flask import Flask
import os

# -----------------------------
# Flask アプリ初期化
# -----------------------------
app = Flask(__name__)

# -----------------------------
# ヘルスチェック
# -----------------------------
@app.route("/")
def home():
    return "Bot is Online!"

# -----------------------------
# Flask 起動関数
# -----------------------------
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

