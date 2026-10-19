"""
Hybrid retrieval over the knowledge base: BM25 for exact words (SKU names,
"RMA", "Prop 65") plus dense embeddings for meaning ("my scan got worse" ->
guarantee page). Fused with reciprocal rank fusion. Everything runs locally:
embeddings come from nomic-embed-text through Ollama.

The production version of this at my last job used Pinecone/Qdrant and a
reranker. For a laptop demo with seven documents that is overkill, so this is
the small version of the same idea.
"""
import json, re, hashlib
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from config import CFG

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "kb"
CACHE = ROOT / "models" / "kb_index.json"
EMBED_MODEL = CFG["models"]["embed"]
TOP_K = int(CFG["retrieval"]["k"])
RRF_K = float(CFG["retrieval"]["rrf_k"])
CATEGORY_BOOST = float(CFG["retrieval"]["category_boost"])


def chunk_kb():
    """One chunk per '##' section, with the document title kept on the front."""
    chunks = []
    for p in sorted(KB.glob("*.md")):
        text = p.read_text()
        title = text.splitlines()[0].lstrip("# ").strip()
        parts = re.split(r"\n(?=## )", text)
        for part in parts:
            body = part.strip()
            if not body or body.startswith("# "):  # skip the title/source header block
                # keep the intro paragraph if there is one under the title
                intro = "\n".join(l for l in body.splitlines()[1:] if l.strip() and not l.startswith("Source:"))
                if len(intro) > 80:
                    chunks.append({"doc": p.name, "title": title, "heading": "overview", "text": intro})
                continue
            heading = body.splitlines()[0].lstrip("# ").strip()
            lines = body.splitlines()[1:]
            bullets = [l for l in lines if l.lstrip().startswith(("- ", "1.", "2.", "3."))]
            if len(bullets) >= 4:
                # long bullet lists get one chunk per bullet, so a question about
                # capsule size does not have to compete with the whole FAQ section
                lead = " ".join(l for l in lines if l.strip() and l not in bullets)
                for b in bullets:
                    chunks.append({"doc": p.name, "title": title, "heading": heading,
                                   "text": f"{heading}: {b.lstrip('- ').strip()}" + (f"\n({lead})" if lead else "")})
            else:
                chunks.append({"doc": p.name, "title": title, "heading": heading, "text": body})
    return chunks


# which documents a category usually lives in. used as a soft boost, not a filter,
# so a billing email that asks a dosing question can still reach the dosing page.
CATEGORY_DOCS = {
    "guarantee_claim": ["guarantee.md", "contact_and_escalation.md"],
    "results_question": ["guarantee.md", "safety_strontium_and_dexa.md"],
    "safety_concern": ["safety_strontium_and_dexa.md"],
    "dosage_question": ["dosing_and_products.md"],
    "shipping_issue": ["shipping.md"],
    "subscription_billing": ["subscribe_and_save.md"],
    "positive_feedback": ["contact_and_escalation.md"],
}


def tok(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def embed(texts):
    import ollama
    if hasattr(ollama, "embed"):
        r = ollama.embed(model=EMBED_MODEL, input=texts)
        return np.array(r["embeddings"], dtype=np.float32)
    return np.array([ollama.embeddings(model=EMBED_MODEL, prompt=t)["embedding"] for t in texts], dtype=np.float32)


class Retriever:
    def __init__(self, use_dense=True):
        self.chunks = chunk_kb()
        self.bm25 = BM25Okapi([tok(c["title"] + " " + c["heading"] + " " + c["text"]) for c in self.chunks])
        self.dense = None
        if use_dense:
            self.dense = self._load_or_build_dense()

    def _load_or_build_dense(self):
        key = hashlib.md5(json.dumps([c["text"] for c in self.chunks]).encode()).hexdigest()
        if CACHE.exists():
            cached = json.loads(CACHE.read_text())
            if cached.get("key") == key:
                return np.array(cached["vecs"], dtype=np.float32)
        try:
            vecs = embed([f"search_document: {c['title']} - {c['heading']}\n{c['text']}" for c in self.chunks])
        except Exception as e:  # ollama not running, model not pulled, etc.
            print("dense embeddings unavailable, BM25 only:", e)
            return None
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps({"key": key, "vecs": vecs.tolist()}))
        return vecs

    def search(self, query, k=None, category=None):
        k = TOP_K if k is None else k
        n = len(self.chunks)
        boost_docs = set(CATEGORY_DOCS.get(category, []))
        bm = self.bm25.get_scores(tok(query))
        bm_rank = np.argsort(-bm)
        fused = np.zeros(n)
        for r, i in enumerate(bm_rank):
            fused[i] += 1.0 / (RRF_K + r)
        dense_rank = None
        if self.dense is not None:
            try:
                q = embed([f"search_query: {query}"])[0]
                q /= np.linalg.norm(q)
                sims = self.dense @ q
                dense_rank = np.argsort(-sims)
                for r, i in enumerate(dense_rank):
                    fused[i] += 1.0 / (RRF_K + r)
            except Exception as e:
                print("dense query failed, BM25 only:", e)
        if boost_docs:
            for i, c in enumerate(self.chunks):
                if c["doc"] in boost_docs:
                    fused[i] += CATEGORY_BOOST  # default 1/60, worth one first-place vote
        top = np.argsort(-fused)[:k]
        out = []
        for i in top:
            c = dict(self.chunks[i])
            c["score"] = round(float(fused[i]), 4)
            c["bm25_rank"] = int(np.where(bm_rank == i)[0][0]) + 1
            c["dense_rank"] = int(np.where(dense_rank == i)[0][0]) + 1 if dense_rank is not None else None
            out.append(c)
        return out


if __name__ == "__main__":
    r = Retriever()
    print(len(r.chunks), "chunks,", "dense on" if r.dense is not None else "BM25 only")
    for q, cat in [("my scan got worse after a year and i want my money back", "guarantee_claim"),
                   ("charged twice on my card", "subscription_billing"),
                   ("is strontium the same as the drug pulled in europe", "safety_concern"),
                   ("can i open the capsules", "dosage_question"),
                   ("i am in alberta can i subscribe and save", "subscription_billing")]:
        print("\nQ:", q, f"[{cat}]")
        for h in r.search(q, k=4, category=cat):
            print(f"  {h['doc']} > {h['heading']}  (bm25 #{h['bm25_rank']}, dense #{h['dense_rank']})")
