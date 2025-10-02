# Globridge — MVP

A minimal, **fully working** MVP for cross-border expansion matchmaking.

**Features**

- Business listing portal (create profile: brand story, investment needs, expansion potential)
- Cost comparison tool (compare expansion costs across countries, e.g., USA vs India)
- Investor/partner matching (investors browse opportunities; simple matching)
- Simple communication (in‑app messaging). Optional email notifications via SMTP env vars.

## Quick start

```bash
# 1) Create a virtual env (optional but recommended)
python3 -m venv .venv && source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) Run the server
export GLOBRIDGE_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
uvicorn app.main:app --reload
```

Now open http://127.0.0.1:8000

### Default roles

- **Business** users can create/edit one business profile.
- **Investor** users can browse, match, and message business owners.

### Optional SMTP (email notifications for messages)

Create a `.env` in project root (or export shell envs):

```
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=youruser
SMTP_PASSWORD=yourpass
SMTP_FROM="Globridge <no-reply@globridge.app>"
```

If SMTP is **not** set, in‑app messaging still works; emails are simply skipped.

### Cost model

The cost tool uses a simple multiplier matrix and baseline inputs. You can tune `COUNTRY_MULTIPLIERS` in `app/main.py` or pass custom inputs in the UI.

This is an MVP; you can add real data or APIs later.

---

## Project layout

```
globridge_mvp/
├── app/
│   ├── main.py           # FastAPI app, DB models, API routes
│   └── __init__.py
├── templates/
│   └── index.html        # Single-page UI
├── static/
│   ├── styles.css
│   └── app.js            # SPA logic (fetch API + UI)
├── requirements.txt
└── README.md
```

### Admin reset

If you need a clean DB, stop the server and delete `globridge.db` in the project root.

---

## Deploying cheaply

- **Railway** / **Render**: push this folder to a Git repo and deploy a Python service with `uvicorn app.main:app --host 0.0.0.0 --port 10000` (or provided port). Add a persistent disk for `globridge.db`.
- **Fly.io**: `fly launch` with a simple Dockerfile, mount a volume for the SQLite DB.
- **Local LAN / demo day**: just run `uvicorn` locally and share your screen.
```