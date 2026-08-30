import streamlit as st
from ui_common import page_setup, load, eyebrow
from config import CONFIG
from data import store

page_setup("BeatStars")
data = load()
bs = data["beatstars"]

st.title("BeatStars")
eyebrow("Manual tracker — no public API exists")

st.link_button("Open my BeatStars", CONFIG.beatstars_url, use_container_width=False)
st.caption("BeatStars has no official API, so numbers are logged here (or imported from "
           "`data/beatstars.csv`). If they ever ship an API, only the connector changes.")

st.subheader("Log a beat's numbers")
with st.form("bs"):
    c1, c2, c3 = st.columns(3)
    title = c1.text_input("Beat title")
    plays = c2.number_input("Plays", min_value=0, step=1)
    downloads = c3.number_input("Downloads", min_value=0, step=1)
    c4, c5 = st.columns(2)
    sales = c4.number_input("Sales", min_value=0, step=1)
    revenue = c5.number_input("Revenue ($)", min_value=0.0, step=1.0)
    if st.form_submit_button("Add entry") and title:
        store.add_beatstars_entry(CONFIG.db_path, title, int(plays), int(downloads),
                                  int(sales), float(revenue))
        st.success(f"Logged {title}")
        st.rerun()

if not bs.empty:
    st.subheader("History")
    st.dataframe(bs[["beat_title", "plays", "downloads", "sales", "revenue", "captured_at"]]
                 .sort_values("captured_at", ascending=False),
                 use_container_width=True, hide_index=True)
    tot = bs.groupby("beat_title").agg(plays=("plays", "max"), sales=("sales", "max"),
                                       revenue=("revenue", "max")).reset_index()
    st.subheader("By beat")
    st.bar_chart(tot.set_index("beat_title")["plays"])
