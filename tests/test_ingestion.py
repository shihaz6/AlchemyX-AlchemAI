from src.alchemyx.ingestion.ingestion import (
    IngestionResult,
    ingest_corpus,
    print_ingestion_summary,
    read_pdf,
    resolve_corpus_path,
)


class FakePipeline:

    def __init__(self):
        self.documents = []

    def add_document(self, doc_id, text, chunk_size=300, overlap=50):
        self.documents.append((doc_id, text, chunk_size, overlap))


class FakeBM25Store:

    def __init__(self):
        self.documents = []

    def add_documents(self, documents):
        self.documents.extend(documents)


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

    result = ingest_corpus(str(corpus), pipeline, bm25_store)

    assert pipeline.documents == [
        (
            "nested/source.md",
            "one two three four five six seven eight nine ten",
            30,
            5,
        )
    ]
    assert bm25_store.documents == [
        {
            "id": "nested/source.md_chunk0",
            "text": "one two three four five six seven eight nine ten",
            "source_doc": "nested/source.md",
            "chunk_index": 0,
        }
    ]
    assert result.ingested == ["nested/source.md"]
    assert result.skipped == []
    assert result.failed == {}


def test_ingest_corpus_reports_skipped_unsupported_files(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "notes.csv").write_text("not supported", encoding="utf-8")

    pipeline = FakePipeline()
    bm25_store = FakeBM25Store()

    result = ingest_corpus(str(corpus), pipeline, bm25_store)

    assert pipeline.documents == []
    assert bm25_store.documents == []
    assert result.ingested == []
    assert result.skipped == ["notes.csv"]
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
        ("valid.md", "valid document", 30, 5)
    ]


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
