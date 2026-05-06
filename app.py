import hashlib
import json
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request

from modules.feed_parser import fetch_feeds, detect_ats
from modules.fit_scorer import calculate_fit_score
from modules.job_fetcher import (
    check_url_alive,
    extract_contact_from_text,
    extract_job_details,
    fetch_company_info,
    fetch_job_text,
    resolve_aggregator_url,
)
from modules.keyword_engine import (
    extract_resume_keywords,
    generate_recommendations,
    score_ats,
    should_skip_job,
)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
JOBS_PATH = os.path.join(BASE_DIR, "jobs.json")
VERSION_PATH = os.path.join(BASE_DIR, "VERSION")


def read_version():
    try:
        with open(VERSION_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "unknown"

VALID_STATUSES = {"new", "saved", "applied", "waiting", "rejected", "expired"}

# ── New-bucket retention policy ───────────────────────────────────────────────
# Hard ceiling: New jobs older than this always expire regardless of count.
MAX_AGE_DAYS = 30
# When the New bucket hits TRIM_THRESHOLD, trim to TRIM_AGE_DAYS to avoid
# overwhelming the queue. If it stays under TRIM_THRESHOLD, keep the full window.
TRIM_THRESHOLD = 50
TRIM_AGE_DAYS  = 7


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_jobs():
    if not os.path.exists(JOBS_PATH):
        return {}
    with open(JOBS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_jobs(jobs):
    with open(JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)


def make_job_id(url):
    return hashlib.sha256(url.encode()).hexdigest()[:8]


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def resolve_path(config_path):
    """Resolve a path relative to BASE_DIR."""
    if os.path.isabs(config_path):
        return config_path
    return os.path.normpath(os.path.join(BASE_DIR, config_path))


def ensure_resume_keywords(config):
    """Cache resume keywords in config.json if not already done."""
    if not config.get("resume_keywords"):
        resume_path = resolve_path(config["resume_path"])
        print(f"[startup] Extracting keywords from {resume_path}")
        keywords = extract_resume_keywords(resume_path)
        config["resume_keywords"] = keywords
        save_config(config)
        print(f"[startup] Cached {len(keywords)} resume keywords")
    return config


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    return jsonify(load_jobs())


@app.route("/api/refresh", methods=["POST"])
def refresh_feeds():
    config = load_config()
    config = ensure_resume_keywords(config)
    resume_keywords = config["resume_keywords"]
    ats_weights  = config["ats_score_weights"]
    user_profile = config.get("user_profile", {})
    job_filters  = config.get("job_filters", {})
    jobs = load_jobs()

    feed_items = fetch_feeds(config)
    added = 0
    skipped = 0

    ats_domains = config.get("ats_domains", {})

    for item in feed_items:
        # For aggregator URLs, try to resolve to a direct ATS posting URL first
        if item["ats"] == "Unknown":
            resolved = resolve_aggregator_url(item["url"], ats_domains)
            if resolved != item["url"]:
                item["url"] = resolved
                item["ats"] = detect_ats(resolved, ats_domains)

        # No recognized platform and no company name — not enough signal, skip
        if item["ats"] == "Unknown" and not item.get("company", "").strip():
            skipped += 1
            continue

        job_id = make_job_id(item["url"])
        if job_id in jobs:
            continue  # Already tracked — never overwrite

        # Fetch full posting text; fall back to RSS snippet
        posting_text = fetch_job_text(item["url"], item["ats"], item.get("summary", ""))
        if not posting_text:
            posting_text = item.get("summary", "")

        # Extract job details early — work_style needed by the pre-filter
        job_details = extract_job_details(posting_text)

        # Pre-filter: drop cybersecurity, degree-required, and out-of-range roles
        skip, reason = should_skip_job(
            item["title"],
            posting_text,
            job_details.get("work_style", ""),
            job_filters,
        )
        if skip:
            print(f"[filter] Skipped: {item['title'][:60]} — {reason}")
            skipped += 1
            continue

        # Scores
        ats_result = score_ats(posting_text, resume_keywords, ats_weights)
        fit = calculate_fit_score(
            item["title"],
            posting_text,
            ats_result["ats_score"],
            user_profile,
        )

        # Company info and contact
        company_info = fetch_company_info(
            item["url"], item["ats"], item.get("company", ""), posting_text
        )
        contact = extract_contact_from_text(posting_text)

        jobs[job_id] = {
            "id": job_id,
            "title": item["title"],
            "company": item.get("company", ""),
            "ats": item["ats"],
            "url": item["url"],
            "feed_label": item["feed_label"],
            "status": "new",
            "gold": fit >= 8,
            "fit_score": fit,
            "ats_score": ats_result["ats_score"],
            "matched_keywords": ats_result["matched_keywords"],
            "missing_keywords": ats_result["missing_keywords"],
            "recommendations": "",
            "posting_text": posting_text,
            "company_info": company_info,
            "contact": contact,
            "salary": job_details.get("salary", ""),
            "location": job_details.get("location", ""),
            "work_style": job_details.get("work_style", ""),
            "notes": "",
            "date_found": now_iso(),
            "date_applied": None,
            "date_status_changed": now_iso(),
        }
        added += 1

    # ── Expiration sweep ─────────────────────────────────────────────────────
    cutoff_max  = datetime.now() - timedelta(days=MAX_AGE_DAYS)
    cutoff_trim = datetime.now() - timedelta(days=TRIM_AGE_DAYS)

    new_count   = sum(1 for j in jobs.values() if j["status"] == "new")
    apply_trim  = new_count >= TRIM_THRESHOLD
    expired_count = 0

    for jid, job in jobs.items():
        if job["status"] != "new":
            continue

        try:
            date_found = datetime.fromisoformat(job["date_found"])
            if date_found < cutoff_max:
                job["status"] = "expired"
                job["date_status_changed"] = now_iso()
                expired_count += 1
                continue
            if apply_trim and date_found < cutoff_trim:
                job["status"] = "expired"
                job["date_status_changed"] = now_iso()
                expired_count += 1
                continue
        except Exception:
            pass

        if not check_url_alive(job["url"]):
            job["status"] = "expired"
            job["date_status_changed"] = now_iso()
            expired_count += 1

    save_jobs(jobs)
    return jsonify({"added": added, "expired": expired_count, "skipped": skipped, "total": len(jobs)})


@app.route("/api/jobs/<job_id>/status", methods=["PATCH"])
def update_status(job_id):
    jobs = load_jobs()
    if job_id not in jobs:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "")

    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status: {new_status}"}), 400

    if new_status == "applied":
        jobs[job_id]["date_applied"] = now_iso()

    jobs[job_id]["status"] = new_status
    jobs[job_id]["date_status_changed"] = now_iso()
    save_jobs(jobs)
    return jsonify(jobs[job_id])


@app.route("/api/jobs/<job_id>/notes", methods=["PATCH"])
def update_notes(job_id):
    jobs = load_jobs()
    if job_id not in jobs:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    jobs[job_id]["notes"] = data.get("notes", "")
    save_jobs(jobs)
    return jsonify({"ok": True})


@app.route("/api/jobs/<job_id>/url", methods=["PATCH"])
def update_url(job_id):
    jobs = load_jobs()
    if job_id not in jobs:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    new_url = data.get("url", "").strip()
    if not new_url:
        return jsonify({"error": "URL cannot be empty"}), 400

    jobs[job_id]["url"] = new_url
    save_jobs(jobs)
    return jsonify({"ok": True})


@app.route("/api/debug-feeds", methods=["GET"])
def debug_feeds():
    """Diagnostic: report how many entries each feed returns, and a sample title."""
    from modules.feed_parser import _fetch_rss_bytes, _fetch_json
    import feedparser as _fp
    config = load_config()
    results = []
    for feed_cfg in config.get("rss_feeds", []):
        label = feed_cfg.get("label", "")
        url   = feed_cfg.get("url", "")
        ftype = feed_cfg.get("type", "rss")
        try:
            if ftype == "remotive_api":
                data  = _fetch_json(url)
                count = len(data.get("jobs", [])) if data else 0
                sample = data["jobs"][0].get("title", "") if count else ""
                results.append({"label": label, "status": 200 if data else 0, "count": count, "sample": sample[:80], "type": ftype})
            elif ftype == "arbeitnow_api":
                data  = _fetch_json(url)
                count = len(data.get("data", [])) if data else 0
                sample = data["data"][0].get("title", "") if count else ""
                results.append({"label": label, "status": 200 if data else 0, "count": count, "sample": sample[:80], "type": ftype})
            else:
                content = _fetch_rss_bytes(url)
                parsed  = _fp.parse(content) if content else _fp.parse(url)
                http_status = 200 if content else parsed.get("status", 0)
                count  = len(parsed.entries)
                sample = parsed.entries[0].get("title", "") if count else ""
                results.append({"label": label, "status": http_status, "count": count, "sample": sample[:80], "type": "rss"})
        except Exception as exc:
            results.append({"label": label, "status": "error", "count": 0, "sample": str(exc)[:80], "type": ftype})
    return jsonify(results)


@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def delete_job(job_id):
    jobs = load_jobs()
    if job_id not in jobs:
        return jsonify({"error": "Not found"}), 404
    del jobs[job_id]
    save_jobs(jobs)
    return jsonify({"ok": True})


@app.route("/api/jobs/<job_id>/recommendations", methods=["GET"])
def get_recommendations(job_id):
    jobs = load_jobs()
    if job_id not in jobs:
        return jsonify({"error": "Not found"}), 404

    job = jobs[job_id]

    # Generate once and cache
    if not job.get("recommendations"):
        recs = generate_recommendations(
            job["title"],
            job["company"],
            job["ats_score"],
            job["missing_keywords"],
            job["matched_keywords"],
        )
        jobs[job_id]["recommendations"] = recs
        save_jobs(jobs)

    return jsonify({"recommendations": jobs[job_id]["recommendations"]})


@app.route("/api/version", methods=["GET"])
def get_version():
    return jsonify({"version": read_version()})


def _has_git():
    """Return True if this installation is a git repo."""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "-C", BASE_DIR, "rev-parse", "--git-dir"],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


@app.route("/api/check-update", methods=["GET"])
def check_update():
    """Compare local VERSION against the raw file on GitHub."""
    from modules.job_fetcher import fetch_job_text  # reuse requests session
    import requests as _req

    config = load_config()
    github_repo = config.get("github_repo", "")
    if not github_repo or "YOUR_USERNAME" in github_repo:
        return jsonify({"available": False, "reason": "github_repo not configured"})

    local = read_version()
    try:
        url = f"https://raw.githubusercontent.com/{github_repo}/main/VERSION"
        resp = _req.get(url, timeout=6)
        resp.raise_for_status()
        remote = resp.text.strip()
        return jsonify({
            "available": remote != local,
            "local": local,
            "remote": remote,
            "has_git": _has_git(),
        })
    except Exception as exc:
        return jsonify({"available": False, "error": str(exc)})


@app.route("/api/update", methods=["POST"])
def do_update():
    """Pull latest code (git users only), reinstall deps, then restart."""
    import subprocess, threading, platform, shutil

    if not _has_git():
        return jsonify({"ok": False, "error": "Not a git repo — manual update required."})

    try:
        # 1. Save user files in memory before git touches anything
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config_backup = f.read()
        jobs_backup = None
        if os.path.exists(JOBS_PATH):
            with open(JOBS_PATH, encoding="utf-8") as f:
                jobs_backup = f.read()

        # 2. Reset config.json to HEAD so git pull won't conflict
        subprocess.run(
            ["git", "-C", BASE_DIR, "checkout", "HEAD", "--", "config.json"],
            capture_output=True, timeout=10
        )

        # 3. Pull
        result = subprocess.run(
            ["git", "-C", BASE_DIR, "pull", "--ff-only", "origin", "main"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            # Restore config before bailing
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(config_backup)
            return jsonify({"ok": False, "error": result.stderr.strip() or "git pull failed"})

        # 4. Restore user files — never let a pull overwrite personal data
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(config_backup)
        if jobs_backup is not None:
            with open(JOBS_PATH, "w", encoding="utf-8") as f:
                f.write(jobs_backup)

        # 5. Update dependencies
        pip = os.path.join(BASE_DIR, "venv", "bin", "pip")
        if not os.path.exists(pip):
            pip = shutil.which("pip") or shutil.which("pip3") or "pip"
        subprocess.run(
            [pip, "install", "-r", os.path.join(BASE_DIR, "requirements.txt"), "--quiet"],
            capture_output=True, timeout=120
        )

        # 6. Restart the server process after response is sent
        def _restart():
            import time, sys
            time.sleep(1.5)
            if platform.system() == "Windows":
                subprocess.Popen([sys.executable] + sys.argv, cwd=BASE_DIR)
                os._exit(0)
            else:
                os.execv(sys.executable, [sys.executable] + sys.argv)

        threading.Thread(target=_restart, daemon=True).start()
        return jsonify({"ok": True, "restarting": True, "version": read_version()})

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    config = load_config()
    ensure_resume_keywords(config)
    port = config["app"].get("port", 5000)
    debug = config["app"].get("debug", False)
    print(f"[job-radar] Running at http://127.0.0.1:{port}")
    app.run(port=port, debug=debug)
