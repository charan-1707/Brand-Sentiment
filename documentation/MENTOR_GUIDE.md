# Brand Sentiment Analyzer — Mentor Guide

## 1. The problem it solves (1 line)

Companies get thousands of opinions on social media every day (posts, comments, reviews) — nobody can read them all manually, so this app **collects them automatically, reads them with Machine Learning, and shows a live dashboard of what people think about a product**.

```
Before: intern scrolling Twitter all day, copying facts into Excel
After : app does it 24/7 — collects, judges, charts, and exports a PDF report
```

---

## 2. What the app actually does (the big picture)

```
        ┌─────────┐   ┌──────────────┐   ┌────────────┐   ┌──────────────┐   ┌──────────┐
        │  DATA   │ → │  READ + JUDGE │ → │  STORE      │ → │  SHOW         │ → │  EXPORT  │
        └─────────┘   └──────────────┘   └────────────┘   └──────────────┘   └──────────┘

  collects mentions    ML model decides:        saved in MySQL    KPIs + charts    CSV / PDF in
  from internet        positive / negative /    ('mentions'       every role       one click
  (or simulates        neutral + topic tags     table)            can see          (Reports)
  fake ones)           (delivery, price...)
```

Every product works — the **tracked brand is just a setting** (`BRAND_NAME=Samsung`, `Nike`, anything in `.env`). Demo mode defaults to `"Brand"`.

---

## 3. Technology stack (plain words)

| Spot in the app | What is used | Why this |
|---|---|---|
| UI (frontend) | **React 18** + Vite + axios + Recharts | Fast pages, interactive charts |
| Application (backend) | **Python + FastAPI** | Easy REST APIs, has auto `/docs` page |
| Job that runs "every 5 minutes" | **APScheduler** | Built-in background scheduler |
| Database | **MySQL 8 + SQLAlchemy** | Real relational storage |
| NLP intelligence | **scikit-learn**: TF-IDF + Logistic Regression | Trained once on 200k real tweets (Kaggle) |
| Reports | **pandas** (CSV) + **reportlab** (PDF) | Standard export tools |
| Live data pulls | httpx (HTTP) + public APIs: HackerNews, Reddit RSS, Mastodon, Bluesky, GDELT | No API keys needed |
| Login security | JWT (`python-jose`) + hashed passwords (pbkdf2) | Standard auth |
| Everything runs inside | **Docker Compose** (3 containers) | Same behavior on any PC |

---

## 4. The modules (folder-by-folder)

### Module 1 — Authentication & roles (`backend/auth.py`, `routers/auth.py`)
* Register / `Login` / logout. After login the backend hands user a **JWT token** (valid 2h) — every following request proves who they are.
* 3 roles, stricter rights top → bottom:
  * `viewer` — can only LOOK (dashboard, mentions, reports)
  * `manager` — can also ADD data (type mentions, upload CSV) and generate reports
  * `admin` — manages users, retrains model, controls ingestion, wipes demo data
* First startup auto-creates the admin account: `admin / admin123`.

### Module 2 — Data ingestion `backend/ingestion/` (4 channels)
All four paths converge to the same gate: **clean the text → ML classifies it → save to DB**.

| Channel | File | Trigger | Notes |
|---|---|---|---|
| Simulated generator | `generator.py` | every 5 min (scheduler), 8 mentions/batch | Product-neutral templates (32 total), recent-heavy fake timestamps, slight negative drift so demo charts look realistic |
| Seed demo | same file | Admin → "Seed 150 demo mentions" | Instant 150 mentions spread over 30 days |
| Real internet pull | `real_sources.py` | Admin → "Pull REAL data" | HN + Reddit + Mastodon + Bluesky + GDELT; safe-to-fail (a dead site = just a note, never crashes) |
| CSV import | `csv_import.py` | Mentions page (manager) | Bulk file upload, max 25 MB; each row still goes through the ML |

### Module 3 — The NLP engine `backend/sentiment/` (the heart)
* **Training (once):** `train.py` reads Kaggle Twitter CSV (200k rows) → `TfidfVectorizer` (15k word-features) → `LogisticRegression` → saved as `models_out/*.joblib`. Accuracy measured on unseen 20%: **79.8%**.
* **Predicting (always):** `classifier.py` loads the model at startup, then for each mention:
  1. `preprocess.py` cleans text (removes links, `#tags`, `@names`)
  2. model stamps `positive / negative / neutral` + confidence (0-1)
  3. keyword rules tag topics: `refund, delivery, support, warranty, price, quality, performance, software, apps, design, availability` (works for ANY product)
* **Retrain from the UI:** Admin page can upload a new CSV (or press "Retrain on bundled data") → model updates in-place, no restart.
* Safety net: if a model file is missing, the app still works using **VADER** (a rule-based sentiment library).

### Module 4 — Dashboard API + charts (`routers/dashboard.py` → frontend `Dashboard.jsx`)
* Backend exposes 6 JSON endpoints: `/summary, /trends, /distribution, /topics, /complaints, /sources` (SQL aggregations over the mentions table).
* Frontend calls all 6 with **one click refresh** (`Promise.all`) and draws:
  KPI cards + area chart (trend over time) + bar chart (topics) + pie chart (sentiment split) + source bars + recent complaints feed.
* `?days=30` dropdown changes the analysis window on every chart simultaneously.

### Module 5 — Reports (`routers/reports.py` → `reports/generator.py`)
* Manager clicks: choose period + `csv` or `pdf` →
  * **PDF:** title "Brand Sentiment Analyzer", KPI table, top-topics table, worst recent complaints.
  * **CSV:** raw mentions list.
* Saved in DB + a file; everyone (viewer too) can download later via a blob link.

### Module 6 — Admin console (`routers/admin.py` → `Admin.jsx`)
| Control | Meaning |
|---|---|
| Users & roles table | promote/demote `viewer→manager→admin`, deactivate users |
| "Sentiment model" card | accuracy, what it trained on, **retrain button/file upload** |
| "Scheduled ingestion" card | `Run now` (batch immediately), `Pause / Resume` (stop the 5-min job), next-run status |
| "Pull REAL mentions" | live internet data for any product name |
| "Demo reset" (danger zone) | **wipes ALL mentions + jobs + reports + report files** for a clean-slate demo; users/logs/model kept |

---

## 5. Tech design / tools choice (defend-long version)

* **FastAPI + one process**: API, scheduler, ML all live in one backend container — simple to demo and explain; purpose: business works even if a data source dies (autonomy, monitoring).
* **Rate limiting middleware (300 req/min) + security headers**: shows OS-level hardening and controls API uploads.
* **Docker Compose** = 3 services: `db` (MySQL), `backend` (:8000), `frontend` (:8080). One command `docker compose up --build -d` starts everything on any machine — that's why the app is portable.
* **nginx** in the frontend container: serves React build, forwards `/api/*` to backend — so the browser talks to ONE origin; plus CORS: local dev only allowed origins (5173).
* **Environment variables** (`backend/.env`): DB credentials, `SECRET_KEY` (JWT signing), `BRAND_NAME` (tracked product), interval, rate limit, admin credentials — security-sensitive info out of source code.

---

## 6. Quick run instructions

**Full stack (recommended):**
```powershell
docker compose up --build -d     # starts db + backend + frontend
```
Open:
* App:  `http://localhost:8080` (login `admin / admin123`)
* API docs:  `http://localhost:8000/docs`
* Health:  `http://localhost:8000/api/ready` → `{"ready": true}`
* Admin page → **Seed demo** for instant charts

**Local development (only if you want code edits):** Python venv + `uvicorn main:app --port 8000` / Node + `npm run dev` (Vite :5173 proxies `/api` to :8000).

---

## 7. Tests & quality

* Unit tests: run from `backend/` with `python -m pytest tests -q` — 11 tests (classifier + preprocess, no DB needed), all green.
* `backend/verify_e2e.py` — end-to-end smoke (health → login → seed → dashboard → reports → forbidden actions rejected for the wrong role).
* Manual RBAC check: a non-admin calling `/api/admin/reset` → blocked (401/403).

---

## 8. Nice 5-minute demo script for mentor

```
1. Login as admin → point out 3 links: Dashboard / Mentions / Reports / Admin
2. Pause scheduler + Reset all demo data    (clean slate)
3. Add text mention by hand   "delivery took forever and box arrived damaged"
     → auto-classified NEGATIVE, topic: delivery; facet appears in dashboard
4. Admin → Seed 150 demo mentions → go to Dashboard → all KPIs + charts alive
5. Admin → pull live mentions (e.g. brand:  Samsung)  → REAL posts from Reddit/HN/Mastodon/Bluesky flow in
6. Show the topic breakdown updating live (refund, delivery, support, quality...)
7. Reports → generate PDF → download — full report of everything generated
8. Admin → Remove all demo data (clean slate before leaving)
```
---
