<div align="center">

## 🚀 HackingNaruto/leech — KPSML-X Custom Build

[![GitHub Stars](https://img.shields.io/github/stars/HackingNaruto/leech?style=plastic&logo=github&color=FFD700&label=Stars)](https://github.com/HackingNaruto/leech/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/HackingNaruto/leech?style=plastic&logo=git&color=orange&label=Forks)](https://github.com/HackingNaruto/leech/fork)
[![Upstream](https://img.shields.io/badge/Upstream-KPSML--X-blue?style=plastic&logo=git)](https://github.com/Tamilupdates/KPSML-X)

#### ***⚡️ Download Anything. Upload Everywhere. Now with Media Processing. 🔥***

</div>

---

## ✨ Custom Features (Added on Top of KPSML-X)

| Feature | Command | Description |
|---|---|---|
| 🎬 **Sample Video** | `/usetting` | Auto-create 15s/30s/60s preview clip |
| 🔄 **Convert Video** | `/usetting` | Convert MKV↔MP4↔AVI (lossless) |
| 📝 **Intro Subtitle** | `/usetting` | Add custom text as intro subtitle |
| 📦 **Auto Merge Zip** | `/usetting` | Extract ZIP → merge video parts in order |
| 🏷️ **Smart Audio Tag** | `/usetting` | Auto-detect codec → tag as `@Ch - DD+ 5.1` |

---

## 🛠️ Deploy Guide

### ✅ Method 1: Kaggle (Recommended — Free, Fast, 12h Runtime)

> Kaggle gives **2× Tesla T4 GPU + 30 GB RAM** for free. Best for heavy leeching.

**Step 1 — Kaggle Account Setup**
1. Go to [kaggle.com](https://www.kaggle.com) → Sign up / Login
2. Go to **Settings** → **Phone Verify** (required for internet access)
3. Go to **Settings** → **API** → **Create New Token** → Download `kaggle.json`

**Step 2 — Create a New Notebook**
1. Click **"+ Create"** → **"New Notebook"**
2. On the right panel → **Settings** → Enable **"Internet"**
3. Set **Accelerator** to `None` (GPU not needed for bot)
4. Set **Persistence** to `Files`

**Step 3 — Paste this code in the first cell:**

```python
# ── Install dependencies ──
!pip install -q pyrogram tgcrypto motor aiofiles aiohttp python-dotenv qbittorrent-api aria2p yt-dlp natsort pytz requests bs4 uvloop

# ── Clone your bot repo ──
!git clone https://github.com/HackingNaruto/leech /kaggle/working/leech
%cd /kaggle/working/leech

# ── Create config.env ──
config = """
BOT_TOKEN = your_bot_token_here
TELEGRAM_API = your_api_id
TELEGRAM_HASH = your_api_hash
OWNER_ID = your_telegram_id
DATABASE_URL = your_mongodb_url
DOWNLOAD_DIR = /kaggle/working/downloads/
"""

with open("config.env", "w") as f:
    f.write(config)

# ── Run the bot ──
!python3 -m bot
```

**Step 4 — Fill in your values:**

| Variable | Where to get |
|---|---|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `TELEGRAM_API` + `TELEGRAM_HASH` | [my.telegram.org](https://my.telegram.org) |
| `OWNER_ID` | [@userinfobot](https://t.me/userinfobot) |
| `DATABASE_URL` | [mongodb.com/atlas](https://www.mongodb.com/atlas) → Free cluster → Connect |

**Step 5 — Run the notebook!**  
Click **▶ Run All** — Bot starts within 1–2 minutes. 🚀

> ⚠️ Kaggle stops after **12 hours**. Re-run the notebook to restart.

---

### ✅ Method 2: VPS / Linux Server (24/7)

```bash
# 1. Clone the repo
git clone https://github.com/HackingNaruto/leech
cd leech

# 2. Install system dependencies
apt-get install -y ffmpeg python3-pip aria2

# 3. Install Python packages
pip3 install -r requirements.txt

# 4. Create config
cp config_sample.env config.env
nano config.env   # Fill in your values

# 5. Run with screen (keeps running after logout)
screen -S leech
python3 -m bot
# Press Ctrl+A then D to detach
```

---

### ✅ Method 3: Heroku

1. Fork this repo → Connect to [heroku.com](https://heroku.com)
2. Add **Buildpacks**: `heroku/python` + FFmpeg buildpack
3. Set **Config Vars** (same as `config.env` keys)
4. Deploy branch: `main`
5. Enable **Worker** dyno (not Web)

---

## ⚙️ Minimum Required Config Variables

```env
BOT_TOKEN        = 123456:ABC...          # From @BotFather
TELEGRAM_API     = 123456                 # From my.telegram.org
TELEGRAM_HASH    = abcdef1234...          # From my.telegram.org
OWNER_ID         = 123456789             # Your Telegram User ID
DATABASE_URL     = mongodb+srv://...      # MongoDB Atlas free URL
DOWNLOAD_DIR     = /tmp/downloads/        # Temp download path
```

---

## 📱 Bot Commands

| Command | Description |
|---|---|
| `/leech` | Download & upload to Telegram |
| `/mirror` | Download & mirror to Google Drive |
| `/usetting` | 🆕 Per-user media processing settings |
| `/bs` | Bot settings (admin) |
| `/status` | View active tasks |
| `/cancel` | Cancel a task |

---

## 🎛️ /usetting Menu Guide

Send `/usetting` to the bot — you'll see an interactive menu:

```
🎛️ Your Personal Settings

🎬 Video Engine
  ├ Sample Video   : ❌
  ├ Sample Duration: 60s
  ├ Convert Video  : ❌
  └ Convert Format : MKV

📝 Intro Subtitle
  ├ IntroSub       : ❌
  ├ Intro Text     : (not set)
  └ Duration       : 30s

🏷️ Audio Tag
  ├ Audio Tag      : ❌
  └ Tag Text       : (not set)

📦 Auto Merge
  └ Zip Auto Merge : ❌
```

**How it works:**
- Enable **Sample Video** → Every leech will auto-generate a preview clip sent separately
- Enable **Audio Tag** → Set text like `@MyChannel` → Bot will auto-tag as `@MyChannel - DD+ 5.1`
- Enable **Auto Merge Zip** → Send a `.zip` with video parts → Bot extracts, sorts & merges them
- Enable **IntroSub** → Set text → Bot adds it as subtitle for first N seconds of every video

---

## 📦 Upstream

This bot is built on top of **[KPSML-X by Tamilupdates](https://github.com/Tamilupdates/KPSML-X)**.  
All original features are preserved. Custom features are added via:
- `bot/helper/ext_utils/media_processor.py`
- `bot/helper/ext_utils/media_pipeline.py`
- `bot/modules/user_settings.py`

---

<div align="center">

Made with ❤️ by [@HackingNaruto](https://github.com/HackingNaruto)  
Based on [KPSML-X](https://github.com/Tamilupdates/KPSML-X)

</div>
