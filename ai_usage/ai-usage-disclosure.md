# AI Usage Disclosure

**AlchemyX / AlchemAI — SLIIT Codefest 2026 AI Competition, Sub-track 1C: Searching the Way a Human Does**

This document discloses how AI tools were used during the development of this project, as required by the competition's AI Usage Policy. Full exported chat logs are preserved, unmodified, in this `ai_usage/` directory.

## How AI Was Used

AI tools were used as development assistants for: code review and debugging, edge-case testing, prompt refinement, architecture discussion, failure analysis, integration support, and documentation preparation.

Core engineering decisions and implementation remained under team control. The retrieval architecture, sufficiency and stopping logic, evidence handling, ingestion workflow, and overall system design were designed and implemented by the team, with AI used to explore alternatives, catch bugs, and stress-test our own reasoning — not to generate the solution for us.

Below, each team member's usage is described with specific examples from their logs, not just a general statement of tool use.

---

## Shihaz Shaheem — Retrieval & Re-query

**AI tools used:** Claude, ChatGPT, Codex

**Specific examples of AI-assisted work:**
- Used Claude in a step-by-step, Socratic format to build the retrieval pipeline (chunking, Voyage embeddings, ChromaDB integration) — asked to trace and reason through bugs before being given fixes, rather than being handed working code.
- Independently caught and fixed a bug where a single shared embedding function was being used for both document storage and query embedding, causing a Voyage `input_type` mismatch that silently degraded retrieval quality.
- Identified and fixed a bug in the chunking function where a small trailing text fragment could be left as its own low-content chunk; implemented a fix that merges undersized trailing chunks into the previous chunk instead.
- Used ChatGPT to debug a performance issue where the system was re-embedding the entire document corpus on every query instead of embedding once at ingestion; identified and fixed this after ChatGPT asked a clarifying question about what was actually being re-embedded.
- Validated the choice of cosine similarity over ChromaDB's default L2 distance metric by empirically testing both and comparing separation between relevant and irrelevant query results.


Folder: `Shihaz's chatlogs/` (`codex sessions/`, `Shihaz-chatgpt.md`, `Shihaz-claude.md`)

---

## Sisindu Hemasinghe — Sufficiency & Stopping Logic

**AI tools used:** Gemini

**Specific examples of AI-assisted work:**
- Explicitly instructed Gemini not to write code first, asking instead: *"Give me failure cases and design questions I should answer myself"* — used AI to scaffold his own design reasoning before implementation, not to generate the sufficiency-checker outright.
- Used this process to identify concrete failure modes before writing code: the "premature sufficiency" trap (stopping on surface keyword matches without true multi-hop resolution), the "infinite loop" trap (vague missing-information descriptions causing repeated identical re-queries), and structured-output/hallucination risks specific to a fictional, closed-world corpus where the model cannot fall back on general knowledge.
- Used AI-suggested design questions (e.g., cumulative vs. incremental context across loop iterations, stagnation detection for early stopping) to inform the final `SufficiencyChecker` and `AgentLoop` implementation, which the team then built and tested independently.

Folder: `Sisindu's chatlogs/Sisindu.md`

---

## Lowaga Rajapaksha — Corpus & Ingestion

**AI tools used:** ChatGPT

**Specific examples of AI-assisted work:**
- Directed ChatGPT explicitly to act as a step-by-step coding assistant rather than generating a complete ingestion script: *"Do not write the full script for me at once. I will ask you for specific logic, syntax, and debugging help step-by-step."*
- Used AI to evaluate library choices (PyMuPDF vs. pdfplumber vs. pypdf vs. OCRmyPDF) and settled on a PyMuPDF + Tesseract OCR-fallback design, explicitly rejecting a naive "OCR everything" approach in favor of per-page detection of whether OCR is actually needed.
- Fixed a real Windows-specific `pytesseract` PATH configuration error with AI guidance, and updated a deprecated `fitz` import to the current `pymupdf` API after encountering a deprecation warning during testing.
- Iterated on chunking logic with AI assistance to move from naive word-count splitting to sentence-boundary-aware chunking, specifically to avoid cutting sentences mid-thought across chunk boundaries.

Folder: `Lowaga's chatlogs/Lowaga.md`

---

## Sakitha Palliyaguru — UI, Demo & Documentation

**AI tools used:** ChatGPT

**Specific examples of AI-assisted work:**
- Used AI to translate and explain the three competition sub-tracks (1A/1B/1C) in Sinhala during early planning, to support team decision-making on which sub-track to pursue.
- Used AI to convert an initial React frontend into a Streamlit implementation after the team identified that connecting React to the Python backend would require building a separate API layer, which was judged too high-risk given the remaining timeline.
- Debugged and fixed a real rendering issue where raw HTML/CSS wrapper markup was appearing on-screen instead of rendering correctly, while explicitly preserving the existing theme and layout rather than accepting a full redesign.
- Worked through wiring the Streamlit UI to the actual backend (`AgentLoop`, `SufficiencyChecker`, `HybridRerankRetrievalPipeline`, `AnswerGenerator`) after initially building against a placeholder/demo adapter function, replacing mock data with real system calls.

Folder: `Sakitha's chatlogs/Sakitha.md`

---

## Notes

- All logs in this directory are preserved unmodified as originally exported.
- Logs are included for transparency and AI-use disclosure; some conversations were conducted in Sinhala, with English summaries of key decisions provided above.
- The presence of an AI suggestion in a log does not mean it was directly adopted — AI-generated suggestions were reviewed, tested, modified, or rejected by the team before being incorporated into the project. Several examples above (input_type mismatch, chunking fragment bug, deprecated import) were bugs the team identified and fixed themselves, sometimes with AI assistance in diagnosis and sometimes independently.
- Final architectural decisions, implementation choices, testing, and validation remained under team control throughout.

## Directory Structure

```text
ai_usage/
├── ai-usage-disclosure.md          (this file)
├── Lowaga's chatlogs/
│   └── Lowaga.md
├── Sakitha's chatlogs/
│   └── Sakitha.md
├── Shihaz's chatlogs/
│   ├── Shihaz-chatgpt.md
│   └── Shihaz-claude.md
└── Sisindu's chatlogs/
|   └── Sisindu.md
└── Codex sessions /
```
