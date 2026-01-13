# Security Setup - Credentials Management

## Overview

This document explains how credentials are securely managed to prevent accidental exposure on GitHub.

**Status:** ✅ Repository is now safe to push to GitHub

---

## What Was Changed

### 1. Environment Variables System

**Created:**
- `.gitignore` - Prevents `.env` from being committed
- `.env` - Your actual credentials (ignored by git)
- `env.example` - Template file (safe to commit)
- `utils/config.py` - Loads credentials from environment

**Updated:**
- `02_map_etim_to_oekobaudat_llm.py` - Reads from env vars
- `utils/test_azure_openai.py` - Reads from env vars
- `requirements_mapper.txt` - Added python-dotenv

### 2. Security Flow

```
┌─────────────────────────────────────────────────────┐
│  env.example (GitHub ✓)                             │
│  - Template with placeholders                       │
│  - Safe to commit                                   │
└─────────────────────────────────────────────────────┘
                        ↓ User copies
┌─────────────────────────────────────────────────────┐
│  .env (Ignored by git ✗)                            │
│  - Contains actual credentials                      │
│  - Never committed                                  │
│  - Listed in .gitignore                             │
└─────────────────────────────────────────────────────┘
                        ↓ Loaded by
┌─────────────────────────────────────────────────────┐
│  utils/config.py                                    │
│  - Reads environment variables                      │
│  - Validates configuration                          │
└─────────────────────────────────────────────────────┘
                        ↓ Used by
┌─────────────────────────────────────────────────────┐
│  Workflow Scripts                                   │
│  - 02_map_etim_to_oekobaudat_llm.py                 │
│  - utils/test_azure_openai.py                       │
└─────────────────────────────────────────────────────┘
```

---

## Files Status

### ✅ Safe to Commit (Public)

| File | Purpose |
|------|---------|
| `.gitignore` | Lists files to ignore |
| `env.example` | Template with placeholders |
| `utils/config.py` | Loads environment variables |
| `SETUP.md` | Setup instructions |
| All `.py` workflow files | Code that reads from env |

### ❌ Never Commit (Private)

| File | Reason | Protected By |
|------|--------|--------------|
| `.env` | Contains actual API keys | `.gitignore` |
| `__pycache__/` | Python cache | `.gitignore` |
| `*.pyc` | Compiled Python | `.gitignore` |

---

## Verification Checklist

Before pushing to GitHub:

```bash
# 1. Check .gitignore exists
ls .gitignore

# 2. Verify .env is ignored
git status
# .env should NOT appear in the list

# 3. Test configuration loads
python utils/config.py

# 4. Check what will be committed
git add .
git status
# Verify .env is NOT in "Changes to be committed"
```

---

## How It Works

### Old Way (❌ Insecure)

```python
# Hardcoded in code
AZURE_OPENAI_API_KEY = "7XlbGEPxqGU7QcpVQFZnRwLFnCn9qUwN..."  # ❌ Visible in GitHub!
```

### New Way (✅ Secure)

**In `.env` file (ignored by git):**
```env
AZURE_OPENAI_API_KEY=7XlbGEPxqGU7QcpVQFZnRwLFnCn9qUwN...
```

**In code:**
```python
from utils.config import get_azure_config

config = get_azure_config()  # Reads from .env
api_key = config['api_key']   # ✅ Not in code!
```

---

## First-Time Setup for New Users

When someone clones your repository:

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/bsDD.git
cd bsDD

# 2. Install dependencies
pip install -r requirements_mapper.txt

# 3. Create .env from template
cp env.example .env

# 4. Edit .env with their own credentials
# (They need to get their own Azure OpenAI credentials)

# 5. Verify setup
python utils/config.py
```

---

## Configuration API

### Load Configuration

```python
from utils.config import get_azure_config

config = get_azure_config()
# Returns: {
#   'endpoint': 'https://...',
#   'api_key': '...',
#   'deployment': 'gpt-5-mini'
# }
```

### Check Configuration

```python
from utils.config import check_config

if check_config():
    print("Configuration is valid")
else:
    print("Please set up .env file")
```

### Get Individual Variables

```python
from utils.config import get_env

custom_var = get_env('MY_CUSTOM_VAR', default='default_value')
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Yes | - | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Yes | - | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | No | `gpt-5-mini` | Model deployment name |

---

## Troubleshooting

### Error: ".env file not found"

**Solution:**
```bash
cp env.example .env
# Then edit .env with your credentials
```

### Error: "AZURE_OPENAI_ENDPOINT not set"

**Solution:** Edit `.env` file and add:
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

### .env file is showing in git status

**Solution:**
```bash
# Add to .gitignore
echo ".env" >> .gitignore

# Remove from git cache if already added
git rm --cached .env
```

### Accidentally committed .env file

**Solution:**
```bash
# Remove from git
git rm --cached .env
git commit -m "Remove .env file"

# Ensure .gitignore has .env
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to .gitignore"

# IMPORTANT: Rotate your API keys in Azure Portal!
```

---

## Best Practices

### ✅ DO

- Use `.env` for all secrets
- Keep `.gitignore` updated
- Provide `env.example` as template
- Document setup process
- Check `git status` before committing
- Rotate keys if accidentally exposed

### ❌ DON'T

- Hardcode credentials in code
- Commit `.env` file
- Share `.env` file
- Put credentials in comments
- Use production keys in examples

---

## Additional Security

### For CI/CD (GitHub Actions, etc.)

Use repository secrets instead of `.env`:

1. Go to GitHub repository → Settings → Secrets
2. Add secrets:
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_DEPLOYMENT`

3. Reference in workflow:
```yaml
env:
  AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
  AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
  AZURE_OPENAI_DEPLOYMENT: ${{ secrets.AZURE_OPENAI_DEPLOYMENT }}
```

---

## Testing Security

```bash
# 1. Check .env is ignored
git check-ignore .env
# Should output: .env

# 2. Simulate adding all files
git add -n .
# -n = dry run, shows what would be added
# .env should NOT appear

# 3. Check .gitignore rules
git status --ignored
# .env should be under "Ignored files"
```

---

## References

- [12-Factor App - Config](https://12factor.net/config)
- [Python-dotenv Documentation](https://github.com/theskumar/python-dotenv)
- [GitHub - Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

---

**Status:** ✅ Credentials are now secure  
**Last Updated:** January 13, 2026  
**Safe to Push:** Yes
