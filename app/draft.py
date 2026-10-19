"""
Draft a reply from the retrieved policy chunks using a local model (llama3.2
through Ollama). The draft is a starting point for a person, not an auto-send.

Routing rule lives here too, because it is the thing that actually matters
operationally: some emails should never get a templated reply, they should
get a phone call from a Bone Health Consultant.
"""
import re

from config import CFG

MODEL = CFG["models"]["draft"]
DRAFT_OPTIONS = dict(CFG["models"]["draft_options"])
MAX_WORDS = int(CFG["draft_qa"]["max_words"])
BANDS = CFG["confidence_bands"]

SYSTEM = f"""You write first drafts of replies for AlgaeCal Customer Care.
Rules:
- Use ONLY the facts in the POLICY NOTES. If the notes do not cover it, say the team will check and come back, do not guess.
- Never promise a refund amount. Never give medical advice; suggest the customer confirm with their doctor or pharmacist when health comes up.
- Plain, warm, short. Under {MAX_WORDS} words. No bullet points. No exclamation marks.
- Answer the actual question first. Do not open with thanks for reaching out.
- Sign off as "AlgaeCal Customer Care"."""


def _rule_matches(rule, category, sentiment, body):
    w = rule["when"]
    if w.get("category") != category:
        return False
    if "sentiment" in w and w["sentiment"] != sentiment:
        return False
    if "body_regex" in w and not re.search(w["body_regex"], body, re.I):
        return False
    return True


def route_rule(category, sentiment, body):
    """Evaluate config/triage.yaml routing_rules top to bottom; first match wins.
    Returns {"action", "reason", "short", "rule_id"}. The default route has
    rule_id None and an empty short label."""
    for rule in CFG["routing_rules"]:
        if _rule_matches(rule, category, sentiment, body):
            return {"action": rule["action"], "reason": rule["reason"], "short": rule.get("short", ""), "rule_id": rule["id"]}
    d = CFG["default_route"]
    return {"action": d["action"], "reason": d["reason"], "short": "", "rule_id": None}


def route(category, sentiment, body):
    """Returns (route, reason). 'consultant_call' means a human calls, no auto draft."""
    r = route_rule(category, sentiment, body)
    return r["action"], r["reason"]


# words that, if the model uses them and the notes do not, usually mean it is
# giving an instruction it invented. plus any number the notes do not contain.
DIRECTIVE = {"taper", "tapering", "stop", "stopping", "discontinue", "double", "doubling", "increase",
             "increasing", "reduce", "reducing", "avoid", "avoiding", "halve", "skip", "skipping", "switch",
             "switching", "combine", "mix", "mixing", "refrigerate", "freeze", "crush", "dissolve",
             "hour", "hours", "days", "weeks", "months", "minutes"}


def lexical_check(draft, chunks, email_body):
    """Flags numbers and instruction words in the draft that appear in neither the
    policy notes nor the customer's email. Returns a list of flags, empty = passed.

    This is deliberately narrow. My first version scored every content word and
    flagged 75 of 76 drafts, because a polite reply uses plenty of words the
    policy does not ("thrilled", "loyalty"). I also tried asking llama3.2 to
    judge its own drafts against the notes. It missed a real error (it had
    written that AlgaeCal Plus contains strontium; it does not) and flagged
    sentences copied straight from the notes, then got stuck in a loop. A 3B
    model is not a reviewer. Numbers and directives are the claims that hurt
    when they are wrong, so that is what this checks. A person still reads
    every draft before it goes out."""
    notes = " ".join(c["text"] for c in chunks) + " " + email_body
    have_nums = set(re.findall(r"\d+(?:\.\d+)?", notes))
    have_words = set(re.findall(r"[a-z]+", notes.lower()))
    flags = []
    for n in sorted(set(re.findall(r"\d+(?:\.\d+)?", draft)) - have_nums):
        flags.append(f"number {n} not in notes")
    for w in sorted(set(re.findall(r"[a-z]+", draft.lower())) & DIRECTIVE):
        stems = {w, w.rstrip("s"), w.replace("ing", ""), w.replace("ing", "e")}
        if not (stems & have_words):
            flags.append(f"instruction '{w}' not in notes")
    return flags


def confidence_band(p):
    """Categorical confidence the way support tools show it. Thresholds checked on
    5-fold out-of-fold predictions: high (>=0.55) is right 88% of the time,
    medium 79%, low (<0.35) 52%. See models/eval.json."""
    return "high" if p >= BANDS["high"] else ("medium" if p >= BANDS["medium"] else "low")


QA_CHECKS = [
    # (key, label, critical, description)
    ("grounded", "Grounded in policy", True, "no number or instruction word outside the retrieved notes or the customer email"),
    ("no_refund_promise", "No refund promise", True, "does not state a refund amount or promise a refund outcome"),
    ("no_medical_advice", "No medical directive", True, "does not tell the customer to start, stop or change a medicine or dose on its own authority"),
    ("answers_first", "Answers the question first", False, "does not open with thanks or a preamble"),
    ("length", f"Under {MAX_WORDS} words", False, "the system prompt's limit"),
    ("tone", "Plain tone", False, "no exclamation marks, no bullet points"),
    ("signoff", "Signed as Customer Care", False, "ends with the team sign-off"),
]


def draft_qa(draft, chunks, email_body):
    """Deterministic QA scorecard for a draft. Each check is a rule taken from the
    system prompt or from the lexical grounding check, so it is cheap, explainable
    and does not ask the model to grade itself. Critical fails zero the score,
    the way QA tools treat an auto-fail category. Returns dict with per-check
    results, a 0-100 score and a list of failed labels."""
    d = draft.strip(); low = d.lower()
    flags = lexical_check(d, chunks, email_body)
    res = {}
    res["grounded"] = (not flags, "; ".join(flags) if flags else "")
    m = re.search(r"(refund(ed)? (of|in full|you)|full refund|will (be )?refund|refund will)", low)
    if m is None and "refund" in low:
        m = re.search(r"(\$\s?\d[\d.,]*|\d+\s?(usd|dollars))", low)  # an amount next to refund talk
    res["no_refund_promise"] = (m is None, m.group(0) if m else "")
    m = re.search(r"\b(stop taking|discontinue|taper|double (the|your) dose|increase (the|your) dose|reduce (the|your) dose|skip (a|the) dose|take .{0,20}instead of your)\b", low)
    res["no_medical_advice"] = (m is None, m.group(0) if m else "")
    first = re.sub(r"^(dear|hi|hello)\s+[^,\n]+,?\s*", "", low).strip()[:60]
    res["answers_first"] = (not first.startswith(("thank", "thanks", "we appreciate", "i appreciate")), first[:40])
    n = len(d.split())
    res["length"] = (n <= MAX_WORDS, f"{n} words")
    bad = ("!" in d) or bool(re.search(r"^\s*[-*•]\s", d, re.M))
    res["tone"] = (not bad, "exclamation or bullets" if bad else "")
    res["signoff"] = ("customer care" in low[-80:], "")
    crit_fail = any(not res[k][0] for k, _, c, _ in QA_CHECKS if c)
    passed = sum(1 for k, *_ in QA_CHECKS if res[k][0])
    score = 0 if crit_fail else round(100 * passed / len(QA_CHECKS))
    return {"score": score, "critical_fail": crit_fail, "passed": passed, "total": len(QA_CHECKS),
            "checks": [{"key": k, "label": lab, "critical": c, "ok": res[k][0], "evidence": res[k][1], "why": why} for k, lab, c, why in QA_CHECKS],
            "failed": [lab for k, lab, *_ in QA_CHECKS if not res[k][0]]}


def _sentences(text):
    parts = re.split(r"(?<=[.?!])\s+|\n+", text.strip())
    return [p.strip() for p in parts if len(p.split()) >= 4]


def sentence_support(draft, chunks, email_body, embed_fn):
    """Claim-level groundedness without a judge model. Every sentence of the draft
    is embedded and compared with every sentence of the retrieved notes and of the
    customer's email; the best cosine similarity is its support score. The UI
    thresholds it. This is the offline version of Ragas faithfulness: supported
    sentences / all sentences."""
    claims = [c for c in _sentences(draft) if not re.match(r"^(dear|hi|hello)\b", c, re.I) and "customer care" not in c.lower()]
    ctx = []
    for c in chunks:
        for sent in _sentences(re.sub(r"^## .*$", "", c["text"], flags=re.M)):
            ctx.append((f"{c['doc']} › {c['heading']}", sent))
    for sent in _sentences(email_body):
        ctx.append(("customer email", sent))
    if not claims or not ctx:
        return []
    A = embed_fn([f"search_query: {c}" for c in claims])
    B = embed_fn([f"search_document: {t}" for _, t in ctx])
    S = A @ B.T
    out = []
    for i, c in enumerate(claims):
        j = int(S[i].argmax())
        out.append({"sentence": c, "sim": round(float(S[i, j]), 3), "source": ctx[j][0], "evidence": ctx[j][1]})
    return out


def draft_reply(email_body, from_name, category, chunks, model=MODEL):
    import ollama
    notes = "\n\n".join(f"[{c['title']} > {c['heading']}]\n{c['text']}" for c in chunks)
    first = from_name.split()[0] if from_name else "there"
    user = f"CATEGORY: {category}\nCUSTOMER FIRST NAME: {first}\n\nPOLICY NOTES:\n{notes}\n\nCUSTOMER EMAIL:\n{email_body}\n\nWrite the reply."
    r = ollama.chat(model=model, options=DRAFT_OPTIONS,
                    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])
    return r["message"]["content"].strip()


if __name__ == "__main__":
    from retrieve import Retriever
    r = Retriever()
    body = "Can I take all four AlgaeCal Plus capsules at once in the morning? I take a lot of pills and it is easier to do them together."
    chunks = r.search(body, k=4, category="dosage_question")
    print(route("dosage_question", "neutral", body))
    print(draft_reply(body, "Evelyn Marchand", "dosage_question", chunks))
