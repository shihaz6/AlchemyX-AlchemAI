import os
from dotenv import find_dotenv, load_dotenv
from bm25_store import BM25Store
from chunking import chunk_text
from hybrid_search import HybridSearch
from reranker import Reranker
from retrieval import RetrievalPipeline

load_dotenv(find_dotenv())
API_KEY = os.getenv("VOYAGE_API_KEY")
if not API_KEY:
    raise RuntimeError("VOYAGE_API_KEY is missing. Add it to the .env file.")

pipeline = RetrievalPipeline(api_key=API_KEY)
bm25_store = BM25Store()
hybrid_search = HybridSearch(pipeline, bm25_store)
reranker = Reranker(api_key=API_KEY)
MIN_RERANK_SCORE = 0.5

caldrin_doc = """
Ser Caldrin Vale was a Veyran knight and diplomatic envoy active during the late Toll Wars period. 
Born to a minor riverland house, Caldrin entered service under the merchant-princes of Lumenford 
after losing his family estate to debt. Caldrin is chiefly remembered for his role in the Night of 
Falling Bells, a failed winter parley held at Thornwatch. He was assigned to escort Mira Quen, a 
Lumenford courier with informal ties to canal smugglers, to the monastery-fortress.
"""

mira_doc = """
Mira Quen was a canal-singer and smuggler from the glass-market city of Lumenford. 
She disappeared on the Night of Falling Bells with a sealed reliquary, and Abbess 
Ilyra Senn later claimed she had asked Mira to remove it before Thornwatch's council 
could hand it to the Iron Prior.
"""

def add_document_to_indexes(doc_id, text, chunk_size=30, overlap=5):
    pipeline.add_document(
        doc_id=doc_id,
        text=text,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    bm25_store.add_documents(
        [
            {
                "id": f"{doc_id}_chunk{index}",
                "text": chunk,
                "source_doc": doc_id,
                "chunk_index": index,
            }
            for index, chunk in enumerate(chunks)
        ]
    )


add_document_to_indexes(doc_id="caldrin_wiki", text=caldrin_doc)
add_document_to_indexes(doc_id="mira_wiki", text=mira_doc)


def print_results(results):
    if not results:
        print("No evidence above relevance threshold.")
        return

    for rank, result in enumerate(results, start=1):
        print(rank, result.id, result.score, result.text[:100])


def find_rank(results, expected_id):
    for rank, result in enumerate(results, start=1):
        if result.id == expected_id:
            return rank

    return None


test_queries = [
    "Who did Caldrin escort?",
    "Why did Mira take the reliquary?",
    "What happened during the Night of Falling Bells?",
    "Who asked Mira to remove the reliquary?",
    "What is the time now?",
]

expected_chunks = {
    "Who did Caldrin escort?": "caldrin_wiki_chunk2",
    "Why did Mira take the reliquary?": "mira_wiki_chunk1",
    "What happened during the Night of Falling Bells?": "caldrin_wiki_chunk2",
    "Who asked Mira to remove the reliquary?": "mira_wiki_chunk1",
}

for query in test_queries:
    print(f"\n--- Query: {query} ---")

    semantic_results = pipeline.query(query)
    bm25_results = bm25_store.search(query)
    hybrid_results = hybrid_search.search(query)
    candidates = hybrid_search.search(query, top_k=15)
    final_results = reranker.rerank(
        query,
        candidates,
        top_k=5,
        min_relevance_score=MIN_RERANK_SCORE,
    )

    print("\nSemantic:")
    print_results(semantic_results)

    print("\nBM25:")
    print_results(bm25_results)

    print("\nHybrid RRF:")
    print_results(hybrid_results)

    print("\nHybrid RRF + Reranker:")
    print(f"min_relevance_score={MIN_RERANK_SCORE}")
    print_results(final_results)

    expected_id = expected_chunks.get(query)
    if expected_id:
        print("\nExpected chunk ranks:")
        print(f"Semantic: {expected_id} -> rank {find_rank(semantic_results, expected_id)}")
        print(f"BM25:     {expected_id} -> rank {find_rank(bm25_results, expected_id)}")
        print(f"Hybrid:   {expected_id} -> rank {find_rank(hybrid_results, expected_id)}")
        print(f"Reranked: {expected_id} -> rank {find_rank(final_results, expected_id)}")
    else:
        print("\nNo expected chunk; checking whether retrieval returns irrelevant matches.")
