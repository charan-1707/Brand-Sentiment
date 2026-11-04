"""End-to-end smoke test for the Brand Sentiment API.

Run while the server is up:  python verify_e2e.py
Covers: health, admin login+seed, dashboard analytics, CSV+PDF reports,
viewer registration, role guards (403), mention CRUD, scheduler status.
"""
import sys

import httpx

BASE = "http://127.0.0.1:8000"
passed, failed = [], []


def check(name, cond, extra=""):
    (passed if cond else failed).append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")


def main():
    r = httpx.get(f"{BASE}/api/health", timeout=10)
    check("health", r.status_code == 200, r.text[:80])

    r = httpx.post(f"{BASE}/api/auth/login",
                   data={"username": "admin", "password": "admin123"}, timeout=10)
    check("admin login", r.status_code == 200)
    if r.status_code != 200:
        print("cannot continue without admin token"); return
    admin_tok = r.json()["access_token"]
    AH = {"Authorization": f"Bearer {admin_tok}"}
    check("admin role", r.json()["user"]["role"] == "admin")

    r = httpx.get(f"{BASE}/api/auth/me", headers=AH, timeout=10)
    check("me", r.status_code == 200 and r.json()["username"] == "admin")

    r = httpx.post(f"{BASE}/api/admin/seed-demo", headers=AH, timeout=120)
    ok = r.status_code == 200 and r.json().get("added", 0) >= 100
    check("seed-demo 150 mentions", ok, str(r.json())[:100])

    r = httpx.get(f"{BASE}/api/dashboard/summary", headers=AH,
                  params={"days": 30}, timeout=15)
    s = r.json() if r.status_code == 200 else {}
    check("dashboard summary", s.get("total_mentions", 0) >= 100,
          f"total={s.get('total_mentions')}")

    for name, url in [("trends", "/api/dashboard/trends"),
                      ("distribution", "/api/dashboard/distribution"),
                      ("topics", "/api/dashboard/topics"),
                      ("complaints", "/api/dashboard/complaints")]:
        r = httpx.get(f"{BASE}{url}", headers=AH,
                      params={"days": 30, "limit": 8}, timeout=15)
        check(f"dashboard {name}",
              r.status_code == 200 and isinstance(r.json(), list)
              and len(r.json()) > 0, f"n={len(r.json()) if r.status_code == 200 else 0}")

    for fmt in ("csv", "pdf"):
        r = httpx.post(f"{BASE}/api/reports", headers=AH,
                       json={"days": 30, "format": fmt}, timeout=60)
        ok = r.status_code == 201 and r.json().get("mention_count", 0) > 0
        check(f"report {fmt} generated", ok, str(r.json())[:100])
        if ok:
            rid = r.json()["id"]
            d = httpx.get(f"{BASE}/api/reports/{rid}/download", headers=AH,
                          timeout=60)
            check(f"report {fmt} download",
                  d.status_code == 200 and len(d.content) > 1000,
                  f"bytes={len(d.content)}")

    # viewer role: register -> dashboard OK, admin route forbidden
    import random
    u = f"viewer{random.randint(1000, 9999)}"
    r = httpx.post(f"{BASE}/api/auth/register",
                   json={"username": u, "email": f"{u}@x.com",
                         "password": "pass1234"}, timeout=10)
    check("viewer register", r.status_code in (200, 201))
    r = httpx.post(f"{BASE}/api/auth/login", data={"username": u,
                                                   "password": "pass1234"},
                   timeout=10)
    check("viewer login", r.status_code == 200)
    vt = r.json().get("access_token", "")
    VH = {"Authorization": f"Bearer {vt}"}
    r = httpx.get(f"{BASE}/api/dashboard/summary", headers=VH, timeout=10)
    check("viewer reads dashboard", r.status_code == 200)
    r = httpx.get(f"{BASE}/api/admin/model", headers=VH, timeout=10)
    check("viewer blocked from admin (403)", r.status_code == 403)
    r = httpx.post(f"{BASE}/api/mentions", headers=VH,
                   json={"text": "test"}, timeout=10)
    check("viewer blocked from adding mentions (403)", r.status_code == 403)

    # manager flow: add mention (auto-classified) + model info as admin
    r = httpx.post(f"{BASE}/api/mentions", headers=AH,
                   json={"text": "My NovaPhone battery is absolutely fantastic!"},
                   timeout=15)
    m = r.json() if r.status_code == 201 else {}
    check("add mention auto-classified", m.get("sentiment") == "positive",
          f"sentiment={m.get('sentiment')}")
    mid = m.get("id")
    if mid:
        r = httpx.delete(f"{BASE}/api/mentions/{mid}", headers=AH, timeout=10)
        check("delete mention", r.status_code == 200)

    r = httpx.get(f"{BASE}/api/admin/model", headers=AH, timeout=10)
    check("model info", r.status_code == 200
          and r.json().get("backend") == "tfidf_logreg",
          str(r.json())[:120])
    r = httpx.get(f"{BASE}/api/admin/ingest/status", headers=AH, timeout=10)
    check("scheduler status", r.status_code == 200, str(r.json())[:120])
    r = httpx.get(f"{BASE}/api/admin/ingest/jobs", headers=AH, timeout=10)
    check("ingestion jobs logged",
          r.status_code == 200 and len(r.json()) >= 1)

    print(f"\n==== {len(passed)} passed, {len(failed)} failed ====")
    if failed:
        print("FAILED:", failed); sys.exit(1)


if __name__ == "__main__":
    main()
