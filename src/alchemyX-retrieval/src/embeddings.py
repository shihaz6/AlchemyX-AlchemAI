from chromadb import Documents, EmbeddingFunction, Embeddings
import voyageai

class VoyageEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key, model="voyage-4-lite", input_type="document"):
        self.client = voyageai.Client(api_key=api_key)
        self.model = model
        self.input_type = input_type

    def __call__(self, input: Documents) -> Embeddings:
        result = self.client.embed(input, model=self.model, input_type=self.input_type)
        return result.embeddings
