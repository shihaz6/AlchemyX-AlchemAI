import chromadb
try:
    from .Retrieval_Result import RetrievalResult
    from .embeddings import VoyageEmbeddingFunction
    from .chunking import chunk_text
except ImportError:
    from Retrieval_Result import RetrievalResult
    from embeddings import VoyageEmbeddingFunction
    from chunking import chunk_text
class RetrievalPipeline:
    def __init__(self, api_key, collection_name="alchemyx_docs"):
        # Setting up the voyage embedding function, used for documents being stored
        self.document_ef = VoyageEmbeddingFunction(api_key=api_key, input_type="document")
        self.query_ef = VoyageEmbeddingFunction(api_key=api_key, input_type="query")

        # Setting up chromadb client and collection, using voyage for embeddings
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.document_ef,
            metadata={"hnsw:space": "cosine"}

        )

    def add_document(self, doc_id, text, chunk_size=300, overlap=50):

        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

        chunk_ids = [f"{doc_id}_chunk{i}" for i in range(len(chunks))]

        # Store which document each chunk came from — useful later for citing sources
        metadatas = [{"source_doc": doc_id, "chunk_index": i} for i in range(len(chunks))]

        self.collection.add(
            documents=chunks,
            ids=chunk_ids,
            metadatas=metadatas
        )
        print(f"Added {len(chunks)} chunks from '{doc_id}'")

    def query(self, question, n_results=3) -> list[RetrievalResult]:

        query_embeddings = self.query_ef([question])
        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results
        )
        return self._to_retrieval_results(results)

    def search_many(self, queries, n_results=5) -> list[RetrievalResult]:
        queries = list(queries)
        if not queries:
            return []

        query_embeddings = self.query_ef(queries)
        raw_results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results
        )

        results_by_id = {}

        for result in self._to_retrieval_results(raw_results):
            existing_result = results_by_id.get(result.id)
            if existing_result is not None and existing_result.score >= result.score:
                continue

            results_by_id[result.id] = result

        return sorted(
            results_by_id.values(),
            key=lambda result: result.score,
            reverse=True,
        )

    @staticmethod
    def _to_retrieval_results(raw_results) -> list[RetrievalResult]:
        retrieval_results = []

        ids_by_query = raw_results.get("ids") or []
        documents_by_query = raw_results.get("documents") or []
        metadatas_by_query = raw_results.get("metadatas") or []
        distances_by_query = raw_results.get("distances") or []

        for query_index, ids in enumerate(ids_by_query):
            documents = (
                documents_by_query[query_index]
                if query_index < len(documents_by_query)
                else []
            )
            metadatas = (
                metadatas_by_query[query_index]
                if query_index < len(metadatas_by_query)
                else []
            )
            distances = (
                distances_by_query[query_index]
                if query_index < len(distances_by_query)
                else []
            )

            for result_index, result_id in enumerate(ids):
                metadata = (
                    metadatas[result_index]
                    if result_index < len(metadatas) and metadatas[result_index]
                    else {}
                )
                distance = (
                    distances[result_index]
                    if result_index < len(distances)
                    else 0.0
                )
                score = 1.0 - distance if distance is not None else 0.0

                retrieval_results.append(
                    RetrievalResult(
                        id=result_id,
                        text=(
                            documents[result_index]
                            if result_index < len(documents)
                            else ""
                        ),
                        source_doc=metadata.get("source_doc", ""),
                        chunk_index=metadata.get("chunk_index", 0),
                        score=score,
                    )
                )
        return retrieval_results
