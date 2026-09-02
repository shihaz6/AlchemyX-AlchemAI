import uuid

from src.alchemyx.retrieval import retrieval as retrieval_module
from src.alchemyx.retrieval.retrieval import RetrievalPipeline


class FakeEmbeddingFunction:

    def __init__(self, api_key, model=None, input_type="document"):
        self.input_type = input_type

    def __call__(self, input):
        return [self._embed(text) for text in input]

    def name(self):
        return "default"

    @staticmethod
    def _embed(text):
        normalized = text.lower()
        if "caldrin" in normalized or "escort" in normalized:
            return [1.0, 0.0, 0.0]
        if "mira" in normalized or "reliquary" in normalized:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


def make_pipeline(monkeypatch, tmp_path):
    monkeypatch.setattr(
        retrieval_module,
        "VoyageEmbeddingFunction",
        FakeEmbeddingFunction,
    )
    return RetrievalPipeline(
        api_key="test-key",
        collection_name=f"test_{uuid.uuid4().hex}",
        persist_directory=str(tmp_path / "chroma"),
    )


def test_retrieval_multiple_documents_and_source_doc(monkeypatch, tmp_path):
    pipeline = make_pipeline(monkeypatch, tmp_path)
    pipeline.add_document(
        "caldrin_wiki",
        "Caldrin escorted Mira.",
        chunk_size=20,
        overlap=0,
    )
    pipeline.add_document(
        "mira_wiki",
        "Mira carried a reliquary.",
        chunk_size=20,
        overlap=0,
    )

    results = pipeline.query("Who did Caldrin escort?", n_results=2)

    assert len(results) == 2
    assert results[0].source_doc == "caldrin_wiki"
    assert results[0].id == "caldrin_wiki_chunk0"


def test_retrieval_duplicate_document_reindexing_deletes_old_chunks(
    monkeypatch,
    tmp_path,
):
    pipeline = make_pipeline(monkeypatch, tmp_path)
    pipeline.add_document("doc", "old text one two three", chunk_size=3, overlap=0)
    pipeline.add_document("doc", "new text only", chunk_size=10, overlap=0)

    stored = pipeline.collection.get(where={"source_doc": "doc"})

    assert stored["ids"] == ["doc_chunk0"]
    assert stored["documents"] == ["new text only"]


def test_search_many_deduplicates_results(monkeypatch, tmp_path):
    pipeline = make_pipeline(monkeypatch, tmp_path)
    pipeline.add_document(
        "caldrin_wiki",
        "Caldrin escorted Mira.",
        chunk_size=20,
        overlap=0,
    )

    results = pipeline.search_many(["Caldrin", "escort"], n_results=1)

    assert [result.id for result in results] == ["caldrin_wiki_chunk0"]


def test_retrieval_persistent_chroma_index(monkeypatch, tmp_path):
    monkeypatch.setattr(
        retrieval_module,
        "VoyageEmbeddingFunction",
        FakeEmbeddingFunction,
    )
    collection_name = f"test_{uuid.uuid4().hex}"
    persist_directory = str(tmp_path / "chroma")

    first_pipeline = RetrievalPipeline(
        api_key="test-key",
        collection_name=collection_name,
        persist_directory=persist_directory,
    )
    first_pipeline.add_document(
        "caldrin_wiki",
        "Caldrin escorted Mira.",
        chunk_size=20,
        overlap=0,
    )

    second_pipeline = RetrievalPipeline(
        api_key="test-key",
        collection_name=collection_name,
        persist_directory=persist_directory,
    )
    results = second_pipeline.query("Caldrin", n_results=1)

    assert results[0].id == "caldrin_wiki_chunk0"


def test_retrieval_detects_unchanged_document(monkeypatch, tmp_path):
    pipeline = make_pipeline(monkeypatch, tmp_path)
    text = "Caldrin escorted Mira."

    assert pipeline.has_document("caldrin_wiki", text) is False
    pipeline.add_document("caldrin_wiki", text, chunk_size=20, overlap=0)

    assert pipeline.has_document("caldrin_wiki", text) is True
    assert pipeline.has_document("caldrin_wiki", "Changed text") is False


def test_add_document_batches_chroma_add_calls(monkeypatch):
    class FakeCollection:

        def __init__(self):
            self.deleted = []
            self.add_calls = []

        def delete(self, where):
            self.deleted.append(where)

        def add(self, documents, ids, metadatas):
            self.add_calls.append((documents, ids, metadatas))

    class FakeClient:

        def __init__(self, path):
            self.path = path
            self.collection = FakeCollection()

        def get_or_create_collection(self, **kwargs):
            return self.collection

    fake_client = FakeClient("unused")
    monkeypatch.setattr(
        retrieval_module.chromadb,
        "PersistentClient",
        lambda path: fake_client,
    )
    monkeypatch.setattr(
        retrieval_module,
        "VoyageEmbeddingFunction",
        FakeEmbeddingFunction,
    )
    monkeypatch.setattr(retrieval_module, "EMBEDDING_BATCH_SIZE", 2)

    pipeline = RetrievalPipeline(api_key="test-key")
    text = " ".join(f"word{index}" for index in range(60))
    pipeline.add_document(
        "doc",
        text,
        chunk_size=20,
        overlap=0,
    )

    assert len(fake_client.collection.add_calls) == 2
    assert [
        ids
        for _documents, ids, _metadatas in fake_client.collection.add_calls
    ] == [
        ["doc_chunk0", "doc_chunk1"],
        ["doc_chunk2"],
    ]
