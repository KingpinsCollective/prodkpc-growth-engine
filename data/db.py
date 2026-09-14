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
    backlog_pg = """CREATE TABLE IF NOT EXISTS backlog (
        id SERIAL PRIMARY KEY, video_id TEXT UNIQUE, title TEXT, artist TEXT,
        on_beatstars BOOLEAN DEFAULT FALSE, beatstars_url TEXT, ig_reel_url TEXT,
        favorite BOOLEAN DEFAULT FALSE, notes TEXT,
        created_at TIMESTAMPTZ DEFAULT now())"""
    backlog_sql = """CREATE TABLE IF NOT EXISTS backlog (
        id INTEGER PRIMARY KEY, video_id TEXT UNIQUE, title TEXT, artist TEXT,
        on_beatstars INTEGER DEFAULT 0, beatstars_url TEXT, ig_reel_url TEXT,
        favorite INTEGER DEFAULT 0, notes TEXT, created_at TEXT)"""
    try:
        with _conn(cfg) as c:
            cur = c.cursor() if pg_enabled(cfg) else c
            cur.execute(ddl_pg if pg_enabled(cfg) else ddl_sql)
            cur.execute(backlog_pg if pg_enabled(cfg) else backlog_sql)
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


# ---------- Backlog (per-beat hub: YouTube stats + BeatStars + IG over time) ----------
def import_backlog(cfg, rows):
    """rows: list of (video_id, title, artist). Inserts new ones, skips existing.
    Returns count of new rows added."""
    added = 0
    with _conn(cfg) as c:
        cur = c.cursor()
        for vid, title, artist in rows:
            if pg_enabled(cfg):
                cur.execute(
                    "INSERT INTO backlog(video_id,title,artist) VALUES(%s,%s,%s)"
                    " ON CONFLICT (video_id) DO NOTHING", (vid, title, artist))
                added += cur.rowcount or 0
            else:
                cur.execute(
                    "INSERT OR IGNORE INTO backlog(video_id,title,artist,created_at)"
                    " VALUES(?,?,?,?)", (vid, title, artist,
                                        datetime.now(timezone.utc).isoformat()))
                added += cur.rowcount or 0
    return added


def list_backlog(cfg):
    try:
        with _conn(cfg) as c:
            return pd.read_sql_query("SELECT * FROM backlog ORDER BY created_at DESC", c)
    except Exception:
        return pd.DataFrame()


def update_backlog(cfg, bid, on_beatstars=None, beatstars_url=None,
                   ig_reel_url=None, favorite=None, notes=None):
    fields = [(k, v) for k, v in
              [("on_beatstars", on_beatstars), ("beatstars_url", beatstars_url),
               ("ig_reel_url", ig_reel_url), ("favorite", favorite), ("notes", notes)]
              if v is not None]
    if not fields:
        return
    ph = _ph(cfg)
    sets = ", ".join(f"{k}={ph}" for k, _ in fields)
    vals = [v for _, v in fields] + [bid]
    with _conn(cfg) as c:
        cur = c.cursor() if pg_enabled(cfg) else c
        cur.execute(f"UPDATE backlog SET {sets} WHERE id={ph}", vals)


def delete_backlog(cfg, bid):
    ph = _ph(cfg)
    with _conn(cfg) as c:
        cur = c.cursor() if pg_enabled(cfg) else c
        cur.execute(f"DELETE FROM backlog WHERE id={ph}", (bid,))
