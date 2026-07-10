# AI Resume Enhancer

A multi-agent AI tool that analyzes a resume, generates a tailored CV, and writes a personalized cover letter based on a job description. Built with CrewAI, Gemini, and Streamlit.

## What it does

You upload a resume (`.txt` or `.docx`) and paste in a job description. Three AI agents work in sequence:

1. **Resume Analyzer** reviews the resume for strengths, weaknesses, grammar issues, and gives actionable feedback.
2. **CV Generator** produces a professional CV tailored to the resume and the target job description.
3. **Cover Letter Generator** writes a formal cover letter under 450 words, tailored to the role.

The app runs entirely through a Streamlit UI. Upload, click a button, and get all three outputs. You can then request a revision to any section, or download the CV and cover letter as `.docx` files.

## Features

- **Resume upload**: `.txt`, `.docx`, and `.pdf` (text-based PDFs; scanned/image PDFs are not OCR'd)
- **AI analysis, CV, and cover letter generation** tailored to a job description
- **Section revisions**: request a targeted change to any section (e.g. "make this more concise") without regenerating everything from scratch
- **Download as Word documents**: export the generated CV and cover letter as `.docx` files

## Architecture

```
app.py              Streamlit UI: file upload, input handling, results display, revision UI
crew_setup.py        CrewAI agents, tasks, LLM configuration, and section revision logic
security.py           Input validation and prompt injection screening
document_export.py    Builds downloadable .docx files from generated text
test_security.py      Test suite measuring detection rate and false positive rate
```

Each agent runs with `allow_delegation=False`, so no agent can spawn sub-tasks or hand off work to another agent outside its defined role. This keeps the blast radius small if any single agent misbehaves.

## Why input handling matters here

Resume text and job descriptions are user-controlled input that gets fed directly into LLM prompts. That's a prompt injection surface: a malicious resume could contain text designed to override the AI's instructions rather than actually being a resume.

This project handles that with a few layers:

- **Length and empty-input validation** before anything reaches the LLM.
- **Delimiter fencing**: resume and job description text are wrapped in explicit markers (`<<<DATA_START>>>` / `<<<DATA_END>>>`), and every task tells the model to treat that content as data, not as instructions.
- **Heuristic screening**: a lightweight pattern check flags common injection phrases (e.g. "ignore previous instructions") and logs them for review, without hard-blocking legitimate resumes that happen to contain overlapping words.
- **No tool access for agents**: none of the agents can browse the web, run code, or touch the file system, so even a successful injection is limited to producing bad text, not taking real actions.

This isn't a claim that prompt injection is fully solved (it isn't, industry-wide), just that the app follows a defense-in-depth approach in line with OWASP's LLM Top 10 guidance on prompt injection.

## Setup

1. Clone the repo and install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your Gemini API key:
   ```
   cp .env.example .env
   ```
3. Run the app:
   ```
   streamlit run app.py
   ```

## Tech stack

- **CrewAI** for multi-agent orchestration
- **Google Gemini** as the underlying LLM
- **Streamlit** for the UI
- **python-docx** for parsing `.docx` resumes

