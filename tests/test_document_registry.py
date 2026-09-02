from src.alchemyx.retrieval.document_registry import DocumentRegistry


def test_document_registry_searches_file_metadata(tmp_path):
    path = tmp_path / "registry.json"
    registry = DocumentRegistry(path)
    registry.replace_document(
        "misc/raw_data.csv",
        {
            "source_doc": "misc/raw_data.csv",
            "file_name": "raw_data.csv",
            "extension": ".csv",
            "relative_path": "misc/raw_data.csv",
            "document_type": "csv",
            "metadata_keywords": "",
        },
    )

    reloaded = DocumentRegistry(path)
    results = reloaded.search("is there a csv in the archive", top_k=5)

    assert [result.source_doc for result in results] == ["misc/raw_data.csv"]
    assert results[0].text.startswith("FILE: raw_data.csv")


def test_document_registry_prunes_stale_documents():
    registry = DocumentRegistry()
    registry.replace_document("current.txt", {"source_doc": "current.txt"})
    registry.replace_document("mira_wiki", {"source_doc": "mira_wiki"})

    removed = registry.delete_documents_except({"current.txt"})

    assert removed == ["mira_wiki"]
    assert list(registry.documents) == ["current.txt"]
