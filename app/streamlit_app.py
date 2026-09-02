"""Minimal Streamlit frontend for AlchemyX."""

import json
import sys
from pathlib import Path

import streamlit as st
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
ADAPTER_ROOT = SRC_ROOT / "alchemyx"
sys.path.insert(0, str(ADAPTER_ROOT))
sys.path.insert(0, str(SRC_ROOT))

from backend_adapter import run_research, search_archive


st.set_page_config(page_title="AlchemAI", page_icon="A", layout="wide")


def status_badge(label):
    st.caption(f"`{label}`")


def format_seconds(value):
    if value is None:
        return "n/a"
    return f"{value:.1f}s"


def render_sources(sources):
    with st.expander("Evidence & Sources", expanded=False):
        if not sources:
            st.info("No sources were retrieved.")
            return

        for source in sources:
            role = source.get("role", "supporting").replace("_", " ").title()
            title = source.get("title", "Unknown document")
            st.markdown(f"**{title}**")
            cols = st.columns([1, 1, 1, 1])
            cols[0].caption(f"Type: {source.get('document_type', 'Document')}")
            cols[1].caption(f"Role: {role}")
            cols[2].caption(f"Authority: {source.get('authority_assessment', 'Available evidence')}")
            cols[3].caption(f"Chunks: {source.get('chunks', 0)}")
            st.caption(f"Entity match: {source.get('entity_match', 'Unknown')}")
            formats = ", ".join(source.get("formats", [])) or "Unknown"
            st.caption(f"Formats: {formats}")
            if source.get("claim"):
                st.caption(f"Claim: {source['claim']}")
            if source.get("authority_summary"):
                st.write(source["authority_summary"])
            elif source.get("reason"):
                st.write(source["reason"])
            if source.get("excerpt"):
                st.caption(source["excerpt"])
            st.divider()


def render_context_sources(result):
    related_sources = result.get("related_sources", [])
    excluded_sources = result.get("excluded_sources", [])
    if related_sources:
        with st.expander("Related But Not Used", expanded=False):
            for source in related_sources:
                st.markdown(f"**{source.get('title', 'Unknown document')}**")
                st.caption(f"Entity match: {source.get('entity_match', 'Related')}")
                if source.get("excerpt"):
                    st.caption(source["excerpt"])
    if excluded_sources:
        with st.expander("Excluded Evidence", expanded=False):
            st.caption("These retrieved chunks were not used as direct evidence.")
            for source in excluded_sources:
                st.markdown(f"**{source.get('title', 'Unknown document')}**")
                st.caption(f"Entity match: {source.get('entity_match', 'Excluded')}")


def render_timeline(timeline):
    st.subheader("Research Timeline")
    if not timeline:
        st.info("No timeline was returned.")
        return

    for entry in timeline:
        iteration = entry.get("iteration", "?")
        title = f"Iteration {iteration}"
        if entry.get("stop_reason_label"):
            title += f" - Stopped: {entry['stop_reason_label']}"
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(f"Query: {entry.get('query', '')}")
            cols = st.columns(5)
            cols[0].metric("Retrieved", entry.get("retrieved", 0))
            cols[1].metric("Reranked", entry.get("reranked", 0))
            cols[2].metric("Distinct sources", entry.get("distinct_sources", 0))
            cols[3].metric("Conflict", entry.get("conflict_status", "None"))
            cols[4].metric("Sufficiency", entry.get("sufficiency_label", "No"))
            if entry.get("candidate_values"):
                st.caption("Candidate answers: " + ", ".join(entry["candidate_values"]))
            if entry.get("missing"):
                st.caption("Missing: " + "; ".join(entry["missing"]))
            if entry.get("new_evidence_summary"):
                st.caption(entry["new_evidence_summary"])
            if entry.get("next_queries"):
                st.caption("Next search: " + "; ".join(entry["next_queries"]))


def render_conflict_panel(conflict):
    if not conflict or not conflict.get("detected"):
        return

    with st.expander("Why This Answer Won", expanded=True):
        st.markdown("**Competing claims**")
        for claim in conflict.get("competing_claims", []):
            sources = ", ".join(claim.get("sources", [])) or "Retrieved evidence"
            st.caption(f"{claim.get('value', 'Unknown')} - {sources}")
        if conflict.get("resolution_summary"):
            st.markdown("**Resolution**")
            st.write(conflict["resolution_summary"])
        if conflict.get("selected_value"):
            st.markdown("**Selected answer**")
            st.write(conflict["selected_value"])


def render_performance(timings):
    with st.expander("Performance", expanded=False):
        if not timings:
            st.info("No timing data was returned.")
            return
        rows = [
            ("Entity extraction", timings.get("entity_extraction")),
            ("Entity validation", timings.get("entity_validation")),
            ("Retrieval", timings.get("retrieval")),
            ("Reranking", timings.get("reranking")),
            ("Sufficiency", timings.get("sufficiency")),
            ("Adjudication", timings.get("adjudication")),
            ("Follow-up query generation", timings.get("followup_query_generation")),
            ("Agent loop total", timings.get("agent_loop")),
            ("Final generation", timings.get("final_generation")),
            ("End-to-end total", timings.get("end_to_end")),
        ]
        for label, value in rows:
            if value is None:
                st.caption(f"{label}: unavailable")
            else:
                st.caption(f"{label}: {value:.2f}s")


def render_technical_details(result):
    with st.expander("Technical Details", expanded=False):
        st.caption(f"Research run: {result.get('research_run_id', '')}")
        st.caption(f"Internal stop reason: {result.get('stop_reason', '')}")
        st.caption(f"Chunks retrieved: {result.get('chunks_retrieved', 0)}")
        technical_sources = result.get("technical_sources", [])
        if technical_sources:
            st.code(
                json.dumps(
                    [
                        {
                            "id": source.get("id"),
                            "source_doc": source.get("source_doc"),
                            "chunk_index": source.get("chunk_index"),
                            "score": source.get("score"),
                        }
                        for source in technical_sources
                    ],
                    indent=2,
                ),
                language="json",
            )


def render_research_page():
    st.title("AlchemAI")
    st.write("Agentic Research Assistant by AlchemyX")

    with st.form("research_form", clear_on_submit=False):
        question = st.text_area(
            "Question",
            placeholder="Ask a question about your indexed archive...",
            height=120,
        )
        submitted = st.form_submit_button(
            "Ask question",
            type="primary",
            disabled=st.session_state.get("research_in_progress", False),
        )

    if submitted:
        if not question.strip():
            st.session_state.pop("research_result", None)
            st.warning("Please enter a question before submitting.")
        else:
            try:
                st.session_state["research_in_progress"] = True
                with st.spinner("Researching..."):
                    result = run_research(question.strip())
                st.session_state["research_result"] = result
                st.session_state["research_question"] = question.strip()
            except Exception as exc:
                st.exception(exc)
                st.stop()
            finally:
                st.session_state["research_in_progress"] = False


    result = st.session_state.get("research_result")
    if not result:
        return

    st.divider()
    st.subheader("Final Answer")
    st.write(result.get("clean_answer") or result.get("answer", "No answer was returned."))

    conflict = result.get("conflict", {})
    timings = result.get("timings", {})
    metrics = st.columns(6)
    metrics[0].metric("Iterations", result.get("iterations", 0))
    metrics[1].metric("Sufficiency", "Yes" if result.get("sufficient") else "No")
    metrics[2].metric("Conflict", conflict.get("status", "None"))
    metrics[3].metric("Sources", result.get("sources_retrieved", 0))
    metrics[4].metric("Total Time", format_seconds(timings.get("end_to_end")))
    metrics[5].metric("Stop Reason", result.get("stop_reason_label", "Unknown"))

    render_timeline(result.get("timeline", []))
    render_conflict_panel(conflict)
    render_sources(result.get("sources", []))
    render_context_sources(result)
    render_performance(timings)
    render_technical_details(result)


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
                score = result.get("rank_score", result.get("score", 0.0))
                st.markdown(
                    f"**{index}. {document}** | chunk {chunk} | "
                    f"rank score {score:.3f}"
                )
                st.write(result.get("text", ""))


page = st.sidebar.radio("Page", ["Research", "Explore Archive"])
if page == "Research":
    render_research_page()
else:
    render_archive_page()
