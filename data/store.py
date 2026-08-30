"""
Storage layer. Plain SQLite (no ORM) so it's dependency-light and easy to
inspect with any SQLite browser. Everything the connectors collect lands here;
everything the analytics + UI read comes from here. Add a new table = add a
new source, without touching anything else.

Time-series tables (channel_snapshots, ig_account_snapshots) let us compute
*velocity* — growth over time — which is what actually matters, not a single
number in a vacuum.
"""
import os
import json
import sqlite3
from datetime import datetime, timezone

import pandas as pd


def _conn(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def init_db(db_path):
    with _conn(db_path) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS channel_snapshots (
            id INTEGER PRIMARY KEY,
            source TEXT, channel_id TEXT,
            subscribers INTEGER, total_views INTEGER, video_count INTEGER,
            captured_at TEXT
        );
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT, published_at TEXT,
            views INTEGER, likes INTEGER, comments INTEGER,
            duration_sec INTEGER, tags TEXT, category_id TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS ig_account_snapshots (
            id INTEGER PRIMARY KEY,
            ig_user_id TEXT, followers INTEGER, media_count INTEGER,
            reach INTEGER, captured_at TEXT
        );
        CREATE TABLE IF NOT EXISTS ig_media (
            media_id TEXT PRIMARY KEY,
            caption TEXT, media_type TEXT, timestamp TEXT,
            likes INTEGER, comments INTEGER, reach INTEGER, plays INTEGER,
            permalink TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS beatstars_entries (
            id INTEGER PRIMARY KEY,
            beat_title TEXT, plays INTEGER, downloads INTEGER,
            sales INTEGER, revenue REAL, captured_at TEXT
        );
        """)


def _now():
    return datetime.now(timezone.utc).isoformat()


# ---------- writes ----------
def save_channel_snapshot(db_path, source, channel_id, subs, views, vids, captured_at=None):
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO channel_snapshots(source,channel_id,subscribers,total_views,video_count,captured_at)"
            " VALUES(?,?,?,?,?,?)",
            (source, channel_id, subs, views, vids, captured_at or _now()),
        )


def upsert_video(db_path, v):
    with _conn(db_path) as c:
        c.execute(
            """INSERT INTO videos(video_id,title,published_at,views,likes,comments,duration_sec,tags,category_id,updated_at)
               VALUES(:video_id,:title,:published_at,:views,:likes,:comments,:duration_sec,:tags,:category_id,:updated_at)
               ON CONFLICT(video_id) DO UPDATE SET
                 title=excluded.title, views=excluded.views, likes=excluded.likes,
                 comments=excluded.comments, tags=excluded.tags, updated_at=excluded.updated_at""",
            {**v, "tags": json.dumps(v.get("tags") or []), "updated_at": _now()},
        )


def save_ig_account_snapshot(db_path, ig_user_id, followers, media_count, reach, captured_at=None):
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO ig_account_snapshots(ig_user_id,followers,media_count,reach,captured_at)"
            " VALUES(?,?,?,?,?)",
            (ig_user_id, followers, media_count, reach, captured_at or _now()),
        )


def upsert_ig_media(db_path, m):
    with _conn(db_path) as c:
        c.execute(
            """INSERT INTO ig_media(media_id,caption,media_type,timestamp,likes,comments,reach,plays,permalink,updated_at)
               VALUES(:media_id,:caption,:media_type,:timestamp,:likes,:comments,:reach,:plays,:permalink,:updated_at)
               ON CONFLICT(media_id) DO UPDATE SET
                 likes=excluded.likes, comments=excluded.comments, reach=excluded.reach,
                 plays=excluded.plays, updated_at=excluded.updated_at""",
            {**m, "updated_at": _now()},
        )


def add_beatstars_entry(db_path, beat_title, plays, downloads, sales, revenue):
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO beatstars_entries(beat_title,plays,downloads,sales,revenue,captured_at)"
            " VALUES(?,?,?,?,?,?)",
            (beat_title, plays, downloads, sales, revenue, _now()),
        )


# ---------- reads (as DataFrames for analytics + UI) ----------
def _df(db_path, sql):
    with _conn(db_path) as c:
        return pd.read_sql_query(sql, c)


def channel_snapshots(db_path):
    df = _df(db_path, "SELECT * FROM channel_snapshots ORDER BY captured_at")
    if not df.empty:
        df["captured_at"] = pd.to_datetime(df["captured_at"])
    return df


def videos(db_path):
    df = _df(db_path, "SELECT * FROM videos")
    if not df.empty:
        df["published_at"] = pd.to_datetime(df["published_at"])
        df["tags"] = df["tags"].apply(lambda t: json.loads(t) if t else [])
    return df


def ig_snapshots(db_path):
    df = _df(db_path, "SELECT * FROM ig_account_snapshots ORDER BY captured_at")
    if not df.empty:
        df["captured_at"] = pd.to_datetime(df["captured_at"])
    return df


def ig_media(db_path):
    df = _df(db_path, "SELECT * FROM ig_media")
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def beatstars(db_path):
    df = _df(db_path, "SELECT * FROM beatstars_entries ORDER BY captured_at")
    if not df.empty:
        df["captured_at"] = pd.to_datetime(df["captured_at"])
    return df
