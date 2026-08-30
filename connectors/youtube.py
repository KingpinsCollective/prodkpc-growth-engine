"""
YouTube connector — fully functional against the YouTube Data API v3.

Setup (5 min, free):
  1. console.cloud.google.com -> new project -> enable "YouTube Data API v3"
  2. Create an API key. Put it in .env as YOUTUBE_API_KEY.
  3. Put your channel ID in .env as YOUTUBE_CHANNEL_ID
     (find it at youtube.com/account_advanced, or it's in your channel URL).

What it pulls:
  - Channel: subscriber count, total views, video count (snapshotted for velocity)
  - Every video: title, publish time, views/likes/comments, duration, TAGS, category

Deeper "which videos gained subscribers / impressions / CTR" data lives in the
YouTube *Analytics* API, which needs OAuth (not just a key). The stub at the
bottom shows where that plugs in — the Data API above already powers every
correlation in this app.
"""
import re
from .base import Connector
from data import store

_DUR = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _duration_to_sec(iso):
    m = _DUR.match(iso or "")
    if not m:
        return 0
    h, mn, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mn * 60 + s


class YouTubeConnector(Connector):
    id = "youtube"
    name = "YouTube"
    kind = "api"

    def is_configured(self):
        return bool(self.config.youtube_api_key and self.config.youtube_channel_id)

    def _client(self):
        from googleapiclient.discovery import build
        return build("youtube", "v3", developerKey=self.config.youtube_api_key,
                     cache_discovery=False)

    def collect(self, db_path):
        if not self.is_configured():
            return {"source": self.id, "ok": False, "msg": "not configured"}
        yt = self._client()
        ch = yt.channels().list(
            part="statistics,contentDetails", id=self.config.youtube_channel_id
        ).execute()
        if not ch.get("items"):
            return {"source": self.id, "ok": False, "msg": "channel not found"}
        item = ch["items"][0]
        stats = item["statistics"]
        subs = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        vids = int(stats.get("videoCount", 0))
        store.save_channel_snapshot(db_path, self.id, self.config.youtube_channel_id,
                                    subs, views, vids)

        uploads = item["contentDetails"]["relatedPlaylists"]["uploads"]
        video_ids, token = [], None
        while len(video_ids) < 200:
            pl = yt.playlistItems().list(
                part="contentDetails", playlistId=uploads, maxResults=50, pageToken=token
            ).execute()
            video_ids += [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
            token = pl.get("nextPageToken")
            if not token:
                break

        saved = 0
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            vr = yt.videos().list(
                part="snippet,statistics,contentDetails", id=",".join(batch)
            ).execute()
            for v in vr.get("items", []):
                sn, st = v["snippet"], v.get("statistics", {})
                store.upsert_video(db_path, {
                    "video_id": v["id"],
                    "title": sn.get("title", ""),
                    "published_at": sn.get("publishedAt", ""),
                    "views": int(st.get("viewCount", 0)),
                    "likes": int(st.get("likeCount", 0)),
                    "comments": int(st.get("commentCount", 0)),
                    "duration_sec": _duration_to_sec(v["contentDetails"].get("duration", "")),
                    "tags": sn.get("tags", []),
                    "category_id": sn.get("categoryId", ""),
                })
                saved += 1
        return {"source": self.id, "ok": True,
                "msg": f"subs={subs:,} · videos synced={saved}"}


# ---- where deeper own-channel analytics plug in later (OAuth required) ----
class YouTubeAnalyticsConnector:
    """
    Placeholder for the YouTube Analytics API (watch time, traffic sources,
    impressions, CTR, and subscribers-gained-per-video). Requires an OAuth flow
    (google-auth-oauthlib) rather than a plain key. Implement collect() the same
    shape as above and add it to the registry when you want that layer.
    """
    id = "youtube_analytics"
