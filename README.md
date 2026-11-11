# Profile Analyser

Paste a LinkedIn profile link and a job description. The app:

1. Pulls the full profile JSON through an Apify actor (`harvestapi/linkedin-profile-scraper`, no LinkedIn login needed).
2. Has Gemini rate the profile against the job description across six categories.
3. Lists concrete, ready-to-paste profile fixes (headline, About, per-section changes, missing keywords).
4. Generates a tailored one-page resume as DOCX, PDF or Markdown, using only facts from the profile.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Keys

Copy `.env.example` to `.env` and fill in:

| Name | Where to get it |
| --- | --- |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| `APIFY_API_TOKEN` | Apify Console → Settings → API & Integrations |

Optional: `GEMINI_MODEL` (default: newest stable Flash model your key can use) and `APIFY_ACTOR_ID`.

Each profile scrape costs about $0.004 of Apify credit; results are cached for an hour per URL.

## Layout

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit UI |
| `core/scraper.py` | Apify call, URL validation, JSON slimming |
| `core/analyzer.py` | Gemini prompts and structured-output calls |
| `core/schemas.py` | Pydantic shapes Gemini must return |
| `core/scoring.py` | Overall score from category scores |
| `core/resume_builder.py` | Markdown / DOCX / PDF rendering |

## Streamlit Cloud

Deploy `app.py` and add the two keys under **App settings → Secrets**:

```toml
GEMINI_API_KEY = "..."
APIFY_API_TOKEN = "..."
```
