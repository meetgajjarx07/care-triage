"""
Run every email through the whole thing and write out/results.csv.

classify -> sentiment -> retrieve policy -> route -> (maybe) draft reply -> check

python pipeline.py              everything, drafts for every 'draft_reply' email (slow-ish, local LLM)
python pipeline.py --no-draft   skip LLM drafting, just classify/retrieve/route (seconds)

Also writes out/trace.jsonl, one record per email with every stage's output and
timing (what the dashboard's trace view shows), and out/run.json with the run
metadata (models, versions, counts, wall time).
"""
import sys, time, json, platform, socket
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn, streamlit  # version stamps only

from config import CFG, config_hash
from retrieve import Retriever, EMBED_MODEL
from draft import route_rule, draft_reply, lexical_check, draft_qa, confidence_band, sentence_support, MODEL as DRAFT_MODEL, DRAFT_OPTIONS, SYSTEM
from classify import email_text, embed
from triage import retrieve_graded, make_brief

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"; OUT.mkdir(exist_ok=True)

run_started = datetime.now()
t_run = time.time()
df = pd.read_csv(ROOT / "data" / "emails.csv")
cat_model = joblib.load(ROOT / "models" / "category.joblib")
sent_model = joblib.load(ROOT / "models" / "sentiment.joblib")
t0 = time.time(); ret = Retriever(); t_index = time.time() - t0

t0 = time.time()
X = embed([email_text(s, b) for s, b in zip(df.subject, df.body)])
t_embed = time.time() - t0
t0 = time.time()
cat_proba = cat_model.predict_proba(X)
sent_proba = sent_model.predict_proba(X)
t_clf = time.time() - t0
df["pred_category"] = cat_model.classes_[cat_proba.argmax(axis=1)]
df["pred_category_conf"] = cat_proba.max(axis=1).round(3)
df["pred_sentiment"] = sent_model.classes_[sent_proba.argmax(axis=1)]
df["pred_sentiment_conf"] = sent_proba.max(axis=1).round(3)
df["confidence_band"] = [confidence_band(p) for p in df.pred_category_conf]

# short escalation reasons come from each rule's `short` in config/triage.yaml

do_draft = "--no-draft" not in sys.argv
routes, reasons, sources, drafts, lat, checks, traces, qa_scores, qa_fails, reason_short = [], [], [], [], [], [], [], [], [], []
brief_asks, brief_check, brief_facts, crag_kept, crag_dropped, crag_low = [], [], [], [], [], []
for i, row in df.iterrows():
    hits, ret_stage, override = retrieve_graded(ret, row["subject"], row["body"], row["pred_category"])
    brief = make_brief(row["subject"], row["body"], row["from_name"])
    rr = override or route_rule(row["pred_category"], row["pred_sentiment"], row["body"])
    rt, why = rr["action"], rr["reason"]
    routes.append(rt); reasons.append(why)
    sources.append(json.dumps([{"doc": h["doc"], "heading": h["heading"]} for h in hits]))
    reason_short.append(rr["short"] if rt == "consultant_call" else "")
    d, fl, t_draft, qa, support = "", [], None, None, []
    if do_draft and rt == "draft_reply":
        t0 = time.time()
        try:
            d = draft_reply(row["body"], row["from_name"], row["pred_category"], hits)
        except Exception as e:
            d = f"[draft failed: {e}]"
        t_draft = time.time() - t0
        fl = lexical_check(d, hits, row["body"])
        qa = draft_qa(d, hits, row["body"])
        try:
            support = sentence_support(d, hits, row["body"], embed)
        except Exception:
            support = []
        print(f"{row['id']} {row['pred_category']:<22} drafted in {t_draft:.1f}s  {'FLAG: ' + '; '.join(fl) if fl else 'ok'}")
    drafts.append(d); lat.append(round(t_draft, 1) if t_draft is not None else None); checks.append("; ".join(fl))
    brief_asks.append(brief["asks"] if brief else ""); brief_check.append(brief["check"] if brief else "")
    brief_facts.append(json.dumps(brief["facts"]) if brief else "[]")
    cr = ret_stage.get("crag"); crag_kept.append(cr["kept"] if cr else None); crag_dropped.append(len(cr["dropped"]) if cr else None); crag_low.append(bool(cr["low_evidence"]) if cr else False)
    qa_scores.append(qa["score"] if qa else None); qa_fails.append("; ".join(qa["failed"]) if qa else "")
    traces.append({
        "id": row["id"], "received_at": row["received_at"], "from_name": row["from_name"],
        "subject": row["subject"], "body": row["body"],
        "label_category": row["category"], "label_sentiment": row["sentiment"], "label_cancel_intent": int(row["cancel_intent"]),
        "stages": {
            "embed": {"model": EMBED_MODEL, "dim": int(X.shape[1]), "ms": round(1000 * t_embed / len(df), 1),
                      "input": email_text(row["subject"], row["body"])[:160]},
            "classify": {"ms": round(1000 * t_clf / len(df), 2),
                         "category": {c: round(float(p), 3) for c, p in zip(cat_model.classes_, cat_proba[i])},
                         "sentiment": {c: round(float(p), 3) for c, p in zip(sent_model.classes_, sent_proba[i])}},
            "retrieve": ret_stage,
            "brief": brief,
            "route": {"decision": rt, "reason": why, "rule_id": rr["rule_id"], "short": rr["short"]},
            "draft": None if t_draft is None else {"model": DRAFT_MODEL, "ms": round(1000 * t_draft), **DRAFT_OPTIONS,
                                                   "words": len(d.split()), "text": d},
            "check": None if t_draft is None else {"flags": fl, "passed": not fl, "qa": qa, "support": support},
        },
    })

df["route"] = routes
df["route_reason"] = reasons
df["sources"] = sources
df["draft_reply"] = drafts
df["draft_seconds"] = lat
df["check_flags"] = checks
df["escalation_reason"] = reason_short
df["qa_score"] = qa_scores
df["qa_failed"] = qa_fails
df["brief_asks"] = brief_asks
df["brief_check"] = brief_check
df["brief_facts"] = brief_facts
df["crag_kept"] = crag_kept
df["crag_dropped"] = crag_dropped
df["crag_low_evidence"] = crag_low
df["needs_review"] = (df["route"] == "consultant_call") | (df["check_flags"] != "")

df.to_csv(OUT / "results.csv", index=False)
with open(OUT / "trace.jsonl", "w") as f:
    for t in traces:
        f.write(json.dumps(t) + "\n")

n_draft = int((df.route == "draft_reply").sum())
run = {
    "run_id": run_started.strftime("run-%Y%m%d-%H%M%S"),
    "config_version": CFG["version"], "config_hash": config_hash(),
    "routing_rules": [r["id"] for r in CFG["routing_rules"]],
    "started_at": run_started.isoformat(timespec="seconds"),
    "finished_at": datetime.now().isoformat(timespec="seconds"),
    "wall_seconds": round(time.time() - t_run, 1),
    "host": socket.gethostname(), "python": platform.python_version(), "sklearn": sklearn.__version__,
    "streamlit": streamlit.__version__, "numpy": np.__version__, "pandas": pd.__version__,
    "embed_model": EMBED_MODEL, "draft_model": DRAFT_MODEL if do_draft else None,
    "genai": CFG.get("genai", {}),
    "crag_low_evidence": int(df.crag_low_evidence.sum()), "crag_dropped_total": int(df.crag_dropped.fillna(0).sum()),
    "draft_options": DRAFT_OPTIONS,
    "system_prompt": SYSTEM,
    "kb_docs": len({c["doc"] for c in ret.chunks}), "kb_chunks": len(ret.chunks),
    "dense_index": ret.dense is not None,
    "emails": int(len(df)), "window": [df.received_at.min(), df.received_at.max()],
    "timing_seconds": {"index_load": round(t_index, 2), "embed_all": round(t_embed, 2), "classify_all": round(t_clf, 3),
                       "draft_total": round(float(df.draft_seconds.fillna(0).sum()), 1)},
    "routes": {k: int(v) for k, v in df.route.value_counts().items()},
    "drafted": n_draft,
    "flagged": int(((df.route == "draft_reply") & (df.check_flags != "")).sum()),
    "qa_below_100": int(((df.route == "draft_reply") & (df.qa_score < 100)).sum()),
    "confidence_bands": {k: int(v) for k, v in df.confidence_band.value_counts().items()},
    "train_set_accuracy_optimistic": round(float((df.pred_category == df.category).mean()), 3),
}
(OUT / "run.json").write_text(json.dumps(run, indent=2))

print("\nwrote", OUT / "results.csv", "and trace.jsonl, run.json")
print(df["route"].value_counts().to_string())
print("drafts flagged by the lexical check:", run["flagged"], "of", n_draft)
print("category accuracy on all 110 (model saw these, so optimistic):", run["train_set_accuracy_optimistic"])
