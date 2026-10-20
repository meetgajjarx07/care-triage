"""
Voice of customer: the email pipeline pointed at reviews.

Reads data/reviews.csv (104 fictional reviews shaped like a Yotpo export plus
Amazon and independent-site rows), then for each review:

  embed  -> nomic-embed-text, the same model the email sorter uses
  theme  -> logistic regression over 7 themes, predicted OUT OF FOLD (5-fold),
            so the theme shown for every review comes from a model that never saw it
  mood   -> from the stars (1-2 negative, 3 neutral, 4-5 positive); no model needed
  read   -> the language model writes a one-line gist and copies one phrase out of
            the review; the phrase is kept only if it really appears in the text
  rule   -> what happens next (config/triage.yaml `reviews.rules`): health or scan
            complaints get a private consultant outreach, other negative reviews get
            a drafted public reply, the rest are counted
  draft  -> a public reply under 90 words from the policy pages only
  check  -> the same seven QA rules as email drafts; critical fails zero the score

Writes out/voc_results.csv, out/voc_trace.jsonl, out/voc_run.json.

python voc.py              everything (~10 min with the local model)
python voc.py --no-llm     themes and rules only, no gist, no drafts (seconds)
"""
import sys, json, time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from config import CFG, config_hash
from classify import embed
from retrieve import Retriever, TOP_K
from draft import draft_qa, lexical_check, sentence_support, DRAFT_OPTIONS, MODEL as DRAFT_MODEL
import genai

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"; OUT.mkdir(exist_ok=True)
RV = CFG["reviews"]
THEMES = RV["themes"]
THEME_LABEL = {"results": "Results on a scan", "side_effects": "Stomach and side effects", "price": "Price and value", "pills": "Pill size and taking it",
               "shipping": "Shipping and delivery", "support": "Support and consultants", "subscription": "Subscription and billing"}
MAX_WORDS = int(RV["public_reply_max_words"])

PUBLIC_SYSTEM = f"""You write short public replies to product reviews for AlgaeCal Customer Care. Anyone can read them.
Rules:
- Use ONLY the facts in the POLICY NOTES. If the notes do not cover it, say the team will look into it and invite the reviewer to contact support.
- Never mention the reviewer's health, scan, medication or dose. Never give medical advice. Never promise a refund or an amount.
- Do not argue with the review. Acknowledge the specific problem in the first sentence.
- Plain, warm, short. Under {MAX_WORDS} words. No bullet points. No exclamation marks.
- Sign off as "AlgaeCal Customer Care"."""

READ_SYSTEM = """You read one customer review and answer in JSON only:
{"gist": "what this reviewer is saying, under 14 words, plain words",
 "quote": "one short phrase copied exactly from the review that shows it",
 "asks_for": one of "nothing", "a reply", "a refund", "help with the order", "medical guidance"}"""


def review_text(title, body):
    return f"classification: {title}. {body}"


def sentiment_from_stars(stars):
    return "negative" if stars <= 2 else ("neutral" if stars == 3 else "positive")


def read_review(title, body):
    """The generative step, guarded: the quote is kept only if it is really in the text."""
    t0 = time.time()
    raw = genai._chat("review", READ_SYSTEM, f"REVIEW TITLE: {title}\n\nREVIEW:\n{body}", num_predict=120)
    j = genai._json(raw, {})
    quote = str(j.get("quote") or "").strip().strip('"').strip(".")
    text = f"{title} {body}".lower()
    ok = bool(quote) and quote.lower() in text
    asks = str(j.get("asks_for") or "nothing").strip().lower()
    if asks not in ("nothing", "a reply", "a refund", "help with the order", "medical guidance"):
        asks = "nothing"
    return {"model": genai.MODEL, "ms": round(1000 * (time.time() - t0)), "gist": str(j.get("gist") or "").strip()[:140],
            "quote": quote if ok else "", "quote_rejected": "" if ok else quote, "asks_for": asks}


def review_rule(theme, sentiment):
    for r in RV["rules"]:
        w = r["when"]
        if w.get("sentiment") and w["sentiment"] != sentiment:
            continue
        if w.get("theme_in") and theme not in w["theme_in"]:
            continue
        return {"rule_id": r["id"], "action": r["action"], "short": r["short"], "reason": r["reason"]}
    d = RV["default"]
    return {"rule_id": "default", "action": d["action"], "short": d["short"], "reason": d["reason"]}


def draft_public_reply(title, body, theme, chunks):
    import ollama
    notes = "\n\n".join(f"[{c['title']} > {c['heading']}]\n{c['text']}" for c in chunks)
    user = f"THEME: {THEME_LABEL.get(theme, theme)}\n\nPOLICY NOTES:\n{notes}\n\nREVIEW TITLE: {title}\nREVIEW:\n{body}\n\nWrite the public reply."
    r = ollama.chat(model=DRAFT_MODEL, options=DRAFT_OPTIONS, messages=[{"role": "system", "content": PUBLIC_SYSTEM}, {"role": "user", "content": user}])
    return r["message"]["content"].strip()


def theme_model():
    """Fit the theme model on all labelled reviews (for live use; the batch run reports it out of fold)."""
    df = pd.read_csv(ROOT / "data" / "reviews.csv")
    X = embed([review_text(a, b) for a, b in zip(df.title, df.body)])
    lr_kw = {"C": CFG["classifier"]["C"], "class_weight": CFG["classifier"]["class_weight"], "max_iter": CFG["classifier"]["max_iter"]}
    return LogisticRegression(**lr_kw).fit(X, df.theme.values)


def triage_review(title, body, stars, model, ret=None, llm=True, draft=True, progress=None, review_id=None):
    """One review through the same steps the batch run uses, with a progress callback per stage."""
    rec = {"id": review_id or datetime.now().strftime("LIVE-R%H%M%S"), "title": title, "body": body, "stars": int(stars), "live": True, "stages": {}}
    S = rec["stages"]
    def tick(name):
        if progress: progress(name, rec)
    t0 = time.time(); X = embed([review_text(title, body)]); S["embed"] = {"ms": round(1000 * (time.time() - t0))}; tick("embed")
    t0 = time.time(); p = model.predict_proba(X)[0]; theme = str(model.classes_[p.argmax()])
    S["theme"] = {"ms": round(1000 * (time.time() - t0)), "pred": theme, "conf": round(float(p.max()), 3), "probs": {c: round(float(x), 3) for c, x in zip(model.classes_, p)}}
    S["sentiment"] = {"from": "stars", "value": sentiment_from_stars(int(stars))}; tick("theme")
    S["read"] = read_review(title, body) if llm else None
    if S["read"]: tick("read")
    S["rule"] = review_rule(theme, S["sentiment"]["value"]); tick("rule")
    S["draft"] = None; S["check"] = None
    if draft and llm and S["rule"]["action"] == "draft_reply":
        ret = ret or Retriever()
        hits = ret.search(f"{title}. {body}", k=TOP_K, category=RV["theme_to_kb"].get(theme))
        t0 = time.time(); d = draft_public_reply(title, body, theme, hits)
        S["draft"] = {"ms": round(1000 * (time.time() - t0)), "words": len(d.split()), "text": d}; tick("draft")
        qa = draft_qa(d, hits, body); S["check"] = {"flags": lexical_check(d, hits, body), "qa": qa}; tick("check")
    return rec


def main():
    use_llm = "--no-llm" not in sys.argv
    started = datetime.now(); t_run = time.time()
    df = pd.read_csv(ROOT / "data" / "reviews.csv")
    n = len(df)
    t0 = time.time(); X = embed([review_text(a, b) for a, b in zip(df.title, df.body)]); t_embed = time.time() - t0
    y = df.theme.values
    lr_kw = {"C": CFG["classifier"]["C"], "class_weight": CFG["classifier"]["class_weight"], "max_iter": CFG["classifier"]["max_iter"]}
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=7)
    t0 = time.time()
    proba = cross_val_predict(LogisticRegression(**lr_kw), X, y, cv=skf, method="predict_proba")
    t_clf = time.time() - t0
    classes = sorted(set(y))
    pred = np.array(classes)[proba.argmax(axis=1)]
    oof_acc = float((pred == y).mean())
    per_theme = {c: round(float((pred[y == c] == c).mean()), 3) for c in classes}
    df["pred_theme"] = pred; df["pred_theme_conf"] = proba.max(axis=1).round(3)
    df["sentiment"] = [sentiment_from_stars(s) for s in df.stars]
    df["cancel_intent"] = df.body.str.contains(r"cancel|stop sending|not working|looking at alternatives", case=False, regex=True)
    ret = Retriever()
    gists, quotes, asks, actions, reasons, shorts, drafts, qa_scores, qa_failed, traces, d_secs = [], [], [], [], [], [], [], [], [], [], []
    for i, r in df.iterrows():
        rd = read_review(r.title, r.body) if use_llm else {"gist": "", "quote": "", "quote_rejected": "", "asks_for": "nothing", "ms": 0, "model": None}
        rule = review_rule(r.pred_theme, r.sentiment)
        hits, d, qa, fl, support, t_d = [], "", None, [], [], None
        if rule["action"] == "draft_reply":
            hits = ret.search(f"{r.title}. {r.body}", k=TOP_K, category=RV["theme_to_kb"].get(r.pred_theme))
            if use_llm:
                t0 = time.time()
                try:
                    d = draft_public_reply(r.title, r.body, r.pred_theme, hits)
                except Exception as e:
                    d = f"[draft failed: {e}]"
                t_d = time.time() - t0
                fl = lexical_check(d, hits, r.body); qa = draft_qa(d, hits, r.body)
                try:
                    support = sentence_support(d, hits, r.body, embed)
                except Exception:
                    support = []
        print(f"{r.id} {r.stars}★ {r.pred_theme:<13} {rule['action']:<20} {('drafted %.1fs ' % t_d) if t_d else ''}{'QA ' + str(qa['score']) if qa else ''}", flush=True)
        gists.append(rd["gist"]); quotes.append(rd["quote"]); asks.append(rd["asks_for"])
        actions.append(rule["action"]); reasons.append(rule["reason"]); shorts.append(rule["short"])
        drafts.append(d); qa_scores.append(qa["score"] if qa else None); qa_failed.append("; ".join(qa["failed"]) if qa else ""); d_secs.append(round(t_d, 1) if t_d else None)
        traces.append({"id": r.id, "source": r.source, "posted_at": r.posted_at, "stars": int(r.stars), "product": r["product"], "reviewer": r.reviewer,
                       "title": r.title, "body": r.body, "label_theme": r.theme,
                       "stages": {"embed": {"model": CFG["models"]["embed"], "dim": int(X.shape[1]), "ms": round(1000 * t_embed / n, 1)},
                                  "theme": {"ms": round(1000 * t_clf / n, 2), "out_of_fold": True, "probs": {c: round(float(p), 3) for c, p in zip(classes, proba[i])}},
                                  "sentiment": {"from": "stars", "value": r.sentiment},
                                  "read": rd,
                                  "retrieve": {"hits": [{"doc": x["doc"], "heading": x["heading"], "title": x.get("title", ""), "text": x["text"]} for x in hits]},
                                  "rule": rule,
                                  "draft": None if t_d is None else {"model": DRAFT_MODEL, "ms": round(1000 * t_d), **DRAFT_OPTIONS, "words": len(d.split()), "text": d},
                                  "check": None if t_d is None else {"flags": fl, "passed": not fl, "qa": qa, "support": support}}})
    df["gist"] = gists; df["quote"] = quotes; df["asks_for"] = asks
    df["action"] = actions; df["action_reason"] = reasons; df["action_short"] = shorts
    df["draft"] = drafts; df["draft_seconds"] = d_secs; df["qa_score"] = qa_scores; df["qa_failed"] = qa_failed
    df.to_csv(OUT / "voc_results.csv", index=False)
    with open(OUT / "voc_trace.jsonl", "w") as f:
        for t in traces:
            f.write(json.dumps(t) + "\n")
    drafted = df[df.action == "draft_reply"]
    run = {"run_id": started.strftime("voc-%Y%m%d-%H%M%S"), "config_version": CFG["version"], "config_hash": config_hash(),
           "started_at": started.isoformat(timespec="seconds"), "finished_at": datetime.now().isoformat(timespec="seconds"), "wall_seconds": round(time.time() - t_run, 1),
           "reviews": int(n), "window": [df.posted_at.min(), df.posted_at.max()], "sources": {k: int(v) for k, v in df.source.value_counts().items()},
           "embed_model": CFG["models"]["embed"], "draft_model": DRAFT_MODEL if use_llm else None, "llm": use_llm,
           "theme_oof_accuracy": round(oof_acc, 3), "theme_oof_per_theme": per_theme, "themes": classes,
           "sentiments": {k: int(v) for k, v in df.sentiment.value_counts().items()},
           "actions": {k: int(v) for k, v in df.action.value_counts().items()},
           "drafted": int(len(drafted)), "qa_critical": int((drafted.qa_score == 0).sum()) if use_llm else None,
           "quotes_kept": int((df.quote != "").sum()), "quotes_rejected": int(sum(1 for t in traces if t["stages"]["read"].get("quote_rejected"))),
           "planted_trend": "price complaints are weighted into the last three weeks on purpose, to give the page a rise to surface",
           "timing_seconds": {"embed_all": round(t_embed, 2), "theme_cv": round(t_clf, 2), "draft_total": round(float(pd.Series(d_secs).fillna(0).sum()), 1)}}
    (OUT / "voc_run.json").write_text(json.dumps(run, indent=2))
    print("\nout-of-fold theme accuracy:", round(oof_acc, 3), per_theme)
    print(df.action.value_counts().to_string())
    print("wrote out/voc_results.csv, voc_trace.jsonl, voc_run.json")


if __name__ == "__main__":
    main()
