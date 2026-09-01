import re

from rank_bm25 import BM25Okapi

try:
    from .Retrieval_Result import RetrievalResult
except ImportError:
    from Retrieval_Result import RetrievalResult


class BM25Store:
    def __init__(self):
        self.documents = []
        self.tokenized_documents = []
        self.bm25 = None

    def add_documents(self, documents):
        self.documents.extend(documents)
        self._rebuild()

    def replace_documents(self, source_doc, documents):
        self.documents = [
            document
            for document in self.documents
            if document.get("source_doc") != source_doc
        ]
        self.documents.extend(documents)
        self._rebuild()

    def _rebuild(self):
        self.tokenized_documents = [
            self._tokenize(document["text"])
            for document in self.documents
        ]
        self.bm25 = (
            BM25Okapi(self.tokenized_documents)
            if self.tokenized_documents
            else None
        )

    def search(self, query, top_k=5):
        if self.bm25 is None:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        ranked_results = sorted(
            (
                RetrievalResult(
                    id=document.get("id", ""),
                    text=document.get("text", ""),
                    source_doc=document.get("source_doc", ""),
                    chunk_index=document.get("chunk_index", 0),
                    score=float(score),
                )
                for document, score in zip(self.documents, scores)
            ),
            key=lambda result: result.score,
            reverse=True,
        )

        return ranked_results[:top_k]

    @staticmethod
    def _tokenize(text):
        return re.findall(r"\w+", text.lower())
