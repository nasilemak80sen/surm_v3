# 🛢️ SURM Toolkit — Deployment & Database Guide

## Quick Answer: Session Persistence on Streamlit Cloud

**The Problem:** The app's local `sessions/` folder is ephemeral on Streamlit Cloud — it gets deleted on every container restart or redeploy.

**The Solution:** Use a **persistent PostgreSQL database** that survives across restarts. The app auto-detects your environment and switches between:
- **SQLite** (default) — local development & self-hosted servers
- **PostgreSQL** — Streamlit Cloud & multi-user production

---

## Deployment Options

### Option A — Local / Self-Hosted (SQLite)

No database setup needed. Sessions auto-save to `sessions.db` in the app folder.

```bash
# Run locally
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
streamlit run surm.py
```

Sessions persist indefinitely on your machine.

---

### Option B — Streamlit Community Cloud (PostgreSQL Required)

For Streamlit Cloud, you **must** connect a PostgreSQL database because the file system is ephemeral.

#### Step 1: Create a PostgreSQL Database

Free options:

**Option B1a: Neon (Recommended)**
1. Sign up at https://neon.tech (free tier: 0.5 GB storage, up to 100 connections)
2. Create a project → database
3. Copy the connection string (looks like `postgresql://user:password@host/dbname`)
4. Keep this safe — you'll need it in Step 3

**Option B1b: Supabase (PostgreSQL + Auth)**
1. Sign up at https://supabase.com
2. Create a new project
3. Go to **Settings → Database** → copy the connection string
4. Use the non-pooler connection string for Streamlit

**Option B1c: Railway**
1. https://railway.app — free tier with persistent storage
2. Create a PostgreSQL plugin
3. Copy `DATABASE_URL` from the environment

#### Step 2: Update `requirements.txt`

(Already done in v1.1+ — `psycopg2-binary>=2.9.0` is included)

#### Step 3: Deploy to Streamlit Cloud

1. **Push your code to GitHub** (with updated `requirements.txt`)

2. **Go to https://share.streamlit.io**
   - Click **New app**
   - Select your repository
   - Set main file to `surm.py`
   - Click **Advanced settings**

3. **Add the `DATABASE_URL` secret:**
   - In Advanced settings, paste into "Secrets" text box:
   ```toml
   DATABASE_URL = "postgresql://user:password@host:port/dbname"
   ```

4. **Deploy** — Streamlit Cloud auto-creates the `sessions` table on first run.

From now on, all user sessions are stored in your PostgreSQL database and persist across app restarts and redeploys.

---

## How the Database Layer Works

The app auto-detects which database to use:

```python
# In utils/db.py
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgresql"):
    db = PostgresDB(DATABASE_URL)  # Use PostgreSQL
else:
    db = SQLiteDB()  # Use local SQLite
```

Both backends implement the same interface:
- `save(project_name, field_name, session_data)` → overwrites
- `load(project_name, field_name)` → returns {} if not found
- `list_all()` → all sessions, newest first
- `delete(project_name, field_name)` → remove a session

Sessions are tied to **project_name + field_name** — users can save multiple versions of the same project if they change the field name.

---

## Testing the Database Locally (SQLite)

After running locally, check that sessions are saving:

```bash
# A sessions.db file will appear in surm_app/
ls -la surm_app/sessions.db

# View sessions in SQLite (optional):
sqlite3 surm_app/sessions.db
> SELECT project_name, field_name, phase, completion_pct, saved_at FROM sessions;
```

---

## Troubleshooting

### "Connection to database failed" on Streamlit Cloud

**Check:**
1. Is `DATABASE_URL` set in Streamlit Cloud secrets? (**Settings → Secrets**)
2. Is the connection string correct? (Copy-paste from your database provider)
3. Is your PostgreSQL database allowing external connections? (Neon does by default)

### "psycopg2 module not found"

Re-run:
```bash
pip install -r requirements.txt
```

### Sessions disappear after deploy

**If using Streamlit Cloud without PostgreSQL:**
- You MUST set `DATABASE_URL` in secrets, OR
- Sessions will only persist within a single container session

**If using local deployment:**
- Ensure `sessions.db` is not in `.gitignore` (it should be — it stays on your machine)
- Sessions automatically persist to `sessions.db`

---

## Production Considerations

For a **production team deployment:**

1. **Use PostgreSQL** (Neon, Supabase, or your own RDS)
2. **Set `DATABASE_URL`** as an environment variable (not hardcoded)
3. **Backup the database regularly** — PostgreSQL providers offer automated backups
4. **Monitor session count:**
   ```python
   from utils.db import get_db
   db = get_db()
   print(f"Total saved sessions: {db.get_session_count()}")
   ```

---

## File Structure After Setup

```
surm_app/
├── utils/
│   ├── db.py                  ← NEW: Database abstraction (SQLite/PostgreSQL)
│   ├── persistence.py         ← UPDATED: Uses db.py
│   └── ...
├── sessions.db                ← Created locally (SQLite)
├── requirements.txt           ← UPDATED: includes psycopg2-binary
└── ...
```

---

## Key Design Decisions

**One save per project name:**
- If user saves "Ledang FDP" again, it overwrites the previous save
- No version history by default (simplicity)
- Users can create versions by changing project name: "Ledang FDP v2"

**Auto-save + manual save:**
- **Auto-save** (silent) fires after Tabs 3–7 form submissions
- **Manual save** (button) always available on Front Page + sidebar
- Both overwrite the same record

**No user authentication:**
- Session lookup is by (project_name, field_name) only
- If two users save "Ledang FDP" simultaneously, the last one wins
- For multi-team deployment, add user_id to the session key (see extension below)

---

## Extension: Multi-User Support (Advanced)

To support multiple team members working on the same project without overwriting:

1. **Add `user_id` to the session key:**
   ```python
   # In db.py schema, change UNIQUE constraint:
   # UNIQUE(user_id, project_name, field_name)
   ```

2. **Capture user identity from Streamlit Cloud:**
   ```python
   import streamlit as st
   user = st.secrets.get("STREAMLIT_USER_ID", "anonymous")
   db.save(user, project_name, field_name, session_data)
   ```

3. **Show only the current user's sessions:**
   ```python
   sessions = db.list_all_for_user(user_id)
   ```

---

## Summary

| Deployment | Database | Sessions Persist? | Multi-User? |
|---|---|---|---|
| **Local** | SQLite | ✅ Yes (forever) | ❌ No (same machine) |
| **Docker** | SQLite | ✅ Yes (same volume) | ✅ Yes (via network) |
| **Streamlit Cloud** (no DB) | — | ❌ No (lost on restart) | ❌ No |
| **Streamlit Cloud** (PostgreSQL) | PostgreSQL | ✅ Yes (cloud DB) | ✅ Yes (all users) |

---

**Questions?** Check the PostgreSQL provider's documentation (Neon, Supabase) or ask for help in Streamlit's forum.

---

*SURM Toolkit v1.1+ with pluggable database layer*
