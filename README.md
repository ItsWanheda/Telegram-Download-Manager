# ⚡ Telegram Download Manager

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Async](https://img.shields.io/badge/AsyncIO-Enabled-111111?style=for-the-badge)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-00C853?style=for-the-badge)

> **Async • Resumable • Multipart • SQLite • Telegram**

A powerful asynchronous download manager that downloads files from HTTP/HTTPS URLs, supports resumable and multipart downloads, tracks jobs using SQLite, calculates SHA-256 checksums, and automatically uploads completed files to Telegram.

Built with Python, `asyncio`, `aiohttp`, `aiosqlite`, and the Telegram Bot API.

---

## ✨ Features

### 🚀 Download Engine

* ⚡ Fully asynchronous architecture
* 🔀 Concurrent downloads
* 🧩 Multipart HTTP Range downloads
* ♻️ Resumable downloads
* 🔁 Automatic retry with exponential backoff
* 🎯 Automatic fallback to single-stream downloads
* 📦 Configurable chunk sizes
* 📏 Remote file-size detection
* 💾 Disk-space validation
* 🧹 Temporary-file cleanup
* 🔐 SHA-256 checksum generation
* 📝 `Content-Disposition` filename support
* 🛡️ Filename sanitization

### 🗃️ Job Management

* Persistent SQLite database
* SQLite WAL mode
* Job states
* Download progress
* Retry counters
* Upload counters
* Error tracking
* Creation timestamps
* Completion timestamps
* Crash recovery
* Duplicate URL detection
* Job retry
* Job cancellation
* Job listing
* Cleanup utilities

### 📡 Telegram

* Automatic document uploads
* Persistent HTTP connection
* Upload retry handling
* Telegram API error handling
* `Retry-After` support
* Automatic captions
* SHA-256 included in upload metadata

### 🔒 Security

* HTTP/HTTPS validation
* Filename sanitization
* Local/private network blocking by default
* Configurable maximum file size
* Configurable disk-space protection
* Secrets stored through environment variables

---

# 🏗️ Architecture

```text
                         ┌──────────────────┐
                         │      CLI         │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   Application    │
                         │     Manager      │
                         └────────┬─────────┘
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                │
                 ▼                ▼                ▼
        ┌────────────────┐ ┌──────────────┐ ┌───────────────┐
        │    SQLite      │ │  Downloader  │ │    Telegram   │
        │    Database    │ │              │ │    Uploader   │
        └────────────────┘ └──────┬───────┘ └───────────────┘
                                  │
                       ┌──────────┴──────────┐
                       │                     │
                       ▼                     ▼
                Multipart Parts       Single Stream
                       │
                       ▼
                 Final File
                       │
                       ▼
                  SHA-256
                       │
                       ▼
                   Telegram
```

---

# 📁 Project Structure

```text
telegram-download-manager/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── downloader.py
│   ├── main.py
│   ├── models.py
│   ├── telegram.py
│   └── utils.py
│
├── downloads/
│   └── .gitkeep
│
├── logs/
│   └── .gitkeep
│
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

Runtime-generated files:

```text
jobs.db
downloads/*
logs/*
.env
```

These should **never be committed to GitHub**.

---

# 🧰 Requirements

* Python 3.10+
* Telegram Bot
* Telegram chat/channel/group ID
* Internet connection

Recommended:

```text
Python 3.11+
```

---

# 🚀 Installation

## 1. Clone the repository

```bash
git clone https://github.com/ItsWanheda/telegram-download-manager.git
cd telegram-download-manager
```

---

## 2. Create a virtual environment

### Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

---

# 🔐 Configuration

Copy:

```text
.env.example
```

to:

```text
.env
```

### Windows

```powershell
copy .env.example .env
```

### Linux/macOS

```bash
cp .env.example .env
```

Then configure:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

# 🤖 Telegram Setup

Create a Telegram bot through:

```text
@BotFather
```

Create your bot and obtain the bot token.

Then add the bot to the destination chat/channel/group and configure:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Never commit your real token.

---

# ▶️ Usage

## Download a file

```bash
python -m app.main "https://example.com/file.zip"
```

---

## Download multiple files

```bash
python -m app.main \
"https://example.com/file1.zip" \
"https://example.com/file2.zip" \
"https://example.com/file3.zip"
```

Windows PowerShell:

```powershell
py -m app.main `
"https://example.com/file1.zip" `
"https://example.com/file2.zip" `
"https://example.com/file3.zip"
```

---

# 📊 Job Status

View recent jobs:

```bash
python -m app.main --status
```

Example:

```text
ID    STATUS        FILE                                PROGRESS
---------------------------------------------------------------------------
8     completed     ubuntu.iso                         100.0%
7     uploading     archive.zip                        100.0%
6     downloading   large-file.bin                      63.4%
5     failed        backup.tar                          42.1%
```

---

# ♻️ Resume Jobs

Recover pending jobs:

```bash
python -m app.main --resume
```

Interrupted jobs can be recovered after restarting the application.

---

# 🔁 Retry a Job

```bash
python -m app.main --retry 5
```

Replace `5` with the actual job ID.

---

# ❌ Cancel a Job

```bash
python -m app.main --cancel 6
```

---

# 🧹 Cleanup

Remove completed database records and temporary download files:

```bash
python -m app.main --cleanup
```

---

# ⚙️ Configuration

| Variable               |        Default | Description              |
| ---------------------- | -------------: | ------------------------ |
| `TELEGRAM_BOT_TOKEN`   |              — | Telegram bot token       |
| `TELEGRAM_CHAT_ID`     |              — | Telegram destination     |
| `DOWNLOAD_DIR`         |    `downloads` | Download directory       |
| `DB_PATH`              |      `jobs.db` | SQLite database          |
| `LOG_FILE`             | `logs/app.log` | Application log          |
| `MAX_DOWNLOAD_WORKERS` |            `3` | Concurrent downloads     |
| `PART_WORKERS`         |            `4` | Concurrent parts/file    |
| `UPLOAD_WORKERS`       |            `2` | Upload concurrency       |
| `PART_SIZE`            |        `8 MiB` | Multipart size           |
| `CHUNK_SIZE`           |        `1 MiB` | IO chunk size            |
| `MAX_RETRIES`          |            `5` | Retry count              |
| `REQUEST_TIMEOUT`      |         `3600` | Download timeout         |
| `UPLOAD_TIMEOUT`       |         `3600` | Upload timeout           |
| `RESUME_DOWNLOADS`     |         `true` | Resume partial files     |
| `VERIFY_CHECKSUM`      |         `true` | Calculate SHA-256        |
| `DELETE_AFTER_UPLOAD`  |         `true` | Delete local files       |
| `ALLOW_PRIVATE_HOSTS`  |        `false` | Allow private IP targets |
| `MAX_FILE_SIZE`        |            `0` | Maximum file size        |
| `LOG_LEVEL`            |         `INFO` | Logging level            |

---

# 🗄️ Database

The SQLite database is created automatically.

You do **not** manually create or edit `jobs.db`.

The application maintains:

```text
jobs
├── id
├── url
├── filename
├── status
├── downloaded_bytes
├── total_bytes
├── download_attempts
├── upload_attempts
├── sha256
├── error
├── created_at
├── started_at
├── downloaded_at
├── uploaded_at
├── completed_at
└── updated_at
```

---

# 🔄 Job Lifecycle

```text
QUEUED
   │
   ▼
DOWNLOADING
   │
   ├──────────────► FAILED
   │                   │
   │                   ▼
   │                 RETRY
   │                   │
   │                   ▼
   └────────────► QUEUED
                       │
                       ▼
                  DOWNLOADING
                       │
                       ▼
                   UPLOADING
                       │
                       ▼
                  COMPLETED
```

Cancellation:

```text
QUEUED ─────────► CANCELLED
DOWNLOADING ────► CANCELLED
UPLOADING ──────► CANCELLED
```

---

# 🧩 Multipart Downloads

For servers supporting HTTP Range requests, a large file can be split into multiple parts:

```text
File
│
├── Part 00000
├── Part 00001
├── Part 00002
├── Part 00003
└── Part 00004
```

These parts are downloaded concurrently and assembled into the final file.

If the server does not support Range requests, the downloader automatically falls back to single-stream downloading.

---

# ♻️ Resumability

Partial downloads are preserved when:

```env
RESUME_DOWNLOADS=true
```

For example:

```text
downloads/
├── archive.zip.part00000
├── archive.zip.part00001
├── archive.zip.part00002
└── archive.zip.part00003
```

A restart does not necessarily require downloading completed parts again.

---

# 🔐 SHA-256 Verification

When:

```env
VERIFY_CHECKSUM=true
```

the application calculates:

```text
SHA-256
```

after the download completes.

The checksum is stored in SQLite and included in the Telegram caption.

Example:

```text
📦 archive.zip
Job: #42
Size: 1.42 GB
SHA-256: 8a4f...
```

---

# 🛡️ Security

Private/local network targets are blocked by default:

```env
ALLOW_PRIVATE_HOSTS=false
```

This helps prevent accidental requests to internal addresses such as:

```text
127.0.0.1
localhost
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
169.254.0.0/16
```

Enable private targets only when you intentionally need them:

```env
ALLOW_PRIVATE_HOSTS=true
```

---

# 💾 Disk Protection

The application checks available disk space before starting downloads.

Configure:

```env
MIN_FREE_DISK_SPACE=536870912
```

The default reserves approximately:

```text
512 MiB
```

You can also limit remote file size:

```env
MAX_FILE_SIZE=5368709120
```

The above example limits downloads to approximately:

```text
5 GiB
```

Use:

```env
MAX_FILE_SIZE=0
```

for unlimited size.

---

# 📝 Logging

Logs are written to:

```text
logs/app.log
```

and displayed in the terminal.

Example:

```text
2026-08-21 12:00:01 | INFO | download_manager | Starting job 1
2026-08-21 12:00:04 | INFO | download_manager | Job 1: 24.5%
2026-08-21 12:00:17 | INFO | download_manager | Job 1: calculating SHA-256
2026-08-21 12:00:20 | INFO | download_manager | Job 1: uploading to Telegram
2026-08-21 12:00:24 | INFO | download_manager | Job 1 completed
```

---

# 🧪 Testing

Basic configuration test:

```bash
python -m app.main --status
```

Expected on a fresh installation:

```text
No jobs found.
```

Test URL processing:

```bash
python -m app.main "https://example.com/test.zip"
```

---

# ⚠️ Important Notes

### Do not commit `.env`

Your Telegram token is sensitive.

Never commit:

```text
.env
```

### Do not commit `jobs.db`

The database contains runtime state.

### Do not commit downloaded files

The `.gitignore` excludes:

```text
downloads/*
```

### Do not expose your bot token

If your token is accidentally published, immediately revoke/regenerate it through Telegram's bot management interface.

---

# 📌 GitHub Publishing

Before the first commit:

```bash
git status
```

Make sure you do **not** see:

```text
.env
jobs.db
downloads/*.zip
downloads/*.iso
logs/*.log
```

Then:

```bash
git add .
git commit -m "feat: launch async telegram download manager"
git branch -M main
git remote add origin https://github.com/ItsWanheda/telegram-download-manager.git
git push -u origin main
```

---

# 🏷️ Suggested GitHub Topics

```text
python
telegram
telegram-bot
download-manager
asyncio
aiohttp
sqlite
aiosqlite
multipart-download
resumable-download
file-downloader
automation
async-python
telegram-bot-api
```

---

# 📄 License

This project is released under the MIT License.

See `LICENSE`.

---

# 🚧 Roadmap

* [ ] Web dashboard
* [ ] REST API
* [ ] WebSocket live progress
* [ ] Authentication
* [ ] Download priority queue
* [ ] Bandwidth throttling
* [ ] Scheduled downloads
* [ ] Telegram media groups
* [ ] Upload progress reporting
* [ ] Multiple Telegram destinations
* [ ] Configurable per-host limits
* [ ] Download history dashboard
* [ ] Docker support
* [ ] Docker Compose
* [ ] Prometheus metrics
* [ ] Automated tests
* [ ] CI/CD
* [ ] Plugin system

---

# 👨‍💻 Author

**Jax Nomad**

Built with Python, asyncio, aiohttp, SQLite, and the Telegram Bot API.

---

# ⭐ Support

If this project is useful, consider giving the repository a ⭐ on GitHub.

```text
Download → Verify → Upload → Track
```

**Fast. Resumable. Persistent. Automated.**
