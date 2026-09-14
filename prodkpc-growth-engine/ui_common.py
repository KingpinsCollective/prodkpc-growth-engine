"""Shared header/style + data loading for the Streamlit pages."""
import streamlit as st
from config import CONFIG
from data import store

GOLD = "#e8b04b"


def page_setup(title):
    st.set_page_config(page_title=f"ProdKPC · {title}", page_icon="🎛", layout="centered")
    st.markdown(f"""
        <style>
          .stApp {{ background:#141418; }}
          h1,h2,h3 {{ letter-spacing:.01em; }}
          [data-testid="stMetricValue"] {{ color:{GOLD}; }}
          .prodkpc-eyebrow {{ color:#8b8a92; letter-spacing:.16em; text-transform:uppercase;
            font-size:12px; margin-bottom:2px; }}
        </style>
    """, unsafe_allow_html=True)
    store.init_db(CONFIG.db_path)


def eyebrow(text):
    st.markdown(f"<div class='prodkpc-eyebrow'>{text}</div>", unsafe_allow_html=True)


def load():
    return {
        "channel": store.channel_snapshots(CONFIG.db_path),
        "videos": store.videos(CONFIG.db_path),
        "ig_snap": store.ig_snapshots(CONFIG.db_path),
        "ig_media": store.ig_media(CONFIG.db_path),
        "beatstars": store.beatstars(CONFIG.db_path),
    }
