import json

import streamlit as st
from google import genai

from core import resume_builder
from core.analyzer import AnalysisError, analyse_profile, generate_resume, make_client, pick_models
from core.config import DEFAULT_ACTOR_ID, get_setting
from core.schemas import CATEGORY_LABELS
from core.scoring import compute_overall_score, verdict_label
from core.scraper import ScrapeError, fetch_profile, normalise_profile_url, slim_profile

st.set_page_config(page_title="Profile Analyser", page_icon="🎯", layout="wide")

GEMINI_KEY = get_setting("GEMINI_API_KEY")
APIFY_TOKEN = get_setting("APIFY_API_TOKEN")
ACTOR_ID = get_setting("APIFY_ACTOR_ID", DEFAULT_ACTOR_ID) or DEFAULT_ACTOR_ID
MIN_JD_CHARS = 100


@st.cache_data(ttl=3600, show_spinner=False)
def cached_profile(url: str, actor_id: str, _token: str) -> dict:
    """Each scrape costs Apify credit, so reuse it for an hour per URL."""
    return fetch_profile(url, _token, actor_id)


@st.cache_resource(show_spinner=False)
def gemini_client(api_key: str) -> genai.Client:
    return make_client(api_key)


@st.cache_data(ttl=3600, show_spinner=False)
def resolved_models(api_key: str, override: str) -> list[str]:
    return pick_models(gemini_client(api_key), override)


def priority_badge(priority: str) -> str:
    return {"high": "🔴 High", "medium": "🟠 Medium", "low": "🟢 Low"}.get(priority, priority)


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Setup")
    st.write(("✅" if GEMINI_KEY else "❌") + " `GEMINI_API_KEY`")
    st.write(("✅" if APIFY_TOKEN else "❌") + " `APIFY_API_TOKEN`")
    if not (GEMINI_KEY and APIFY_TOKEN):
        st.info("Add the missing keys to the `.env` file, then restart the app.")

    st.divider()
    st.header("Resume contact details")
    st.caption("LinkedIn doesn't expose these, so add them here. Optional.")
    contact = {
        "email": st.text_input("Email"),
        "phone": st.text_input("Phone"),
        "website": st.text_input("Portfolio / GitHub"),
    }

# ---------------- Inputs ----------------
st.title("🎯 Profile Analyser")
st.caption("Paste a LinkedIn profile and a job description. Get a score, concrete fixes and a tailored resume.")

left, right = st.columns([1, 1.4])
with left:
    profile_url = st.text_input("LinkedIn profile link", placeholder="https://www.linkedin.com/in/your-name")
with right:
    job_description = st.text_area("Job description", height=180, placeholder="Paste the full job description here…")

if st.button("Analyse profile", type="primary", disabled=not (GEMINI_KEY and APIFY_TOKEN)):
    if len(job_description.strip()) < MIN_JD_CHARS:
        st.error("Paste the full job description — a few lines isn't enough to rate against.")
        st.stop()
    try:
        url = normalise_profile_url(profile_url)
        with st.status("Working…", expanded=True) as status:
            st.write("Fetching LinkedIn profile through Apify…")
            raw_profile = cached_profile(url, ACTOR_ID, APIFY_TOKEN)
            profile = slim_profile(raw_profile)
            st.write("Analysing against the job description with Gemini…")
            client = gemini_client(GEMINI_KEY)
            models = resolved_models(GEMINI_KEY, get_setting("GEMINI_MODEL"))
            analysis, model = analyse_profile(client, models, profile, job_description)
            status.update(label="Done", state="complete", expanded=False)
    except (ScrapeError, AnalysisError) as exc:
        st.error(str(exc))
        st.stop()

    st.session_state.update(
        url=url, raw_profile=raw_profile, profile=profile, analysis=analysis,
        job_description=job_description, model=model, resume=None,
        # Start later calls from the model that just answered, not the busy ones.
        models=[model] + [m for m in models if m != model],
    )

# ---------------- Results ----------------
if "analysis" not in st.session_state:
    st.stop()

analysis = st.session_state["analysis"]
profile = st.session_state["profile"]
contact["linkedin"] = st.session_state["url"].removeprefix("https://www.")

scores = {s.category.value: max(0, min(100, s.score)) for s in analysis.category_scores}
overall = compute_overall_score(scores)

st.divider()
tab_score, tab_fix, tab_resume, tab_raw = st.tabs(
    ["📊 Score", "🛠 Suggestions", "📄 Resume", "🗂 Raw profile JSON"],
    key="result_tabs",  # keeps the chosen tab selected across reruns
)

with tab_score:
    top_left, top_right = st.columns([1, 2.2])
    with top_left:
        st.metric("Overall match", f"{overall} / 100", verdict_label(overall), delta_color="off", delta_arrow="off")
        st.caption(f"Model: `{st.session_state['model']}`")
    with top_right:
        st.markdown(f"**Verdict.** {analysis.verdict}")
        st.markdown(f"**The role.** {analysis.role_summary}")
        st.markdown(f"**The candidate.** {analysis.candidate_summary}")

    st.subheader("Breakdown")
    for item in analysis.category_scores:
        key = item.category.value
        st.progress(scores[key] / 100, text=f"**{CATEGORY_LABELS.get(key, key)}** — {scores[key]}/100")
        with st.expander("Why this score"):
            st.markdown(f"**Evidence:** {item.evidence}")
            st.markdown(f"**Gap:** {item.gap}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Strengths")
        for line in analysis.strengths:
            st.markdown(f"- {line}")
        st.subheader("Keywords you already cover")
        st.write(", ".join(analysis.matched_keywords) or "—")
    with col_b:
        st.subheader("Weaknesses")
        for line in analysis.weaknesses:
            st.markdown(f"- {line}")
        st.subheader("Missing keywords")
        st.write(", ".join(analysis.missing_keywords) or "—")

with tab_fix:
    st.subheader("Suggested headline")
    st.code(analysis.improved_headline, language=None, wrap_lines=True)
    st.subheader("Suggested About section")
    st.code(analysis.improved_about, language=None, wrap_lines=True)

    st.subheader("Changes to make")
    for tip in analysis.suggestions:
        with st.expander(f"{priority_badge(tip.priority.value)} · {tip.section} — {tip.issue}"):
            st.markdown(tip.recommendation)
            if tip.rewritten_example.strip():
                st.caption("Ready to paste")
                st.code(tip.rewritten_example, language=None, wrap_lines=True)

with tab_resume:
    st.write("Builds a one-page, ATS-friendly resume tailored to this job, using only facts from the profile.")
    if st.button("Generate tailored resume", type="primary"):
        try:
            with st.spinner("Writing resume…"):
                st.session_state["resume"], _ = generate_resume(
                    gemini_client(GEMINI_KEY), st.session_state["models"], profile,
                    st.session_state["job_description"], analysis,
                )
        except AnalysisError as exc:
            st.error(str(exc))

    resume = st.session_state.get("resume")
    if resume:
        if resume.needs_user_input:
            with st.expander("⚠️ Add real numbers to make this stronger", expanded=True):
                st.caption("Nothing was invented. Answer these and edit the DOCX to add the facts.")
                for question in resume.needs_user_input:
                    st.markdown(f"- {question}")

        markdown = resume_builder.to_markdown(resume, contact)
        file_stem = resume.full_name.strip().replace(" ", "_") or "resume"
        d1, d2, d3 = st.columns(3)
        d1.download_button(
            "⬇️ Word (.docx)", resume_builder.to_docx(resume, contact), f"{file_stem}_resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        d2.download_button("⬇️ PDF", resume_builder.to_pdf(resume, contact), f"{file_stem}_resume.pdf", "application/pdf")
        d3.download_button("⬇️ Markdown", markdown, f"{file_stem}_resume.md", "text/markdown")
        with st.container(border=True):
            st.markdown(markdown)

with tab_raw:
    st.caption("Exactly what Apify returned for this profile.")
    st.download_button(
        "⬇️ Download JSON", json.dumps(st.session_state["raw_profile"], indent=2, ensure_ascii=False),
        "profile.json", "application/json",
    )
    st.json(st.session_state["raw_profile"], expanded=1)
