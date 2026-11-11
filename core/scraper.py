"""Fetch a LinkedIn profile as JSON through an Apify actor."""
import json
import re
from datetime import timedelta
from decimal import Decimal
from urllib.parse import unquote

from apify_client import ApifyClient

MAX_CHARGE_USD = Decimal("0.05")

_PROFILE_RE = re.compile(r"linkedin\.com/in/([^/?#\s]+)", re.IGNORECASE)

# Keys that only cost tokens and add nothing to an analysis.
_NOISE_KEYS = {
    "photo", "logo", "companyLogo", "schoolLogo", "backgroundPicture", "coverPicture",
    "companyId", "schoolId", "companyUniversalName", "id", "objectUrn", "entityUrn",
    "moreProfiles", "peopleAlsoViewed", "similarProfiles",
    "urn", "company_id", "current_company_urn", "skills_url", "created_timestamp",
}


class ScrapeError(Exception):
    """A problem the user can act on (bad URL, private profile, bad token...)."""


def normalise_profile_url(raw: str) -> str:
    """Return a canonical https://www.linkedin.com/in/<id> URL, or raise ScrapeError."""
    match = _PROFILE_RE.search(raw or "")
    if not match:
        raise ScrapeError(
            "That doesn't look like a LinkedIn profile link. "
            "Expected something like https://www.linkedin.com/in/your-name"
        )
    return f"https://www.linkedin.com/in/{match.group(1)}"


def _build_input(actor_id: str, url: str, slug: str) -> dict:
    """Each Apify actor names its input fields differently."""
    actor = actor_id.lower().replace("~", "/")
    if actor == "harvestapi/linkedin-profile-scraper":
        return {"profileScraperMode": "Profile details no email ($4 per 1k)", "queries": [url]}
    if actor == "apimaestro/linkedin-profile-detail":
        return {"username": slug, "includeEmail": False}
    # Unknown actor: offer the common field names and let the identity check catch a miss.
    return {"queries": [url], "urls": [url], "profileUrls": [url], "username": slug}


def fetch_profile(profile_url: str, token: str, actor_id: str) -> dict:
    """Run the actor for one profile and return its raw JSON item."""
    url = normalise_profile_url(profile_url)
    slug = url.rsplit("/", 1)[-1]
    client = ApifyClient(token)
    run_input = _build_input(actor_id, url, slug)
    try:
        run = client.actor(actor_id).call(
            run_input=run_input,
            run_timeout=timedelta(seconds=180),
            max_total_charge_usd=MAX_CHARGE_USD,  # hard cost ceiling per scrape
            logger=None,
        )
    except Exception as exc:
        raise ScrapeError(f"Apify run could not start or failed: {exc}") from exc

    if run is None or run.status != "SUCCEEDED":
        detail = f"{run.status}: {run.status_message or ''}" if run else "no run returned"
        raise ScrapeError(f"Apify run did not succeed ({detail}).")

    items = list(client.dataset(run.default_dataset_id).iterate_items(limit=1))
    if not items:
        raise ScrapeError(
            "Apify returned no data. The profile may be private, deleted, or the link is wrong."
        )
    profile = items[0]
    if profile.get("error") and not (profile.get("firstName") or profile.get("headline")):
        raise ScrapeError(f"Apify could not read this profile: {profile['error']}")
    # An actor that doesn't recognise our input may fall back to its built-in demo
    # profile. Refuse anything that isn't the person we asked for.
    if unquote(slug).lower() not in unquote(json.dumps(profile, ensure_ascii=False)).lower():
        raise ScrapeError(
            f"Apify returned a different profile than '{slug}'. The actor '{actor_id}' "
            "probably expects a different input format; check APIFY_ACTOR_ID in .env."
        )
    return profile


def slim_profile(value):
    """Drop image URLs, internal IDs and empty values so the LLM prompt stays small."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in _NOISE_KEYS:
                continue
            cleaned = slim_profile(item)
            if cleaned in (None, "", [], {}):
                continue
            out[key] = cleaned
        return out
    if isinstance(value, list):
        return [c for c in (slim_profile(v) for v in value) if c not in (None, "", [], {})]
    if isinstance(value, str) and "media.licdn.com" in value:
        return None
    return value
