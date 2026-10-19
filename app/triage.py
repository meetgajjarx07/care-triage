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

retrieve_graded() and make_brief() are shared with pipeline.py so the two paths
cannot drift: retrieval plus the model's relevance check (and one query rewrite
when nothing fits; the best match is always kept), and the two-line brief with grounded facts.
"""
import time
from datetime import datetime
from pathlib import Path

import joblib

import classify
import genai
from config import CFG
from draft import (confidence_band, draft_qa, draft_reply, lexical_check, route_rule,
                   sentence_support, MODEL as DRAFT_MODEL, DRAFT_OPTIONS)
from retrieve import Retriever, EMBED_MODEL, TOP_K

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
GENAI = CFG.get("genai", {})

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


def _fmt(hits):
    return [{"doc": x["doc"], "title": x.get("title", x["doc"]), "heading": x["heading"], "text": x["text"], "score": x["score"],
             "bm25_rank": x["bm25_rank"], "dense_rank": x["dense_rank"]} for x in hits]


def retrieve_graded(ret, subject, body, category):
    """Hybrid search, then (if config genai.crag) the language model reads each
    paragraph against the email and drops the ones that are about something else.
    Guards: the search's best match is always kept, so the grader can trim noise
    but never remove the evidence. If the grader rejects every paragraph, the
    question is rephrased once and searched again; if that also fails, the best
    match is kept anyway and the email is flagged as a content gap (low_evidence),
    which the Knowledge base page counts. Returns (hits_to_use, retrieve_stage, None)."""
    q = f"{subject}. {body}"
    t0 = time.time()
    hits = ret.search(q, k=TOP_K, category=category)
    stage = {"ms": _ms(t0), "k": TOP_K, "query": q[:160], "boost_category": category, "hits": _fmt(hits)}
    if not GENAI.get("crag") or not hits:
        return hits, stage, None

    def row(h, g):
        return {"title": h.get("title", h["doc"]), "heading": h["heading"], "relevant": g["relevant"], "why": g["why"]}

    grades, g_ms = genai.grade_chunks(subject, body, hits)
    crag = {"model": genai.MODEL, "ms": g_ms, "attempts": 1, "rewritten_query": None, "low_evidence": False,
            "graded": [row(h, g) for h, g in zip(hits, grades)]}
    if not any(g["relevant"] for g in grades):
        nq, r_ms = genai.rewrite_query(subject, body)
        hits2 = ret.search(nq, k=TOP_K, category=category)
        grades2, g2_ms = genai.grade_chunks(subject, body, hits2)
        crag.update({"attempts": 2, "rewritten_query": nq, "ms": g_ms + r_ms + g2_ms,
                     "second_pass": [row(h, g) for h, g in zip(hits2, grades2)]})
        if any(g["relevant"] for g in grades2):
            hits, grades = hits2, grades2
            stage["hits"] = _fmt(hits2)
        else:
            crag["low_evidence"] = True
    # the best match always stays; the grader only trims the rest
    kept = [hits[0]] + [h for h, g in zip(hits[1:], grades[1:]) if g["relevant"]]
    graded_now = crag.get("second_pass") if (crag["attempts"] == 2 and not crag["low_evidence"]) else crag["graded"]
    crag["kept"] = len(kept)
    crag["dropped"] = [x for x in graded_now[1:] if not x["relevant"]]
    crag["best_kept_by_rule"] = not graded_now[0]["relevant"]
    stage["crag"] = crag
    return kept, stage, None


def make_brief(subject, body, from_name=""):
    """Two lines for whoever handles the email, plus the facts pulled out of it,
    each checked against the email text. None when switched off in config."""
    if not GENAI.get("brief"):
        return None
    return genai.brief(subject, body, from_name)


def triage_email(subject, body, from_name="", draft=True, progress=None, email_id=None):
    """Embed, classify, retrieve and grade, brief, route, then draft and check if the
    route allows. Raises whatever Ollama raises if it is down; callers decide how to show that."""
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

    used, S["retrieve"], override = retrieve_graded(ret, subject, body, category)
    tick("retrieve")

    S["brief"] = make_brief(subject, body, from_name)
    if S["brief"]:
        tick("brief")

    rr = override or route_rule(category, sentiment, body)
    S["route"] = {"decision": rr["action"], "reason": rr["reason"], "rule_id": rr["rule_id"], "short": rr["short"]}
    tick("route")

    S["draft"] = None
    S["check"] = None
    if draft and rr["action"] == "draft_reply":
        t0 = time.time()
        text = draft_reply(body, from_name, category, used)
        S["draft"] = {"model": DRAFT_MODEL, "ms": round(1000 * (time.time() - t0)), **DRAFT_OPTIONS,
                      "words": len(text.split()), "text": text}
        tick("draft")
        t0 = time.time()
        flags = lexical_check(text, used, body)
        qa = draft_qa(text, used, body)
        try:
            support = sentence_support(text, used, body, classify.embed)
        except Exception:
            support = []
        S["check"] = {"ms": _ms(t0), "flags": flags, "passed": not flags, "qa": qa, "support": support}
        tick("check")
    return rec


if __name__ == "__main__":
    import json, sys
    body = " ".join(sys.argv[1:]) or "My card shows two charges this month for one bottle of AlgaeCal Plus."
    rec = triage_email("charged twice", body, "Jean Whitford", draft=True, progress=lambda n, r: print("done:", n))
    print(json.dumps({k: v for k, v in rec["stages"].items() if k != "retrieve"}, indent=1)[:2500])
