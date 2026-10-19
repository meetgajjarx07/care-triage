from retrieve import chunk_kb, Retriever, CATEGORY_DOCS, TOP_K


def test_chunks_have_shape():
    chunks = chunk_kb()
    assert len(chunks) > 20
    assert {"doc", "title", "heading", "text"} <= set(chunks[0])
    assert all(c["text"].strip() for c in chunks)
    docs = {c["doc"] for c in chunks}
    for cat, ds in CATEGORY_DOCS.items():
        assert set(ds) <= docs, f"{cat} points at a missing document"


def test_bm25_search_returns_k_with_ranks():
    r = Retriever(use_dense=False)
    hits = r.search("charged twice on my card", category="subscription_billing")
    assert len(hits) == TOP_K
    assert all(h["bm25_rank"] >= 1 and h["dense_rank"] is None for h in hits)
    assert hits[0]["score"] >= hits[-1]["score"]
    assert any(h["doc"] == "subscribe_and_save.md" for h in hits)


def test_k_override():
    r = Retriever(use_dense=False)
    assert len(r.search("capsules", k=2)) == 2
