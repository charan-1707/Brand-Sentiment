1. Auth & Roles
- What: login/register, 3 roles (viewer read / manager +add / admin all), JWT tokens.
- Tech: FastAPI (OAuth2PasswordBearer), passwords hashed with hashlib.pbkdf2_hmac + salt, tokens via python-jose (HS256, 120 min). Frontend keeps token in localStorage, axios interceptor attaches Bearer.
2. Mention Collection (Ingestion) — backend/ingestion/
- What: Brings data in, 4 channels:
- generator.py — simulated posts (32 templates, 4 sources, random recent timestamps)
- real_sources.py — live pulls from HackerNews API, Reddit RSS, Mastodon, Bluesky, GDELT — zero API keys, never crashes (returns 0 on failure)
- csv_import.py — bulk file upload (25 MB cap)
- scheduler.py — APScheduler background job, adds 8 mentions every 5 min, logs runs to ingestion_jobs table
- Tech: Python + APScheduler (threaded cron), httpx for HTTP calls, feedparser-style RSS parse.
3. Sentiment Engine (ML core) — backend/sentiment/
- What: Decides positive/negative/neutral + extracts up to 3 topics (battery, camera, price, support...).
- Tech: scikit-learn pipeline — TfidfVectorizer (1-2 grams, 15k features) + LogisticRegression, trained on 200k Kaggle tweets (Sentiment140), 80/20 split, 79.8% accuracy. Saved with joblib in models_out/. Fallback: VADER rule-based if model file missing. preprocess.py strips URLs/hashtags before classify.
- Built once with: train.py (retrainable live from Admin page).
4. Analytics Dashboard — routers/dashboard.py + Dashboard.jsx
- What: 6 endpoints — summary, trends, distribution, topics, complaints, sources — computed in SQL via analytics.py.
- Tech: Backend SQLAlchemy aggregations; frontend React + Recharts (AreaChart trends, BarChart topics, PieChart distribution), all 6 APIs fired in Promise.all.
5. Reports — routers/reports.py + reports/generator.py
- What: One click → CSV or PDF summary of any period.
- Tech: pandas (DataFrame → CSV), reportlab (A4 PDF with KPI tables + charts), stored in generated_reports/, downloaded via Blob URL.
6. Admin Console — routers/admin.py + Admin.jsx
- What: User role management, model info/retrain, ingestion trigger/pause, live pull, job history.
- Tech: RBAC-protected FastAPI routes + React admin page.

Flow that ties it: Scheduler/seed/live → generator+real_sources → preprocess → classifier → MySQL → dashboard API → Recharts UI → pandas/reportlab PDF.