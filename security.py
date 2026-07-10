"""
Input validation and prompt injection screening for resume and job description text.

Resumes and job descriptions are user-controlled text that gets fed straight into
LLM prompts. This module adds a first line of defense: length limits, basic
sanitization, and a heuristic scan for common prompt injection phrases.
"""
import re
from typing import List, Tuple

MAX_RESUME_CHARS = 20_000
MAX_JD_CHARS = 10_000
MAX_REVISION_CHARS = 1_000

# Common phrases used to try to hijack LLM instructions.
# This is a heuristic screen, not a guarantee. Treat hits as a signal to log
# and review, not an automatic hard block, since real resumes can contain
# words like "system" (Operating Systems) or "instructions" (wrote onboarding
# instructions) without any malicious intent.
INJECTION_PATTERNS = [
    r"ignore (all |any |previous |above |prior |such |these |your )*instructions",
    r"disregard (the |all |any |prior |previous |above )*(system |previous )?(prompt|instructions)",
    r"you are now",
    r"new instructions?\s*:",
    r"system prompt",
    r"act as (if|a|an)",
    r"reveal (your|the) (prompt|instructions)",
    r"<\|.*?\|>",
    r"\[system\]",
    r"do anything now",
]


class InputValidationError(Exception):
    """Raised when input fails hard validation (empty, too long)."""


def sanitize_text(text: str, max_len: int, field_name: str) -> str:
    if not text or not text.strip():
        raise InputValidationError(f"{field_name} cannot be empty.")
    if len(text) > max_len:
        raise InputValidationError(
            f"{field_name} is too long ({len(text)} characters). Max allowed is {max_len}."
        )
    # Strip control chars and zero-width characters sometimes used to smuggle
    # hidden instructions past a human reviewer skimming the text.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\u200b-\u200f]", "", text)
    return text.strip()


def screen_for_injection(text: str) -> List[str]:
    """Return the list of suspicious patterns matched. Empty list means clean."""
    return [p for p in INJECTION_PATTERNS if re.search(p, text, re.IGNORECASE)]


def validate_resume_input(resume: str, job_description: str) -> Tuple[str, str, List[str]]:
    """
    Validate and sanitize both inputs.

    Returns (clean_resume, clean_job_description, warnings).
    Raises InputValidationError on hard failures (empty or too long).
    """
    resume = sanitize_text(resume, MAX_RESUME_CHARS, "Resume")
    job_description = sanitize_text(job_description, MAX_JD_CHARS, "Job description")

    warnings = screen_for_injection(resume) + screen_for_injection(job_description)
    return resume, job_description, warnings


def validate_revision_request(revision_request: str) -> Tuple[str, List[str]]:
    """
    Validate and sanitize a section revision request.
    Returns (clean_request, warnings). Raises InputValidationError on hard failures.
    """
    revision_request = sanitize_text(revision_request, MAX_REVISION_CHARS, "Revision request")
    warnings = screen_for_injection(revision_request)
    return revision_request, warnings
