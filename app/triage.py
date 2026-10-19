"""
Triage one email, right now, through the same code the batch pipeline runs.

The batch pipeline (pipeline.py) is for the inbox. This is for one email at a
time: the dashboard's Live triage page and the API call it. It returns a record
shaped exactly like a line of out/trace.jsonl, so the dashboard renders a live
result and a recorded one with the same code.

    from triage import triage_email
    rec = triage_email("charged twice", "My card shows two charges...", "Jean", draft=True)

`progress` is an optional callback: progress(stage_name, result_so_far) is called
after each stage so a UI can draw the pipeline as it happens.
"""
import time
from datetime import datetime
from pathlib import Path

import joblib

import classify
from draft import (confidence_band, draft_qa, draft_reply, lexical_check, route_rule,
                   sentence_support, MODEL as DRAFT_MODEL, DRAFT_OPTIONS)
from retrieve import Retriever, EMBED_MODEL, TOP_K

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

_state: dict = {}


def components():
    """Retriever and the two classifiers, loaded once per process."""
    if "ret" not in _state:
        _state["ret"] = Retriever()
        _state["cat"] = joblib.load(MODELS / "category.joblib")
        _state["sent"] = joblib.load(MODELS / "sentiment.joblib")
    return _state["ret"], _state["cat"], _state["sent"]


def _ms(t0):
    return round(1000 * (time.time() - t0), 2)


def triage_email(subject, body, from_name="", draft=True, progress=None, email_id=None):
    """Embed, classify, retrieve, route, then draft and check if the route allows.
    Raises whatever Ollama raises if it is down; callers decide how to show that."""
    subject, body = subject.strip(), body.strip()
    ret, cat_m, sent_m = components()
    rec = {"id": email_id or datetime.now().strftime("LIVE-%H%M%S"),
           "received_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "from_name": from_name.strip(),
           "subject": subject, "body": body, "live": True, "stages": {}}
    S = rec["stages"]

    def tick(name):
        if progress:
            progress(name, rec)

    t0 = time.time()
    X = classify.embed([classify.email_text(subject, body)])
    S["embed"] = {"model": EMBED_MODEL, "dim": int(X.shape[1]), "ms": _ms(t0),
                  "input": classify.email_text(subject, body)[:160]}
    tick("embed")

    t0 = time.time()
    cp, sp = cat_m.predict_proba(X)[0], sent_m.predict_proba(X)[0]
    category, sentiment = str(cat_m.classes_[cp.argmax()]), str(sent_m.classes_[sp.argmax()])
    conf = float(cp.max())
    S["classify"] = {"ms": _ms(t0),
                     "category": {c: round(float(p), 3) for c, p in zip(cat_m.classes_, cp)},
                     "sentiment": {c: round(float(p), 3) for c, p in zip(sent_m.classes_, sp)},
                     "pred_category": category, "pred_sentiment": sentiment,
                     "confidence": round(conf, 3), "band": confidence_band(conf)}
    tick("classify")

    t0 = time.time()
    q = f"{subject}. {body}"
    hits = ret.search(q, k=TOP_K, category=category)
    S["retrieve"] = {"ms": _ms(t0), "k": TOP_K, "query": q[:160], "boost_category": category,
                     "hits": [{"doc": x["doc"], "heading": x["heading"], "text": x["text"], "score": x["score"],
                               "bm25_rank": x["bm25_rank"], "dense_rank": x["dense_rank"]} for x in hits]}
    tick("retrieve")

    rr = route_rule(category, sentiment, body)
    S["route"] = {"decision": rr["action"], "reason": rr["reason"], "rule_id": rr["rule_id"], "short": rr["short"]}
    tick("route")

    S["draft"] = None
    S["check"] = None
    if draft and rr["action"] == "draft_reply":
        t0 = time.time()
        text = draft_reply(body, from_name, category, hits)
        S["draft"] = {"model": DRAFT_MODEL, "ms": round(1000 * (time.time() - t0)), **DRAFT_OPTIONS,
                      "words": len(text.split()), "text": text}
        tick("draft")
        t0 = time.time()
        flags = lexical_check(text, hits, body)
        qa = draft_qa(text, hits, body)
        try:
            support = sentence_support(text, hits, body, classify.embed)
        except Exception:
            support = []
        S["check"] = {"ms": _ms(t0), "flags": flags, "passed": not flags, "qa": qa, "support": support}
        tick("check")
    return rec


if __name__ == "__main__":
    import json, sys
    body = " ".join(sys.argv[1:]) or "My card shows two charges this month for one bottle of AlgaeCal Plus."
    rec = triage_email("charged twice", body, "Jean Whitford", draft=True, progress=lambda n, r: print("done:", n))
    print(json.dumps({k: v for k, v in rec["stages"].items() if k != "retrieve"}, indent=1)[:2000])
