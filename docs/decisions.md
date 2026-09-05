# AlchemAI Architecture Decisions

This register records the main design decisions visible in the current codebase and project direction. Entries are grouped by impact and include the rationale and operational consequences of each decision.

## Major Decisions

### [MAJOR] Use Retrieval-Augmented Generation Over Direct LLM Answering

AlchemAI answers questions from an indexed local corpus. Retrieved evidence is passed into sufficiency checking, conflict analysis, and final answer generation before the UI displays a result.

**Rationale:** The system is intended to answer archive-specific questions with source-grounded evidence rather than relying on model memory.

**Impact:** Answer quality is bounded by corpus completeness, extraction quality, index freshness, retrieval ranking, and evidence selection.

### [MAJOR] Keep Streamlit as the User-Facing Application Layer

The interactive application is implemented in `app/streamlit_app.py` with a Research page and an Explore Archive page.

**Rationale:** Streamlit gives the project a simple Python-native interface for local research, form submission, session state, and diagnostic rendering.

**Impact:** Request handling remains synchronous, Streamlit reruns the script on interaction, and multi-user or production serving concerns are outside the UI's current scope.

### [MAJOR] Separate UI Adaptation From Core Domain Logic

The UI calls adapter functions from `src/alchemyx/backend_adapter.py`; the core orchestration remains in `src/alchemyx/main.py`, `src/alchemyx/agent`, `src/alchemyx/retrieval`, `src/alchemyx/ingestion`, and `src/alchemyx/generation`.

**Rationale:** The UI should consume stable dictionaries and avoid direct dependency on retrieval objects, LLM schemas, or infrastructure internals.

**Impact:** UI changes are mostly handled in the adapter and Streamlit page, while the core `AlchemyXSystem.ask(question)` contract remains stable.

### [MAJOR] Preserve the Single-Question Core API

The core system still exposes `AlchemyXSystem.ask(question)` and `ask(question)` for one research request at a time.

**Rationale:** Existing callers and tests expect a simple single-question boundary. Conversation behavior should not force disruptive changes into the agent or retrieval stack.

**Impact:** Multi-turn behavior is layered around the existing API instead of replacing it. Each accepted question normally still performs a complete research run.

### [MAJOR] Add Conversation Session History in the Streamlit Layer

The Research page stores completed turns in `st.session_state["research_turns"]`. Each turn keeps the submitted question, effective question, answer, sources, metrics, timeline, and diagnostics.

**Rationale:** Users need to ask another question after an answer without losing the previous question and answer.

**Impact:** Prior turns remain visible in the current browser session, but they are not persisted to disk and disappear when the Streamlit session resets.

### [MAJOR] Use Strict Follow-Up Contextualization Only

`run_conversation_turn()` expands a question with the previous turn only for explicit follow-up phrases such as "what about", "how about", "cite that", "give sources for that", "explain that", or "summarize that".

**Rationale:** Aggressively appending previous answers can slow retrieval and degrade relevance for normal second questions. Standalone questions should run as raw queries.

**Impact:** Explicit follow-ups can use prior context, while ordinary second questions avoid unnecessary long prompts and should behave like first questions.

### [MAJOR] Use Hybrid Semantic and Lexical Retrieval

Retrieval combines Chroma vector search and BM25 lexical search through the hybrid retrieval stack.

**Rationale:** Semantic search supports paraphrase and conceptual matches, while BM25 helps exact names, identifiers, years, and document-specific terms.

**Impact:** Two indexes must be built, maintained, and kept in sync with the same corpus and chunk metadata.

### [MAJOR] Persist Retrieval Indexes Locally

Chroma, BM25, and document-registry data are persisted under configured local paths such as `data/chroma`, `data/bm25.json`, and `data/document_registry.json`.

**Rationale:** Persistent indexes avoid rebuilding embeddings and lexical state on every application start or query.

**Impact:** Stale, missing, or incorrectly located indexes can break startup or produce outdated answers. Re-indexing is required after corpus or chunking changes.

### [MAJOR] Require Explicit Index Build Before Research

`create_agent_retrieval_pipeline()` fails if the BM25 index is empty or the Chroma collection has no documents.

**Rationale:** Research should not silently run against an empty or incomplete retrieval backend.

**Impact:** Users must run the indexing command before starting normal Streamlit research.

### [MAJOR] Use a Bounded Agentic Research Loop

`AgentLoop.run(question)` can iterate through retrieval, sufficiency checking, conflict handling, and follow-up query generation, capped by `MAX_AGENT_ITERATIONS = 4`.

**Rationale:** Iterative retrieval helps when first-pass evidence is incomplete, while a hard cap controls latency and provider cost.

**Impact:** poorly phrased questions may stop before all useful evidence is found.

### [MAJOR] Separate Evidence Selection From Final Generation

`AgentLoop` determines retrieved documents, sufficiency, and conflict state. `AnswerGenerator` then generates the final cited answer from those documents.

**Rationale:** The final generator should not independently broaden the research scope or cite documents that were not retrieved.

**Impact:** Final answer quality depends on the evidence set selected before generation.

### [MAJOR] Make Source Conflicts Explicit

The evidence adjudicator can detect competing claims, record candidate values, track supporting evidence IDs, and mark conflicts as resolved or unresolved.

**Rationale:** The archive can contain contradictory sources. The system should surface disagreement instead of hiding it behind a single unsupported answer.

**Impact:** Some answers correctly remain unresolved when the retrieved evidence does not justify choosing one claim.

## Moderate Decisions

### [MODERATE] Use MiniMax M3 for Reasoning-Oriented LLM Work

MiniMax M3 was selected as the OpenRouter model for the reasoning-heavy parts of the system after trying alternatives.

**Rationale:** It performed well for reasoning, sufficiency judgment, conflict handling, and final archive-grounded answers in local testing.

**Impact:** The quality and latency profile depends on MiniMax M3 availability through OpenRouter. If the configured model changes, reasoning behavior should be re-tested.

### [MODERATE] Use Voyage AI for Embeddings and Reranking

Voyage is used for embedding generation and candidate reranking.

**Rationale:** External embedding and reranking models provide stronger semantic matching and relevance ordering than simple lexical search alone.

**Impact:** Retrieval depends on API credentials, network availability, model availability, retries, and provider cost.

### [MODERATE] Use OpenRouter for LLM Calls

OpenRouter is used through a shared `OpenRouterClient` for sufficiency checks, evidence adjudication, follow-up planning, and answer generation.

**Rationale:** A centralized LLM client keeps provider access, model configuration, fallback behavior, and call logging in one path.

**Impact:** Structured outputs remain model-dependent, so parsing, repair, fallback, and diagnostics are required.

### [MODERATE] Share One LLM Client Per System Instance

`create_system()` constructs one `OpenRouterClient` and passes it to the sufficiency checker, evidence adjudicator, and answer generator.

**Rationale:** Shared client state supports consistent configuration and per-run call logging.

**Impact:** The call log must be cleared at the start of each `AlchemyXSystem.ask()` call to keep diagnostics request-scoped.

### [MODERATE] Cache the Constructed Backend System Per Streamlit Process

`get_system()` in the backend adapter uses `lru_cache(maxsize=1)`.

**Rationale:** Streamlit reruns the script frequently; rebuilding clients and reopening indexes on each rerun would add unnecessary latency.

**Impact:** Code changes may require restarting Streamlit, and cached state is process-local rather than distributed.

### [MODERATE] Keep One Backend Call Per Submitted Question

The Streamlit Research form invokes one backend research call when the user submits a non-empty question.

**Rationale:** Form submission should avoid duplicate provider calls during Streamlit reruns.

**Impact:** The UI must manage `research_in_progress`, pending display state, and turn history carefully so a rerun does not repeat a research request.

### [MODERATE] Preserve Submitted Question Visibility During Research

The Research form uses `clear_on_submit=False`, stores `pending_question`, and displays the submitted question above the spinner while research is running.

**Rationale:** Long-running research should not make the user feel that the submitted question disappeared.

**Impact:** The input remains visible during processing and is only cleared when starting a new research session.

### [MODERATE] Store Conversation History Only in Session State

Conversation turns are held in Streamlit session state, not in files, indexes, or a database.

**Rationale:** The current app is a local single-process research tool, and session-scoped history is enough for iterative UI use.

**Impact:** Conversation history is not durable, not shared across users or processes, and not available after session reset.

### [MODERATE] Use Previous Conversation Context Only as Query Text

When an explicit follow-up is detected, the adapter builds an effective question containing the previous question, previous answer, and the new follow-up question. It still calls the normal `run_research()` path.

**Rationale:** This adds basic follow-up support without changing retrieval interfaces or requiring a memory database.

**Impact:** Follow-ups may still incur full retrieval and LLM latency. Previous evidence is not yet reused as a local fast path.

### [MODERATE] Keep the Agent Retrieval Contract Narrow

The agent-facing retrieval object provides `.query(text)` and optional contextual/adjudication query methods while returning typed retrieval results.

**Rationale:** A narrow contract lets retrieval internals evolve without forcing the agent loop or callers to change.

**Impact:** Custom retrieval implementations must return compatible result objects with IDs, text, source document, chunk index, and score.

### [MODERATE] Use Reciprocal-Rank Fusion

Semantic and lexical candidates are merged with reciprocal-rank fusion using `RRF_K = 60`.

**Rationale:** RRF combines independent rankings without requiring vector scores and BM25 scores to use the same scale.

**Impact:** Ranking behavior depends on both retrieval branches and the fusion constant.

### [MODERATE] Use Tested Retrieval Breadth Settings

The retrieval configuration was tried with different chunking and retrieval breadth settings, then finalized with `DEFAULT_CHUNK_SIZE = 120`, `DEFAULT_CHUNK_OVERLAP = 40`, and `RERANK_CANDIDATES = 40`.

**Rationale:** The selected settings gave a practical balance between enough context, stable retrieval, and manageable latency for the archive corpus.

**Impact:** Changing these values should trigger re-indexing and retrieval-quality testing because chunk boundaries and candidate breadth directly affect answer quality.

### [MODERATE] Overfetch Before Reranking

The agent retrieval pipeline requests up to `RERANK_CANDIDATES = 40` hybrid candidates, reranks them, filters with `MIN_RERANK_SCORE = 0.5`, and returns `RETRIEVAL_TOP_K = 5` final results.

**Rationale:** Reranking needs enough candidate breadth to find useful evidence that may not rank in the first few hybrid results.

**Impact:** Higher candidate counts can improve relevance but increase reranking latency and provider usage.

### [MODERATE] Expand Candidate Breadth During Adjudication

`query_for_adjudication()` increases candidate and result counts, then prefers source diversity.

**Rationale:** Conflict resolution needs broader and more diverse evidence than ordinary answer lookup.

**Impact:** Adjudication queries can be slower than normal retrieval but are better suited to resolving source disagreement.

### [MODERATE] Treat Ingestion as the Owner of Canonical Chunking

Documents are extracted and chunked in the ingestion path before being written to vector and lexical indexes.

**Rationale:** Chroma and BM25 should use the same chunk boundaries and metadata.

**Impact:** Changes to chunking parameters require re-indexing affected documents.

### [MODERATE] Use Metadata-Enriched Search Text

BM25 documents include searchable text built from content and metadata, while preserving raw content text and metadata text separately.

**Rationale:** File names, paths, document types, and metadata can be important retrieval signals for archive questions.

**Impact:** Metadata quality affects lexical retrieval and source disambiguation.

### [MODERATE] Replace Existing Source Chunks on Re-Index

The BM25 path uses `replace_documents()` when available, and the retrieval pipeline supports source-level replacement behavior.

**Rationale:** Re-indexing a changed document should not leave stale duplicate chunks behind.

**Impact:** Index refresh behavior depends on stable source document IDs and registry metadata.

### [MODERATE] Use Entity-Aware Evidence Filtering

The agent extracts requested entities, validates retrieved chunks against them, and annotates evidence as exact, alias, contextual, related, ambiguous, mismatch, or unusable.

**Rationale:** Archive corpora can contain similarly named people, places, artifacts, and events. Direct answer evidence should match the requested subject.

**Impact:** Entity-resolution errors can exclude relevant evidence or admit weaker contextual evidence.

### [MODERATE] Keep Follow-Up Queries Retrieval-Only

The agent may change the retrieval query during later iterations, but sufficiency and final generation continue to evaluate the original user question.

**Rationale:** Retrieval can evolve to find missing evidence without changing what the user actually asked.

**Impact:** Follow-up query generation must not accidentally redefine the answer target.

### [MODERATE] Validate Structured LLM Responses

Sufficiency, conflict, and answer-generation responses are expected to parse as structured data and are validated before use.

**Rationale:** The application needs machine-consumable fields such as evidence IDs, missing evidence, candidate values, selected claims, and answer text.

**Impact:** Malformed model output can trigger repair or fallback behavior.

### [MODERATE] Validate Citation IDs and Claim Support

Generated evidence IDs must belong to supplied documents, bracketed citations are checked, and cited claims are tested for lexical support.

**Rationale:** The UI should not display fabricated evidence IDs or unsupported citations without detection.

**Impact:** Lexical support is a useful safety heuristic but does not prove semantic correctness.

### [MODERATE] Present Citations as Reader-Friendly Source Numbers

The adapter maps raw evidence chunk IDs to numeric source references such as `[1]`, `[2]`, and `[3]`. The Streamlit answer view shows these numbers inline and renders a simple Sources section with source title, available formats, a short support label, and a short excerpt.

**Rationale:** Readers should be able to connect an answer claim to its source without reading raw chunk IDs, rerank scores, retrieval metadata, or internal file paths.

**Impact:** Reader-facing citations are concise and stable within a single answer. Full chunk IDs, scores, source document paths, and retrieval diagnostics remain available in Technical Details for debugging and evaluation.

### [MODERATE] Keep Technical Citation Metadata Out of the Main Source View

The normal Sources section avoids retrieval internals such as chunk IDs, rank scores, entity-match diagnostics, and run IDs. Related and excluded evidence remain separated from the direct evidence list.

**Rationale:** The main answer view should be optimized for comprehension, while technical metadata should remain inspectable without cluttering the reading path.

**Impact:** The UI becomes cleaner for normal readers, but developers and evaluators must open Technical Details to inspect the exact chunks and scores behind a citation.

### [MODERATE] Surface Evidence Visibility Classes in the UI

The adapter groups chunks into source families and separates evidence, related/contextual sources, and excluded sources.

**Rationale:** Users need to distinguish selected support from retrieved-but-unused context and excluded evidence.

**Impact:** UI source counts and panels reflect adapter visibility rules rather than raw retrieval count alone.

### [MODERATE] Keep Explore Archive Separate From Agentic Research

The Explore Archive page calls retrieval directly and shows top chunks without sufficiency checks, conflict analysis, or final generation.

**Rationale:** Users need a diagnostic view of the underlying indexes independent of the full agent workflow.

**Impact:** Explore results are search results, not final answers.

## Minor Decisions

### [MINOR] Load Configuration From the Project-Root `.env`

`config.py` loads API keys and `ALCHEMYX_CORPUS_PATH` from the repository-root `.env`. Model selections, fallback models, paths, limits, and retry behavior remain in code.

**Rationale:** Secrets should stay outside source code, and the corpus path should be easy to change per machine. Model choices stay code-visible for competition/demo auditability.

**Impact:** Missing `.env` API keys can fail provider initialization. Changing models requires editing `src/alchemyx/config.py`; changing corpus location requires editing `.env`.

### [MINOR] Keep AI Model Selection in `config.py`

Model settings are defined in `src/alchemyx/config.py`: `VOYAGE_MODEL`, `RERANK_MODEL`, `OPENROUTER_MODEL`, and `OPENROUTER_FALLBACK_MODELS`. `.env` contains API keys and corpus path only.

**Rationale:** Keeping model choices in one code configuration file makes competition demos easier to audit and prevents hidden model changes through local environment files.

**Impact:** Changing models requires a code/config edit. Deployments still need `.env` for provider keys.

### [MINOR] Use Default Path Constants and Env Corpus Path

Defaults include collection `alchemyx_docs`, Chroma path `data/chroma`, BM25 path `data/bm25.json`, and registry path `data/document_registry.json`. The corpus path comes from `ALCHEMYX_CORPUS_PATH` in `.env`, falling back to `Archive_test`.

**Rationale:** Local generated data should have predictable code-visible defaults, while the corpus folder needs to be configurable per checkout or demo machine.

**Impact:** Deployments must verify that relative paths resolve to the intended project directory.

### [MINOR] Use Five Final Retrieval Results

`RETRIEVAL_TOP_K = 5`.

**Rationale:** A small final set keeps the evidence context focused for sufficiency checking, generation, and UI review.

**Impact:** Relevant evidence outside the final five is unavailable unless a later agent iteration retrieves it.

### [MINOR] Batch Embeddings in Groups of 1000

`EMBEDDING_BATCH_SIZE = 1000`.

**Rationale:** Batching improves indexing throughput while keeping provider requests bounded.

**Impact:** Large corpora still depend on provider limits, memory, and retry behavior.

### [MINOR] Retry Voyage Requests

Voyage operations use up to three retries with a one-second base retry interval.

**Rationale:** Transient provider failures should not immediately fail indexing or retrieval operations.

**Impact:** Retries improve resilience but can increase latency during outages.

### [MINOR] Use Short Research Run Identifiers

Each research request receives a short identifier derived from a UUID.

**Rationale:** Short IDs make logs, timelines, and UI diagnostics easier to correlate.

**Impact:** IDs are useful for local diagnostics but are not designed as globally unique audit identifiers.

### [MINOR] Clear Per-Run LLM Call Logs

`AlchemyXSystem.ask()` clears the shared client call log when a new research run begins.

**Rationale:** Technical diagnostics should describe the current request, not previous requests.

**Impact:** Historical LLM call details are not retained unless captured elsewhere.

### [MINOR] Convert Source Labels for Readability

The adapter converts file names like `source_alpha_ii.scan.pdf` into readable source titles and groups duplicate formats under one numbered source entry.

**Rationale:** UI citations and source panels should be understandable without exposing raw file naming conventions everywhere or showing the same source repeatedly as separate PDF/DOCX entries.

**Impact:** Display labels may differ from exact source paths, while technical details retain source document metadata, chunk IDs, and per-format evidence.

### [MINOR] Humanize Stop Reasons

Internal stop reasons such as `sufficient_evidence`, `no_new_evidence`, and `max_iterations` are mapped to UI labels.

**Rationale:** Users need readable status text while technical details can preserve internal values.

**Impact:** New stop reasons should be added to the mapping to avoid generic labels.

### [MINOR] Keep Technical Diagnostics in Expanders

The UI includes timings, source metadata, internal errors, and LLM call counts in expandable technical sections.

**Rationale:** Diagnostics are useful for local debugging without dominating the normal answer view.

**Impact:** Production deployments may need to redact or restrict these details.

### [MINOR] Keep Empty-Question Handling in the UI

The Research page warns when a submitted question is empty and does not call the backend.

**Rationale:** Avoid unnecessary provider calls and confusing empty-query results.

**Impact:** Input validation remains simple and UI-local.

### [MINOR] Clear Session State Through a New Research Session Button

The Research page exposes a "New research session" button that clears turn history, current result, previous question, pending question, and input text.

**Rationale:** Users need an explicit way to reset multi-turn context and start clean.

**Impact:** Clearing the session does not affect indexes, corpus files, cached backend clients, or persisted data.

### [MINOR] Keep Fallback Answers Deterministic

When structured final generation fails, the system returns a safe fallback instead of displaying malformed model output.

**Rationale:** Failure modes should remain understandable and evidence-aware.

**Impact:** The fallback may be less polished but avoids presenting unusable or unsupported output.

### [MINOR] Keep Tests Focused on Component Contracts

Tests cover agent behavior, retrieval components, generation, ingestion, adapter mapping, and conversation adapter behavior with injectable fakes.

**Rationale:** Core contracts can be tested without live provider calls.

**Impact:** Live model quality, API quotas, OCR behavior, and Streamlit browser behavior remain environment-dependent.
