"""
Headless collector — the automation backbone.

Run it manually:      python collect.py
Or schedule it (this is what makes growth-tracking "automatic"):
  macOS/Linux cron (daily 8am):   0 8 * * *  cd /path/to/growth-engine && python collect.py
  Windows Task Scheduler:         action = python collect.py, trigger = daily

Each run snapshots every configured source into the SQLite DB. Because we
snapshot over time, the app can show velocity and trends, not just today's number.
"""
from config import CONFIG
from data import store
from connectors.base import registry


def main():
    store.init_db(CONFIG.db_path)
    print("Collecting…")
    for conn in registry(CONFIG):
        try:
            res = conn.collect(CONFIG.db_path)
        except Exception as e:
            res = {"source": conn.id, "ok": False, "msg": f"error: {e}"}
        flag = "OK " if res.get("ok") else "-- "
        print(f"  [{flag}] {conn.name:10s} {res.get('msg','')}")
    print("Done. Launch the dashboard with:  streamlit run app.py")


if __name__ == "__main__":
    main()
