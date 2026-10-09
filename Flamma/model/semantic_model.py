from sentence_transformers import SentenceTransformer


class SemanticModel:

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        print("Loading MiniLM semantic model...")

        self.model = SentenceTransformer(model_name)

        print("MiniLM loaded successfully!")

    def encode(self, texts):
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )