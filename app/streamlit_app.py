"""Minimal Streamlit frontend for AlchemyX."""

import sys
from pathlib import Path

import streamlit as st
import sys
import os

st.write("Python:", sys.executable)
st.write("Working directory:", os.getcwd())
st.write("Voyage key loaded:", bool(os.getenv("VOYAGE_API_KEY")))
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
ADAPTER_ROOT = SRC_ROOT / "alchemyx"
sys.path.insert(0, str(ADAPTER_ROOT))
sys.path.insert(0, str(SRC_ROOT))

from backend_adapter import run_research, search_archive


st.set_page_config(page_title="AlchemAI", page_icon="A", layout="wide")


def render_sources(sources):
    st.subheader("Retrieved Sources")
    if not sources:
        st.info("No sources were retrieved.")
        return

    for index, source in enumerate(sources, start=1):
        title = source.get("source_doc", "Unknown document")
        chunk = source.get("chunk_index", "unknown")
        score = source.get("score", 0.0)
        excerpt = source.get("excerpt") or source.get("text", "")
        with st.expander(f"{index}. {title} | chunk {chunk} | score {score:.3f}"):
            st.write(excerpt)


def render_timeline(steps):
    st.subheader("Research Timeline")
    if not steps:
        st.info("No timeline steps were returned.")
        return

    for index, step in enumerate(steps, start=1):
        title = step.get("title", f"Step {index}")
        description = step.get("description", "")
        meta = step.get("meta", "")
        st.write(f"**{index}. {title}**")
        if description:
            st.caption(description)
        if meta:
            st.caption(meta)


def render_research_page():
    st.title("AlchemAI")
    st.write("Agentic Research Assistant by AlchemyX")

    with st.form("research_form"):
        question = st.text_area(
            "Question",
            placeholder="Ask a question about your indexed archive...",
            height=120,
        )
        submitted = st.form_submit_button("Ask question", type="primary")

    if submitted:
        if not question.strip():
            st.session_state.pop("research_result", None)
            st.warning("Please enter a question before submitting.")
        else:
            try:
                with st.spinner("Researching..."):
                    st.session_state["research_result"] = run_research(question.strip())
                    st.session_state["research_question"] = question.strip()
            except Exception as exc:
                st.exception(exc)
                st.stop()

    st.subheader("Example questions")
    for example in (
        "Who did Caldrin escort?",
        "What happened during the Night of Falling Bells?",
        "Which factions were affected by the Northern Accord?",
    ):
        st.write(f"- {example}")

    result = st.session_state.get("research_result")
    if not result:
        return

    st.divider()
    st.subheader("Final Answer")
    st.write(result.get("answer", "No answer was returned."))

    metrics = st.columns(5)
    metrics[0].metric("Iterations", result.get("iterations", 0))
    metrics[1].metric("Sufficiency", "Yes" if result.get("sufficient") else "No")
    metrics[2].metric("Stop reason", result.get("stop_reason", "Unknown"))
    metrics[3].metric("Sources", result.get("sources_retrieved", 0))
    metrics[4].metric(
        "Question",
        result.get("question", st.session_state.get("research_question", "")),
    )

    render_timeline(result.get("steps", []))
    render_sources(result.get("sources", []))


def render_archive_page():
    st.title("Explore Archive")
    st.write("Search the existing Chroma and BM25 indexes.")

    with st.form("archive_search_form"):
        query = st.text_input("Search query", placeholder="Search the archive...")
        submitted = st.form_submit_button("Search archive", type="primary")

    if submitted:
        if not query.strip():
            st.warning("Please enter a search query.")
        else:
            try:
                with st.spinner("Searching archive..."):
                    results = search_archive(query.strip(), top_k=5)
            except Exception as exc:
                st.exception(exc)
                st.stop()

            st.subheader("Search Results")
            if not results:
                st.info("No matching evidence was found.")
            for index, result in enumerate(results, start=1):
                document = result.get("source_doc", "Unknown document")
                chunk = result.get("chunk_index", "unknown")
                score = result.get("score", 0.0)
                st.markdown(f"**{index}. {document}** | chunk {chunk} | score {score:.3f}")
                st.write(result.get("text", ""))


page = st.sidebar.radio("Page", ["Research", "Explore Archive"])
if page == "Research":
    render_research_page()
else:
    render_archive_page()
