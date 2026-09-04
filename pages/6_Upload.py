import streamlit as st
from ui_common import page_setup, eyebrow
from config import CONFIG
from data import store

page_setup("Upload")

st.title("Upload")
eyebrow("Drop a finished video → prep the release")

st.markdown("Make your video your way, then log it here as a **release**. "
            "Grab the exact BPM + key from Tunebat (more accurate than any auto-guess) "
            "and paste them in — then everything downstream builds off this record.")

video = st.file_uploader("Finished video (mp4 / mov / webm)",
                         type=["mp4", "mov", "webm", "m4v"])
if video is not None:
    st.video(video)
    st.caption("Preview only for now — persistent video storage is the next piece we're wiring up.")

title = st.text_input("Title", placeholder='Lucki Type Beat "Faded"')

st.link_button("↗ Analyze BPM + key on Tunebat", "https://tunebat.com/Analyzer")
c1, c2 = st.columns(2)
bpm = c1.text_input("BPM", placeholder="75")
song_key = c2.text_input("Key", placeholder="G# minor")

if st.button("Save release", type="primary", disabled=not title):
    store.add_release(CONFIG.db_path, title=title, bpm=bpm, song_key=song_key,
                      filename=(video.name if video else ""))
    st.success(f"Saved release: {title}. Next: generate its metadata.")

rel = store.releases(CONFIG.db_path)
if not rel.empty:
    st.subheader("Recent releases")
    show = rel.rename(columns={"song_key": "key"})[["title", "bpm", "key", "status", "created_at"]]
    st.dataframe(show.tail(10).iloc[::-1], use_container_width=True, hide_index=True)
