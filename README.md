# Discord Schedule Bot

月ごとの予定を **前半 / 後半** に分けて Discord に自動投稿するスケジュール管理 Bot

予定の追加・削除はコマンドで行い、Redis に永続化される

---

## 📦 機能概要

- `MM/DD` 形式で予定を追加  
- 日付は自動で `YYYY/MM/DD` に正規化
- 月ごとに **前半 / 後半の 2 投稿** を自動生成
- 投稿内容は日付順に整形
- Redis に永続化
- Bot 起動時に自動で表示を再構築
- 壊れた JSON を検出して安全に停止（防御入り）

---

## 🧱 ディレクトリ構造

```
main.py              # Bot のエントリポイント
│
pytest.ini           # python test setting
│
.github/
├── workflows/
│   └── pytest.yml   # CI setting file
│
app/
├── bot/                 # Discord コマンド層
│   └── bot_commands.py
│
├── config/              # 環境変数・設定ロード
│   └── loadenv.py
│
├── data/                # 永続化・データ整形層（Redis）
│   └── schedule_store.py
│
├── display/             # Discord 表示生成層
│   └── schedule_display.py
│
└── server/              # Flask ヘルスチェックサーバー
    └── server.py
```

---

## 🔧 必要環境

- Python 3.10+
- Redis（クラウド or ローカル）
- Discord Bot Token
- Flask
- discord.py

---

## ⚙️ 環境変数

| 変数名 | 内容 |
|--------|-------|
| `DISCORD_TOKEN` | Discord Bot のトークン |
| `CHANNEL_ID` | 投稿先の Discord チャンネル ID |
| `UPSTASH_REDIS_URL` | Redis 接続 URL |
| `UPSTASH_REDIS_TOKEN` | Redis 接続 トークン |

---

## 🚀 起動方法

```bash
pip install -r requirements.txt
python main.py
```

## 🗂 コマンド一覧

### `!add MM/DD 内容`
予定を追加する。

例：
```
!add 9/14 AAA
```

### `!del MM/DD 番号`
予定を削除する。

例：
```
!del 9/14 1
```

### `!dump`
Redis の内容を JSON で表示。

例：
```
!dump
```


### `!initjson`
Redis のデータを初期化。

例：
```
!initjson
```

## 🔌 GAS（Google Apps Script）による外部 Ping

Render の無料 Web Service は **15 分アクセスが無いとスリープ**します。  
そのため、外部から定期的に URL を叩く仕組みが必要です。

本プロジェクトでは、Google Apps Script（GAS）を使って  
**10 分おきに Render の `/healthz` を叩く**ことでスリープを防止します。

### GAS コード例

`main.gs`
```
function pingRender() {
  wakeUpRender();
}

function wakeUpRender() {
  var url = "https://<your-app>.onrender.com/healthz";
  var options = { muteHttpExceptions: true };
  try {
    var response = UrlFetchApp.fetch(url, options);
    Logger.log("Status: " + response.getResponseCode());
  } catch (e) {
    Logger.log("Failed: " + e.message);
  }
}
```

## 設定手順
1. Google Apps Script を新規作成

2. 上記コードを貼り付け

3. トリガーを設定

    - 種類：時間主導型

    - 間隔：10 分

4. 保存して完了

## ポイント
- デプロイ不要（Web アプリ化しない）

- トリガーだけで動く

- GAS が止まる日があるため、必要なら UptimeRobot を併用可能

## 🧠 内部仕様（技術者向け）
🔹 日付正規化（normalize_date_key）
`MM/DD` → `YYYY/MM/DD`

今日より前の月は翌年扱い

ソート・永続化のためゼロ埋め

内部データは常に安定したフォーマット

🔹 整形パイプライン（save_all）
```
sort → cleanup → save
```

- 日付ソート

- 過去日の削除

- Redis 保存

- 責務分離された安全な整形処理

## 🔹 表示構造（schedule_display）
- 月単位で period を生成

  - `YYYY年M月前半`

  - `YYYY年M月後半`

- 前半（1〜15日）

- 後半（16〜31日）

- Discord に 2 投稿（前半・後半）

- 投稿は必ず DELETE → SEND で順序を保証

## 📤 出力例
### 前半
```
2026年9月前半の予定一覧
**【9/14】**
 1. AAA
 2. BBB

**【9/15】**
 1. CCC
 2. DDD
```

### 後半
```
2026年9月後半の予定一覧
**【9/16】**
 1. EEE

**【9/17】**
 1. FFF

**【9/19】**
 1. GGG
```

## 🛠 保守ポイント
- Redis の JSON が壊れてもクラッシュしない防御入り

- 表示は常に DELETE → SEND で順序を保証

- 月跨ぎの予定も自動で正規化される

- 内部データは常に YYYY/MM/DD で安定

## 📜 License

This project is licensed under the **MIT License**.

Copyright (c) 2026 kuroneko52

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

