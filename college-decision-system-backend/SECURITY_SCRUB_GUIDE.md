# Security Scrubbing and Verification Guide

## 1. Scrubbing Hardcoded Secrets from Git History

If `.env` or any other file with sensitive keys (like `GEMINI_API_KEY`) was accidentally committed to your Git repository, simply deleting the file in your current working directory and making a new commit is **not enough**. The secret still lives in your project's history.

You need to rewrite the history to remove the file completely.

### Option A: Using `git filter-repo` (Recommended and Fastest)

[`git filter-repo`](https://github.com/newren/git-filter-repo) is the modern, officially recommended tool for rewriting Git history.

**Step 1: Install `git-filter-repo`**
Make sure you have Python installed, then run:
```bash
pip install git-filter-repo
```

**Step 2: Scrub the `.env` file**
In your repository root directory (e.g., `C:\Users\mh978\Downloads\college-decision`), run:
```bash
git filter-repo --path college-decision-system/.env --invert-paths
```
*Note: If your `.env` is located somewhere else or you have multiple, adjust the `--path` accordingly. This command removes the file entirely from history.*

**Step 3: Force push the rewritten history**
Because you rewrote the history, you must overwrite the remote repository (like GitHub/GitLab).
```bash
git push origin --force --all
```

### Option B: Using `git filter-branch` (Native fallback, slower)

If you cannot install `git filter-repo`, you can use the built-in, though deprecated, `filter-branch`:

```bash
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch college-decision-system/.env" --prune-empty --tag-name-filter cat -- --all
```
Then force push:
```bash
git push origin --force --all
```

---

## 2. Verifying Secure Secret Loading

Now that we have secured `app/config/settings.py` (it uses `pydantic-settings` with the `SecretStr` type for `GEMINI_API_KEY` and loads environment variables gracefully), you should verify it works properly.

### How to verify:

1. **Check local startup:** 
   Run your application as usual (e.g., `uvicorn app.main:app --reload`). 
   Because of `env_file=".env"`, Pydantic will auto-load your `.env` file in local development without crashing if it's there. 

2. **Verify `.gitignore` is working:**
   Run `git status`. Your `.env` file should **not** show up as an untracked or modified file. This confirms `git` is ignoring it.

3. **Verify the `SecretStr` protection:**
   If you (or another developer) try to print or log the settings anywhere in the codebase:
   ```python
   from app.config.settings import settings
   print(settings.GEMINI_API_KEY)
   ```
   **Output:** 
   It will print `**********` instead of the actual API key. 
   
   To actually *use* the key in your code (like when calling the Gemini client), you now must explicitly ask Pydantic to reveal it:
   ```python
   actual_key = settings.GEMINI_API_KEY.get_secret_value()
   ```
   *Note: I did a quick codebase search and it doesn't appear `settings.GEMINI_API_KEY` is being actively leveraged directly as a raw variable elsewhere in the active routing/use-case paths currently, but this safeguard natively halts accidental leaks going forward.*

4. **Verify Environment Variable Precedence (e.g., in Docker/Production):**
   If you rename `.env` to `.env.backup` and set the environment variable directly in your terminal:
   ```powershell
   $env:GEMINI_API_KEY="my-secure-production-key"
   uvicorn app.main:app --reload
   ```
   Your app will boot perfectly, pulling the key straight from the environment map. Pydantic maps `GEMINI_API_KEY` directly to the `Settings` schema. This is how you run it safely in production!
