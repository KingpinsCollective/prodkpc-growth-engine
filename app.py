
"""
ProdKPC Growth Engine — Overview.
Run:  streamlit run app.py
"""
import pandas as pd
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

# --- Goals: checkable, with growth tracked from completion ---
from data import db
db.init(CONFIG)

# current metrics for snapshotting on completion + measuring deltas
cur_subs = int(chan["subscribers"].iloc[-1]) if not chan.empty else 0
cur_views = int(chan["total_views"].iloc[-1]) if not chan.empty else 0

st.subheader("Goals")
if not db.pg_enabled(CONFIG):
    st.caption("⚪ Goals need the Neon database to persist.")

# suggestions from the data you can turn into goals
suggestions = growth.headline_actions(vids, chan)
existing_goals = db.list_goals(CONFIG)
existing_texts = set(existing_goals["text"]) if not existing_goals.empty else set()
open_suggestions = [s for s in suggestions if s not in existing_texts]
if open_suggestions:
    st.caption("Suggested from your data — add the ones you'll act on:")
    for i, s in enumerate(open_suggestions):
        sc1, sc2 = st.columns([6, 1])
        sc1.markdown(f"- {s}")
        if sc2.button("➕ Add", key=f"sug{i}"):
            db.add_goal(CONFIG, s, source="auto")
            st.rerun()

# add your own
with st.form("add_goal", clear_on_submit=True):
    gc1, gc2 = st.columns([5, 1])
    new_goal = gc1.text_input("Add your own goal", label_visibility="collapsed",
                              placeholder="e.g. Post a 6lack beat this week")
    if gc2.form_submit_button("Add") and new_goal.strip():
        db.add_goal(CONFIG, new_goal.strip(), source="manual")
        st.rerun()

goals = db.list_goals(CONFIG)
if goals.empty:
    st.caption("No goals yet — add one above.")
else:
    active = goals[~goals["done"].apply(bool)]
    done = goals[goals["done"].apply(bool)]

    if not active.empty:
        st.markdown("**Active**")
        for _, g in active.iterrows():
            gid = int(g["id"])
            a1, a2 = st.columns([8, 1])
            if a1.checkbox(g["text"], value=False, key=f"g{gid}"):
                db.complete_goal(CONFIG, gid, cur_subs, cur_views)
                st.rerun()
            if a2.button("✕", key=f"gd{gid}"):
                db.delete_goal(CONFIG, gid)
                st.rerun()

    if not done.empty:
        st.markdown("**Completed — growth since**")
        for _, g in done.iterrows():
            gid = int(g["id"])
            ds = g.get("subs_at_done")
            dv = g.get("views_at_done")
            delta = ""
            if ds is not None and not pd.isna(ds):
                delta = f"  →  +{cur_subs-int(ds)} subs · +{cur_views-int(dv):,} views since"
            d1, d2 = st.columns([8, 1])
            d1.markdown(f"~~{g['text']}~~{delta}")
            if d2.button("↺", key=f"gr{gid}", help="reopen"):
                db.reopen_goal(CONFIG, gid)
                st.rerun()
        st.caption("Deltas are correlation, not proof — a directional read on what moved after you acted.")

st.caption("Browse each source in the sidebar → YouTube, Instagram, BeatStars, Backlog.")
