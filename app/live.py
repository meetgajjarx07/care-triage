"""Live triage page: paste one email, watch every stage run, review the result.

Same code path as the batch pipeline (triage.triage_email), drawn stage by
stage as each one finishes. Needs Ollama running with the embedding model;
drafting also needs the drafting model. Both are checked before the button
is enabled, so the page says what is missing instead of failing half way.
"""
import html
import time

import altair as alt
import pandas as pd
import streamlit as st

from ui import (G40, G90, INK, GREY, CRIT, LABELS, ROUTE_LABEL, BAND_HIGH, BAND_MED, h, page_header, footer,
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

STAGE_META = [
    ("embed", "01", "Embed", "turn the email into a 768-number vector"),
    ("classify", "02", "Classify", "what it is about, how the customer feels, how sure we are"),
    ("retrieve", "03", "Retrieve", "find the policy paragraphs that matter"),
    ("route", "04", "Route", "a person, or a draft for a person"),
    ("draft", "05", "Draft", "write a first reply from those paragraphs only"),
    ("check", "06", "Check", "seven rules, three of them critical"),
]


def _esc(s):
    return html.escape(str(s or ""))


def _stage_card(key, S, pending=False, skipped=""):
    n, name, what = [m[1:] for m in STAGE_META if m[0] == key][0]
    if skipped:
        ms = "—"; body = f'<span style="color:{GREY}">{skipped}</span>'
    elif pending or key not in S or S[key] is None:
        ms = "…"; body = f'<span style="color:{GREY}">{what}</span>'
    else:
        st_ = S[key]; ms = fmt_ms(st_.get("ms", 0))
        body = ""
        if key == "embed":
            body = f'<span class="mono" style="color:{GREY}">{_esc(st_["input"])}…</span> <span style="color:{GREY}">· {st_["dim"]} dims · <code>{st_["model"]}</code></span>'
        elif key == "classify":
            body = (f'{tag(LABELS[st_["pred_category"]], "g")} {band_tag(st_["band"])} '
                    f'<span style="color:{GREY}">p={st_["confidence"]:.2f} · sentiment</span> {sentiment_dot(st_["pred_sentiment"])}')
        elif key == "retrieve":
            chips = "".join(tag(f'{x["doc"].replace(".md", "")} › {x["heading"]}', "chip") for x in st_["hits"])
            body = chips
        elif key == "route":
            body = route_tag(st_["decision"]) + (tag(st_["short"], "n") if st_.get("short") else "") + f'<span style="color:{GREY}"> {st_["reason"]}</span>'
        elif key == "draft":
            body = f'<span style="color:{GREY}"><code>{st_["model"]}</code> · temperature {st_["temperature"]} · {st_["words"]} words</span>'
        elif key == "check":
            qa = st_["qa"]
            body = qa_tag(qa["score"], qa["critical_fail"]) + f'<span style="color:{GREY}"> {qa["passed"]} of {qa["total"]} checks passed' + (f' · {"; ".join(st_["flags"])}' if st_["flags"] else "") + "</span>"
    h(f'<div class="stage"><div class="n">{n}</div><div><div class="h"><span class="name">{name}</span><span class="comp">{"" if body and not pending else ""}</span>'
      f'<span class="ms">{ms}</span></div><div class="body">{body}</div></div></div>')


def _render_stages(box, rec, upto=None, running=None):
    """Draw all six stage rows into `box`. Stages after `upto` are pending."""
    S = rec["stages"]
    order = [m[0] for m in STAGE_META]
    cut = len(order) if upto is None else order.index(upto) + 1
    route = (S.get("route") or {}).get("decision")
    with box.container():
        for i, key in enumerate(order):
            if key in ("draft", "check") and route == "consultant_call":
                _stage_card(key, S, skipped="skipped: a consultant calls, there is no auto draft")
            elif key in ("draft", "check") and S.get("draft") is None and S.get("route") and not rec.get("_want_draft", True):
                _stage_card(key, S, skipped="skipped: drafting switched off for this run")
            elif i < cut and S.get(key) is not None:
                _stage_card(key, S)
            else:
                _stage_card(key, S, pending=True)


def _result(rec, run):
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
    c1, c2 = st.columns([1.15, 1], gap="large")
    with c1:
        h(f'<div class="mail"><div class="hd"><span class="s">{_esc(rec["subject"])}</span><span class="m"><code>{rec["id"]}</code> · {rec["received_at"][11:]}</span></div>'
          f'<div class="bd"><b>{_esc(rec["from_name"]) or "Customer"}</b>\n\n{_esc(rec["body"])}</div></div>')
        if R["decision"] == "consultant_call":
            st.write("")
            notification("info", "This one goes to a Bone Health Consultant as a phone call.",
                         f' {R["reason"].capitalize()}. The consultant sees the four policy paragraphs on the right when they pick up the phone. No draft is written.')
    with c2:
        cat = C["category"]
        pc = pd.DataFrame({"label": [LABELS[k] for k in cat], "p": list(cat.values()), "key": list(cat.keys())})
        pc["kind"] = pc.key.map(lambda k: "chosen" if k == C["pred_category"] else "other")
        ch = alt.Chart(pc).mark_bar(size=13).encode(
            y=alt.Y("label:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False)),
            x=alt.X("p:Q", title=None, scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
            color=alt.condition(alt.datum.kind == "chosen", alt.value(G90), alt.value(G40)), tooltip=["label", alt.Tooltip("p:Q", format=".3f")]).properties(height=165)
        st.altair_chart(ch + ch.mark_text(align="left", dx=4, color=INK, fontSize=11).encode(text=alt.Text("p:Q", format=".2f")), width="stretch")
        h(f'<div class="note">Category probabilities. High is p ≥ {BAND_HIGH}, medium ≥ {BAND_MED}. Below that the row is marked low and a person should not trust the sort.</div>')
    section("Policy the system found", f'top {S["retrieve"]["k"]} of {run.get("kb_chunks", "")} chunks · BM25 + dense, fused · {fmt_ms(S["retrieve"]["ms"])}')
    rows = [[f'<b>{x["doc"].replace(".md", "")}</b> › {_esc(x["heading"])}', _esc(x["text"][:260]) + ("…" if len(x["text"]) > 260 else ""), x["bm25_rank"], x["dense_rank"] if x["dense_rank"] else "—"] for x in S["retrieve"]["hits"]]
    h('<table class="stab"><thead><tr><th>Section</th><th>Text</th><th>BM25</th><th>Dense</th></tr></thead><tbody>'
      + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")
    if D:
        section("Draft for a person to read", "written only from the paragraphs above. Underline green = supported sentence, yellow = weak, red = not found in the notes")
        qa = K["qa"]; support = K["support"]
        show = st.toggle("Highlight sentence support", value=True, key=f"hl_{rec['id']}")
        body = highlight_draft(D["text"], support) if (show and support) else D["text"]
        cls = "crit" if qa["critical_fail"] else ("bad" if qa["score"] < 100 else "")
        h(f'<div class="mail draft {cls}"><div class="hd"><span class="s">Draft reply</span><span class="m">{qa_tag(qa["score"], qa["critical_fail"])}</span></div>'
          + _provenance(S["retrieve"]["hits"], D["model"], D["ms"] / 1000, D["words"]) + f'<div class="bd">{body}</div></div>')
        if support:
            n_un = sum(1 for s in support if s["sim"] < CFG["draft_qa"]["support_thresholds"]["weak"])
            h(f'<div class="note" style="margin-top:4px">{len(support)} sentences scored, {n_un} not found in the notes or the email. Similarity is a soft signal; the rules below are the hard one.</div>')
        st.write("")
        _qa_table(qa)
        section("Review", "the decision is appended to out/reviews.jsonl, like every other review")
        rv = load_reviews()
        done = rv[rv.id == rec["id"]] if len(rv) else rv
        if len(done):
            x = done.iloc[-1]
            notification("success" if x.action != "discard" else "warning", f'{x.reviewer} {"approved" if x.action == "approve" else "discarded"} this draft.', f' Logged at {str(x.at)[11:19]}.')
        else:
            b1, b2, b3 = st.columns([1, 1, 2])
            if b1.button("Approve draft", type="primary", key=f"ap_{rec['id']}", width="stretch"):
                add_review(id=rec["id"], action="approve", reviewer=st.session_state.get("reviewer", "khushi")); flash(f"{rec['id']} approved"); st.rerun()
            if b2.button("Discard draft", key=f"di_{rec['id']}", width="stretch"):
                add_review(id=rec["id"], action="discard", reviewer=st.session_state.get("reviewer", "khushi"), reason="live triage"); flash(f"{rec['id']} draft discarded", ":material/delete:"); st.rerun()
            h('<div class="note">Nothing here sends email. Approving means a person agreed with the draft; what happens next is the care team\'s call.</div>')


def live():
    run = load_json("run")
    page_header("Live triage", "Paste one email and watch the same pipeline run on it, stage by stage, on this machine. "
                "Nothing leaves the laptop and nothing is sent.", run)
    ok, models = ollama_status()
    want = CFG["models"]
    embed_ok = ok and want["embed"].split(":")[0] in models
    draft_ok = ok and want["draft"].split(":")[0] in models
    if not ok:
        notification("error", "Ollama is not running.", " Start it (the Ollama app, or <code>ollama serve</code>), then reload this page. The rest of the dashboard works without it.")
    elif not embed_ok:
        notification("error", f"Embedding model <code>{want['embed']}</code> is not pulled.", f" Run <code>ollama pull {want['embed']}</code>, then reload.")
    elif not draft_ok:
        notification("warning", f"Drafting model <code>{want['draft']}</code> is not pulled.", f" Sorting, policy lookup and routing will run; drafting is switched off. <code>ollama pull {want['draft']}</code> to enable it.")

    c1, c2 = st.columns([1.25, 1], gap="large")
    with c1:
        section("Email", "pick an example or write your own")
        ex = st.selectbox("Example", ["Write my own"] + list(EXAMPLES), index=1, label_visibility="collapsed", key="live_ex")
        name0, subj0, body0 = EXAMPLES.get(ex, ("", "", ""))
        a, b = st.columns([1, 1.6])
        from_name = a.text_input("From", value=name0, key=f"live_from_{ex}", placeholder="Customer name")
        subject = b.text_input("Subject", value=subj0, key=f"live_subj_{ex}", placeholder="Subject line")
        body = st.text_area("Body", value=body0, height=150, key=f"live_body_{ex}", placeholder="Paste the customer's email here", label_visibility="collapsed")
        want_draft = st.toggle("Write a draft reply when the route allows it", value=draft_ok, disabled=not draft_ok, key="live_draft",
                               help="Drafting is the slow stage: a 3B model on the CPU, roughly 5 to 20 seconds depending on the machine.")
        go = st.button("Triage this email", type="primary", disabled=not (embed_ok and body.strip()), key="live_go")
    with c2:
        section("Pipeline", "each row fills in as the stage finishes")
        box = st.empty()

    rec = st.session_state.get("live_rec")
    if go:
        from triage import triage_email
        rec = {"stages": {}, "_want_draft": want_draft}
        _render_stages(box, rec, upto=None, running="embed")

        def progress(stage, r):
            r["_want_draft"] = want_draft
            _render_stages(box, r, upto=stage)
            time.sleep(0.15)  # let the eye catch each stage

        try:
            with st.spinner("Running…", show_time=True):
                rec = triage_email(subject, body, from_name, draft=want_draft, progress=progress)
            rec["_want_draft"] = want_draft
            st.session_state["live_rec"] = rec
            st.session_state["live_log"] = st.session_state.get("live_log", []) + [rec["id"]]
        except Exception as e:
            notification("error", "The run failed part way.", f" {_esc(str(e))[:300]}. Check that Ollama is running and both models are pulled.")
            rec = None
    if rec and rec.get("stages", {}).get("embed"):
        _render_stages(box, rec)
        st.write("")
        _result(rec, run)
    else:
        with box.container():
            for key, *_ in STAGE_META:
                _stage_card(key, {}, pending=True)
        h('<div class="note" style="margin-top:8px">Same six stages as the batch run on the Pipeline page. Timings are for this one email on this machine.</div>')
    footer(run)
