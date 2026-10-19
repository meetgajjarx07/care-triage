"""
Category + sentiment classifiers for support emails.

What I tried, 5-fold CV repeated 4x on the 110 labelled emails:

    TF-IDF (word + char ngrams) + logistic regression   ~59% acc   (sentiment ~64%)
    llama3.2 zero-shot, label names only                 ~54% acc on one 28-email split
    nomic-embed-text embeddings + logistic regression    ~77% acc   (sentiment ~81%)

So the classifier reuses the same local embedding model the retriever uses.
One embedding call per email, then a logistic regression that trains in well
under a second. 110 labels is still small; the categories that confuse it are
the ones that confuse people too (guarantee claim vs results question vs
"cancel because it didn't work").

python classify.py           train, print held-out report + CV number, save models/
python classify.py --llm     also run llama3.2 zero-shot on the same held-out split

Writes models/metrics.json (headline numbers) and models/eval.json (everything
the dashboard's model-quality page shows: holdout predictions per email,
per-class precision/recall, every CV fold score, the TF-IDF baseline).
"""
import sys, json, time, platform
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split, RepeatedStratifiedKFold, StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.pipeline import make_pipeline, make_union

from config import CFG

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "emails.csv"
MODELS = ROOT / "models"
EMBED_MODEL = CFG["models"]["embed"]
LR_KW = {"C": CFG["classifier"]["C"], "class_weight": CFG["classifier"]["class_weight"], "max_iter": CFG["classifier"]["max_iter"]}

CATEGORIES = ["guarantee_claim", "results_question", "safety_concern",
              "dosage_question", "shipping_issue", "subscription_billing",
              "positive_feedback"]
SENTIMENTS = ["negative", "neutral", "positive"]


def email_text(subject, body):
    # nomic wants a task prefix; "classification:" is the documented one
    return f"classification: {subject}. {body}"


def embed(texts):
    import ollama
    vecs = np.array(ollama.embed(model=EMBED_MODEL, input=list(texts))["embeddings"], dtype=np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def fit_lr(E, y, C=None):
    kw = dict(LR_KW)
    if C is not None:
        kw["C"] = C
    return LogisticRegression(**kw).fit(E, y)


def tfidf_baseline():
    return make_pipeline(
        make_union(TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True),
                   TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)),
        LogisticRegression(**LR_KW))


def report(label, labels, df, E, raw_texts, seed=7):
    y = df[label].values
    idx_tr, idx_te = train_test_split(np.arange(len(df)), test_size=0.25, random_state=seed, stratify=y)
    lr = fit_lr(E[idx_tr], y[idx_tr])
    pred = lr.predict(E[idx_te])
    proba = lr.predict_proba(E[idx_te])
    print(f"\n== {label} ==  train {len(idx_tr)}  test {len(idx_te)}")
    print(classification_report(y[idx_te], pred, zero_division=0))
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=4, random_state=1)
    folds = cross_val_score(LogisticRegression(**LR_KW), E, y, cv=cv)
    base_folds = cross_val_score(tfidf_baseline(), raw_texts, y, cv=cv)
    rep = classification_report(y[idx_te], pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y[idx_te], pred, labels=labels)
    # out-of-fold predictions for every email: each row predicted by a model that never saw it
    oof_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=3)
    oof_proba = cross_val_predict(LogisticRegression(**LR_KW), E, y, cv=oof_cv, method="predict_proba")
    classes_sorted = sorted(labels)  # sklearn orders classes_ alphabetically
    oof_pred = np.array(classes_sorted)[oof_proba.argmax(axis=1)]
    oof_cm = confusion_matrix(y, oof_pred, labels=labels)
    oof_rep = classification_report(y, oof_pred, labels=labels, output_dict=True, zero_division=0)
    headline = {"holdout_acc": round(accuracy_score(y[idx_te], pred), 3),
                "holdout_macro_f1": round(f1_score(y[idx_te], pred, average="macro"), 3),
                "cv5x4_acc": round(float(folds.mean()), 3)}
    detail = {
        "labels": labels,
        "train_n": int(len(idx_tr)), "test_n": int(len(idx_te)),
        "holdout": [{"id": df.id.iloc[i], "true": y[i], "pred": p, "conf": round(float(pr.max()), 3)}
                    for i, p, pr in zip(idx_te, pred, proba)],
        "confusion": cm.tolist(),
        "per_class": {k: {"precision": round(v["precision"], 3), "recall": round(v["recall"], 3),
                          "f1": round(v["f1-score"], 3), "support": int(v["support"])}
                      for k, v in rep.items() if k in labels},
        "cv_folds": [round(float(f), 3) for f in folds],
        "cv_mean": round(float(folds.mean()), 3), "cv_std": round(float(folds.std()), 3),
        "tfidf_cv_folds": [round(float(f), 3) for f in base_folds],
        "tfidf_cv_mean": round(float(base_folds.mean()), 3), "tfidf_cv_std": round(float(base_folds.std()), 3),
        "class_counts": {k: int(v) for k, v in pd.Series(y).value_counts().items()},
        "oof": {
            "note": "5-fold out-of-fold predictions on all rows (StratifiedKFold, random_state=3)",
            "acc": round(accuracy_score(y, oof_pred), 3),
            "macro_f1": round(f1_score(y, oof_pred, average="macro"), 3),
            "confusion": oof_cm.tolist(),
            "per_class": {k: {"precision": round(v["precision"], 3), "recall": round(v["recall"], 3),
                              "f1": round(v["f1-score"], 3), "support": int(v["support"])}
                          for k, v in oof_rep.items() if k in labels},
            "rows": [{"id": df.id.iloc[i], "true": y[i], "pred": oof_pred[i], "conf": round(float(oof_proba[i].max()), 3),
                      "p_true": round(float(oof_proba[i][classes_sorted.index(y[i])]), 3)} for i in range(len(y))],
        },
    }
    return idx_te, pred, headline, detail


def llm_zero_shot(texts, model="llama3.2"):
    import ollama
    labels = ", ".join(CATEGORIES)
    out = []
    for t in texts:
        r = ollama.chat(model=model, options={"temperature": 0}, messages=[{
            "role": "user",
            "content": f"Classify this customer support email for a bone health supplement company into exactly one of: {labels}.\nReply with the label only.\n\nEMAIL:\n{t[:1500]}"}])
        ans = r["message"]["content"].strip().lower().replace(" ", "_")
        out.append(next((c for c in CATEGORIES if c in ans), "unknown"))
    return out


if __name__ == "__main__":
    df = pd.read_csv(DATA)
    MODELS.mkdir(exist_ok=True)
    texts = [email_text(s, b) for s, b in zip(df.subject, df.body)]
    raw = [f"{s} {b}" for s, b in zip(df.subject, df.body)]
    t0 = time.time(); E = embed(texts); t_embed = time.time() - t0

    idx_te, pred_cat, m_cat, d_cat = report("category", CATEGORIES, df, E, raw)
    _, _, m_sent, d_sent = report("sentiment", SENTIMENTS, df, E, raw)

    # final models on all 110 rows; the numbers above are the honest ones
    # plain sklearn objects on disk; callers embed with embed() first
    joblib.dump(fit_lr(E, df.category), MODELS / "category.joblib")
    joblib.dump(fit_lr(E, df.sentiment), MODELS / "sentiment.joblib")

    summary = {"n": len(df), "embed_seconds_all": round(t_embed, 2),
               "category": m_cat, "sentiment": m_sent}
    eval_out = {"trained_at": datetime.now().isoformat(timespec="seconds"),
                "embed_model": EMBED_MODEL, "embed_dim": int(E.shape[1]),
                "classifier": f"LogisticRegression(C={LR_KW['C']}, class_weight={LR_KW['class_weight']}, max_iter={LR_KW['max_iter']})",
                "split": "stratified 25% holdout, random_state=7; CV = RepeatedStratifiedKFold(5x4, random_state=1)",
                "sklearn": sklearn.__version__, "python": platform.python_version(),
                "embed_seconds_all": round(t_embed, 2),
                "category": d_cat, "sentiment": d_sent}

    if "--llm" in sys.argv:
        t0 = time.time()
        llm_pred = llm_zero_shot([f"{s}\n{b}" for s, b in zip(df.subject.iloc[idx_te], df.body.iloc[idx_te])])
        y_te = df.category.values[idx_te]
        summary["llm_zero_shot"] = {"holdout_acc": round(accuracy_score(y_te, llm_pred), 3),
                                    "holdout_macro_f1": round(f1_score(y_te, llm_pred, average="macro", labels=CATEGORIES, zero_division=0), 3),
                                    "seconds_per_email": round((time.time() - t0) / len(idx_te), 2)}
        eval_out["llm_zero_shot"] = {"model": "llama3.2", **summary["llm_zero_shot"],
                                     "holdout": [{"id": df.id.iloc[i], "true": t, "pred": p} for i, t, p in zip(idx_te, y_te, llm_pred)]}
        print("\n== llama3.2 zero-shot, same held-out split ==")
        print(classification_report(y_te, llm_pred, zero_division=0))

    (MODELS / "metrics.json").write_text(json.dumps(summary, indent=2))
    (MODELS / "eval.json").write_text(json.dumps(eval_out, indent=2))
    print(json.dumps(summary, indent=2))
