"""Live feed: the fictional emails and reviews arrive one by one on a compressed
clock, and each one is run through the real pipeline on this machine the moment it
lands. Nothing on this page is replayed from the batch run; every stage you see
fill in was computed just now."""
import time

import altair as alt
import pandas as pd
import streamlit as st

from config import CFG
from ui import (G70, CORAL, INK, GREY, LINE, LINE2, BLUE, LAYER, OK, CRIT, LABELS, h, page_header, footer, section, stats,
                notification, ollama_status, load_json)
import triage
import voc
import voc_view

CSS = f"""<style>
.clock {{ display: flex; gap: 24px; align-items: baseline; margin: 0 0 10px; }}
.clock .t {{ font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 28px; line-height: 36px; color: {INK}; }}
.clock .d {{ font-size: 12px; color: {GREY}; }}
.fi {{ background: {LAYER}; border: 1px solid {LINE}; border-left: 3px solid {LINE2}; padding: 10px 14px; margin: 0 0 8px; }}
.fi.now {{ border-left-color: {BLUE}; }} .fi.call {{ border-left-color: {CORAL}; }} .fi.fail {{ border-left-color: {CRIT}; }} .fi.ok {{ border-left-color: {OK}; }}
.fi .hd {{ display: flex; gap: 10px; align-items: baseline; font-size: 14px; }} .fi .hd b {{ font-weight: 600; }}
.fi .hd .k {{ font-size: 11px; letter-spacing: .32px; text-transform: uppercase; color: {GREY}; min-width: 58px; }}
.fi .hd .m {{ margin-left: auto; font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 11px; color: {GREY}; white-space: nowrap; }}
.fi .bd {{ font-size: 13px; color: {GREY}; margin: 3px 0 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.st {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.st .p {{ font-size: 12px; line-height: 18px; padding: 1px 8px; border: 1px solid {LINE2}; color: {GREY}; background: #fff; }}
.st .p.on {{ border-color: {BLUE}; color: {INK}; }} .st .p.on b {{ color: {BLUE}; font-weight: 600; }}
.st .p.bad {{ border-color: {CRIT}; color: {INK}; }} .st .p.bad b {{ color: {CRIT}; }}
.st .p.call {{ border-color: {CORAL}; color: {INK}; }} .st .p.call b {{ color: {CORAL}; }}
.st .p.ms {{ border: 0; padding-left: 0; font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 11px; }}
</style>"""

EMAIL_STEPS = [("embed", "Read"), ("classify", "Sorted"), ("retrieve", "Policy"), ("brief", "Brief"), ("route", "Routed"), ("draft", "Drafted"), ("check", "Checked")]
REVIEW_STEPS = [("embed", "Read"), ("theme", "Theme"), ("read", "Gist"), ("rule", "Rule"), ("draft", "Drafted"), ("check", "Checked")]


@st.cache_data(show_spinner=False)
def stream(include_reviews=True):
    em = pd.read_csv(triage.ROOT / "data" / "emails.csv")
    rows = [{"kind": "email", "at": pd.Timestamp(r.received_at), "id": r.id, "who": r.from_name, "title": r.subject, "body": r.body, "stars": None, "source": "email"}
            for r in em.itertuples()]
    if include_reviews:
        rv = pd.read_csv(triage.ROOT / "data" / "reviews.csv")
        rows += [{"kind": "review", "at": pd.Timestamp(r.posted_at), "id": r.id, "who": r.reviewer, "title": r.title, "body": r.body, "stars": int(r.stars), "source": r.source}
                 for r in rv.itertuples()]
    rows.sort(key=lambda r: r["at"])
    return rows


@st.cache_resource(show_spinner=False)
def review_model():
    return voc.theme_model()


def _pill(label, value, state):
    return f'<span class="p {state}">{label}' + (f' <b>{value}</b>' if value else "") + "</span>"


def _email_pills(S, done, llm=True):
    out = []
    for key, label in EMAIL_STEPS:
        if key in ("brief", "draft", "check") and not llm: continue
        if key not in done:
            if key == "brief" and not CFG.get("genai", {}).get("brief"): continue
            out.append(_pill(label, "", "")); continue
        st_ = S.get(key) or {}
        if key == "embed": out.append(_pill(label, f'{st_.get("ms", 0)} ms', "on"))
        elif key == "classify": out.append(_pill(label, f'{LABELS.get(st_["pred_category"], st_["pred_category"])} · {st_["pred_sentiment"]} · {st_["band"]}', "on"))
        elif key == "retrieve":
            cr = st_.get("crag"); out.append(_pill(label, f'{len(st_.get("hits", []))} paragraphs' + (f', {len(cr["dropped"])} dropped' if cr else ""), "on"))
        elif key == "brief": out.append(_pill(label, (st_.get("asks") or "")[:48], "on"))
        elif key == "route":
            call = st_["decision"] == "consultant_call"; out.append(_pill(label, ("Call: " + st_["short"]) if call else "Draft", "call" if call else "on"))
        elif key == "draft": out.append(_pill(label, f'{st_["words"]} words · {st_["ms"]/1000:.1f} s', "on"))
        elif key == "check":
            qa = st_.get("qa") or {}; bad = qa.get("critical_fail"); out.append(_pill(label, "Failed: " + ", ".join(qa.get("failed", [])) if bad else ("Looks safe" if qa.get("score") == 100 else f'QA {qa.get("score")}'), "bad" if bad else "on"))
    return "".join(out)


def _review_pills(S, done, llm):
    out = []
    for key, label in REVIEW_STEPS:
        if key in ("read", "draft", "check") and not llm: continue
        if key not in done: out.append(_pill(label, "", "")); continue
        st_ = S.get(key) or {}
        if key == "embed": out.append(_pill(label, f'{st_.get("ms", 0)} ms', "on"))
        elif key == "theme": out.append(_pill(label, f'{voc_view.THEME_LABEL.get(st_["pred"], st_["pred"])} · {S["sentiment"]["value"]}', "on"))
        elif key == "read": out.append(_pill(label, (st_.get("gist") or "")[:56], "on"))
        elif key == "rule":
            a = st_["action"]; out.append(_pill(label, voc_view.ACTION_LABEL.get(a, a), "call" if a == "consultant_outreach" else "on"))
        elif key == "draft": out.append(_pill(label, f'{st_["words"]} words · {st_["ms"]/1000:.1f} s', "on"))
        elif key == "check":
            qa = st_.get("qa") or {}; bad = qa.get("critical_fail"); out.append(_pill(label, "Failed: " + ", ".join(qa.get("failed", [])) if bad else "Looks safe", "bad" if bad else "on"))
    return "".join(out)


def _card(item, rec, done, now, llm):
    S = rec.get("stages", {}) if rec else {}
    kind = item["kind"]
    cls = "now" if now else ""
    if not now and rec:
        if kind == "email":
            qa = (S.get("check") or {}).get("qa") or {}
            cls = "call" if S.get("route", {}).get("decision") == "consultant_call" else ("fail" if qa.get("critical_fail") else "ok")
        else:
            qa = (S.get("check") or {}).get("qa") or {}
            a = S.get("rule", {}).get("action"); cls = "call" if a == "consultant_outreach" else ("fail" if qa.get("critical_fail") else ("ok" if a == "draft_reply" else ""))
    stars = ("★" * item["stars"] + "☆" * (5 - item["stars"]) + " · ") if kind == "review" else ""
    pills = (_email_pills(S, done, llm) if kind == "email" else _review_pills(S, done, llm)) if rec else ""
    return (f'<div class="fi {cls}"><div class="hd"><span class="k">{"Email" if kind == "email" else item["source"]}</span><b>{item["title"]}</b><span>{item["who"]}</span>'
            f'<span class="m">{stars}{item["at"]:%d %b %H:%M}</span></div><div class="bd">{item["body"][:150]}</div><div class="st">{pills}</div></div>')


def _render_stream(ph, items, recs, cur=None, cur_rec=None, cur_done=(), llm=True, keep=7):
    cards = ""
    if cur is not None:
        cards += _card(cur, cur_rec, cur_done, True, llm)
    for it, rec in list(zip(items, recs))[::-1][:keep]:
        cards += _card(it, rec, {k for k, v in rec["stages"].items() if v}, False, llm)
    ph.markdown(cards, unsafe_allow_html=True)


def _render_side(tiles, chart, needs, items, recs, side="all", full=True):
    n = len(items); em = [(i, r) for i, r in zip(items, recs) if i["kind"] == "email"]; rv = [(i, r) for i, r in zip(items, recs) if i["kind"] == "review"]
    calls = sum(1 for _, r in em if r["stages"]["route"]["decision"] == "consultant_call")
    drafted = sum(1 for _, r in em if r["stages"].get("draft")) + sum(1 for _, r in rv if r["stages"].get("draft"))
    failed = sum(1 for _, r in em + rv if ((r["stages"].get("check") or {}).get("qa") or {}).get("critical_fail"))
    outreach = sum(1 for _, r in rv if r["stages"]["rule"]["action"] == "consultant_outreach")
    with tiles.container():
        cells = [("Arrived", n, "", f"{len(em)} emails, {len(rv)} reviews" if rv else "sorted, matched to policy, routed"),
                 ("To a consultant", calls + outreach, "", f"{calls} calls, {outreach} private outreach" if rv else "a person phones, no draft")]
        if full:
            cells += [("Drafts", drafted, "", "written just now, on this laptop"),
                      ("Failed a check", failed, "", "a person reads these first", "warn" if failed else "ok")]
        stats(cells)
    if side != "all":
        return
    with chart.container():
        rows = [{"what": LABELS.get(r["stages"]["classify"]["pred_category"], ""), "kind": "Email"} for _, r in em] + \
               [{"what": voc_view.THEME_LABEL.get(r["stages"]["theme"]["pred"], ""), "kind": "Review"} for _, r in rv]
        if rows:
            d = pd.DataFrame(rows).groupby(["what", "kind"]).size().reset_index(name="n")
            ch = alt.Chart(d).mark_bar(size=14).encode(
                y=alt.Y("what:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False)), x=alt.X("n:Q", title=None, axis=alt.Axis(tickMinStep=1)),
                color=alt.Color("kind:N", scale=alt.Scale(domain=["Email", "Review"], range=[G70, CORAL]), legend=alt.Legend(orient="top", title=None)), tooltip=["what", "kind", "n"]).properties(height=max(140, 26 * d.what.nunique() + 40))
            st.altair_chart(ch, width="stretch")
    with needs.container():
        rows = []
        for it, r in list(zip(items, recs))[::-1]:
            S = r["stages"]
            if it["kind"] == "email" and S["route"]["decision"] == "consultant_call": rows.append((it["id"], it["title"][:40], "Call: " + S["route"]["short"]))
            elif it["kind"] == "review" and S["rule"]["action"] == "consultant_outreach": rows.append((it["id"], it["title"][:40], "Consultant reaches out"))
            elif ((S.get("check") or {}).get("qa") or {}).get("critical_fail"): rows.append((it["id"], it["title"][:40], "Draft failed a check"))
            if len(rows) >= 8: break
        if rows:
            h('<table class="stab"><thead><tr><th>ID</th><th>Subject</th><th>Why</th></tr></thead><tbody>' + "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows) + "</tbody></table>")


def panel(key="feed", limit=None, controls=True, full_default=False, reviews_default=True, pause_default=0.6, start_label="Start", side="all"):
    """The stream and the side counters. The Live feed page uses it with controls;
    Walkthrough stop 1 uses it with one button and a limit, so the pile lands and
    gets sorted in front of the audience without leaving the page."""
    h(CSS)
    F = st.session_state.setdefault(key, {"i": 0, "items": [], "recs": [], "running": False})
    ok, models = ollama_status()
    _n = len(stream(st.session_state.get(f"{key}_src", "Emails and reviews") == "Emails and reviews" if controls else reviews_default))
    _n = min(_n, limit) if limit else _n
    if F["i"] >= _n:
        F["running"] = False
    if controls:
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1.6, 1.4, 1.2])
        if c1.button("Pause" if F["running"] else ("Start" if F["i"] == 0 else ("Done" if F["i"] >= _n else "Resume")), type="primary", width="stretch", key=f"{key}_go", disabled=F["i"] >= _n):
            F["running"] = not F["running"]; st.rerun()
        if c2.button("Reset", width="stretch", key=f"{key}_reset"):
            st.session_state[key] = {"i": 0, "items": [], "recs": [], "running": False}; st.rerun()
        mode = c3.radio("Depth", ["Sort, find, route", "Everything: brief, grading, draft, check"], index=1 if full_default else 0, key=f"{key}_mode", disabled=F["running"],
                        help="The first runs under a second per item with no language model. The second adds the generative steps and takes a few seconds per item.")
        src = c4.radio("Stream", ["Emails and reviews", "Emails only"], index=0 if reviews_default else 1, key=f"{key}_src", disabled=F["running"])
        pause = c5.slider("Pause between items, s", 0.0, 3.0, pause_default, 0.2, key=f"{key}_pause", disabled=F["running"])
        full = mode.startswith("Everything"); with_reviews = src == "Emails and reviews"
    else:
        a, b, _ = st.columns([1.3, 1, 3])
        label = start_label if F["i"] == 0 else ("Pause" if F["running"] else ("Done" if F["i"] >= _n else "Resume"))
        if a.button(label, type="primary", width="stretch", key=f"{key}_go", disabled=F["i"] >= _n):
            F["running"] = not F["running"]; st.rerun()
        if b.button("Reset", width="stretch", key=f"{key}_reset"):
            st.session_state[key] = {"i": 0, "items": [], "recs": [], "running": False}; st.rerun()
        full, with_reviews, pause = full_default, reviews_default, pause_default
    items = stream(with_reviews)
    if limit:
        items = items[:limit]
    if not ok:
        notification("error", "Ollama is not running.", " The feed embeds every item with nomic-embed-text, so it needs Ollama even in the fast mode.")
        F["running"] = False
    clock = st.empty()
    if not F["running"] and not F["items"]:
        if items:
            clock.markdown(f'<div class="clock"><span class="t">{items[0]["at"]:%a %d %b %H:%M}</span><span class="d">first of {len(items)} waiting</span></div>', unsafe_allow_html=True)
        return
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        section("Arriving", "newest first; the blue one is being processed now")
        stream_ph = st.empty()
    with right:
        section("As it happens", "counted from the items processed on this page")
        tiles = st.empty(); chart = st.empty()
        if side == "all":
            section("Needs a person", "calls, private outreach, failed checks")
        needs = st.empty()

    def show_clock(it, note=""):
        clock.markdown(f'<div class="clock"><span class="t">{it["at"]:%a %d %b %H:%M}</span><span class="d">{F["i"]} of {len(items)} arrived · {note}</span></div>', unsafe_allow_html=True)

    if F["items"]:
        _render_side(tiles, chart, needs, F["items"], F["recs"], side, full)
    if F["i"] < len(items):
        show_clock(items[F["i"]], "running on this laptop, nothing replayed" if F["running"] else "paused")
    else:
        clock.markdown('<div class="clock"><span class="t">Done</span><span class="d">every item processed, by the real pipeline, just now</span></div>', unsafe_allow_html=True)
    _render_stream(stream_ph, F["items"], F["recs"], llm=full)
    if not F["running"] or F["i"] >= len(items):
        F["running"] = False
        return

    rm = review_model() if with_reviews else None
    while F["running"] and F["i"] < len(items):
        it = items[F["i"]]
        show_clock(it, "running on this laptop, nothing replayed")
        done = set()

        def prog(name, rec, it=it, done=done):
            done.add(name); _render_stream(stream_ph, F["items"], F["recs"], it, rec, done, llm=full)
        _render_stream(stream_ph, F["items"], F["recs"], it, {"stages": {}}, done, llm=full)
        try:
            if it["kind"] == "email":
                rec = triage.triage_email(it["title"], it["body"], it["who"], draft=full, progress=prog, email_id=it["id"], use_genai=full)
            else:
                rec = voc.triage_review(it["title"], it["body"], it["stars"], rm, ret=triage.components()[0], llm=full, draft=full, progress=prog, review_id=it["id"])
        except Exception as e:
            notification("error", "The pipeline stopped.", f" {e}"); F["running"] = False; break
        F["items"].append(it); F["recs"].append(rec); F["i"] += 1
        _render_stream(stream_ph, F["items"], F["recs"], llm=full)
        _render_side(tiles, chart, needs, F["items"], F["recs"], side, full)
        time.sleep(pause)
    st.rerun()


def feed():
    run = load_json("run")
    page_header("Live feed", "The fictional emails and reviews arrive on a compressed clock. Each one is run through the real pipeline the moment it lands.", run)
    panel("feed", controls=True)
    footer(run)
