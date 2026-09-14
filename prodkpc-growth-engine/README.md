# ProdKPC Growth Engine

One console that gels three workflows — **YouTube**, **Instagram**, **BeatStars** —
into a single, modular Python app. Built to be automated: a scheduled collector
snapshots every source over time, and a Streamlit dashboard turns that into
"do this next" growth moves.

## What's real (read this first)

| Source | Status | Why |
|---|---|---|
| **YouTube** | ✅ Fully automated | YouTube Data API v3 (free key). Subs, per-video views/likes/comments, tags, duration, publish time. |
| **Instagram** | ✅ Automated, but gated | Meta Graph API. Your **own** Business/Creator account only, after app + token setup. No competitor scraping — the API forbids it. |
| **BeatStars** | ✍️ Manual / CSV | BeatStars has **no public API**. Numbers are entered in-app or imported from `data/beatstars.csv`. |

## Quick start

```bash
pip install -r requirements.txt

# see the whole app immediately with sample data:
python seed_demo.py
streamlit run app.py
```

## Wiring real data

1. `cp .env.example .env`
2. **YouTube** (5 min, free): Google Cloud Console → enable *YouTube Data API v3* →
   create an API key → put it + your channel ID in `.env`.
3. **Instagram** (~20 min): convert @prodkpc to Business/Creator, link a Facebook Page,
   create a Meta app with *Instagram Graph API*, get a long-lived token + IG user id → `.env`.
4. Pull data: `python collect.py`
5. Automate it — schedule `python collect.py` daily (cron / Windows Task Scheduler).
   Snapshots over time are what power the velocity + trend views.

## Architecture (why it's easy to change)

```
config.py            credentials from .env
collect.py           headless snapshotter (schedule this)
data/store.py        SQLite — every source writes here
connectors/
  base.py            Connector interface + registry  <-- the extension point
  youtube.py         real Data API v3
  instagram.py       real Graph API
  beatstars.py       manual/CSV
analytics/
  growth.py          velocity, top tags, upload windows, breakouts
  correlate.py       metadata -> performance (Spearman)
app.py + pages/      Streamlit dashboard
```

**To add a source** (a transactional feed, a new API, TikTok, SoundCloud):
create `connectors/yourthing.py` implementing `Connector.collect()`, add it to
`registry()` in `base.py`. The collector, storage, and UI pick it up — nothing
else changes. That's the whole point of the design.

## Notes
- No keys hard-coded — everything reads from `.env`.
- Delete `data/growth.db` to reset. `seed_demo.py` only adds demo rows.
