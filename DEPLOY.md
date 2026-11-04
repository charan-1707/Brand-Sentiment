# Deploy: Vercel (frontend) + Railway (backend + MySQL)

```
Browser -> Vercel (React static build) --HTTPS--> Railway (FastAPI + APScheduler)
                                                        |
                                                   Railway MySQL
```

No rewrite of the app logic. The scheduler, ML model, CSV ingestion, and reports keep working because the backend runs as a normal long-lived container.

---

## 0. Push the code to GitHub

The project is not a git repo yet. Run:

```powershell
cd E:\BrandSentiment
git init
git add .
git commit -m "Brand Sentiment Analyzer"
```

Create an empty repo on github.com (e.g. `brand-sentiment`), then:

```powershell
git remote add origin https://github.com/<you>/brand-sentiment.git
git branch -M main
git push -u origin main
```

`.gitignore` already excludes `.env`, `.venv`, `node_modules`, logs, and the 126 MB Kaggle CSV.

---

## 1. Railway — backend + MySQL

1. Go to https://railway.app → **New Project** → **Deploy from GitHub repo** → pick the repo.
2. In the project, click **New → Database → MySQL**.
3. Open the backend service → **Settings**:
   - **Root Directory**: `/backend`
   - **Builder**: `Dockerfile`
4. Open the backend service → **Variables** → **Raw editor**, paste:

```env
MYSQL_HOST=${{MySQL.MYSQLHOST}}
MYSQL_PORT=${{MySQL.MYSQLPORT}}
MYSQL_USER=${{MySQL.MYSQLUSER}}
MYSQL_PASSWORD=${{MySQL.MYSQLPASSWORD}}
MYSQL_DB=${{MySQL.MYSQLDATABASE}}
SECRET_KEY=<paste-a-long-random-string>
APP_ENV=prod
BRAND_NAME=Brand
CORS_ORIGINS=https://your-app.vercel.app
CORS_ORIGIN_REGEX=https://.*\.vercel\.app
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<pick-a-strong-password>
INGEST_SOURCE=both
```

> The backend also accepts a single `DATABASE_URL=${{MySQL.MYSQL_URL}}` instead of the five `MYSQL_*` values — both are supported.

5. **Settings → Networking → Generate Domain**. Note the URL, e.g. `https://brand-sentiment-production.up.railway.app`.
6. Wait for deploy, then check:

```
https://<railway-domain>/api/ready
```

Expected: `{"ready": true, "db": true, "model": "tfidf_logreg", ...}`

7. Optional (recommended): add volumes so retrained models and generated reports survive redeploys:
   - Volume mounted at `/app/models_out`
   - Volume mounted at `/app/generated_reports`

---

## 2. Vercel — frontend

1. Go to https://vercel.com → **Add New → Project** → import the same GitHub repo.
2. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. **Environment Variables** (Production + Preview):

```env
VITE_API_URL=https://<railway-domain>/api
```

4. **Deploy**. Note the URL, e.g. `https://brand-sentiment.vercel.app`.
5. Go back to Railway → backend → Variables → set:

```env
CORS_ORIGINS=https://brand-sentiment.vercel.app
```

Railway redeploys automatically. (The regex above already allows Vercel preview URLs.)

---

## 3. First run

1. Open the Vercel URL → login `admin` / your `ADMIN_PASSWORD`.
2. Admin → **Seed 150 demo mentions** (or **Pull REAL live mentions**).
3. Mentions → **Upload CSV** → `backend/data/demo_mentions.csv` from the repo.
4. Admin → **Retrain** (optional).
5. Reports → generate PDF/CSV.

---

## Notes & limits

- **Cost**: Railway has no permanent free tier — the $5 trial credit covers a demo; after that Hobby is ~$5/month. The scheduler only runs while the backend service is running.
- **Reports**: generated files live on the container disk. They disappear on redeploy unless you attach the optional volume.
- **Kaggle CSV**: the bundled `backend/data/kaggle_twitter.csv` (126 MB) is excluded from git/Docker on purpose. The pretrained model is shipped in `backend/models_out/`, and retraining from an uploaded CSV still works (upload limit `MAX_UPLOAD_MB=25`).
- **Secrets**: never commit `.env`; set everything in the Railway dashboard.
- **Health check**: use `/api/ready` (DB + model) rather than `/api/health`.
