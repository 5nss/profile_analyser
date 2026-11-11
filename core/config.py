"""Settings lookup: .env locally, st.secrets on Streamlit Cloud."""
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_ACTOR_ID = "harvestapi/linkedin-profile-scraper"


def get_setting(name: str, default: str = "") -> str:
    value = (os.getenv(name) or "").strip()
    if value:
        return value
    try:
        import streamlit as st

        return str(st.secrets.get(name, default)).strip()
    except Exception:
        # No secrets.toml present (normal for local runs).
        return default
