import streamlit as st
from ui_common import page_setup, load, eyebrow
from analytics import growth

page_setup("YouTube")
data = load()
vids, chan = data["videos"], data["channel"]

st.title("YouTube")
eyebrow("Subscribers · the lanes that pull · what's moving now")

if chan.empty and vids.empty:
    st.info("No YouTube data yet. Add YOUTUBE_API_KEY + YOUTUBE_CHANNEL_ID to `.env` and run "
            "`python collect.py` — or `python seed_demo.py` for sample data.")
    st.stop()

vel = growth.subscriber_velocity(chan)
c1, c2, c3 = st.columns(3)
c1.metric("Subscribers", f"{vel['current']:,}",
          f"{vel['gained']:+,} / {vel['window_days']}d" if vel["window_days"] else None)
c2.metric("Subs / day", vel["per_day"] if vel["window_days"] else "—")
c3.metric("Total views", f"{int(chan['total_views'].iloc[-1]):,}" if not chan.empty else "—")

if not chan.empty:
    st.subheader("Subscriber trend")
    st.line_chart(chan.set_index("captured_at")["subscribers"])

# ---- Real-time: recent uploads with velocity ----
st.subheader("Recent uploads — how your latest drops are doing")
ru = growth.recent_uploads(vids, n=12)
if ru.empty:
    st.caption("No dated uploads yet.")
else:
    show = ru.copy()
    show["published"] = show["published_at"].dt.date
    st.dataframe(show[["title", "views", "views_per_day", "published"]]
                 .rename(columns={"views_per_day": "views/day"}),
                 use_container_width=True, hide_index=True)
    st.caption("views/day = velocity since upload — the fairest read on a fresh post "
               "before total views catch up.")

# ---- Real lanes: by artist, with recency filter ----
st.subheader("Your strongest lanes (by artist)")
window = st.radio("Window", ["All time", "Last 12 months", "Last 3 months"],
                  horizontal=True, index=0, label_visibility="collapsed")
months = {"All time": None, "Last 12 months": 12, "Last 3 months": 3}[window]
lanes = growth.artist_lanes(vids, months=months, min_beats=1)
if lanes.empty:
    st.caption("No type-beat uploads in this window yet.")
else:
    top = lanes.head(12)
    st.bar_chart(top.set_index("artist")["avg_views"])
    st.dataframe(top, use_container_width=True, hide_index=True)
    st.caption("Grouped by the artist in each title (type beats only) — your old "
               "gaming/editing uploads are excluded so the lanes are real.")

# ---- Browse everything ----
st.subheader("Browse all videos")
if not vids.empty:
    b = vids.copy().sort_values("views", ascending=False)
    st.dataframe(b[["title", "views", "likes", "comments", "published_at"]],
                 use_container_width=True, hide_index=True)
