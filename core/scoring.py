"""Turns Gemini's six category scores into one overall number.

Kept in plain Python (not asked of the LLM) so the result is reproducible and tunable.
"""

# Fit (skills + experience) carries 60%; presentation carries the rest.
WEIGHTS = {
    "skills_match": 0.30,
    "experience_relevance": 0.30,
    "impact_evidence": 0.15,
    "keywords_ats": 0.10,
    "education_fit": 0.10,
    "profile_completeness": 0.05,
}
SKILLS_FLOOR = 35
CAP_WHEN_SKILLS_WEAK = 55

VERDICT_BANDS = [
    (80, "Strong match"),
    (65, "Good match"),
    (45, "Partial match"),
    (0, "Weak match"),
]


def compute_overall_score(scores: dict[str, int]) -> int:
    """Combine category scores into a single 0-100 score.

    `scores` maps category key -> 0-100, with keys:
        skills_match, experience_relevance, education_fit,
        keywords_ats, impact_evidence, profile_completeness
    A category may be missing if the model skipped it.
    """
    present = {key: value for key, value in scores.items() if key in WEIGHTS}
    if not present:
        return 0
    total_weight = sum(WEIGHTS[key] for key in present)
    overall = sum(WEIGHTS[key] * value for key, value in present.items()) / total_weight
    # A polished profile for the wrong job must not read as a good match.
    if present.get("skills_match", 100) < SKILLS_FLOOR:
        overall = min(overall, CAP_WHEN_SKILLS_WEAK)
    return round(overall)


def verdict_label(overall: int) -> str:
    for threshold, label in VERDICT_BANDS:
        if overall >= threshold:
            return label
    return VERDICT_BANDS[-1][1]
