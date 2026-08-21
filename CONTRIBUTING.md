# Contributing to Telegram Download Manager

Thank you for considering contributing to Telegram Download Manager! 🚀

Contributions are welcome, including:

* Bug fixes
* Security improvements
* Performance improvements
* New features
* Documentation
* Tests
* Refactoring
* Developer tooling

Please read this document before opening an issue or pull request.

---

# 📋 Table of Contents

* [Code of Conduct](#code-of-conduct)
* [Getting Started](#getting-started)
* [Development Setup](#development-setup)
* [Project Structure](#project-structure)
* [Making Changes](#making-changes)
* [Testing](#testing)
* [Code Style](#code-style)
* [Commit Messages](#commit-messages)
* [Pull Requests](#pull-requests)
* [Security Issues](#security-issues)
* [Documentation](#documentation)

---

# 🤝 Code of Conduct

All contributors are expected to follow the project's:

[Code of Conduct](CODE_OF_CONDUCT.md)

Please keep discussions constructive, respectful, and technically focused.

---

# 🚀 Getting Started

Fork the repository and clone your fork:

```bash
git clone https://github.com/ItsWanheda/telegram-download-manager.git
cd telegram-download-manager
```

Add the upstream repository:

```bash
git remote add upstream https://github.com/ORIGINAL_OWNER/telegram-download-manager.git
```

---

# 🐍 Development Setup

Create a virtual environment.

## Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
```

## Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Copy the environment template:

```bash
cp .env.example .env
```

Windows:

```powershell
copy .env.example .env
```

Configure your local Telegram credentials.

**Never commit `.env`.**

---

# 📁 Project Structure

```text
app/
├── config.py       Configuration
├── database.py     SQLite persistence
├── downloader.py   Async download engine
├── main.py         CLI/application
├── models.py       Data models
├── telegram.py     Telegram uploader
└── utils.py        Shared utilities
```

---

# 🔧 Making Changes

Create a feature branch:

```bash
git checkout -b feature/my-feature
```

For bug fixes:

```bash
git checkout -b fix/my-bug
```

Keep changes focused.

Avoid mixing unrelated changes into the same pull request.

---

# 🧪 Testing

At minimum, verify that the application starts:

```bash
python -m app.main --status
```

Test a download:

```bash
python -m app.main "https://example.com/file.zip"
```

Test job management:

```bash
python -m app.main --status
python -m app.main --resume
```

Security-sensitive changes should also test:

* URL validation
* private IP blocking
* filename sanitization
* path traversal
* retry behavior
* malformed HTTP responses
* interrupted downloads

---

# 🎨 Code Style

Follow normal Python conventions.

Recommended:

* Python 3.10+
* PEP 8
* Type hints
* Clear function names
* Small focused functions
* Explicit error handling
* Async-safe resource management

Avoid:

* unnecessary global state
* hard-coded credentials
* broad silent exception handling
* undocumented behavior
* duplicated logic

---

# 🧠 Async Code

This project uses `asyncio`.

Avoid blocking operations inside asynchronous functions when practical.

Prefer asynchronous libraries for:

```text
HTTP
SQLite
network operations
```

When unavoidable filesystem operations are expensive, consider moving them away from the event loop.

---

# 🔐 Security

Security issues must **not** be reported through public GitHub Issues.

See:

```text
SECURITY.md
```

for responsible disclosure instructions.

---

# 📝 Commit Messages

Use clear, descriptive commit messages.

Recommended format:

```text
type: short description
```

Examples:

```text
feat: add download priority queue
fix: prevent range response corruption
perf: reuse aiohttp download session
docs: improve installation guide
refactor: simplify database job updates
test: add downloader retry coverage
security: harden URL validation
ci: add Python test matrix
```

Recommended commit types:

```text
feat
fix
docs
refactor
perf
test
security
ci
build
chore
```

---

# 🔀 Pull Requests

Before opening a PR:

```bash
git pull --rebase upstream main
```

Then run your tests.

Push your branch:

```bash
git push origin feature/my-feature
```

Open a Pull Request against:

```text
main
```

---

# 📦 Pull Request Requirements

A good PR should contain:

* Clear title
* Problem description
* Solution description
* Testing performed
* Relevant screenshots/logs when useful
* Documentation updates when necessary

Keep PRs focused.

---

# 🔍 Review Process

Maintainers may review:

* Correctness
* Security
* Performance
* Compatibility
* Maintainability
* Documentation
* Test coverage

Changes may require revisions before merging.

---

# 📚 Documentation

If your feature changes user-visible behavior, update:

```text
README.md
```

If it changes configuration, update:

```text
.env.example
README.md
```

If it changes security behavior, update:

```text
SECURITY.md
```

---

# 🌱 Good First Contributions

If you're new to the project, useful contributions include:

* Documentation improvements
* Better error messages
* Tests
* CLI improvements
* Performance profiling
* Small bug fixes
* Examples

---

# ❤️ Thank You

Every contribution helps make Telegram Download Manager better.

Thank you for contributing!
