from app.evidence.chunker import chunk_text
from app.evidence.tagger import tag_gravity, tag_materials, tag_variables
from app.rag.embeddings import HashEmbedder, cosine


def test_chunker_and_tagger():
    text = ("In microgravity, flame spread over PMMA depends on oxygen concentration and forced flow velocity. " * 6 + "\n\n") * 3
    chunks = chunk_text(text)
    assert chunks and all(len(c.text) > 100 for c in chunks)
    t = chunks[0].text
    assert {"oxygen", "airflow"} <= set(tag_variables(t))
    assert tag_materials(t) == ["PMMA"] and tag_gravity(t) == "microgravity"


def test_embeddings_prefer_related_text():
    e = HashEmbedder()
    q, a, b = e.embed(["oxygen concentration flame spread", "Higher oxygen concentration increases flame spread rate",
                       "The cafeteria menu includes soup and bread"])
    assert cosine(q, a) > cosine(q, b) and len(q) == 384
