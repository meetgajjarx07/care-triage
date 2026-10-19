"""Live triage page: paste one email and watch it handled, one step at a time.

Six steps in plain words, each one filling in as the system finishes it:
what the email is about, which policy applies, who should handle it, a first
draft, whether the draft is safe, and a person's decision. The technical view
(timings, model names, probabilities, retrieval ranks, the full scorecard) is
one click away at the bottom, under "How it decided".

Same code path as the batch pipeline (triage.triage_email). Needs Ollama with
the embedding model; drafting also needs the drafting model. Both are checked
before the button is enabled, so the page says what is missing instead of
failing half way.
"""
import html
import time

import altair as alt
import pandas as pd
import streamlit as st

from ui import (G40, G90, INK, CRIT, LABELS, ROUTE_LABEL, BAND_HIGH, BAND_MED, h, page_header, footer,
                section, tag, route_tag, band_tag, qa_tag, sentiment_dot, fmt_ms, faithfulness, highlight_draft,
                notification, ollama_status, add_review, flash, load_json, load_reviews)
from config import CFG
from views import _qa_table, _provenance

# Fresh emails, not in data/emails.csv, written in the voice of the customers
# the real inbox would see. Fictional people.
EXAMPLES = {
    "Scan got worse, wants her money back": (
        "Patricia Nowak", "my scan went down",
        "I have been on the Bone Builder Pack for 14 months, every single day, and my DEXA last week shows my spine went from "
        "minus 2.4 to minus 2.6. I have the scan reports. I was promised my bones would get stronger. I would like a refund."),
    "Charged twice this month": (
        "Jean Whitford", "two charges on my card",
        "My Visa statement shows two charges of $73.19 from you on the 3rd and again on the 5th, but I only received one box of "
        "AlgaeCal Plus. I am on the monthly subscription. Please refund one of them, or tell me what happened."),
    "Scared after a diagnosis, asks about her medication": (
        "Margaret Holloway", "just diagnosed, not sure what to do",
        "My doctor told me on Tuesday that I have osteoporosis in my spine, T-score minus 2.8. She wants me to start Fosamax. "
        "I would rather try something natural first but I am honestly frightened of breaking a hip like my mother did. "
        "Can I take AlgaeCal Plus together with the Fosamax, or instead of it? I am 67 and otherwise healthy."),
    "Wants to take all the capsules at once": (
        "Evelyn Marchand", "all four capsules in the morning?",
        "I take a lot of pills in the morning and it would be much easier to take all four AlgaeCal Plus capsules together with "
        "breakfast. Does it still work the same way if I do that, or do I really have to split them up?"),
    "Package stuck for two weeks": (
        "Harold Benson", "order not here yet",
        "Order 7741902 was shipped on the 1st according to your email and the tracking has said 'in transit' for 13 days. "
        "I have four days of Plus left. Can you send another one or tell me what is going on?"),
}

STEPS = [  # (key, question, what happens while it runs)
    ("about", "What is this email about?", "reading the email"),
    ("policy", "Which policy applies?", "looking through the policy library"),
    ("who", "Who should handle it?", "applying the routing rules"),
    ("draft", "A first draft", "writing, from the policy paragraphs only"),
    ("safe", "Is the draft safe?", "checking the draft"),
    ("person", "A person decides", ""),
]
STAGE_TO_STEP = {"embed": 0, "classify": 1, "retrieve": 2, "route": 3, "draft": 4, "check": 5}
MOOD = {"negative": "unhappy", "neutral": "calm", "positive": "happy"}
CRITICAL = [("grounded", "Sticks to the policy", "every number and instruction in the draft comes from the policy paragraphs or the customer's own email"),
            ("no_refund_promise", "Does not promise a refund", "only a person can decide that"),
            ("no_medical_advice", "Does not give medical advice", "it may suggest the customer ask their doctor, never tell them what to take")]

CSS = f"""<style>
.step {{ display: grid; grid-template-columns: 34px 1fr; gap: 12px; padding: 14px 16px 14px 14px; background: #fff; border: 1px solid #e0e0e0; margin-bottom: 8px; }}
.step .num {{ width: 28px; height: 28px; border-radius: 50%; background: #0f62fe; color: #fff; font-size: 13px; font-weight: 600; display: flex; align-items: center; justify-content: center; margin-top: 2px; }}
.step.pending .num {{ background: #e0e0e0; color: #525252; }}
.step.flag .num {{ background: {CRIT}; }}
.step.skip .num {{ background: #8d8d8d; }}
.step .q {{ font-size: 12px; line-height: 16px; letter-spacing: 0.32px; color: #525252; }}
.step .a {{ font-size: 18px; line-height: 26px; color: {INK}; margin: 2px 0 4px; }}
.step .a.small {{ font-size: 14px; line-height: 20px; white-space: pre-wrap; }}
.step .why {{ font-size: 13px; line-height: 18px; color: #525252; max-width: 80ch; }}
.step.pending .a {{ color: #8d8d8d; font-size: 14px; }}
.chk {{ display: flex; gap: 10px; align-items: flex-start; font-size: 14px; line-height: 20px; margin: 6px 0; }}
.chk .ic {{ flex: 0 0 18px; width: 18px; height: 18px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: #fff; margin-top: 1px; }}
.chk .ic.ok {{ background: #24a148; }} .chk .ic.bad {{ background: {CRIT}; }}
.chk .d {{ color: #525252; font-size: 12px; line-height: 16px; }}
.chk .ev {{ color: {CRIT}; font-size: 13px; }}
.pill {{ display: inline-block; font-size: 12px; line-height: 16px; padding: 2px 8px; border-radius: 20px; margin-left: 6px; vertical-align: middle; }}
.pill.ok {{ background: #a7f0ba; color: #0e6027; }} .pill.warn {{ background: #fcf4d6; color: #684e00; border: 1px solid #f1c21b; }} .pill.bad {{ background: #ffd7d9; color: #a2191f; }}
</style>"""


def _esc(s):
    return html.escape(str(s or ""))


def _band_words():
    """How often each confidence band is right, from out-of-fold predictions in models/eval.json."""
    ev = load_json("eval")
    rows = ev.get("category", {}).get("oof", {}).get("rows", [])
    acc = {"high": 0.88, "medium": 0.79, "low": 0.52}
    if rows:
        d = pd.DataFrame(rows)
        d["band"] = pd.cut(d.conf, [-1, BAND_MED, BAND_HIGH, 2], labels=["low", "medium", "high"])
        d["ok"] = d.true == d.pred
        for b, g in d.groupby("band", observed=True):
            if len(g):
                acc[str(b)] = float(g.ok.mean())
    return acc


def _in_n(p):
    """0.88 -> 'about 9 times in 10'; 0.79 -> 'about 4 times in 5'; 0.52 -> 'about half the time'."""
    if p >= 0.95: return "almost every time"
    if p >= 0.85: return "about 9 times in 10"
    if p >= 0.75: return "about 4 times in 5"
    if p >= 0.6: return "about 2 times in 3"
    if p >= 0.45: return "about half the time"
    return "less than half the time"


def _step(i, state, q, answer="", why="", extra=""):
    """state: pending | done | flag | skip"""
    h(f'<div class="step {state}"><div class="num">{i + 1}</div><div><div class="q">{q}</div>'
      f'<div class="a{" small" if state == "done" and len(answer) > 160 else ""}">{answer}</div>{extra}'
      + (f'<div class="why">{why}</div>' if why else "") + '</div></div>')


def _render_steps(box, rec, upto=None):
    """Draw the six step cards into `box`; steps beyond `upto` (a stage name) show as pending."""
    S = rec.get("stages", {})
    done = 6 if upto is None else STAGE_TO_STEP[upto] + 1
    route = (S.get("route") or {}).get("decision")
    bands = _band_words()
    with box.container():
        # 1 about
        if done >= 2 and S.get("classify"):
            C = S["classify"]; band = C["band"]
            sure = {"high": "Sure", "medium": "Fairly sure", "low": "Not sure"}[band]
            tail = "" if band != "low" else " A person should check this one before trusting the sort."
            _step(0, "done", STEPS[0][1], f'{LABELS[C["pred_category"]]}. The customer sounds {MOOD[C["pred_sentiment"]]}.',
                  f'{sure}: at this confidence level it is right {_in_n(bands[band])}.{tail} It learned this from 110 emails a person labelled by hand.')
        else:
            _step(0, "pending", STEPS[0][1], STEPS[0][2] + "…" if done >= 1 else "")
        # 2 policy
        if done >= 3 and S.get("retrieve"):
            seen = list(dict.fromkeys((x.get("title", x["doc"]), x["heading"]) for x in S["retrieve"]["hits"]))
            lines = "".join(f'<div>{_esc(t)}: <b>{_esc(hd)}</b></div>' for t, hd in seen)
            _step(1, "done", STEPS[1][1], f'<div style="font-size:15px;line-height:22px">{lines}</div>',
                  "From a small policy library built from AlgaeCal's public pages. These paragraphs are the only facts the draft is allowed to use.")
        else:
            _step(1, "pending", STEPS[1][1], STEPS[1][2] + "…" if done == 2 else "")
        # 3 who
        if done >= 4 and S.get("route"):
            R = S["route"]
            if R["decision"] == "consultant_call":
                _step(2, "done", STEPS[2][1], "A Bone Health Consultant calls.",
                      f'{R["reason"][0].upper() + R["reason"][1:]}. This is a plain rule, not a guess: some emails should never get a templated reply.')
            else:
                _step(2, "done", STEPS[2][1], "The care team, with a first draft to start from.",
                      "No rule says this needs a phone call and the policy covers it, so the system writes a draft for a person to read.")
        else:
            _step(2, "pending", STEPS[2][1], STEPS[2][2] + "…" if done == 3 else "")
        # 4 draft, 5 safe
        if route == "consultant_call":
            _step(3, "skip", STEPS[3][1], "Skipped on purpose.", "Consultants call. The system never drafts on their behalf; they see the policy paragraphs above when they pick up the phone.")
            _step(4, "skip", STEPS[4][1], "Nothing to check.", "")
        elif S.get("route") and not rec.get("_want_draft", True):
            _step(3, "skip", STEPS[3][1], "Drafting was switched off for this run.", "")
            _step(4, "skip", STEPS[4][1], "Nothing to check.", "")
        else:
            if done >= 5 and S.get("draft"):
                D = S["draft"]
                _step(3, "done", STEPS[3][1], _esc(D["text"]),
                      f'Written in {max(1, round(D["ms"] / 1000))} second{"" if round(D["ms"] / 1000) <= 1 else "s"} by a small language model on this laptop, using only the paragraphs in step 2. Nobody has read it yet.')
            else:
                _step(3, "pending", STEPS[3][1], STEPS[3][2] + "…" if done == 4 else "")
            if done >= 6 and S.get("check"):
                K = S["check"]; qa = K["qa"]; byk = {c["key"]: c for c in qa["checks"]}
                rows = ""
                for key, label, why in CRITICAL:
                    c = byk[key]
                    ev = f'<div class="ev">It wrote: “{_esc(c["evidence"])}”</div>' if (not c["ok"] and c["evidence"]) else ""
                    rows += f'<div class="chk"><span class="ic {"ok" if c["ok"] else "bad"}">{"✓" if c["ok"] else "✕"}</span><div><div>{label}</div><div class="d">{why}</div>{ev}</div></div>'
                minor = [c for c in qa["checks"] if not c["critical"]]
                n_ok = sum(1 for c in minor if c["ok"])
                all_ok = n_ok == len(minor)
                rows += (f'<div class="chk"><span class="ic {"ok" if all_ok else "bad"}">{"✓" if all_ok else "!"}</span><div><div>Also: answers the question first, under {CFG["draft_qa"]["max_words"]} words, plain tone, signed off</div>'
                         f'<div class="d">{n_ok} of {len(minor)}' + ("" if all_ok else ": " + ", ".join(c["label"].lower() for c in minor if not c["ok"])) + '</div></div></div>')
                if qa["critical_fail"]:
                    verdict = 'Flagged. <span class="pill bad">a person must read this closely</span>'
                elif qa["score"] < 100:
                    verdict = 'Mostly fine. <span class="pill warn">one small thing to fix</span>'
                else:
                    verdict = 'Looks safe. <span class="pill ok">all checks passed</span>'
                _step(4, "flag" if qa["critical_fail"] else "done", STEPS[4][1], verdict, "", rows)
            else:
                _step(4, "pending", STEPS[4][1], STEPS[4][2] + "…" if done == 5 else "")
        # 6 person
        if done >= 6 and S.get("route"):
            if route == "consultant_call":
                _step(5, "done", STEPS[5][1], "The consultant, on the phone.", "The system's job ended at step 3. Nothing is sent by this tool.")
            elif S.get("check"):
                _step(5, "done", STEPS[5][1], "Approve, or discard. Buttons below.", "A person reads every draft before anything goes out. Nothing is sent by this tool.")
            else:
                _step(5, "done", STEPS[5][1], "A person writes the reply.", "")
        else:
            _step(5, "pending", STEPS[5][1], "")


def _technical(rec, run):
    """The engineer's view, under an expander: stage timings, probabilities, retrieval ranks, full scorecard."""
    S = rec["stages"]
    C = S["classify"]; R = S["route"]; D = S.get("draft"); K = S.get("check")
    total = S["embed"]["ms"] + C["ms"] + S["retrieve"]["ms"] + (D["ms"] if D else 0) + (K["ms"] if K else 0)
    f = faithfulness(K["support"]) if K else None
    h('<div class="scores">'
      + f'<div class="score"><div class="l">Email</div><div class="v mono">{rec["id"]}</div></div>'
      + f'<div class="score"><div class="l">Category</div><div class="v">{LABELS[C["pred_category"]]}</div></div>'
      + f'<div class="score"><div class="l">Confidence</div><div class="v">{C["band"].capitalize()} · {C["confidence"]:.2f}</div></div>'
      + f'<div class="score"><div class="l">Sentiment</div><div class="v">{C["pred_sentiment"]}</div></div>'
      + f'<div class="score"><div class="l">Route</div><div class="v">{ROUTE_LABEL[R["decision"]]}</div></div>'
      + (f'<div class="score"><div class="l">Draft QA</div><div class="v" style="color:{CRIT if K["qa"]["critical_fail"] else INK}">{K["qa"]["score"]} / 100</div></div>' if K else "")
      + (f'<div class="score"><div class="l">Sentence support</div><div class="v">{f:.0%}</div></div>' if f is not None else "")
      + f'<div class="score"><div class="l">Total time</div><div class="v">{fmt_ms(total)}</div></div>'
      + '</div>')
    st.write("")
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        stage_rows = [("embed", f'<code>{S["embed"]["model"]}</code> · {S["embed"]["dim"]} dims', S["embed"]["ms"]),
                      ("classify", f'two logistic regressions · {tag(LABELS[C["pred_category"]], "g")}{band_tag(C["band"])} p={C["confidence"]:.2f} · {sentiment_dot(C["pred_sentiment"])}', C["ms"]),
                      ("retrieve", f'BM25 + dense, reciprocal rank fusion, top {S["retrieve"]["k"]}', S["retrieve"]["ms"]),
                      ("route", route_tag(R["decision"]) + (tag(R["short"], "n") if R.get("short") else "") + f' rule <code>{R["rule_id"] or "default"}</code>', 0.01),
                      ("draft", f'<code>{D["model"]}</code> · temperature {D["temperature"]} · seed {D["seed"]} · {D["words"]} words' if D else "skipped", D["ms"] if D else None),
                      ("check", (qa_tag(K["qa"]["score"], K["qa"]["critical_fail"]) + f' {K["qa"]["passed"]} of {K["qa"]["total"]} rules' + (" · " + "; ".join(K["flags"]) if K["flags"] else "")) if K else "skipped", K["ms"] if K else None)]
        for i, (name, body, ms) in enumerate(stage_rows):
            h(f'<div class="stage"><div class="n">0{i + 1}</div><div><div class="h"><span class="name">{name}</span><span class="ms">{fmt_ms(ms) if ms is not None else "—"}</span></div><div class="body">{body}</div></div></div>')
    with c2:
        cat = C["category"]
        pc = pd.DataFrame({"label": [LABELS[k] for k in cat], "p": list(cat.values()), "key": list(cat.keys())})
        pc["kind"] = pc.key.map(lambda k: "chosen" if k == C["pred_category"] else "other")
        ch = alt.Chart(pc).mark_bar(size=13).encode(
            y=alt.Y("label:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False)),
            x=alt.X("p:Q", title=None, scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
            color=alt.condition(alt.datum.kind == "chosen", alt.value(G90), alt.value(G40)), tooltip=["label", alt.Tooltip("p:Q", format=".3f")]).properties(height=165)
        st.altair_chart(ch + ch.mark_text(align="left", dx=4, color=INK, fontSize=11).encode(text=alt.Text("p:Q", format=".2f")), width="stretch")
        h(f'<div class="note">Category probabilities. High is p ≥ {BAND_HIGH}, medium ≥ {BAND_MED}, low below that.</div>')
    section("Retrieved chunks", f'top {S["retrieve"]["k"]} of {run.get("kb_chunks", "")} · {fmt_ms(S["retrieve"]["ms"])}')
    rows = [[f'<b>{x["doc"].replace(".md", "")}</b> › {_esc(x["heading"])}', _esc(x["text"][:240]) + ("…" if len(x["text"]) > 240 else ""), x["bm25_rank"], x["dense_rank"] if x["dense_rank"] else "—", f'{x["score"]:.4f}'] for x in S["retrieve"]["hits"]]
    h('<table class="stab"><thead><tr><th>Section</th><th>Text</th><th>BM25</th><th>Dense</th><th>Fused</th></tr></thead><tbody>'
      + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")
    if D and K:
        section("Draft with sentence support", "green = supported by the notes, yellow = weak, red = not found")
        qa = K["qa"]; support = K["support"]
        body = highlight_draft(D["text"], support) if support else D["text"]
        cls = "crit" if qa["critical_fail"] else ("bad" if qa["score"] < 100 else "")
        h(f'<div class="mail draft {cls}"><div class="hd"><span class="s">Draft reply</span><span class="m">{qa_tag(qa["score"], qa["critical_fail"])}</span></div>'
          + _provenance(S["retrieve"]["hits"], D["model"], D["ms"] / 1000, D["words"]) + f'<div class="bd">{body}</div></div>')
        st.write("")
        _qa_table(qa)
    with st.expander("Raw record (JSON)"):
        st.json({k: v for k, v in rec.items() if not k.startswith("_")}, expanded=1)


def _decision(rec):
    rv = load_reviews()
    done = rv[rv.id == rec["id"]] if len(rv) else rv
    if len(done):
        x = done.iloc[-1]
        notification("success" if x.action != "discard" else "warning", f'{x.reviewer} {"approved" if x.action == "approve" else "discarded"} this draft.', f' Logged at {str(x.at)[11:19]}. Nothing was sent.')
        return
    b1, b2, b3 = st.columns([1, 1, 2.4])
    if b1.button("Approve draft", type="primary", key=f"ap_{rec['id']}", width="stretch"):
        add_review(id=rec["id"], action="approve", reviewer=st.session_state.get("reviewer", "khushi")); flash(f"{rec['id']} approved"); st.rerun()
    if b2.button("Discard draft", key=f"di_{rec['id']}", width="stretch"):
        add_review(id=rec["id"], action="discard", reviewer=st.session_state.get("reviewer", "khushi"), reason="live triage"); flash(f"{rec['id']} draft discarded", ":material/delete:"); st.rerun()
    h('<div class="note">Approving means a person agreed with the draft. Sending it is the care team\'s job in their own mail tool, not this one.</div>')


def panel(key="live", default_index=1, technical=True):
    """The email picker on the left and the six steps on the right. Used by the Live
    triage page and by the Walkthrough; `key` keeps their widgets and results apart."""
    run = load_json("run")
    h(CSS)
    ok, models = ollama_status()
    want = CFG["models"]
    embed_ok = ok and want["embed"].split(":")[0] in models
    draft_ok = ok and want["draft"].split(":")[0] in models
    if not ok:
        notification("error", "Ollama is not running.", " Start it (the Ollama app, or <code>ollama serve</code>), then reload this page. The rest of the dashboard works without it.")
    elif not embed_ok:
        notification("error", f"Embedding model <code>{want['embed']}</code> is not pulled.", f" Run <code>ollama pull {want['embed']}</code>, then reload.")
    elif not draft_ok:
        notification("warning", f"Drafting model <code>{want['draft']}</code> is not pulled.", f" Steps 1 to 3 will run; the draft is switched off. <code>ollama pull {want['draft']}</code> to enable it.")

    c1, c2 = st.columns([1, 1.25], gap="large")
    with c1:
        section("The email", "pick an example or write your own")
        ex = st.selectbox("Example", ["Write my own"] + list(EXAMPLES), index=default_index, label_visibility="collapsed", key=f"{key}_ex")
        name0, subj0, body0 = EXAMPLES.get(ex, ("", "", ""))
        a, b = st.columns([1, 1.6])
        from_name = a.text_input("From", value=name0, key=f"{key}_from_{ex}", placeholder="Customer name")
        subject = b.text_input("Subject", value=subj0, key=f"{key}_subj_{ex}", placeholder="Subject line")
        body = st.text_area("Body", value=body0, height=170, key=f"{key}_body_{ex}", placeholder="Paste the customer's email here", label_visibility="collapsed")
        want_draft = st.toggle("Write a first draft when the route allows it", value=draft_ok, disabled=not draft_ok, key=f"{key}_draft",
                               help="The draft is the slow step: a small language model on the CPU, roughly 2 to 20 seconds depending on the machine.")
        go = st.button("Handle this email", type="primary", disabled=not (embed_ok and body.strip()), key=f"{key}_go")
        h('<div class="note" style="margin-top:10px">What happens, in order: it works out what the email is about, finds the policy that applies, decides whether a person should call or a draft will do, writes the draft from those policy paragraphs only, checks the draft, and then a person decides. The same six steps run on every email in the Inbox.</div>')
    with c2:
        section("Step by step", "each step fills in as it finishes")
        box = st.empty()

    rec = st.session_state.get(f"{key}_rec")
    if go:
        from triage import triage_email
        rec = {"stages": {}, "_want_draft": want_draft}
        _render_steps(box, rec, upto="embed")

        def progress(stage, r):
            r["_want_draft"] = want_draft
            _render_steps(box, r, upto=stage)
            time.sleep(0.25)  # let the eye catch each step

        try:
            with st.spinner("Working…", show_time=True):
                rec = triage_email(subject, body, from_name, draft=want_draft, progress=progress)
            rec["_want_draft"] = want_draft
            st.session_state[f"{key}_rec"] = rec
        except Exception as e:
            notification("error", "The run failed part way.", f" {_esc(str(e))[:300]}. Check that Ollama is running and both models are pulled.")
            rec = None
    if rec and rec.get("stages", {}).get("embed"):
        _render_steps(box, rec)
        if rec["stages"].get("check"):
            with c2:
                _decision(rec)
        if technical:
            st.write("")
            with st.expander("How it decided (the technical view)"):
                _technical(rec, run)
    else:
        with box.container():
            for i, (key_, q, _) in enumerate(STEPS):
                _step(i, "pending", q, "")


def live():
    run = load_json("run")
    page_header("Live triage", "Paste one customer email and watch it handled, one step at a time, on this laptop. "
                "Nothing leaves the machine and nothing is sent.", run)
    panel()
    footer(run)
