# AlchemAI Architecture

## 1. System overview

AlchemAI is a local-corpus, retrieval-augmented research assistant. It exposes a Streamlit UI, indexes documents into persistent vector and lexical indexes, performs iterative hybrid retrieval, validates and adjudicates evidence with an OpenRouter-hosted LLM, and produces a cited answer. The application is synchronous Python; Streamlit owns the browser session and `src/alchemyx` owns the domain logic.

```text
Streamlit UI -> backend_adapter -> AlchemyXSystem
                                      |
                          +-----------+-----------+
                          |                       |
                      AgentLoop             AnswerGenerator
                          |
          Entity resolution -> hybrid retrieval
          -> sufficiency -> conflict adjudication
          -> follow-up queries (bounded iterations)
                                      |
                       Chroma + BM25 + reranker
                                      |
                 local persistent indexes and registry

External services: Voyage AI (embeddings/reranking)
                   OpenRouter (LLM decisions and generation)
```

## 2. Repository structure

| Area | Responsibility |
|---|---|
| `app/streamlit_app.py` | Streamlit pages, forms, session state, answer/evidence/timeline rendering |
| `app/backend_adapter.py` | Compatibility re-export of the package adapter |
| `src/alchemyx/main.py` | Composition root and end-to-end `AlchemyXSystem.ask()` orchestration |
| `src/alchemyx/config.py` | Root `.env` loading and runtime constants |
| `src/alchemyx/agent/` | Agent loop, entity matching, sufficiency, conflicts, follow-ups, LLM client, schemas |
| `src/alchemyx/retrieval/` | Chunking, embeddings, Chroma, BM25, hybrid search, reranking, registry |
| `src/alchemyx/ingestion/` | File extraction, corpus traversal, chunk ingestion, index refresh/reuse |
| `src/alchemyx/generation/` | Answer generation, JSON parsing/repair, citations and support validation |
| `src/alchemyx/telemetry.py` | Research IDs, timing, and logging context |
| `scripts/build_indexes.py` | Corpus indexing command |
| `tests/` | Unit and integration coverage for the system boundaries |

## 3. Runtime composition

`create_system()` constructs one shared `OpenRouterClient`, the agent retrieval pipeline, `SufficiencyChecker`, `EvidenceAdjudicator`, `AgentLoop`, and `AnswerGenerator`. The Streamlit adapter caches this system with `lru_cache(maxsize=1)`, so a process normally reuses its index connections.

## 4. Indexing and ingestion

```text
Configured corpus
  -> discover/extract .txt, .md, .docx, .pdf, .csv
  -> canonical chunking (120 default size, 20 overlap)
  -> Voyage embeddings -> persistent Chroma
  -> lexical tokens    -> persistent BM25 JSON
  -> document metadata -> document registry JSON
```

`scripts/build_indexes.py` uses `DEFAULT_CORPUS_PATH`, creates the retrieval stack, and calls `ingest_corpus()`. The ingestion layer reports ingested/reused documents and fails if no documents were indexed. Source and chunk metadata support replacement of old chunks when documents are re-indexed. Scanned PDFs can use Tesseract and Poppler through the optional OCR dependencies.

Configured defaults are collection `alchemyx_docs`, Chroma `data/chroma`, BM25 `data/bm25.json`, registry `data/document_registry.json`, and embedding batches of 1000. The corpus path comes from `ALCHEMYX_CORPUS_PATH` in `.env`, falling back to `Archive_test`. AI model choices are configured in `src/alchemyx/config.py`. This checkout also contains generated Chroma data under `src/alchemyx/ingestion/data/chroma`; deployments should standardize and deliberately manage that generated data.

## 5. Retrieval architecture

The agent-facing retrieval contract is a narrow object with `.query(text)` returning typed retrieval results. Results carry stable IDs, text, source document, chunk index, and scores; entity-match annotations may be attached for downstream evidence filtering.

Each search combines semantic Chroma retrieval and lexical BM25 retrieval, fuses candidates with reciprocal-rank fusion (`RRF_K=60`), optionally reranks up to 15 candidates with Voyage, then sorts and truncates to the final top five (`RETRIEVAL_TOP_K=5`). Fusion and deduplication occur before final truncation. `agent/hybrid_rerank_retrieval.py` adapts the lower-level retrieval stack to the agent contract.

## 6. Agentic research flow

```text
Question
  -> entity extraction/resolution
  -> retrieval and reranking
  -> sufficiency analysis
       | sufficient ----------------------> return evidence
       | conflict -> evidence adjudication
       | insufficient/unresolved
       v
  follow-up query generation -> next iteration
```

`AgentLoop.run(question)` is bounded by `MAX_AGENT_ITERATIONS=4`. Entity resolution classifies exact, alias, contextual, related, and unusable matches. The sufficiency checker identifies whether evidence answers the question and what is missing. The adjudicator evaluates competing claims, authority, selected evidence IDs, and resolved/unresolved conflict state. Follow-up generation searches for missing evidence while budget remains.

Each run returns a short research ID, timeline, stop reason, per-stage timings, internal diagnostics, and LLM call information for the adapter and UI.

## 7. Answer generation and citations

After the agent stops, `AlchemyXSystem.ask()` calls `AnswerGenerator.generate()` with the original question, final documents, and sufficiency result. The generator expects structured JSON containing an answer and evidence IDs. It validates IDs against supplied documents, validates bracketed citations, and checks lexical support between cited claims and evidence.

Malformed output can be repaired; if that fails, a deterministic fallback preserves selected evidence and states that a definitive answer could not be generated. `citation_builder.py` maps document metadata to source citations. The final response contains the answer, evidence IDs, documents, sufficiency/conflict state, iterations, timeline, timings, errors, and LLM call counts.

## 8. Presentation and adapter layer

The Research page submits questions and renders the cleaned answer, metrics, timeline, conflict explanation, evidence, related/excluded sources, performance, and technical details. The Explore Archive page queries existing indexes and shows the top five chunks with source, chunk number, and score.

`alchemyx.backend_adapter.run_research()` is the UI boundary. It converts domain objects to dictionaries, groups chunks into source families, separates evidence/context/excluded visibility, humanizes stop reasons, and applies user-safe answer cleanup. Streamlit does not directly access retrieval infrastructure.

## 9. Configuration and dependencies

API keys and corpus path are loaded from the project-root `.env`. Model selections, fallback models, storage paths, and limits are defined in `src/alchemyx/config.py`. Secrets are not expected in source files.

ChromaDB provides vector persistence; Voyage AI provides embeddings and reranking; rank-bm25 provides lexical search; OpenRouter provides structured research and answer calls; PyMuPDF/python-docx/CSV support extraction; Streamlit provides the UI.

## 10. Operational lifecycle

```text
Install -> configure .env -> place corpus -> build indexes
       -> start Streamlit -> research/search
       -> update corpus -> rebuild indexes
```

Indexes are expected to exist before normal research. There is no UI document-upload workflow; index refresh is explicit through `scripts/build_indexes.py`.

## 11. Testing and quality boundaries

The test suite covers chunking, ingestion, embeddings, Chroma/retrieval, BM25, hybrid search, reranking, registry behavior, agent-loop behavior, sufficiency, adjudication, generation/citations, adapter behavior, and end-to-end flows. `pyproject.toml` configures `src` as the import path and `tests` as the test directory.

Unit tests can inject custom retrieval components and avoid live model calls. Live provider behavior, API quotas, corpus quality, OCR installation, and writable index paths remain environment-dependent.

## 12. Key design contracts

- The agent consumes a narrow `.query(text)` retrieval interface.
- Typed retrieval results survive fusion, reranking, and agent consumption.
- Ingestion owns canonical chunk creation.
- Hybrid retrieval merges, deduplicates, ranks, and truncates at the end.
- Sufficiency/adjudication select evidence IDs; generation is constrained to supplied evidence.
- The UI consumes adapter dictionaries rather than infrastructure internals.
- Indexing and app startup are explicit entry points.

## 13. Known limitations

- Synchronous provider calls block the Streamlit request.
- Voyage/OpenRouter availability and quotas affect latency and answer quality.
- Relative index paths require a standardized working-directory/deployment convention.
- Scanned-PDF OCR requires separate Tesseract and Poppler installation.
- Technical UI diagnostics expose source text and LLM metadata; production deployments should review that exposure.
