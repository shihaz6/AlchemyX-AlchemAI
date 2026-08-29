import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
import voyageai

class VoyageEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key, model = "voyage-4-lite"):
        self.client = voyageai.Client(api_key=api_key)
        self.model = model

    def __call__(self, input:Documents) -> Embeddings:
        result = self.client.embed(input, model=self.model, input_type = "document")
        return result.embeddings

#setting the api key for the voyage model
voyage_ef = VoyageEmbeddingFunction(api_key="pa-r5gOSwHCAT7q-5EN7quT4j0fr6LB9cpbtS0dFUmTV0F")

client = chromadb.Client()
collection = client.create_collection(
    name = "Voyage_test",
    embedding_function = voyage_ef
)

collection.add(
    documents = [
        "The bell fell during the winter parley at Thornwatch.",
        "Reedmere depended on the sluices for flood control.",
        "Mira Quen was a canal-singer and smuggler from Lumenford.",
        "Ser Caldrin Vale was a disgraced knight serving as envoy.",
    ],
    ids = ["doc1", "doc2", "doc3", "doc4"]
)
results = collection.query(query_texts=["What happened to the sanctuary bell?"], n_results=2)
print(results["documents"])
