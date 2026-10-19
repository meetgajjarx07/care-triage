"""
Retrieval evaluation. There are no per-email relevance labels, so the proxy is:
the document(s) a category normally lives in (CATEGORY_DOCS) should appear in
the top-k for an email of that category. It is a weak label and it is the same
map the boost uses, so the "with boost" number is flattered; the honest
comparison is BM25-only vs dense-only vs fused, all without the boost.

python eval_retrieval.py   -> models/retrieval_eval.json
"""
import json, time
from pathlib import Path

import numpy as np
import pandas as pd

from config import CFG
from retrieve import Retriever, CATEGORY_DOCS, tok, embed, RRF_K, CATEGORY_BOOST, TOP_K

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "data" / "emails.csv")
res_path = ROOT / "out" / "results.csv"
pred_cat = pd.read_csv(res_path).set_index("id").loc[df.id, "pred_category"].values if res_path.exists() else df.category.values
ret = Retriever()
docs = [c["doc"] for c in ret.chunks]
queries = [f"{s}. {b}" for s, b in zip(df.subject, df.body)]
expected = [set(CATEGORY_DOCS[c]) for c in df.category]
K = sorted({1, 3, TOP_K})
LOW_Q = float(CFG["retrieval"]["low_evidence_quantile"])

t0 = time.time()
bm = np.array([ret.bm25.get_scores(tok(q)) for q in queries])
t_bm = (time.time() - t0) / len(df)
t0 = time.time()
Q = embed([f"search_query: {q}" for q in queries]); Q /= np.linalg.norm(Q, axis=1, keepdims=True)
dense = Q @ ret.dense.T
t_dense = (time.time() - t0) / len(df)


def rrf(*score_mats, boost_cat=None):
    n = score_mats[0].shape[1]
    out = np.zeros_like(score_mats[0])
    for S in score_mats:
        ranks = np.argsort(-S, axis=1)
        for i in range(S.shape[0]):
            out[i, ranks[i]] += 1.0 / (RRF_K + np.arange(n))
    if boost_cat is not None:
        for i, cat in enumerate(boost_cat):
            for j, d in enumerate(docs):
                if d in CATEGORY_DOCS.get(cat, []):
                    out[i, j] += CATEGORY_BOOST
    return out


def metrics(S):
    order = np.argsort(-S, axis=1)
    res = {}
    for k in K:
        hits = [len({docs[j] for j in order[i, :k]} & expected[i]) > 0 for i in range(len(df))]
        res[f"hit@{k}"] = round(float(np.mean(hits)), 3)
    rr = []
    for i in range(len(df)):
        r = next((r for r, j in enumerate(order[i]) if docs[j] in expected[i]), None)
        rr.append(0 if r is None else 1 / (r + 1))
    res["mrr"] = round(float(np.mean(rr)), 3)
    return res, order


systems = {
    "BM25 only": (bm, None),
    "Dense only (nomic)": (dense, None),
    "Hybrid RRF": (rrf(bm, dense), None),
    "Hybrid RRF + category boost (what the pipeline runs)": (rrf(bm, dense, boost_cat=pred_cat), None),
}
out = {"n": len(df), "k": K, "proxy": "expected doc = CATEGORY_DOCS[true category]; the boosted system uses the classifier's predicted category, as the pipeline does, so its misses are classifier misses", "ms_per_query": {"bm25": round(1000 * t_bm, 2), "dense": round(1000 * t_dense, 1)}, "systems": {}, "per_category": {}}
orders = {}
for name, (S, _) in systems.items():
    m, order = metrics(S)
    out["systems"][name] = m
    orders[name] = order
# per-category hit@4 for the fused-no-boost system (the honest one) and the pipeline one
for name in ["Hybrid RRF", "Hybrid RRF + category boost (what the pipeline runs)"]:
    order = orders[name]
    pc = {}
    for cat in sorted(df.category.unique()):
        idx = np.where(df.category.values == cat)[0]
        pc[cat] = round(float(np.mean([len({docs[j] for j in order[i, :4]} & expected[i]) > 0 for i in idx])), 3)
    out["per_category"][name] = pc
# misses under the pipeline system: emails whose expected doc never shows in top-4
order = orders["Hybrid RRF + category boost (what the pipeline runs)"]
out["misses_top4"] = [{"id": df.id.iloc[i], "category": df.category.iloc[i],
                       "got": [docs[j] for j in order[i, :4]]} for i in range(len(df))
                      if not ({docs[j] for j in order[i, :4]} & expected[i])]
# low-evidence queries: best fused score is weak -> candidate knowledge gaps
S = systems["Hybrid RRF + category boost (what the pipeline runs)"][0]
best = S.max(axis=1)
thr = float(np.percentile(best, 100 * LOW_Q))
out["low_evidence"] = {"threshold_p10": round(thr, 4), "quantile": LOW_Q,
                       "ids": [df.id.iloc[i] for i in np.argsort(best)[:int(np.ceil(LOW_Q * len(df)))]]}
(ROOT / "models" / "retrieval_eval.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out["systems"], indent=2))
print("misses", len(out["misses_top4"]), "low evidence", out["low_evidence"]["ids"])
