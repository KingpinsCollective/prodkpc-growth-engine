"""
Growth analytics. Turns snapshots + video metadata into decisions:
  - subscriber velocity (are you accelerating or flat?)
  - which TAGS overperform (your real lanes, not guesses)
  - best upload windows (day/hour that earns the most views)
  - outlier videos (what broke out — go make more of it)
Everything returns plain DataFrames/dicts so the UI just displays them.
"""
import re
import pandas as pd


def beat_artist(title: str):
    """Extract the target artist from a type-beat title. Returns None for
    non-type-beat videos (old gaming/editing uploads), which filters them out."""
    if not title:
        return None
    t = re.sub(r"^\s*\[[^\]]*\]\s*", "", str(title))     # strip [FREE] etc.
    m = re.search(r"(.*?)\s*type\s*beat", t, flags=re.IGNORECASE)
    if not m:
        return None
    artist = re.sub(r"\s+", " ", m.group(1)).strip(" -–—")
    return artist or None


def _utcnow(series):
    tz = series.dt.tz
    return pd.Timestamp.now(tz=tz) if tz is not None else pd.Timestamp.now()


def artist_lanes(vids: pd.DataFrame, months=None, min_beats=1, n=15) -> pd.DataFrame:
    """Real lanes: group type beats by target artist (not raw tags), avg views."""
    cols = ["artist", "avg_views", "beats", "total_views"]
    if vids.empty:
        return pd.DataFrame(columns=cols)
    v = vids.copy()
    v["artist"] = v["title"].apply(beat_artist)
    v = v[v["artist"].notna()]
    if months and "published_at" in v and not v["published_at"].isna().all():
        cutoff = _utcnow(v["published_at"]) - pd.Timedelta(days=30 * months)
        v = v[v["published_at"] >= cutoff]
    if v.empty:
        return pd.DataFrame(columns=cols)
    v["akey"] = v["artist"].str.lower()
    g = (v.groupby("akey")
           .agg(artist=("artist", "first"), avg_views=("views", "mean"),
                beats=("views", "size"), total_views=("views", "sum"))
           .reset_index(drop=True))
    g = g[g["beats"] >= min_beats].sort_values("avg_views", ascending=False)
    g["avg_views"] = g["avg_views"].round(0).astype(int)
    return g.head(n)[cols]


def recent_uploads(vids: pd.DataFrame, n=12) -> pd.DataFrame:
    """Newest uploads with a views-per-day velocity — the real-time read."""
    cols = ["title", "views", "views_per_day", "published_at"]
    if vids.empty or "published_at" not in vids:
        return pd.DataFrame(columns=cols)
    v = vids.dropna(subset=["published_at"]).copy()
    if v.empty:
        return pd.DataFrame(columns=cols)
    days = (_utcnow(v["published_at"]) - v["published_at"]).dt.days.clip(lower=1)
    v["views_per_day"] = (v["views"] / days).round(1)
    return v.sort_values("published_at", ascending=False).head(n)[cols]


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
    tt = artist_lanes(vids)
    if not tt.empty:
        best = tt.iloc[0]
        actions.append(f'Your strongest lane is {best["artist"]} ({best["avg_views"]:,} avg views over {int(best["beats"])} beats). Make more here.')
    bw = best_upload_windows(vids)
    if not bw.empty:
        top = bw.sort_values("avg_views", ascending=False).iloc[0]
        actions.append(f'{top["weekday"]} uploads average {int(top["avg_views"]):,} views — schedule your drops there.')
    return actions
