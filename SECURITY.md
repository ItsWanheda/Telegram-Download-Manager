# Security Policy

## 🔐 Security Policy

The security of Telegram Download Manager is taken seriously.

This project downloads remote files and transfers them to Telegram, so vulnerabilities involving network requests, URL handling, filesystem access, credentials, and dependency security should be reported responsibly.

---

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 2.x     | ✅ Yes     |
| 1.x     | ❌ No      |
| < 1.x   | ❌ No      |

Only the latest stable release receives security fixes.

---

# 🚨 Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub Issues.**

Instead, use GitHub's private security reporting functionality when available:

**Repository → Security → Report a vulnerability**

If private vulnerability reporting is unavailable, contact the project maintainer privately through the contact information listed on the repository profile.

---

# 📋 What to Include

Please provide as much of the following information as possible:

* Vulnerability description
* Affected version
* Affected component/file
* Steps to reproduce
* Proof of concept, if available
* Expected behavior
* Actual behavior
* Potential security impact
* Suggested mitigation, if known

Please avoid including:

* Telegram bot tokens
* Chat IDs when unnecessary
* Private URLs
* Passwords
* API keys
* Personal information
* Production credentials

Use placeholders instead.

Example:

```text
TELEGRAM_BOT_TOKEN=<REDACTED>
```

---

# 🎯 Security Areas

Security reports involving the following areas are especially important:

### URL Handling

* SSRF
* URL validation bypass
* DNS rebinding
* redirect-based bypasses
* internal network access

### Filesystem

* Path traversal
* Arbitrary file writes
* Unsafe filename handling
* Symlink attacks
* Temporary-file vulnerabilities

### Telegram

* Credential exposure
* Token leakage
* Unauthorized uploads
* API authentication issues

### Database

* SQL injection
* Database corruption
* Unauthorized job manipulation

### Dependencies

* Vulnerable third-party packages
* Dependency confusion
* Supply-chain vulnerabilities

### Application

* Command injection
* Arbitrary code execution
* Denial of service
* Resource exhaustion

---

# 🛡️ Responsible Disclosure

Please allow reasonable time for the vulnerability to be investigated and fixed before publicly disclosing technical details.

Do not exploit a vulnerability beyond what is necessary to demonstrate the issue.

Do not access, modify, delete, or exfiltrate data that does not belong to you.

---

# 🔒 Secrets

Never commit secrets to the repository.

Examples include:

```text
.env
TELEGRAM_BOT_TOKEN
API keys
passwords
private keys
credentials
session tokens
```

The repository intentionally provides:

```text
.env.example
```

instead of a real `.env`.

---

# ⚠️ SSRF Protection

The application blocks private/local network destinations by default:

```env
ALLOW_PRIVATE_HOSTS=false
```

This should remain disabled unless internal network downloads are explicitly required.

---

# 📦 Dependency Security

Dependencies should be kept up to date.

Review:

```text
requirements.txt
```

regularly and monitor GitHub Dependabot/security alerts.

---

# 🧪 Security Testing

Before submitting security-sensitive changes, contributors should test:

* URL validation
* private IP blocking
* redirect handling
* filename sanitization
* path traversal prevention
* oversized downloads
* malformed HTTP responses
* retry behavior
* Telegram credential handling

---

# 📢 Disclosure

Once a vulnerability has been fixed, the project may publish a security advisory containing:

* Affected versions
* Fixed versions
* Vulnerability description
* Severity
* Mitigation
* Credit to the reporter, when requested

---

Thank you for helping keep the project secure.
