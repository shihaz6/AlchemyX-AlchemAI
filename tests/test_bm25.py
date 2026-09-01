from src.alchemyx.retrieval.bm25_store import BM25Store


def test_replace_documents_removes_stale_source_doc_chunks():
    store = BM25Store()
    store.add_documents(
        [
            {
                "id": "doc_a_chunk0",
                "text": "old coolant valve",
                "source_doc": "doc_a",
                "chunk_index": 0,
            },
            {
                "id": "doc_b_chunk0",
                "text": "stable reactor pump",
                "source_doc": "doc_b",
                "chunk_index": 0,
            },
            {
                "id": "doc_c_chunk0",
                "text": "distant monastery bells",
                "source_doc": "doc_c",
                "chunk_index": 0,
            },
        ]
    )

    store.replace_documents(
        "doc_a",
        [
            {
                "id": "doc_a_chunk0",
                "text": "new reliquary archive",
                "source_doc": "doc_a",
                "chunk_index": 0,
            }
        ],
    )

    assert [document["id"] for document in store.documents] == [
        "doc_b_chunk0",
        "doc_c_chunk0",
        "doc_a_chunk0",
    ]
    assert store.search("old coolant", top_k=1)[0].id != "doc_a_chunk0"
    assert store.search("reliquary", top_k=1)[0].id == "doc_a_chunk0"
