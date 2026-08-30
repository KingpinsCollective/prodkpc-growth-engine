"""
ProdKPC Growth Engine — Overview.
Run:  streamlit run app.py
"""
import streamlit as st

from ui_common import page_setup, load, eyebrow
from config import CONFIG
from connectors.base import registry
from analytics import growth

page_setup("Overview")
data = load()

st.title("🎛 ProdKPC Growth Engine")
eyebrow("One console · YouTube · Instagram · BeatStars")

# --- connector status row ---
st.subheader("Sources")
cols = st.columns(3)
for col, conn in zip(cols, registry(CONFIG)):
    with col:
        ok = conn.is_configured()
        dot = "🟢" if ok else "⚪"
        label = "connected" if ok else ("manual" if conn.kind == "manual" else "add keys in .env")
        st.markdown(f"**{dot} {conn.name}** — {label}")

st.divider()

# --- headline KPIs ---
vids = data["videos"]
chan = data["channel"]
ig = data["ig_snap"]
vel = growth.subscriber_velocity(chan)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Subscribers", f"{vel['current']:,}",
          f"{vel['gained']:+,} / {vel['window_days']}d" if vel["window_days"] else None)
k2.metric("Subs / day", vel["per_day"] if vel["window_days"] else "—")
k3.metric("Videos tracked", f"{len(vids):,}")
ig_now = int(ig["followers"].iloc[-1]) if not ig.empty else 0
k4.metric("IG followers", f"{ig_now:,}" if ig_now else "—")

st.divider()

# --- data-driven next moves ---
st.subheader("Do this next")
actions = growth.headline_actions(vids, chan)
if actions:
    for a in actions:
        st.markdown(f"- {a}")
else:
    st.info("No data yet. Run `python seed_demo.py` to explore with sample data, "
            "or add your YouTube key to `.env` and run `python collect.py`.")

st.caption("Browse each source in the sidebar → YouTube, Instagram, BeatStars, Correlations.")
