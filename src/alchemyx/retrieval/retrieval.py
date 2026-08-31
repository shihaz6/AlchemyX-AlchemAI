import chromadb
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

    def query(self, question, n_results=3):

        query_embeddings = self.query_ef([question])
        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results
        )
        return results
