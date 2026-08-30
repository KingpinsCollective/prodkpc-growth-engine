import streamlit as st
from ui_common import page_setup, load, eyebrow
from analytics import growth

page_setup("YouTube")
data = load()
vids, chan = data["videos"], data["channel"]

st.title("YouTube")
eyebrow("Subscribers · videos · the lanes that pull")

if chan.empty and vids.empty:
    st.info("No YouTube data yet. Add YOUTUBE_API_KEY + YOUTUBE_CHANNEL_ID to `.env` and run "
            "`python collect.py` — or `python seed_demo.py` for sample data.")
    st.stop()

# subscriber trend
vel = growth.subscriber_velocity(chan)
c1, c2, c3 = st.columns(3)
c1.metric("Subscribers", f"{vel['current']:,}",
          f"{vel['gained']:+,} / {vel['window_days']}d" if vel["window_days"] else None)
c2.metric("Subs / day", vel["per_day"] if vel["window_days"] else "—")
c3.metric("Total views", f"{int(chan['total_views'].iloc[-1]):,}" if not chan.empty else "—")

if not chan.empty:
    st.subheader("Subscriber trend")
    st.line_chart(chan.set_index("captured_at")["subscribers"])

# top tags — the growth signal
st.subheader("Your strongest lanes (avg views per tag)")
tt = growth.top_tags(vids)
if tt.empty:
    st.caption("Need a few tagged videos to rank lanes.")
else:
    st.bar_chart(tt.set_index("tag")["avg_views"])
    st.dataframe(tt, use_container_width=True, hide_index=True)

# best upload windows
st.subheader("Best upload day")
bw = growth.best_upload_windows(vids)
if not bw.empty:
    st.bar_chart(bw.set_index("weekday")["avg_views"])

# browse everything
st.subheader("Browse videos")
if not vids.empty:
    show = vids.copy()
    show["tags"] = show["tags"].apply(lambda t: ", ".join(t[:6]) if t else "")
    show = show[["title", "views", "likes", "comments", "duration_sec", "published_at", "tags"]]
    show = show.sort_values("views", ascending=False)
    st.dataframe(show, use_container_width=True, hide_index=True)

# breakouts
st.subheader("Breakout videos (2×+ median)")
out = growth.outliers(vids)
if not out.empty:
    out = out.copy()
    out["tags"] = out["tags"].apply(lambda t: ", ".join(t[:6]) if t else "")
    st.dataframe(out, use_container_width=True, hide_index=True)
else:
    st.caption("No clear breakouts yet.")
