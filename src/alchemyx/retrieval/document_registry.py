import json
import re
from pathlib import Path

try:
    from .Retrieval_Result import RetrievalResult
    from .document_metadata import metadata_search_text
except ImportError:
    from Retrieval_Result import RetrievalResult
    from document_metadata import metadata_search_text


REGISTRY_STOPWORDS = {
    "a",
    "an",
    "archive",
    "are",
    "available",
    "corpus",
    "doc",
    "docs",
    "document",
    "documents",
    "file",
    "files",
    "folder",
    "in",
    "is",
    "related",
    "the",
    "there",
    "what",
    "which",
}


class DocumentRegistry:
    def __init__(self, persist_path=None):
        self.persist_path = Path(persist_path) if persist_path else None
        self.documents = {}
        self._load()

    def replace_document(self, source_doc, metadata):
        self.documents[source_doc] = dict(metadata)
        self._save()

    def delete_documents_except(self, source_docs):
        source_docs = set(source_docs)
        removed = [
            source_doc
            for source_doc in self.documents
            if source_doc not in source_docs
        ]
        for source_doc in removed:
            self.documents.pop(source_doc, None)
        self._save()
        return sorted(removed)

    def search(self, query, top_k=5):
        query_tokens = [
            token
            for token in self._tokenize(query)
            if token not in REGISTRY_STOPWORDS
        ]
        if not query_tokens:
            return self.list_documents(top_k)

        results = []
        for source_doc, metadata in self.documents.items():
            text = metadata_search_text(metadata)
            tokens = self._tokenize(text)
            score = sum(tokens.count(token) for token in query_tokens)
            if score <= 0:
                continue
            results.append(self._to_result(source_doc, metadata, score))

        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]

    def list_documents(self, top_k=5):
        return [
            self._to_result(source_doc, metadata, 1.0)
            for source_doc, metadata in list(self.documents.items())[:top_k]
        ]

    def _to_result(self, source_doc, metadata, score):
        text = metadata_search_text(metadata)
        return RetrievalResult(
            id=f"{source_doc}_chunk0",
            text=text,
            source_doc=source_doc,
            chunk_index=0,
            score=float(score),
        )

    def _load(self):
        if self.persist_path is None or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text(encoding="utf-8"))
            documents = data.get("documents", {})
            if isinstance(documents, dict):
                self.documents = documents
        except (OSError, json.JSONDecodeError, TypeError, AttributeError):
            self.documents = {}

    def _save(self):
        if self.persist_path is None:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.persist_path.write_text(
            json.dumps({"documents": self.documents}, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _tokenize(text):
        return re.findall(r"\w+", text.lower())
