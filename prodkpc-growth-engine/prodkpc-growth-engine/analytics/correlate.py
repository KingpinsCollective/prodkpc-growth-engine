"""
Correlation analytics. Answers "what about a video/post predicts performance?"
by building numeric features from metadata and correlating them with views/reach.

Uses Spearman correlation (rank-based) via pandas — robust to the heavy skew of
view counts, and no scipy dependency. A value near +1 means "more of this =>
more views"; near -1 means the opposite; near 0 means no relationship.
"""
import numpy as np
import pandas as pd


def youtube_feature_table(vids: pd.DataFrame) -> pd.DataFrame:
    if vids.empty:
        return pd.DataFrame()
    v = vids.copy()
    v["tag_count"] = v["tags"].apply(lambda t: len(t or []))
    v["title_len"] = v["title"].fillna("").str.len()
    v["duration_min"] = (v["duration_sec"].fillna(0) / 60).round(2)
    v["hour"] = v["published_at"].dt.hour
    v["weekday_num"] = v["published_at"].dt.weekday
    v["is_short"] = (v["duration_sec"].fillna(0) <= 60).astype(int)
    return v


def youtube_correlations(vids: pd.DataFrame) -> pd.DataFrame:
    v = youtube_feature_table(vids)
    if v.empty or len(v) < 4:
        return pd.DataFrame(columns=["feature", "spearman_r", "reading"])
    feats = ["tag_count", "title_len", "duration_min", "hour", "weekday_num", "is_short"]
    rows = []
    for f in feats:
        try:
            r = v[f].rank().corr(v["views"].rank())
        except Exception:
            r = np.nan
        if pd.isna(r):
            continue
        rows.append({"feature": f, "spearman_r": round(float(r), 2),
                     "reading": _reading(f, r)})
    return pd.DataFrame(rows).sort_values("spearman_r", key=lambda s: s.abs(), ascending=False)


def instagram_correlations(media: pd.DataFrame) -> dict:
    """Media-type performance + posting-hour signal for IG."""
    if media.empty:
        return {"by_type": pd.DataFrame(), "by_hour": pd.DataFrame()}
    m = media.copy()
    m["engagement"] = m["likes"].fillna(0) + m["comments"].fillna(0)
    m["score"] = m["reach"].where(m["reach"] > 0, m["engagement"])
    by_type = (m.groupby("media_type")
                 .agg(avg_score=("score", "mean"), posts=("score", "size"))
                 .reset_index().sort_values("avg_score", ascending=False))
    by_type["avg_score"] = by_type["avg_score"].round(0).astype(int)
    m["hour"] = m["timestamp"].dt.hour
    by_hour = (m.groupby("hour").agg(avg_score=("score", "mean"), posts=("score", "size"))
                 .reset_index().sort_values("avg_score", ascending=False))
    by_hour["avg_score"] = by_hour["avg_score"].round(0).astype(int)
    return {"by_type": by_type, "by_hour": by_hour}


def _reading(feature, r):
    strength = "strong" if abs(r) >= 0.4 else ("mild" if abs(r) >= 0.2 else "weak/none")
    labels = {
        "tag_count": "more tags", "title_len": "longer titles",
        "duration_min": "longer videos", "hour": "later-in-day uploads",
        "weekday_num": "later-in-week uploads", "is_short": "being a Short",
    }
    if abs(r) < 0.2:
        return f"{strength} link — {labels[feature]} doesn't move views much"
    direction = "more" if r > 0 else "fewer"
    return f"{strength}: {labels[feature]} => {direction} views"
