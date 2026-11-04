# How to Configure the Brand Name & Run the App

Simple step-by-step. Only requirement: **Docker Desktop** installed and running.

---

## 1. Run the app (every time)

```powershell
cd <project folder>          # the folder that has docker-compose.yml
docker compose up -d         # start everything (add --build only after code/brand changes)
```

Wait ~30 seconds, then open:

| What | Where |
|---|---|
| The app (UI) | http://localhost:8080 |
| API docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health → `{"status":"ok"}` |

**Login:** `admin` / `admin123`

To fill the dashboard: Admin page → **Pause / Resume**, **Run now**, **Seed 150 demo mentions**, or **Pull REAL live mentions**.

**Stop / daily commands**

```powershell
docker compose down      # stop (data is kept in the DB volume)
docker compose up -d     # start again
docker compose ps        # status check (expect 3 healthy services)
```

---

## 2. Configure the brand name (before appending data)

The brand is set by **`BRAND_NAME`** inside the hidden file **`.env`** (project root, next to `docker-compose.yml`).

1. Open the project folder in File Explorer → enable `View ▸ Show ▸ Hidden items`.
2. Open `.env` in Notepad. It has:
   ```
   MYSQL_PASSWORD=charan1707
   SECRET_KEY=change-me-to-a-long-random-string-for-demo
   BRAND_NAME=Brand
   ```
3. Change **`BRAND_NAME=Brand`** to the product you want to analyze and save:
   ```
   BRAND_NAME=Samsung
   ```
4. Restart the stack so the new value loads:
   ```powershell
   docker compose up -d
   ```

### Where the name shows up

| Place | Behavior |
|---|---|
| Navbar title | Always "Brand Sentiment Analyzer" (generic, not brand) |
| Dashboard subtitle | Read-only info: "tracked brand: Samsung" |
| Seeded/demo mentions | New batches are tagged `brand = Samsung` |
| PDF reports | Shown in the report subtitle (Brand: Samsung) |
| Live pulls | Admin field uses it as the default brand to search |

> Old mentions keep the brand they were inserted with. To start fresh: Admin → **🧹 Wipe all demo data**, then seed again — new rows use the new brand.

### Verify it worked

```
http://localhost:8000/api/health  →  {"status":"ok","brand":"Samsung"}
```

---

## 3. Pulling real data for that brand (optional demo step)

1. Login as admin → **Admin** page
2. **🌍 Pull REAL live mentions** → type the brand (e.g. `Samsung`) → **Pull live data**
3. Mentions come from HackerNews, Reddit, Mastodon, Bluesky and News, already classified

Tip: fictional/unknown brand names return 0 rows — real product names work best.

---

## 4. If something is wrong — quick fixes

| Problem | Fix |
|---|---|
| Page says service unavailable | Is Docker Desktop running? Wait for "Engine running" |
| `ready:false db:false` | Wait 60s; check `docker compose logs db` |
| Port already in use | `docker compose down`, close other apps on 8080/8000 |
| Changed `.env` but app shows the old brand | `docker compose up -d` again to reload |
| Dashboard empty | Admin → `Run now` or `Seed 150 demo mentions` |
