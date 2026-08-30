"""
Central config. Credentials come from a .env file locally, or from Streamlit
secrets / GitHub Actions secrets when deployed — never hard-coded.
Missing values just mean a connector reports "not configured"; the app still runs.
"""
import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _get(key, default=""):
    """Look in environment first (local .env, GitHub Actions), then Streamlit
    secrets (Streamlit Community Cloud). Works in every context without crashing."""
    v = os.getenv(key)
    if v:
        return v
    try:
        import streamlit as st
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default


@dataclass
class Config:
    youtube_api_key: str = field(default_factory=lambda: _get("YOUTUBE_API_KEY"))
    youtube_channel_id: str = field(default_factory=lambda: _get("YOUTUBE_CHANNEL_ID"))
    ig_access_token: str = field(default_factory=lambda: _get("IG_ACCESS_TOKEN"))
    ig_user_id: str = field(default_factory=lambda: _get("IG_USER_ID"))
    beatstars_url: str = field(default_factory=lambda: _get("BEATSTARS_URL", "https://beatstars.com/prodkpc"))
    db_path: str = field(default_factory=lambda: _get("DB_PATH") or os.path.join(os.path.dirname(__file__), "data", "growth.db"))


CONFIG = Config()
