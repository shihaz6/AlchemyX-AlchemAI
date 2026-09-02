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


def test_bm25_documents_persist_and_reload(tmp_path):
    path = tmp_path / "bm25.json"
    store = BM25Store(persist_path=path)
    store.add_documents(
        [
            {
                "id": "doc_chunk0",
                "text": "persistent archive evidence",
                "source_doc": "doc",
                "chunk_index": 0,
            }
        ]
    )

    reloaded = BM25Store(persist_path=path)

    assert reloaded.search("archive", top_k=1)[0].id == "doc_chunk0"


def test_bm25_delete_documents_except_removes_stale_sources():
    store = BM25Store()
    store.add_documents(
        [
            {
                "id": "current.txt_chunk0",
                "text": "current",
                "source_doc": "current.txt",
                "chunk_index": 0,
            },
            {
                "id": "mira_wiki_chunk0",
                "text": "stale",
                "source_doc": "mira_wiki",
                "chunk_index": 0,
            },
        ]
    )

    removed = store.delete_documents_except({"current.txt"})

    assert removed == ["mira_wiki"]
    assert [document["source_doc"] for document in store.documents] == ["current.txt"]


def test_bm25_metadata_search_finds_filename_match_without_content_match():
    store = BM25Store()
    store.add_documents(
        [
            {
                "id": "commit_history.csv_chunk0",
                "text": (
                    "FILE: commit_history.csv\n"
                    "TYPE: csv\n"
                    "KEYWORDS: git github commit commits\n\n"
                    "hash author message"
                ),
                "metadata_text": (
                    "FILE: commit_history.csv\n"
                    "TYPE: csv\n"
                    "KEYWORDS: git github commit commits"
                ),
                "source_doc": "commit_history.csv",
                "chunk_index": 0,
            }
        ]
    )

    results = store.search_metadata("github related csv file", top_k=1)

    assert [result.id for result in results] == ["commit_history.csv_chunk0"]


def test_bm25_metadata_search_lists_files_for_generic_file_query():
    store = BM25Store()
    store.add_documents(
        [
            {
                "id": "a.txt_chunk0",
                "text": "FILE: a.txt\nTYPE: txt\n\nfirst chunk",
                "metadata_text": "FILE: a.txt\nTYPE: txt",
                "source_doc": "a.txt",
                "chunk_index": 0,
            },
            {
                "id": "a.txt_chunk1",
                "text": "FILE: a.txt\nTYPE: txt\n\nsecond chunk",
                "metadata_text": "FILE: a.txt\nTYPE: txt",
                "source_doc": "a.txt",
                "chunk_index": 1,
            },
            {
                "id": "b.csv_chunk0",
                "text": "FILE: b.csv\nTYPE: csv\n\nrow",
                "metadata_text": "FILE: b.csv\nTYPE: csv",
                "source_doc": "b.csv",
                "chunk_index": 0,
            },
        ]
    )

    results = store.search_metadata("what files are available", top_k=5)

    assert [result.source_doc for result in results] == ["a.txt", "b.csv"]
