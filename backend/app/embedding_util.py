from app.rag.embeddings import get_embedder


def embed_one(text: str) -> list[float]:
    return get_embedder().embed([text])[0]
