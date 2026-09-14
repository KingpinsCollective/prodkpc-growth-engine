"""
YouTube Analytics connector — the OWNER-only momentum layer (OAuth).

Where the plain Data API gives lifetime public stats, this gives the private,
time-boxed numbers only the channel owner can see:
  - subscribers GAINED per video (which uploads are actually converting)
  - daily channel momentum (views, watch time, subs gained/lost)
  - traffic sources (is discovery coming from YouTube search, suggested, external?)

Auth is different from the Data API: it needs a one-time OAuth authorization
(you approving access to your own analytics), which yields a refresh token.
The collector then uses three secrets to mint short-lived access tokens on each
run — no browser, no interaction. See DEPLOY.md for the one-time setup.

Every query is isolated: if one report fails, the others still land, and the
existing Data API pipeline is never affected.
"""
from datetime import date, timedelta
from .base import Connector
from data import store

SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]


class YouTubeAnalyticsConnector(Connector):
    id = "youtube_analytics"
    name = "YouTube Analytics"
    kind = "api"

    def is_configured(self):
        return bool(self.config.yt_oauth_client_id
                    and self.config.yt_oauth_client_secret
                    and self.config.yt_oauth_refresh_token)

    def _service(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        creds = Credentials(
            token=None,
            refresh_token=self.config.yt_oauth_refresh_token,
            client_id=self.config.yt_oauth_client_id,
            client_secret=self.config.yt_oauth_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )
        creds.refresh(Request())  # fail loudly here if the refresh token is bad
        return build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)

    def collect(self, db_path):
        if not self.is_configured():
            return {"source": self.id, "ok": False, "msg": "not configured"}
        try:
            yt = self._service()
        except Exception as e:
            return {"source": self.id, "ok": False, "msg": f"auth failed: {e}"}

        today = date.today()
        d30 = (today - timedelta(days=30)).isoformat()
        d90 = (today - timedelta(days=90)).isoformat()
        end = today.isoformat()
        notes = []

        # 1) daily channel momentum (last 30 days)
        try:
            r = yt.reports().query(
                ids="channel==MINE", startDate=d30, endDate=end,
                metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost",
                dimensions="day",
            ).execute()
            for row in r.get("rows", []):
                day, views, mins, gained, lost = row
                store.upsert_yt_daily(db_path, day, int(views), int(mins), int(gained), int(lost))
            notes.append(f"daily={len(r.get('rows', []))}d")
        except Exception as e:
            notes.append(f"daily err")

        # 2) per-video: which uploads gained subscribers (last 90 days)
        try:
            r = yt.reports().query(
                ids="channel==MINE", startDate=d90, endDate=end,
                metrics="views,subscribersGained,estimatedMinutesWatched,averageViewDuration",
                dimensions="video", sort="-subscribersGained", maxResults=25,
            ).execute()
            for row in r.get("rows", []):
                vid, views, gained, mins, avg = row
                store.upsert_yt_video_analytics(db_path, vid, int(views), int(gained),
                                                int(mins), int(avg), f"{d90}..{end}")
            notes.append(f"videos={len(r.get('rows', []))}")
        except Exception as e:
            notes.append("videos err")

        # 3) traffic sources (last 90 days)
        try:
            r = yt.reports().query(
                ids="channel==MINE", startDate=d90, endDate=end,
                metrics="views", dimensions="insightTrafficSourceType", sort="-views",
            ).execute()
            rows = [(row[0], int(row[1])) for row in r.get("rows", [])]
            if rows:
                store.replace_yt_traffic(db_path, rows, f"{d90}..{end}")
            notes.append(f"traffic={len(rows)}")
        except Exception as e:
            notes.append("traffic err")

        return {"source": self.id, "ok": True, "msg": " · ".join(notes)}
