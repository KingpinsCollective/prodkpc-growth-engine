"""
Seed the DB with realistic synthetic data so you can explore the whole app
before wiring up any API keys. Safe to run anytime; it only adds demo rows.

    python seed_demo.py

Delete data/growth.db to start clean.
"""
import random
from datetime import datetime, timezone, timedelta

from config import CONFIG
from data import store

random.seed(7)
ARTISTS = ["Lucki", "Yeat", "SoFaygo", "Ken Carson", "Destroy Lonely", "Autumn"]
VIBES = ["dark ambient guitar", "spacey pluck", "ethereal", "hard 808", "melodic rage", "underground"]


def _iso(dt):
    return dt.replace(tzinfo=timezone.utc).isoformat()


def seed():
    store.init_db(CONFIG.db_path)

    # 30 days of channel snapshots with accelerating subs
    base_subs, base_views = 1240, 210_000
    now = datetime.now(timezone.utc)
    for d in range(30, -1, -1):
        day = now - timedelta(days=d)
        subs = base_subs + int((30 - d) ** 1.6) + random.randint(0, 5)
        views = base_views + (30 - d) * random.randint(900, 1600)
        store.save_channel_snapshot(CONFIG.db_path, "youtube", "DEMO", subs, views, 60,
                                    captured_at=day.isoformat())

    # 60 videos with tags/durations/times; some lanes overperform on purpose
    for i in range(60):
        art = random.choice(ARTISTS)
        vibe = random.choice(VIBES)
        pub = now - timedelta(days=random.randint(1, 200), hours=random.randint(0, 23))
        lane_boost = 3.0 if art in ("Lucki", "Yeat") else 1.0
        wd_boost = 1.6 if pub.weekday() in (2, 4) else 1.0  # Wed/Fri pop
        views = int(random.randint(150, 1200) * lane_boost * wd_boost)
        tags = [f"{art.lower()} type beat", f"{art.lower()} type beat 2026",
                *vibe.split(), "free type beat", "prodkpc"]
        store.upsert_video(CONFIG.db_path, {
            "video_id": f"demo{i:03d}",
            "title": f'{art} Type Beat "{vibe.split()[0].title()}"',
            "published_at": _iso(pub),
            "views": views, "likes": int(views * 0.03), "comments": int(views * 0.004),
            "duration_sec": random.choice([54, 132, 168, 190, 210]),
            "tags": tags, "category_id": "10",
        })

    # 20 days IG follower snapshots
    f0 = 820
    for d in range(20, -1, -1):
        day = now - timedelta(days=d)
        store.save_ig_account_snapshot(CONFIG.db_path, "DEMO",
                                       f0 + (20 - d) * random.randint(2, 9), 45,
                                       random.randint(300, 2200),
                                       captured_at=day.isoformat())
    # IG posts: reels beat images on reach
    for i in range(25):
        ts = now - timedelta(days=random.randint(1, 90), hours=random.randint(0, 23))
        mt = random.choices(["REEL", "IMAGE", "CAROUSEL"], weights=[5, 2, 1])[0]
        reach = int(random.randint(200, 900) * (3.2 if mt == "REEL" else 1.0))
        store.upsert_ig_media(CONFIG.db_path, {
            "media_id": f"igdemo{i:03d}",
            "caption": random.choice(ARTISTS) + " type beat out now 🔥 #typebeat #prodkpc",
            "media_type": mt, "timestamp": _iso(ts),
            "likes": int(reach * 0.08), "comments": int(reach * 0.01),
            "reach": reach, "plays": reach if mt == "REEL" else 0,
            "permalink": "https://instagram.com/p/demo",
        })

    # BeatStars manual entries
    for art in ARTISTS[:4]:
        store.add_beatstars_entry(CONFIG.db_path, f"{art} Type Beat",
                                  random.randint(400, 3000), random.randint(20, 200),
                                  random.randint(0, 8), round(random.uniform(0, 240), 2))
    print("Seeded demo data ->", CONFIG.db_path)


if __name__ == "__main__":
    seed()
