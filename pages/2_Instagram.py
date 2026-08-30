import streamlit as st
from ui_common import page_setup, load, eyebrow
from analytics import correlate

page_setup("Instagram")
data = load()
snap, media = data["ig_snap"], data["ig_media"]

st.title("Instagram")
eyebrow("Followers · reach · what content type wins")

if snap.empty and media.empty:
    st.info("No Instagram data yet. This needs a Business/Creator account + Meta app token "
            "(IG_ACCESS_TOKEN, IG_USER_ID in `.env`), then `python collect.py`. "
            "Run `python seed_demo.py` to preview with sample data.")
    st.stop()

if not snap.empty:
    c1, c2 = st.columns(2)
    c1.metric("Followers", f"{int(snap['followers'].iloc[-1]):,}")
    if len(snap) > 1:
        gained = int(snap["followers"].iloc[-1] - snap["followers"].iloc[0])
        c2.metric("Change (tracked window)", f"{gained:+,}")
    st.subheader("Follower trend")
    st.line_chart(snap.set_index("captured_at")["followers"])

corr = correlate.instagram_correlations(media)
if not corr["by_type"].empty:
    st.subheader("Which content type earns reach")
    st.bar_chart(corr["by_type"].set_index("media_type")["avg_score"])
    st.dataframe(corr["by_type"], use_container_width=True, hide_index=True)

if not corr["by_hour"].empty:
    st.subheader("Best posting hours")
    st.dataframe(corr["by_hour"].head(8), use_container_width=True, hide_index=True)

if not media.empty:
    st.subheader("Browse posts")
    show = media[["media_type", "likes", "comments", "reach", "plays", "timestamp", "permalink"]]
    st.dataframe(show.sort_values("reach", ascending=False),
                 use_container_width=True, hide_index=True)
