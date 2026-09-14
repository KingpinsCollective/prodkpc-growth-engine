import pandas as pd
import streamlit as st
from ui_common import page_setup, load, eyebrow
from config import CONFIG
from data import db, store
from analytics import growth

page_setup("Backlog")
db.init(CONFIG)

st.title("Backlog")
eyebrow("Every beat, one row · YouTube + BeatStars + IG in one place")

if not db.pg_enabled(CONFIG):
    st.warning("Backlog needs the persistent database. Add DATABASE_URL (Neon) so entries stick.")

# live YouTube stats to join against
vids = store.videos(CONFIG.db_path)
stats = {}
if not vids.empty:
    for _, v in vids.iterrows():
        stats[v["video_id"]] = {"views": int(v["views"]), "likes": int(v["likes"]),
                                "published": v["published_at"]}

# ---- import control ----
c1, c2 = st.columns([2, 1])
n = c1.slider("How many recent videos to import", 10, 100, 50, step=10)
if c2.button("⤵ Import my recent YouTube videos", type="primary"):
    if vids.empty:
        st.error("No YouTube videos found to import.")
    else:
        recent = vids.dropna(subset=["published_at"]).sort_values("published_at", ascending=False).head(n)
        rows = [(r["video_id"], r["title"], growth.beat_artist(r["title"]) or "")
                for _, r in recent.iterrows()]
        added = db.import_backlog(CONFIG, rows)
        st.success(f"Imported {added} new beat(s). ({len(rows)-added} already in your backlog.)")
        st.rerun()

bl = db.list_backlog(CONFIG)
if bl.empty:
    st.info("Backlog is empty. Set the count above and hit **Import** to pull your catalog in.")
    st.stop()

# ---- filters ----
f1, f2, f3 = st.columns(3)
only_fav = f1.checkbox("★ Favorites only")
only_bs = f2.checkbox("On BeatStars only")
search = f3.text_input("Search title/artist", "")

view = bl.copy()
view["favorite"] = view["favorite"].apply(bool)
view["on_beatstars"] = view["on_beatstars"].apply(bool)
if only_fav:
    view = view[view["favorite"]]
if only_bs:
    view = view[view["on_beatstars"]]
if search:
    s = search.lower()
    view = view[view.apply(lambda r: s in str(r["title"]).lower()
                           or s in str(r["artist"]).lower(), axis=1)]

st.caption(f"{len(view)} of {len(bl)} beats · YouTube views are live from your channel")

for _, row in view.iterrows():
    bid = int(row["id"])
    st_ = stats.get(row["video_id"], {})
    yt_views = st_.get("views")
    star = "★" if row["favorite"] else "☆"
    bs = "🟢 BeatStars" if row["on_beatstars"] else "⚪ not on BeatStars"
    head = f'{star}  {row["title"]}'
    if yt_views is not None:
        head += f'   ·   {yt_views:,} views'
    head += f'   ·   {bs}'
    with st.expander(head):
        if yt_views is not None:
            m1, m2 = st.columns(2)
            m1.metric("YouTube views", f"{yt_views:,}")
            m2.metric("YouTube likes", f"{st_.get('likes',0):,}")
        else:
            st.caption("No live YouTube stats matched (manual or older entry).")

        fav = st.checkbox("★ Favorite", value=row["favorite"], key=f"fav{bid}")
        onbs = st.checkbox("On BeatStars (for sale)", value=row["on_beatstars"], key=f"bs{bid}")
        bs_url = st.text_input("BeatStars link", value=row.get("beatstars_url") or "", key=f"bsu{bid}",
                               placeholder="https://beatstars.com/prodkpc/...")
        ig_url = st.text_input("Instagram reel link (add when posted)", value=row.get("ig_reel_url") or "",
                               key=f"ig{bid}", placeholder="https://instagram.com/reel/...")
        notes = st.text_area("Notes", value=row.get("notes") or "", key=f"n{bid}", height=68)

        s, d = st.columns([1, 1])
        if s.button("Save", key=f"save{bid}"):
            db.update_backlog(CONFIG, bid, on_beatstars=onbs, beatstars_url=bs_url,
                              ig_reel_url=ig_url, favorite=fav, notes=notes)
            st.success("Saved.")
            st.rerun()
        if d.button("🗑 Remove", key=f"del{bid}"):
            db.delete_backlog(CONFIG, bid)
            st.rerun()
