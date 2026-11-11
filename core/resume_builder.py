"""Render a Resume into Markdown (preview), DOCX and PDF. Single column, ATS-friendly."""
import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from fpdf import FPDF

from .schemas import Resume


def contact_line(resume: Resume, contact: dict) -> str:
    parts = [resume.location, contact.get("email"), contact.get("phone"),
             contact.get("linkedin"), contact.get("website")]
    return "  |  ".join(p.strip() for p in parts if p and p.strip())


# ---------- Markdown ----------

def to_markdown(resume: Resume, contact: dict) -> str:
    lines = [f"# {resume.full_name}", f"**{resume.headline}**", "", contact_line(resume, contact), ""]
    if resume.summary:
        lines += ["## Summary", resume.summary, ""]
    if resume.skills:
        lines.append("## Skills")
        lines += [f"- **{g.category}:** {', '.join(g.skills)}" for g in resume.skills]
        lines.append("")
    if resume.experience:
        lines.append("## Experience")
        for job in resume.experience:
            lines.append(f"**{job.title}** — {job.company}  ")
            lines.append(f"*{' · '.join(p for p in (job.dates, job.location) if p)}*")
            lines += [f"- {b}" for b in job.bullets]
            lines.append("")
    if resume.projects:
        lines.append("## Projects")
        for project in resume.projects:
            tech = f" — *{project.tech}*" if project.tech else ""
            lines.append(f"**{project.name}**{tech}")
            lines += [f"- {b}" for b in project.bullets]
            lines.append("")
    if resume.education:
        lines.append("## Education")
        for edu in resume.education:
            lines.append(f"**{edu.degree}** — {edu.school}  ")
            lines.append(f"*{edu.dates}*" + (f" · {edu.details}" if edu.details else ""))
            lines.append("")
    if resume.certifications:
        lines.append("## Certifications")
        lines += [f"- {c}" for c in resume.certifications]
    return "\n".join(lines)


# ---------- DOCX ----------

def _docx_heading(doc: Document, text: str) -> None:
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(8)
    para.paragraph_format.space_after = Pt(2)
    run = para.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(11)
    # Thin rule under the heading.
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, val in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "444444")):
        bottom.set(qn(f"w:{key}"), val)
    borders.append(bottom)
    para._p.get_or_add_pPr().append(borders)


def _docx_line(doc: Document, bold: str, rest: str = "", italic: str = "") -> None:
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(0)
    para.add_run(bold).bold = True
    if rest:
        para.add_run(rest)
    if italic:
        para.add_run(italic).italic = True


def _docx_bullets(doc: Document, bullets: list[str]) -> None:
    for bullet in bullets:
        para = doc.add_paragraph(bullet, style="List Bullet")
        para.paragraph_format.space_after = Pt(0)


def to_docx(resume: Resume, contact: dict) -> bytes:
    doc = Document()
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Inches(0.6)
        section.left_margin = section.right_margin = Inches(0.7)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name.paragraph_format.space_after = Pt(0)
    run = name.add_run(resume.full_name)
    run.bold = True
    run.font.size = Pt(20)

    for text in (resume.headline, contact_line(resume, contact)):
        if text:
            para = doc.add_paragraph(text)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_after = Pt(0)

    if resume.summary:
        _docx_heading(doc, "Summary")
        doc.add_paragraph(resume.summary).paragraph_format.space_after = Pt(0)
    if resume.skills:
        _docx_heading(doc, "Skills")
        for group in resume.skills:
            _docx_line(doc, f"{group.category}: ", ", ".join(group.skills))
    if resume.experience:
        _docx_heading(doc, "Experience")
        for job in resume.experience:
            meta = " | ".join(p for p in (job.dates, job.location) if p)
            _docx_line(doc, job.title, f", {job.company}", f"   {meta}" if meta else "")
            _docx_bullets(doc, job.bullets)
    if resume.projects:
        _docx_heading(doc, "Projects")
        for project in resume.projects:
            _docx_line(doc, project.name, "", f"   {project.tech}" if project.tech else "")
            _docx_bullets(doc, project.bullets)
    if resume.education:
        _docx_heading(doc, "Education")
        for edu in resume.education:
            tail = " | ".join(p for p in (edu.dates, edu.details) if p)
            _docx_line(doc, edu.degree, f", {edu.school}", f"   {tail}" if tail else "")
    if resume.certifications:
        _docx_heading(doc, "Certifications")
        _docx_bullets(doc, resume.certifications)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


# ---------- PDF ----------

_PDF_REPLACEMENTS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "•": "-", "·": "-",
    "…": "...", " ": " ", "→": "->",
}


def _latin(text: str) -> str:
    """The built-in PDF fonts only cover Latin-1; map common typography, drop the rest."""
    for src, dst in _PDF_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "ignore").decode("latin-1")


class _ResumePDF(FPDF):
    def heading(self, text: str) -> None:
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, _latin(text.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(70, 70, 70)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1.5)

    def text_block(self, text: str, style: str = "", size: float = 10, align: str = "L") -> None:
        self.set_font("Helvetica", style, size)
        self.multi_cell(0, 5, _latin(text), align=align, new_x="LMARGIN", new_y="NEXT")

    def entry(self, bold: str, rest: str, meta: str) -> None:
        self.set_font("Helvetica", "B", 10)
        self.write(5, _latin(bold))
        self.set_font("Helvetica", "", 10)
        self.write(5, _latin(rest))
        self.ln(5)
        if meta:
            self.text_block(meta, style="I", size=9)

    def bullets(self, items: list[str]) -> None:
        self.set_font("Helvetica", "", 10)
        for item in items:
            self.set_x(self.l_margin + 3)
            self.multi_cell(0, 5, _latin(f"- {item}"), align="L", new_x="LMARGIN", new_y="NEXT")


def to_pdf(resume: Resume, contact: dict) -> bytes:
    pdf = _ResumePDF(format="A4")
    pdf.set_margins(16, 14, 16)
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    pdf.text_block(resume.full_name, style="B", size=20, align="C")
    if resume.headline:
        pdf.text_block(resume.headline, size=11, align="C")
    line = contact_line(resume, contact)
    if line:
        pdf.text_block(line, size=9, align="C")

    if resume.summary:
        pdf.heading("Summary")
        pdf.text_block(resume.summary)
    if resume.skills:
        pdf.heading("Skills")
        for group in resume.skills:
            pdf.entry(f"{group.category}: ", ", ".join(group.skills), "")
    if resume.experience:
        pdf.heading("Experience")
        for job in resume.experience:
            pdf.entry(job.title, f", {job.company}", " | ".join(p for p in (job.dates, job.location) if p))
            pdf.bullets(job.bullets)
            pdf.ln(1.5)
    if resume.projects:
        pdf.heading("Projects")
        for project in resume.projects:
            pdf.entry(project.name, "", project.tech)
            pdf.bullets(project.bullets)
            pdf.ln(1.5)
    if resume.education:
        pdf.heading("Education")
        for edu in resume.education:
            pdf.entry(edu.degree, f", {edu.school}", " | ".join(p for p in (edu.dates, edu.details) if p))
    if resume.certifications:
        pdf.heading("Certifications")
        pdf.bullets(resume.certifications)

    return bytes(pdf.output())
