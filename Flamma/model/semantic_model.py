from sentence_transformers import SentenceTransformer
from model.errors import TextModelUnavailable


class SemanticModel:

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        print("Loading MiniLM semantic model...")

        # Model files are installed once during setup. Chat requests must not
        # retry remote metadata requests when a cached model is available.
        try:
            self.model = SentenceTransformer(model_name, local_files_only=True)
        except OSError as error:
            raise TextModelUnavailable("The text model is not available in the local cache.") from error

        print("MiniLM loaded successfully!")

    def encode(self, texts):
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
