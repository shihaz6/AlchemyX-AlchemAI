# AlchemAI System Limitations

## 1. External service dependency

AlchemAI depends on Voyage AI for embeddings and reranking and OpenRouter for sufficiency checks, conflict adjudication, follow-up planning, and final answer generation. Provider outages, rate limits, network failures, model availability, invalid API keys, or incorrect model settings in `src/alchemyx/config.py` can prevent research or reduce answer quality. OpenRouter supports fallback models configured in `config.py`, but all fallback paths still depend on provider availability and valid credentials.

## 2. Synchronous request processing

The ingestion, retrieval, reranking, and LLM calls are synchronous. A long-running provider request blocks the Streamlit request, which can make the UI appear unresponsive and limits throughput for concurrent users.

## 3. Local index lifecycle

Indexes are not built through the UI. Documents must be placed in the configured corpus and indexed separately with scripts/build_indexes.py. Indexes can become stale when the corpus changes, so documents must be re-indexed after additions, replacements, or deletions.

The corpus path is configurable through `ALCHEMYX_CORPUS_PATH` in `.env`, falling back to `Archive_test` when it is omitted. A wrong corpus path can build indexes from the wrong folder or fail indexing.

## 4. Relative storage paths

The default Chroma, BM25, and document-registry locations are relative paths such as data/chroma, data/bm25.json, and data/document_registry.json. Running the application from an unexpected working directory or deploying it with different filesystem permissions can cause missing-index or write failures.

## 5. Corpus and extraction constraints

The supported formats are .txt, .md, .docx, .pdf, and .csv. Unsupported formats require a separate extraction step. PDF extraction quality depends on the source document; scanned PDFs additionally require Tesseract OCR and Poppler to be installed and correctly configured.

Tables, complex layouts, images, handwriting, and heavily structured documents may not be represented faithfully after text extraction and chunking.

## 6. Fixed chunking and retrieval limits

The system uses configured chunk size and overlap rather than dynamically adapting chunks to every document structure. Important context can be split across chunks or omitted from the final context.

The normal retrieval path overfetches hybrid candidates, reranks them, filters by relevance score, and returns up to five final results. Relevant evidence outside that final set cannot be used by sufficiency checking or answer generation unless a follow-up iteration retrieves it.

## 7. Bounded agent research

The agent is limited to four iterations. Complex, multi-hop, or poorly phrased questions may require more searches than the configured budget allows. Follow-up queries are generated from model judgments and may fail to discover the missing evidence.

## 8. Entity-resolution errors

Entity matching can classify evidence as exact, alias, contextual, related, or unusable. Incorrect entity resolution can exclude genuinely relevant evidence or allow related evidence to be treated as direct support. The system does not guarantee perfect entity disambiguation.

## 9. Conflict resolution is not authoritative

The evidence adjudicator can identify competing claims and select evidence based on the available authority signals, but it cannot independently establish which source is objectively correct. Conflicts can remain unresolved, and a selected claim may still be wrong if the corpus is incomplete, outdated, or inaccurate.

## 10. LLM output variability

Sufficiency, adjudication, follow-up planning, and answer generation depend on LLM behavior. Structured JSON parsing, repair attempts, evidence-ID validation, and fallback answers reduce failure impact but cannot eliminate hallucinations, omissions, or inconsistent reasoning.

## 11. Citation validation limitations

Citation checks verify that cited IDs were supplied and that cited claims have lexical overlap with the evidence. Lexical overlap is only a heuristic; it does not prove semantic correctness, complete support, or absence of contradictions.

## 12. Reader-friendly citation display limitations

The answer view converts raw evidence chunk IDs into numbered source references such as [1] and groups duplicate formats under one readable source entry. This makes citations easier to read, but the numbers are presentation labels for the current answer only.

Reader-facing source cards show title, format, support label, and a short excerpt. They intentionally hide chunk IDs, rank scores, entity-match diagnostics, and internal source paths. Users who need exact retrieval provenance must open Technical Details.

Grouped source entries can also hide per-format differences in the main view. If a PDF and DOCX copy of the same source produce different chunks, the user-facing Sources section still presents them as one source family while technical metadata preserves the individual chunks.

## 13. Conversation and follow-up limitations

The Streamlit app stores conversation turns in session state and supports explicit follow-up phrases such as "what about", "how about", "cite that", or "explain that". It does not provide full conversational memory, durable chat history, or broad pronoun resolution for every short second question.

Follow-up contextualization uses the previous question and a truncated previous answer as query text, then runs the normal research path. It does not reuse the previous evidence set as a guaranteed context cache.

## 14. Corpus quality and freshness

Answer quality is bounded by the indexed corpus. Missing, duplicated, contradictory, stale, or low-quality documents can produce incomplete or misleading answers. The system does not provide an external fact-checking or automatic freshness guarantee.

## 15. Single-process application assumptions

The Streamlit adapter caches one system instance per process. This is efficient for a local or small deployment, but it does not provide a distributed serving architecture, shared request queue, multi-process coordination, or high-availability guarantees.

## 16. Observability and privacy considerations

The application exposes source excerpts, technical source metadata, timings, internal errors, and LLM call diagnostics in the UI. These details may reveal sensitive corpus content or operational information and should be restricted or redacted for production users.

## 17. Security and deployment scope

The repository is designed as a local research application, not a complete multi-tenant service. Authentication, authorization, per-user data isolation, audit logging, request quotas, and secure remote deployment controls are not provided by the Streamlit application itself.

## 18. Testing and environment limitations

The test suite covers core component contracts and offline/injectable flows, but live Voyage AI and OpenRouter behavior remains environment-dependent. Tests cannot fully guarantee provider compatibility, production corpus quality, OCR behavior on every PDF, or performance under real traffic. In this checkout, runtime verification also depends on having a usable Python interpreter or virtual environment; a local non-executable `python` file can shadow the expected Python command.

## 19. Generated index management

Vector and lexical indexes are generated artifacts rather than immutable source data. They consume disk space and may need to be rebuilt when models, chunking parameters, metadata rules, or source documents change. Deployments must define backup, cleanup, portability, and rebuild procedures.
