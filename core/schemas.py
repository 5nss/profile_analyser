"""Shapes Gemini must return. Every field is required: Gemini's schema support
is a subset of JSON Schema and optional/default fields are the usual trouble spot."""
from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    SKILLS_MATCH = "skills_match"
    EXPERIENCE_RELEVANCE = "experience_relevance"
    EDUCATION_FIT = "education_fit"
    KEYWORDS_ATS = "keywords_ats"
    IMPACT_EVIDENCE = "impact_evidence"
    PROFILE_COMPLETENESS = "profile_completeness"


CATEGORY_LABELS = {
    Category.SKILLS_MATCH.value: "Skills match",
    Category.EXPERIENCE_RELEVANCE.value: "Experience relevance",
    Category.EDUCATION_FIT.value: "Education fit",
    Category.KEYWORDS_ATS.value: "Keywords / ATS",
    Category.IMPACT_EVIDENCE.value: "Impact & evidence",
    Category.PROFILE_COMPLETENESS.value: "Profile completeness",
}


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CategoryScore(BaseModel):
    category: Category
    score: int = Field(description="0-100. 100 = fully meets what the job description asks for.")
    evidence: str = Field(description="What in the profile justifies this score. Quote or cite specifics.")
    gap: str = Field(description="What is missing or weak relative to the job description.")


class Suggestion(BaseModel):
    section: str = Field(description="Profile section: Headline, About, Experience, Skills, Education, Projects, Certifications, Other.")
    priority: Priority
    issue: str
    recommendation: str
    rewritten_example: str = Field(description="Ready-to-paste improved text, or empty string if not applicable.")


class ProfileAnalysis(BaseModel):
    candidate_summary: str = Field(description="3-4 sentence neutral summary of who this candidate is.")
    role_summary: str = Field(description="1-2 sentences on what the job description is really asking for.")
    category_scores: list[CategoryScore] = Field(description="Exactly one entry per category.")
    matched_keywords: list[str]
    missing_keywords: list[str] = Field(description="Important JD terms absent from the profile.")
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[Suggestion] = Field(description="Ordered most impactful first.")
    improved_headline: str
    improved_about: str
    verdict: str = Field(description="2-3 sentence honest hiring-manager style verdict.")


class ExperienceItem(BaseModel):
    title: str
    company: str
    location: str
    dates: str = Field(description="e.g. 'Jan 2023 - Present'")
    bullets: list[str]


class EducationItem(BaseModel):
    degree: str
    school: str
    dates: str
    details: str = Field(description="Grade, honours or relevant coursework; empty string if none.")


class ProjectItem(BaseModel):
    name: str
    tech: str = Field(description="Comma-separated technologies; empty string if unknown.")
    bullets: list[str]


class SkillGroup(BaseModel):
    category: str
    skills: list[str]


class Resume(BaseModel):
    full_name: str
    headline: str = Field(description="Target-role title line under the name.")
    location: str
    summary: str = Field(description="3-4 line professional summary tailored to the job.")
    skills: list[SkillGroup]
    experience: list[ExperienceItem]
    projects: list[ProjectItem]
    education: list[EducationItem]
    certifications: list[str]
    needs_user_input: list[str] = Field(
        description="Questions for the candidate where a real number or fact would strengthen a bullet."
    )
