"""
Retrieval/knowledge pipeline grounding the natural-language reporting
layer -- the JD's "document ingestion, chunking, embeddings, and vector
indexing ... kept in sync as source data changes" requirement.

Indexes the governed semantic layer (src/semantic_layer.py) and the real
X12 834 spec notes (docs/x12_834_spec_notes.md), so a question like "what
does maintenance code 024 mean" or "which field is the real join key for
clients" is answered from the governed source of truth rather than an
LLM's unguided guess -- directly reusing the Chroma grounding pattern
verified elsewhere in this portfolio (AdvisorAgent, Undercurrent).
"""
from pathlib import Path

import chromadb
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from src.semantic_layer import SEMANTIC_LAYER

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"


class LocalTfidfEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    Chroma's default embedding function downloads a model from
    huggingface.co, which is network-blocked from this build sandbox (the
    same constraint disclosed for Undercurrent elsewhere in this
    portfolio). This is a real, locally-fit TF-IDF + truncated-SVD
    embedding -- no network call, deterministic, fit once on the corpus
    being indexed.
    """

    def __init__(self, corpus: list[str], n_components: int = 32):
        self.vectorizer = TfidfVectorizer(stop_words="english")
        tfidf = self.vectorizer.fit_transform(corpus)
        n_components = min(n_components, min(tfidf.shape) - 1)
        self.svd = TruncatedSVD(n_components=n_components, random_state=20240601)
        self.svd.fit(tfidf)

    def __call__(self, input: list[str]) -> list[list[float]]:
        tfidf = self.vectorizer.transform(input)
        vecs = self.svd.transform(tfidf)
        return [v.tolist() for v in vecs]


def _semantic_layer_chunks():
    chunks = []
    for entity, spec in SEMANTIC_LAYER["entities"].items():
        for field, desc in spec.get("fields", {}).items():
            chunks.append(
                {
                    "id": f"semantic:{entity}.{field}",
                    "text": f"Entity '{entity}', field '{field}': {desc}",
                    "metadata": {"source": "semantic_layer", "entity": entity, "field": field},
                }
            )
        for i, note in enumerate(spec.get("known_data_quality_notes", [])):
            chunks.append(
                {
                    "id": f"semantic:{entity}.dq_note.{i}",
                    "text": f"Known data-quality note for entity '{entity}': {note}",
                    "metadata": {"source": "semantic_layer", "entity": entity, "type": "data_quality_note"},
                }
            )
    for rule, desc in SEMANTIC_LAYER["business_rules"].items():
        chunks.append(
            {
                "id": f"semantic:rule.{rule}",
                "text": f"Business rule '{rule}': {desc}",
                "metadata": {"source": "semantic_layer", "type": "business_rule"},
            }
        )
    return chunks


def _spec_doc_chunks():
    spec_path = DOCS_DIR / "x12_834_spec_notes.md"
    text = spec_path.read_text()
    # chunk by markdown section (## headers)
    sections = text.split("\n## ")
    chunks = []
    for i, section in enumerate(sections):
        if not section.strip():
            continue
        title = section.split("\n", 1)[0].strip("# ")
        chunks.append(
            {
                "id": f"spec:section.{i}",
                "text": section,
                "metadata": {"source": "x12_834_spec_notes", "section": title},
            }
        )
    return chunks


def build_index():
    chunks = _semantic_layer_chunks() + _spec_doc_chunks()
    embedding_fn = LocalTfidfEmbeddingFunction([c["text"] for c in chunks])

    client = chromadb.Client()
    try:
        client.delete_collection("coverageledger_grounding")
    except Exception:
        pass
    collection = client.create_collection("coverageledger_grounding", embedding_function=embedding_fn)

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )
    return collection


def query(collection, question: str, n_results: int = 3):
    results = collection.query(query_texts=[question], n_results=n_results)
    return [
        {"text": doc, "metadata": meta}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


if __name__ == "__main__":
    col = build_index()
    for q in ["what does maintenance code 024 mean", "what is the real join key for clients"]:
        print(f"\nQ: {q}")
        for r in query(col, q, n_results=2):
            print(" -", r["text"][:120].replace("\n", " "))
