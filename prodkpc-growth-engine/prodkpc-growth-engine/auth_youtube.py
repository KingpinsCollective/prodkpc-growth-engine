"""
One-time helper to mint a YouTube Analytics refresh token — the LOCAL route.
(If you'd rather not run Python locally, DEPLOY.md has a no-code browser route
using Google's OAuth Playground. This script is the alternative.)

Usage:
    pip install -r requirements.txt
    python auth_youtube.py path/to/client_secret.json

It opens a browser, you approve access to your own analytics, and it prints the
three values to paste into GitHub secrets: client id, client secret, refresh
token. Nothing is stored on disk.
"""
import sys
import json


def main():
    if len(sys.argv) < 2:
        print("Usage: python auth_youtube.py path/to/client_secret.json")
        sys.exit(1)
    secret_path = sys.argv[1]

    from google_auth_oauthlib.flow import InstalledAppFlow
    scopes = ["https://www.googleapis.com/auth/yt-analytics.readonly"]
    flow = InstalledAppFlow.from_client_secrets_file(secret_path, scopes=scopes)
    creds = flow.run_local_server(port=0, prompt="consent")

    with open(secret_path) as f:
        data = json.load(f)
    info = data.get("installed") or data.get("web") or {}

    print("\n" + "=" * 60)
    print("Paste these into GitHub -> Settings -> Secrets -> Actions:")
    print("=" * 60)
    print("YT_OAUTH_CLIENT_ID     =", info.get("client_id", ""))
    print("YT_OAUTH_CLIENT_SECRET =", info.get("client_secret", ""))
    print("YT_OAUTH_REFRESH_TOKEN =", creds.refresh_token)
    print("=" * 60)
    if not creds.refresh_token:
        print("\n(!) No refresh token returned. Revoke the app's access at "
              "myaccount.google.com/permissions and run again — Google only "
              "returns a refresh token on first consent.")


if __name__ == "__main__":
    main()
