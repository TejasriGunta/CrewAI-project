import logging
from typing import Optional

import streamlit as st
from docx import Document
from pypdf import PdfReader

from crew_setup import resume_enhancer_crew, revise_section
from security import (
    validate_resume_input,
    validate_revision_request,
    InputValidationError,
)
from document_export import build_cv_docx, build_cover_letter_docx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.title("🚀 AI Resume Enhancer with CV and Cover Letter Generator")
st.markdown("Enhance your resume and generate personalized cover letters using AI.")

uploaded_resume = st.file_uploader(
    "📄 Upload Resume (Text, Docx, or PDF)", type=["txt", "docx", "pdf"]
)
job_description = st.text_area("📝 Enter your Job Description")


@st.cache_data(show_spinner=False)
def read_resume(file) -> Optional[str]:
    if file.name.endswith(".txt"):
        return file.read().decode("utf-8", errors="ignore")
    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(para.text for para in doc.paragraphs)
    elif file.name.endswith(".pdf"):
        reader = PdfReader(file)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    return None


def _init_session_state():
    for key in ("analysis_text", "cv_text", "cover_letter_text", "candidate_name"):
        if key not in st.session_state:
            st.session_state[key] = ""


_init_session_state()

if st.button("🚀 Enhance Resume & Generate Cover Letter"):
    if not uploaded_resume or not job_description:
        st.warning("⚠️ Please upload a resume and provide a job description.")
        st.stop()

    resume_text = read_resume(uploaded_resume)
    if not resume_text or not resume_text.strip():
        st.error(
            "Could not read text from the uploaded file. If this is a scanned "
            "or image-based PDF, please upload a text-based resume instead."
        )
        st.stop()

    try:
        clean_resume, clean_jd, warnings = validate_resume_input(resume_text, job_description)
    except InputValidationError as e:
        st.error(f"⚠️ {e}")
        st.stop()

    if warnings:
        # Log, don't hard-block — heuristics can false-positive on normal
        # resume language. This is a monitoring signal, not a gate.
        logger.warning("Injection screen flagged input, patterns: %s", warnings)

    st.info("⏳ Processing... Please wait.")

    try:
        result = resume_enhancer_crew.kickoff(inputs={
            "resume": clean_resume,
            "job_description": clean_jd,
        })
    except Exception:
        logger.exception("Crew execution failed")
        st.error("Something went wrong while generating your results. Please try again.")
        st.stop()

    tasks_output = result.tasks_output
    st.session_state.analysis_text = tasks_output[0].raw
    st.session_state.cv_text = tasks_output[1].raw
    st.session_state.cover_letter_text = result.raw
    st.session_state.candidate_name = "Candidate"  # placeholder; refine if resume parsing extracts a name


def render_section(section_key: str, section_label: str, section_name_for_llm: str):
    """Renders a section's text plus a revision request box that regenerates it."""
    st.subheader(section_label)
    st.write(st.session_state[section_key])

    with st.expander(f"✏️ Request a revision to {section_label}"):
        revision_input = st.text_area(
            "What would you like changed?",
            key=f"revision_input_{section_key}",
            placeholder="e.g. make the tone more concise, emphasize leadership experience",
        )
        if st.button(f"Apply revision to {section_label}", key=f"revise_btn_{section_key}"):
            if not revision_input.strip():
                st.warning("Please describe what you'd like changed.")
            else:
                clean_request = None
                try:
                    clean_request, warnings = validate_revision_request(revision_input)
                except InputValidationError as e:
                    st.error(f"⚠️ {e}")

                if clean_request:
                    if warnings:
                        logger.warning("Injection screen flagged revision request: %s", warnings)
                    with st.spinner("Revising..."):
                        try:
                            revised = revise_section(
                                section_name_for_llm,
                                st.session_state[section_key],
                                clean_request,
                            )
                            st.session_state[section_key] = revised
                            st.rerun()
                        except Exception:
                            logger.exception("Section revision failed")
                            st.error("Could not apply the revision. Please try again.")


if st.session_state.cv_text:
    st.header("AI Resume Enhancement Results")

    render_section("analysis_text", "Analysis", "resume analysis")
    render_section("cv_text", "CV", "CV")
    render_section("cover_letter_text", "Cover Letter", "cover letter")

    st.divider()
    st.subheader("📥 Download")

    col1, col2 = st.columns(2)
    with col1:
        cv_buffer = build_cv_docx(st.session_state.candidate_name, st.session_state.cv_text)
        st.download_button(
            "Download CV (.docx)",
            data=cv_buffer,
            file_name="cv.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with col2:
        cl_buffer = build_cover_letter_docx(
            st.session_state.candidate_name, st.session_state.cover_letter_text
        )
        st.download_button(
            "Download Cover Letter (.docx)",
            data=cl_buffer,
            file_name="cover_letter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
