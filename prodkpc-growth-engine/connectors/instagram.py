"""
Instagram connector — Meta Graph API (real calls).

Reality check: this only works for YOUR OWN Instagram Business or Creator
account, and only after Meta app setup. There is no way to pull arbitrary
accounts or scrape competitors through the official API.

Setup (~20 min, the fiddly one):
  1. Convert @prodkpc to a Business/Creator account and link it to a Facebook Page.
  2. developers.facebook.com -> create app -> add "Instagram Graph API".
  3. Generate a long-lived access token; get your IG user id.
  4. Put IG_ACCESS_TOKEN and IG_USER_ID in .env.

What it pulls (your account only):
  - followers_count, media_count, account reach (snapshotted for velocity)
  - per post: caption, media_type (IMAGE/VIDEO/REEL/CAROUSEL), likes, comments,
    reach, plays, timestamp, permalink

That per-post metadata is exactly what the Correlations page uses to tell you
which media type / caption pattern / posting time actually moves reach + follows.
"""
import requests
from .base import Connector
from data import store

GRAPH = "https://graph.facebook.com/v20.0"


class InstagramConnector(Connector):
    id = "instagram"
    name = "Instagram"
    kind = "api"

    def is_configured(self):
        return bool(self.config.ig_access_token and self.config.ig_user_id)

    def _get(self, path, params):
        params = {**params, "access_token": self.config.ig_access_token}
        r = requests.get(f"{GRAPH}/{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def collect(self, db_path):
        if not self.is_configured():
            return {"source": self.id, "ok": False, "msg": "not configured"}
        uid = self.config.ig_user_id

        acct = self._get(uid, {"fields": "followers_count,media_count"})
        reach = 0
        try:
            ins = self._get(f"{uid}/insights",
                            {"metric": "reach", "period": "day"})
            reach = ins["data"][0]["values"][0]["value"] if ins.get("data") else 0
        except Exception:
            pass  # insights need sufficient account activity; degrade gracefully
        store.save_ig_account_snapshot(db_path, uid,
                                       acct.get("followers_count", 0),
                                       acct.get("media_count", 0), reach)

        media = self._get(f"{uid}/media", {
            "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
            "limit": 100,
        })
        saved = 0
        for m in media.get("data", []):
            reach_m = plays_m = 0
            try:
                mi = self._get(f"{m['id']}/insights", {"metric": "reach,plays"})
                for row in mi.get("data", []):
                    val = row["values"][0]["value"]
                    if row["name"] == "reach":
                        reach_m = val
                    elif row["name"] == "plays":
                        plays_m = val
            except Exception:
                pass
            store.upsert_ig_media(db_path, {
                "media_id": m["id"],
                "caption": m.get("caption", ""),
                "media_type": m.get("media_type", ""),
                "timestamp": m.get("timestamp", ""),
                "likes": m.get("like_count", 0),
                "comments": m.get("comments_count", 0),
                "reach": reach_m, "plays": plays_m,
                "permalink": m.get("permalink", ""),
            })
            saved += 1
        return {"source": self.id, "ok": True,
                "msg": f"followers={acct.get('followers_count',0):,} · posts synced={saved}"}
