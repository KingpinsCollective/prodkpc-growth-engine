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
