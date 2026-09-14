"""
Persistent store for things the USER creates in the app — releases now, and
backlog + goals soon. Uses Neon Postgres when DATABASE_URL is set (survives
redeploys); falls back to local SQLite otherwise (fine for local dev).

Separate from data/store.py, which holds the read-only analytics the daily
collector writes (that data is re-fetchable; this data is not).

Connections are opened per-operation and always closed, so Neon's free-tier
connection limit isn't exhausted.
"""
import sqlite3
import contextlib
import pandas as pd
from datetime import datetime, timezone


def pg_enabled(cfg):
    return bool(getattr(cfg, "database_url", ""))


def backend_name(cfg):
    return "Neon Postgres (persistent)" if pg_enabled(cfg) else "local SQLite (temporary)"


@contextlib.contextmanager
def _conn(cfg):
    """Yield a DB connection (Postgres or SQLite), always closed after use."""
    if pg_enabled(cfg):
        import psycopg2
        c = psycopg2.connect(cfg.database_url)
        try:
            yield c
            c.commit()
        finally:
            c.close()
    else:
        c = sqlite3.connect(cfg.db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()


def _ph(cfg):
    return "%s" if pg_enabled(cfg) else "?"


def init(cfg):
    ddl_pg = """CREATE TABLE IF NOT EXISTS releases (
        id SERIAL PRIMARY KEY, title TEXT, artist TEXT, bpm TEXT, song_key TEXT,
        filename TEXT, video_url TEXT, status TEXT DEFAULT 'prepped',
        created_at TIMESTAMPTZ DEFAULT now())"""
    ddl_sql = """CREATE TABLE IF NOT EXISTS releases (
        id INTEGER PRIMARY KEY, title TEXT, artist TEXT, bpm TEXT, song_key TEXT,
        filename TEXT, video_url TEXT, status TEXT, created_at TEXT)"""
    try:
        with _conn(cfg) as c:
            c.cursor().execute(ddl_pg if pg_enabled(cfg) else ddl_sql)
    except Exception:
        pass  # never let init crash the page


def add_release(cfg, title, artist="", bpm="", song_key="", filename="",
                video_url="", status="prepped"):
    ph = _ph(cfg)
    with _conn(cfg) as c:
        if pg_enabled(cfg):
            c.cursor().execute(
                f"INSERT INTO releases(title,artist,bpm,song_key,filename,video_url,status)"
                f" VALUES({ph},{ph},{ph},{ph},{ph},{ph},{ph})",
                (title, artist, bpm, song_key, filename, video_url, status))
        else:
            c.execute(
                "INSERT INTO releases(title,artist,bpm,song_key,filename,video_url,status,created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (title, artist, bpm, song_key, filename, video_url, status,
                 datetime.now(timezone.utc).isoformat()))


def list_releases(cfg):
    try:
        with _conn(cfg) as c:
            return pd.read_sql_query("SELECT * FROM releases ORDER BY created_at DESC", c)
    except Exception:
        return pd.DataFrame()


def update_release(cfg, rid, title=None, bpm=None, song_key=None, status=None):
    fields = [(k, v) for k, v in
              [("title", title), ("bpm", bpm), ("song_key", song_key), ("status", status)]
              if v is not None]
    if not fields:
        return
    ph = _ph(cfg)
    sets = ", ".join(f"{k}={ph}" for k, _ in fields)
    vals = [v for _, v in fields] + [rid]
    with _conn(cfg) as c:
        cur = c.cursor() if pg_enabled(cfg) else c
        cur.execute(f"UPDATE releases SET {sets} WHERE id={ph}", vals)


def delete_release(cfg, rid):
    ph = _ph(cfg)
    with _conn(cfg) as c:
        cur = c.cursor() if pg_enabled(cfg) else c
        cur.execute(f"DELETE FROM releases WHERE id={ph}", (rid,))
