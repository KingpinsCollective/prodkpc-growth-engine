import streamlit as st
import pandas as pd
from ui_common import page_setup, load, eyebrow
from config import CONFIG
from data import store

page_setup("Momentum")
data = load()

st.title("Momentum")
eyebrow("Owner-only analytics · who's gaining subs right now")

daily = store.yt_daily(CONFIG.db_path)
va = store.yt_video_analytics(CONFIG.db_path)
traffic = store.yt_traffic(CONFIG.db_path)

if daily.empty and va.empty and traffic.empty:
    st.info("No analytics yet. This is the OAuth layer — once you add the three "
            "YT_OAUTH_* secrets and re-run the collector, this page fills with "
            "subscriber-driving videos, daily momentum, and traffic sources. "
            "Setup steps are in DEPLOY.md.")
    st.stop()

# --- daily momentum (last 30 days) ---
if not daily.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Subs gained (30d)", int(daily["subs_gained"].sum()))
    net = int(daily["subs_gained"].sum() - daily["subs_lost"].sum())
    c2.metric("Net subs (30d)", f"{net:+,}")
    c3.metric("Views (30d)", f"{int(daily['views'].sum()):,}")

    st.subheader("Daily subscribers gained")
    st.bar_chart(daily.set_index("day")["subs_gained"])

    st.subheader("Daily views")
    st.line_chart(daily.set_index("day")["views"])

# --- which videos are converting subscribers ---
if not va.empty:
    st.subheader("Videos earning you subscribers (last 90 days)")
    vids = store.videos(CONFIG.db_path)[["video_id", "title"]] if not store.videos(CONFIG.db_path).empty else pd.DataFrame(columns=["video_id", "title"])
    merged = va.merge(vids, on="video_id", how="left")
    merged["title"] = merged["title"].fillna("(older/removed video)")
    show = merged.sort_values("subs_gained", ascending=False)[
        ["title", "subs_gained", "views", "avg_view_sec"]
    ].rename(columns={"subs_gained": "subs+", "avg_view_sec": "avg_view_s"})
    st.dataframe(show.head(20), use_container_width=True, hide_index=True)
    top = show.iloc[0]
    if top["subs+"] > 0:
        st.markdown(f"**Your #1 subscriber magnet lately:** *{top['title']}* "
                    f"(+{int(top['subs+'])} subs). Make more like it.")

# --- where discovery comes from ---
if not traffic.empty:
    st.subheader("Where your views come from")
    label = {
        "YT_SEARCH": "YouTube search", "RELATED_VIDEO": "Suggested videos",
        "NO_LINK_OTHER": "Direct / other", "EXT_URL": "External sites",
        "PLAYLIST": "Playlists", "SUBSCRIBER": "Subscriptions feed",
        "CHANNEL": "Channel page", "NOTIFICATION": "Notifications",
        "YT_CHANNEL": "Channel page", "ADVERTISING": "Ads",
    }
    t = traffic.copy()
    t["source"] = t["source"].map(lambda s: label.get(s, s.replace("_", " ").title()))
    st.bar_chart(t.set_index("source")["views"])
    top_src = t.iloc[0]
    st.caption(f"Most discovery is coming from **{top_src['source']}**. For beats, "
               f"high YouTube-search share means your titles/tags are doing their job.")
