from sentence_transformers import SentenceTransformer
import os

_MODEL = None

def get_model():
    global _MODEL
    if _MODEL is None:
        model_path = os.getenv("EMBEDDING_MODEL_PATH")
        _MODEL = SentenceTransformer(model_path, local_files_only=True)
    return _MODEL

def generate_embeddings(chunks):
    model = get_model()
    texts = ["passage: " + (chunk.get("description") or chunk.get("name") or "") for chunk in chunks]
    embs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embs
