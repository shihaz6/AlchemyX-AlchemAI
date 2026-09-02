from src.alchemyx.ingestion.ingestion import (
    IngestionResult,
    ingest_corpus,
    print_ingestion_summary,
    read_csv,
    read_pdf,
    resolve_corpus_path,
)


class FakePipeline:

    def __init__(self):
        self.documents = []
        self.removed_except = None

    def add_document(
        self,
        doc_id,
        text,
        chunk_size=300,
        overlap=50,
        metadata=None,
    ):
        self.documents.append((doc_id, text, chunk_size, overlap, metadata))

    def delete_documents_except(self, source_docs):
        self.removed_except = set(source_docs)
        return []


class FakeBM25Store:

    def __init__(self):
        self.documents = []
        self.removed_except = None

    def add_documents(self, documents):
        self.documents.extend(documents)

    def delete_documents_except(self, source_docs):
        self.removed_except = set(source_docs)
        return []


class FakeDocumentRegistry:
    def __init__(self):
        self.documents = {}
        self.removed_except = None

    def replace_document(self, source_doc, metadata):
        self.documents[source_doc] = metadata

    def delete_documents_except(self, source_docs):
        self.removed_except = set(source_docs)
        return []


def test_ingest_corpus_adds_documents_to_chroma_and_bm25_indexes(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    nested = corpus / "nested"
    nested.mkdir()
    (nested / "source.md").write_text(
        "one two three four five six seven eight nine ten",
        encoding="utf-8",
    )

    pipeline = FakePipeline()
    bm25_store = FakeBM25Store()
    document_registry = FakeDocumentRegistry()

    result = ingest_corpus(
        str(corpus),
        pipeline,
        bm25_store,
        document_registry=document_registry,
    )

    assert pipeline.documents == [
        (
            "nested/source.md",
            "one two three four five six seven eight nine ten",
            120,
            20,
            {
                "source_doc": "nested/source.md",
                "file_name": "source.md",
                "extension": ".md",
                "relative_path": "nested/source.md",
                "document_type": "md",
                "metadata_keywords": "",
            },
        )
    ]
    assert bm25_store.documents == [
        {
            "id": "nested/source.md_chunk0",
            "text": (
                "FILE: source.md\n"
                "TYPE: md\n"
                "EXTENSION: .md\n"
                "PATH: nested/source.md\n"
                "SOURCE: nested/source.md\n\n"
                "one two three four five six seven eight nine ten"
            ),
            "content_text": "one two three four five six seven eight nine ten",
            "metadata_text": (
                "FILE: source.md\n"
                "TYPE: md\n"
                "EXTENSION: .md\n"
                "PATH: nested/source.md\n"
                "SOURCE: nested/source.md"
            ),
            "source_doc": "nested/source.md",
            "chunk_index": 0,
            "file_name": "source.md",
            "extension": ".md",
            "relative_path": "nested/source.md",
            "document_type": "md",
            "metadata_keywords": "",
        }
    ]
    assert result.ingested == ["nested/source.md"]
    assert result.skipped == []
    assert result.failed == {}
    assert result.removed == []
    assert pipeline.removed_except == {"nested/source.md"}
    assert bm25_store.removed_except == {"nested/source.md"}
    assert set(document_registry.documents) == {"nested/source.md"}
    assert document_registry.removed_except == {"nested/source.md"}


def test_ingest_corpus_adds_csv_documents_to_indexes(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "notes.csv").write_text(
        "name,role\nCaldrin Vale,knight\nMira Quen,smuggler\n",
        encoding="utf-8",
    )

    pipeline = FakePipeline()
    bm25_store = FakeBM25Store()

    result = ingest_corpus(str(corpus), pipeline, bm25_store)

    expected_text = (
        "name: Caldrin Vale; role: knight\n"
        "name: Mira Quen; role: smuggler"
    )
    assert pipeline.documents == [
        (
            "notes.csv",
            expected_text,
            120,
            20,
            {
                "source_doc": "notes.csv",
                "file_name": "notes.csv",
                "extension": ".csv",
                "relative_path": "notes.csv",
                "document_type": "csv",
                "metadata_keywords": "",
            },
        )
    ]
    assert bm25_store.documents == [
        {
            "id": "notes.csv_chunk0",
            "text": (
                "FILE: notes.csv\n"
                "TYPE: csv\n"
                "EXTENSION: .csv\n"
                "PATH: notes.csv\n"
                "SOURCE: notes.csv\n\n"
                f"{expected_text.replace('\n', ' ')}"
            ),
            "content_text": expected_text.replace("\n", " "),
            "metadata_text": (
                "FILE: notes.csv\n"
                "TYPE: csv\n"
                "EXTENSION: .csv\n"
                "PATH: notes.csv\n"
                "SOURCE: notes.csv"
            ),
            "source_doc": "notes.csv",
            "chunk_index": 0,
            "file_name": "notes.csv",
            "extension": ".csv",
            "relative_path": "notes.csv",
            "document_type": "csv",
            "metadata_keywords": "",
        }
    ]
    assert result.ingested == ["notes.csv"]
    assert result.skipped == []
    assert result.failed == {}


def test_ingest_corpus_raises_for_missing_corpus_folder(tmp_path):
    pipeline = FakePipeline()
    bm25_store = FakeBM25Store()

    try:
        ingest_corpus(str(tmp_path / "missing"), pipeline, bm25_store)
    except FileNotFoundError as exc:
        assert "Corpus folder does not exist" in str(exc)
    else:
        raise AssertionError("Expected missing corpus folder to raise")


def test_resolve_corpus_path_uses_base_for_relative_paths(tmp_path):
    assert resolve_corpus_path("Archive_test", tmp_path) == (
        tmp_path / "Archive_test"
    )


def test_ingest_corpus_continues_after_file_failure(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "broken.txt").write_bytes(b"\xff")
    (corpus / "valid.md").write_text("valid document", encoding="utf-8")

    pipeline = FakePipeline()
    bm25_store = FakeBM25Store()

    result = ingest_corpus(str(corpus), pipeline, bm25_store)

    assert result.ingested == ["valid.md"]
    assert result.skipped == []
    assert "broken.txt" in result.failed
    assert pipeline.documents == [
        (
            "valid.md",
            "valid document",
            120,
            20,
            {
                "source_doc": "valid.md",
                "file_name": "valid.md",
                "extension": ".md",
                "relative_path": "valid.md",
                "document_type": "md",
                "metadata_keywords": "",
            },
        )
    ]
    assert pipeline.removed_except is None
    assert bm25_store.removed_except is None


def test_ingest_corpus_reports_removed_stale_indexes(tmp_path):
    class StalePipeline(FakePipeline):
        def delete_documents_except(self, source_docs):
            super().delete_documents_except(source_docs)
            return ["mira_wiki"]

    class StaleBM25Store(FakeBM25Store):
        def delete_documents_except(self, source_docs):
            super().delete_documents_except(source_docs)
            return ["mira_wiki"]

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "current.txt").write_text("current document", encoding="utf-8")

    pipeline = StalePipeline()
    bm25_store = StaleBM25Store()
    document_registry = FakeDocumentRegistry()
    document_registry.documents["mira_wiki"] = {"source_doc": "mira_wiki"}

    result = ingest_corpus(
        str(corpus),
        pipeline,
        bm25_store,
        document_registry=document_registry,
    )

    assert result.ingested == ["current.txt"]
    assert result.removed == ["mira_wiki"]


def test_read_pdf_uses_tesseract_env_var_for_ocr(monkeypatch):
    class FakePage:

        def get_text(self):
            return ""

    class FakeDocument:

        def __enter__(self):
            return [FakePage()]

        def __exit__(self, exc_type, exc, traceback):
            return False

    class FakeFitz:

        @staticmethod
        def open(file_path):
            return FakeDocument()

    class FakePytesseractModule:

        class pytesseract:
            tesseract_cmd = None

        @staticmethod
        def image_to_string(image):
            return "ocr text"

    class FakePdf2Image:

        @staticmethod
        def convert_from_path(file_path):
            return ["image"]

    monkeypatch.setenv("TESSERACT_CMD", "/opt/tesseract/bin/tesseract")
    monkeypatch.setitem(__import__("sys").modules, "pymupdf", FakeFitz)
    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        FakePytesseractModule,
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "pdf2image",
        FakePdf2Image,
    )

    assert read_pdf("scan.pdf") == "ocr text"
    assert (
        FakePytesseractModule.pytesseract.tesseract_cmd
        == "/opt/tesseract/bin/tesseract"
    )


def test_read_csv_with_headers_extracts_rows(tmp_path):
    csv_path = tmp_path / "raw.csv"
    csv_path.write_text("alpha,beta\none,two\n", encoding="utf-8")

    assert read_csv(csv_path) == "alpha: one; beta: two"


def test_print_ingestion_summary_reports_failures(capsys):
    result = IngestionResult(
        ingested=["valid.md"],
        skipped=["notes.csv"],
        failed={"broken.txt": "invalid encoding"},
    )

    print_ingestion_summary(result)

    output = capsys.readouterr().out
    assert "Ingested: 1" in output
    assert "Skipped: 1" in output
    assert "Failed: 1" in output
    assert "- broken.txt: invalid encoding" in output
