import re
import streamlit as st
from ui_common import page_setup, eyebrow
from config import CONFIG
from data import store, r2

page_setup("Upload")

st.title("Upload")
eyebrow("Drop a finished video → store it → prep the release")

r2_on = r2.configured(CONFIG)
if not r2_on:
    st.info("Video storage (Cloudflare R2) isn't configured yet — add the R2 secrets "
            "and the video will be stored with a public URL. For now you can still log releases.")

st.markdown("Make your video your way, then log it as a **release**. "
            "Grab the exact BPM + key from Tunebat and paste them in.")

video = st.file_uploader("Finished video (mp4 / mov / webm)",
                         type=["mp4", "mov", "webm", "m4v"])
if video is not None:
    st.video(video)

title = st.text_input("Title", placeholder='Lucki Type Beat "Faded"')
st.link_button("↗ Analyze BPM + key on Tunebat", "https://tunebat.com/Analyzer")
c1, c2 = st.columns(2)
bpm = c1.text_input("BPM", placeholder="75")
song_key = c2.text_input("Key", placeholder="G# minor")


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "untitled"


if st.button("Save release", type="primary", disabled=not title):
    video_url = ""
    if video is not None and r2_on:
        ext = video.name.rsplit(".", 1)[-1].lower()
        key = f"{_slug(title)}.{ext}"
        with st.spinner("Uploading video to storage…"):
            res = r2.upload_video(CONFIG, video.getvalue(), key,
                                  content_type=video.type or "video/mp4")
        if res.get("ok"):
            video_url = res["url"]
            st.success(f"Stored video → {video_url}")
        else:
            st.warning(f"Video storage failed ({res.get('error','')}). Saved the release without it.")
    store.add_release(CONFIG.db_path, title=title, bpm=bpm, song_key=song_key,
                      filename=(video.name if video else ""), video_url=video_url)
    st.success(f"Saved release: {title}. Next: generate its metadata.")

rel = store.releases(CONFIG.db_path)
if not rel.empty:
    st.subheader("Recent releases")
    show = rel.rename(columns={"song_key": "key"})
    cols = [c for c in ["title", "bpm", "key", "video_url", "status", "created_at"] if c in show.columns]
    st.dataframe(show[cols].tail(10).iloc[::-1], use_container_width=True, hide_index=True,
                 column_config={"video_url": st.column_config.LinkColumn("video")})
