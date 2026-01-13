# Pre-Push Checklist

Run these checks before pushing to GitHub to ensure credentials are secure.

## ✅ Security Checklist

### 1. Verify .env is ignored

```bash
git check-ignore .env
```

**Expected:** `.env` (file is ignored) ✓

---

### 2. Check git status

```bash
git status
```

**Verify:** `.env` is NOT listed ✓

---

### 3. Dry-run add all files

```bash
git add -n .
```

**Verify:** `.env` does NOT appear in the list ✓

---

### 4. Check ignored files

```bash
git status --ignored
```

**Verify:** `.env` appears under "Ignored files" ✓

---

### 5. Test configuration loads

```bash
python utils/config.py
```

**Expected:** "OK - Configuration loaded successfully" ✓

---

## 📋 Files That Should Be Committed

✅ `.gitignore` - Protects .env  
✅ `env.example` - Template with placeholders  
✅ `SETUP.md` - Setup instructions  
✅ `utils/config.py` - Config loader  
✅ All workflow scripts (*.py)  
✅ Documentation (*.md)  

## ❌ Files That Should NEVER Be Committed

❌ `.env` - Your actual credentials  
❌ `__pycache__/` - Python cache  
❌ `*.pyc` - Compiled Python  

---

## 🚀 Ready to Push?

If all checks pass:

```bash
# 1. Add files
git add .

# 2. Double-check status
git status

# 3. Commit
git commit -m "Your commit message"

# 4. Push
git push origin main
```

---

## 🆘 Emergency: I Accidentally Committed .env

**If you haven't pushed yet:**

```bash
# Remove from staging
git reset HEAD .env

# Ensure it's in .gitignore
echo ".env" >> .gitignore
```

**If you already pushed:**

```bash
# 1. Remove from repository
git rm --cached .env
git commit -m "Remove .env file"
git push

# 2. Update .gitignore
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to .gitignore"
git push

# 3. IMMEDIATELY rotate your API keys in Azure Portal!
```

Then follow: [GitHub Guide - Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

---

## 📝 Quick Reference

| File | Status | Action |
|------|--------|--------|
| `.env` | Ignored | Never commit |
| `env.example` | Tracked | Safe to commit |
| `.gitignore` | Tracked | Must commit |
| `utils/config.py` | Tracked | Safe to commit |

---

**Last Check:** Run `git diff --cached` to see what will be committed

**Safe:** ✓ No credentials in the diff

**Not Safe:** ✗ Credentials visible → Remove those files!
