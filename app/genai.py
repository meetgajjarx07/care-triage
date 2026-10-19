"""Generative steps beyond the draft, each with a guard around it.

Three uses of the local language model, the same shape as the email system
at Must IT: it grades what retrieval brought back and asks again when nothing
fits (corrective RAG), it writes a two-line brief with the facts pulled out
of the email for whoever handles it, and it writes the first draft (draft.py).
It never routes, and it never grades its own draft; the checks are rules.

Guards: the search's best match is always kept and the grader can only drop
weaker paragraphs, never add facts; when the grader rejects everything the
question is rephrased once and searched again, and if that also fails the
email is marked a content gap for a person to read closely; every extracted
fact is kept only if it appears in the customer's own text. All calls are JSON mode,
temperature 0, fixed seed, so a rerun gives the same answers.
"""
import json
import re
import time

from config import CFG

MODEL = CFG["models"]["draft"]
G = CFG.get("genai", {})
OPTIONS = dict(G.get("options", {"temperature": 0, "seed": 7, "num_predict": 200}))


def _chat(task, system, user, num_predict=None):
    """One JSON-mode call. `task` is only a label (tests fake this function by it)."""
    import ollama
    opts = dict(OPTIONS)
    if num_predict:
        opts["num_predict"] = num_predict
    r = ollama.chat(model=MODEL, options=opts, format="json",
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return r["message"]["content"]


def _json(text, default):
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text or "", re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return default


def grounded_facts(facts, email):
    """Keep a fact only if the email contains it: every number in it must appear in
    the email, and so must most of its words. Returns (kept, dropped)."""
    low = email.lower()
    words = set(re.findall(r"[a-z0-9$.]+", low))
    nums = set(re.findall(r"\d+(?:\.\d+)?", low))
    kept, dropped = [], []
    for f in facts or []:
        f = str(f).strip()
        if not f:
            continue
        fn = re.findall(r"\d+(?:\.\d+)?", f)
        fw = [w for w in re.findall(r"[a-z0-9$.]+", f.lower()) if len(w) > 2]
        ok_nums = all(n in nums for n in fn)
        ok_words = (not fw) or sum(w in words for w in fw) >= max(1, round(0.6 * len(fw)))
        (kept if (ok_nums and ok_words and (fn or fw)) else dropped).append(f)
    return kept, dropped


BRIEF_SYSTEM = """You prepare a two-line brief for a customer care agent at a supplement company.
Reply in JSON only: {"asks": "...", "check": "...", "facts": ["...", "..."]}
- asks: one plain sentence, what the customer wants.
- check: one plain sentence, what the agent should look up or confirm before replying.
- facts: short strings copied exactly from the email (order numbers, amounts, dates, doses, products, scan values). Copy, never infer. Empty list if none."""


def brief(subject, body, from_name=""):
    t0 = time.time()
    raw = _chat("brief", BRIEF_SYSTEM, f"FROM: {from_name}\nSUBJECT: {subject}\n\nEMAIL:\n{body}", num_predict=180)
    j = _json(raw, {})
    kept, dropped = grounded_facts(j.get("facts") or [], f"{subject} {body}")
    return {"model": MODEL, "ms": round(1000 * (time.time() - t0)),
            "asks": str(j.get("asks") or "").strip(), "check": str(j.get("check") or "").strip(),
            "facts": kept, "dropped_facts": dropped}


GRADE_SYSTEM = """You decide whether a policy paragraph is useful for replying to a customer's email.
Reply in JSON only: {"useful": true or false, "why": "under 12 words"}
useful is true if the paragraph is about the same subject as the email, or contains any fact, step or contact detail an agent would use in the reply.
useful is false only if the paragraph is about a different subject."""


def grade_chunks(subject, body, hits):
    """One small call per retrieved paragraph (a 3B model cannot be trusted to return
    a list for four at once; it was tried). Fails open per paragraph: if an answer
    cannot be parsed, that paragraph counts as useful, so a bad call never hides evidence."""
    t0 = time.time()
    out = []
    for h in hits:
        para = f"{h.get('title', h['doc'])} › {h['heading']}\n{h['text'][:700]}"
        j = _json(_chat("grade", GRADE_SYSTEM, f"CUSTOMER EMAIL:\n{subject}. {body}\n\nPARAGRAPH:\n{para}", num_predict=60), None)
        key = "useful" if isinstance(j, dict) and "useful" in j else ("relevant" if isinstance(j, dict) and "relevant" in j else None)
        if key:
            rel = j[key]
            rel = rel if isinstance(rel, bool) else str(rel).strip().lower() in ("true", "yes", "1")
            out.append({"relevant": rel, "why": str(j.get("why", "")).strip()})
        else:
            out.append({"relevant": True, "why": "not graded, kept"})
    return out, round(1000 * (time.time() - t0))


REWRITE_SYSTEM = """Rewrite the customer's question as a short search query made of the terms a policy page would use (under 12 words).
Reply in JSON only: {"query": "..."}"""


def rewrite_query(subject, body):
    t0 = time.time()
    j = _json(_chat("rewrite", REWRITE_SYSTEM, f"{subject}. {body}", num_predict=60), {})
    return str(j.get("query") or f"{subject}. {body}").strip(), round(1000 * (time.time() - t0))
