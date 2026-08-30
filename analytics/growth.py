"""
Growth analytics. Turns snapshots + video metadata into decisions:
  - subscriber velocity (are you accelerating or flat?)
  - which TAGS overperform (your real lanes, not guesses)
  - best upload windows (day/hour that earns the most views)
  - outlier videos (what broke out — go make more of it)
Everything returns plain DataFrames/dicts so the UI just displays them.
"""
import pandas as pd


def subscriber_velocity(snap: pd.DataFrame) -> dict:
    """Sub growth between the newest snapshot and ~7 days earlier."""
    if snap.empty or len(snap) < 2:
        return {"current": int(snap["subscribers"].iloc[-1]) if not snap.empty else 0,
                "gained": 0, "per_day": 0.0, "window_days": 0}
    s = snap.sort_values("captured_at")
    latest = s.iloc[-1]
    cutoff = latest["captured_at"] - pd.Timedelta(days=7)
    prior = s[s["captured_at"] <= cutoff]
    base = prior.iloc[-1] if not prior.empty else s.iloc[0]
    days = (latest["captured_at"] - base["captured_at"]).total_seconds() / 86400
    gained = int(latest["subscribers"] - base["subscribers"])
    if days < 0.5:  # not enough time elapsed to trust a per-day rate
        return {"current": int(latest["subscribers"]), "gained": gained,
                "per_day": 0.0, "window_days": 0}
    return {"current": int(latest["subscribers"]), "gained": gained,
            "per_day": round(gained / days, 2), "window_days": round(days, 1)}


def top_tags(vids: pd.DataFrame, min_uses=2, n=15) -> pd.DataFrame:
    """Average views per tag — the lanes that actually pull. Ranked by avg views."""
    if vids.empty:
        return pd.DataFrame(columns=["tag", "avg_views", "uses", "total_views"])
    rows = []
    for _, v in vids.iterrows():
        for t in (v["tags"] or []):
            rows.append({"tag": str(t).lower().strip(), "views": v["views"]})
    if not rows:
        return pd.DataFrame(columns=["tag", "avg_views", "uses", "total_views"])
    df = pd.DataFrame(rows)
    g = df.groupby("tag").agg(avg_views=("views", "mean"),
                              uses=("views", "size"),
                              total_views=("views", "sum")).reset_index()
    g = g[g["uses"] >= min_uses].sort_values("avg_views", ascending=False)
    g["avg_views"] = g["avg_views"].round(0).astype(int)
    return g.head(n)


def best_upload_windows(vids: pd.DataFrame) -> pd.DataFrame:
    """Avg views by weekday — when your uploads land best."""
    if vids.empty:
        return pd.DataFrame(columns=["weekday", "avg_views", "uploads"])
    v = vids.dropna(subset=["published_at"]).copy()
    if v.empty:
        return pd.DataFrame(columns=["weekday", "avg_views", "uploads"])
    v["weekday"] = v["published_at"].dt.day_name()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    g = v.groupby("weekday").agg(avg_views=("views", "mean"),
                                 uploads=("views", "size")).reindex(order).dropna().reset_index()
    g["avg_views"] = g["avg_views"].round(0).astype(int)
    return g


def outliers(vids: pd.DataFrame, mult=2.0) -> pd.DataFrame:
    """Videos whose views clear mult x the median — your breakouts."""
    if vids.empty:
        return vids
    med = vids["views"].median() or 0
    out = vids[vids["views"] >= max(med * mult, 1)].sort_values("views", ascending=False)
    return out[["title", "views", "likes", "comments", "published_at", "tags"]].head(15)


def headline_actions(vids: pd.DataFrame, snap: pd.DataFrame) -> list:
    """Plain-English next moves derived from the data — shown on the Overview."""
    actions = []
    vel = subscriber_velocity(snap)
    if vel["window_days"]:
        pace = vel["per_day"]
        if pace <= 0:
            actions.append("Subscribers are flat or down this week — lean on your top-tag lane below and lift upload volume.")
        else:
            actions.append(f"You're netting ~{pace:.1f} subs/day. At this pace that's ~{int(pace*30)} next month — beat it by doubling down on the lanes below.")
    tt = top_tags(vids)
    if not tt.empty:
        best = tt.iloc[0]
        actions.append(f'Your strongest lane is "{best["tag"]}" ({best["avg_views"]:,} avg views over {int(best["uses"])} beats). Make more here.')
    bw = best_upload_windows(vids)
    if not bw.empty:
        top = bw.sort_values("avg_views", ascending=False).iloc[0]
        actions.append(f'{top["weekday"]} uploads average {int(top["avg_views"]):,} views — schedule your drops there.')
    return actions
