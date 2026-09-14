import re
import streamlit as st
from ui_common import page_setup, eyebrow
from config import CONFIG
from data import db, r2

page_setup("Upload")
db.init(CONFIG)

st.title("Upload")
eyebrow("Drop a finished video → store it → prep the release")

r2_on = r2.configured(CONFIG)
pg_on = db.pg_enabled(CONFIG)

cols = st.columns(2)
cols[0].caption(("🟢 " if r2_on else "⚪ ") + f"Video storage: {'R2' if r2_on else 'not set'}")
cols[1].caption(("🟢 " if pg_on else "⚪ ") + f"Release DB: {db.backend_name(CONFIG)}")
if not pg_on:
    st.info("Releases are saving to temporary storage and will vanish on redeploy. "
            "Add DATABASE_URL (Neon) to make them permanent.")

st.markdown("Make your video your way, then log it as a **release**. "
            "Grab the exact BPM + key from Tunebat and paste them in.")

video = st.file_uploader("Finished video (mp4 / mov / webm)", type=["mp4", "mov", "webm", "m4v"])
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
    db.add_release(CONFIG, title=title, bpm=bpm, song_key=song_key,
                   filename=(video.name if video else ""), video_url=video_url)
    st.success(f"Saved release: {title}. Next: generate its metadata.")
    st.rerun()

# ---- Editable, persistent release list ----
rel = db.list_releases(CONFIG)
if not rel.empty:
    st.subheader("Releases")
    st.caption("Edit a title, BPM, or key any time — then Save, or Delete to remove.")
    for _, row in rel.iterrows():
        rid = int(row["id"])
        head = f'{row["title"]}  ·  {row.get("bpm") or "—"} BPM  ·  {row.get("song_key") or "—"}'
        with st.expander(head):
            e1, e2, e3 = st.columns([3, 1, 1])
            nt = e1.text_input("Title", value=row["title"] or "", key=f"t{rid}")
            nb = e2.text_input("BPM", value=row.get("bpm") or "", key=f"b{rid}")
            nk = e3.text_input("Key", value=row.get("song_key") or "", key=f"k{rid}")
            if row.get("video_url"):
                st.markdown(f"[▶ stored video]({row['video_url']})")
            s, d = st.columns([1, 1])
            if s.button("Save changes", key=f"s{rid}"):
                db.update_release(CONFIG, rid, title=nt, bpm=nb, song_key=nk)
                st.success("Updated.")
                st.rerun()
            if d.button("🗑 Delete", key=f"d{rid}"):
                db.delete_release(CONFIG, rid)
                st.rerun()
