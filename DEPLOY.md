# Deploying (GitHub → Streamlit Cloud → iPhone)

You need a computer for this one-time push. After that it's phone-only and self-updating.

## 1. Put the code on GitHub
- Create a new repo at github.com (name it e.g. `prodkpc-growth-engine`). Private is fine.
- Push this folder to it. Either drag the files into GitHub's "upload files" web UI,
  or from a terminal in this folder:
  ```
  git init && git add . && git commit -m "initial"
  git branch -M main
  git remote add origin https://github.com/YOURNAME/prodkpc-growth-engine.git
  git push -u origin main
  ```
- Your API key is NOT in here — `.env` is gitignored. Good.

## 2. Deploy on Streamlit Community Cloud (free)
- Go to share.streamlit.io → sign in with GitHub → **New app**.
- Pick your repo, branch `main`, main file `app.py` → Deploy.
- Once it builds, open **Settings → Secrets** and paste (TOML format):
  ```
  YOUTUBE_API_KEY = "your-key-here"
  YOUTUBE_CHANNEL_ID = "UCiUG-a1UFFkq6vlOFtzE7YA"
  ```
  (Add IG_ACCESS_TOKEN / IG_USER_ID later when Instagram is set up.)
- Reboot the app from its menu so it picks up the secrets.

## 3. Turn on the daily auto-update
- In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret.**
- Add the same `YOUTUBE_API_KEY` and `YOUTUBE_CHANNEL_ID`.
- The workflow in `.github/workflows/collect.yml` runs daily and commits fresh data.
  Trigger it once by hand: repo **Actions** tab → "Daily collect" → **Run workflow**.

## 4. Make it an app on your iPhone
- Open your Streamlit app URL in Safari.
- Share button → **Add to Home Screen**. It launches full-screen with its own icon.

Done. It updates itself every day and you drive it entirely from your phone.

## Persistence note
The free setup commits a SQLite file daily — perfect for the YouTube/IG numbers.
Manual BeatStars entries typed into the live app won't survive a redeploy on the
free host; when you want those durable, swap SQLite for a free Postgres
(Neon/Supabase) — only `data/store.py` changes.

---

# Adding the YouTube Analytics layer (owner-only momentum)

This unlocks subscribers-gained-per-video, daily momentum, and traffic sources —
the "what's converting right now" data. It uses OAuth, so there's a one-time
authorization. Do it once; the daily collector runs headless forever after.

## A. Create OAuth credentials (Google Cloud)
1. console.cloud.google.com → your existing project → **APIs & Services → Enable APIs**
   → enable **"YouTube Analytics API"** (separate from the Data API).
2. **APIs & Services → OAuth consent screen**:
   - User type **External** → fill the required app name + your email.
   - **Add scope** `https://www.googleapis.com/auth/yt-analytics.readonly`.
   - **IMPORTANT — Publishing status: click "Publish app" / set to "In production."**
     In "Testing" mode, refresh tokens expire after 7 days and your collector
     would silently die in a week. Production keeps the token alive. You'll see an
     "unverified app" warning later — that's expected for a personal app; you click
     through it (it's your own data).
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - For the no-code Playground route (recommended): type **Web application**,
     and under *Authorized redirect URIs* add
     `https://developers.google.com/oauthplayground`.
   - Save. Copy the **Client ID** and **Client secret**.

## B. Get a refresh token — no-code route (OAuth Playground)
1. Go to **developers.google.com/oauthplayground**.
2. Top-right **gear (⚙)** → check **"Use your own OAuth credentials"** → paste your
   Client ID and Client secret.
3. Left panel: in the "Input your own scopes" box, paste
   `https://www.googleapis.com/auth/yt-analytics.readonly` → **Authorize APIs**.
4. Sign in with the Google account that owns the channel → click through the
   "unverified app" warning (Advanced → Go to … ).
5. Click **"Exchange authorization code for tokens."** Copy the **Refresh token**.

(Alternative local route: `python auth_youtube.py client_secret.json` — see that file.)

## C. Add three GitHub secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:
- `YT_OAUTH_CLIENT_ID`
- `YT_OAUTH_CLIENT_SECRET`
- `YT_OAUTH_REFRESH_TOKEN`

Add the same three in **Streamlit → app Settings → Secrets** (TOML format) if you
want the Momentum page to work between daily runs.

## D. Run it
Repo **Actions → Daily collect → Run workflow.** In the "Collect snapshots" step
you want: `[OK ] YouTube Analytics  daily=30d · videos=25 · traffic=…`.
Then open the app → **Momentum** page.

---

# Video storage (Cloudflare R2)

The Upload page stores finished videos in an R2 bucket and records the public URL
(needed later for Instagram publishing). Add these to **Streamlit → app Settings →
Secrets** (TOML format) — R2 is used by the interactive app, not the daily collector:

```
R2_ACCESS_KEY_ID = "your-access-key-id"
R2_SECRET_ACCESS_KEY = "your-secret-access-key"
R2_ENDPOINT = "https://<accountid>.r2.cloudflarestorage.com"
R2_BUCKET = "prodkpc-videos"
R2_PUBLIC_BASE = "https://pub-95e446d1e0e34fabab097243229d313d.r2.dev"
```

IMPORTANT: R2_ENDPOINT is the **account-level** endpoint with NO bucket on the end
(no `/prodkpc-videos`). boto3 adds the bucket itself.
