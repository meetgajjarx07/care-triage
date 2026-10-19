"""Inbox replay page: the ten-week run played back in half a minute.

Same emails, same decisions as the batch run in out/results.csv, shown
arriving one at a time so a viewer can watch the counters, the category
bars and the weekly chart fill up. Nothing is classified on this page; the
Live triage page does that for one fresh email. The page says so.

Everything is plain HTML re-rendered in one container per frame, which is
cheap enough for 110 frames in 30 seconds on a laptop.
"""
import html
import time

import streamlit as st

from ui import (INK, CRIT, LABELS, h, page_header, footer, section, load_results, load_json, has_run, no_run_notice)

SPEEDS = {"30 seconds": 30, "60 seconds": 60, "2 minutes": 120}
FEED_ROWS = 7

CSS = f"""<style>
@keyframes slidein {{ from {{ opacity: 0; transform: translateY(-10px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes pop {{ 0% {{ color: #0f62fe; }} 100% {{ color: {INK}; }} }}
@keyframes grow {{ from {{ transform: scaleX(0.6); }} to {{ transform: none; }} }}
.clock {{ display: flex; justify-content: space-between; align-items: baseline; font-size: 14px; color: #525252; margin: 0 0 6px; }}
.clock b {{ font-size: 18px; font-weight: 400; color: {INK}; }}
.bar {{ height: 4px; background: #e0e0e0; margin: 0 0 14px; }}
.bar span {{ display: block; height: 4px; background: #0f62fe; transition: width .2s linear; }}
.bigs {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: #e0e0e0; border: 1px solid #e0e0e0; margin: 0 0 16px; }}
.big {{ background: #fff; padding: 14px 18px 12px; }}
.big .l {{ font-size: 12px; line-height: 16px; letter-spacing: .32px; color: #525252; }}
.big .v {{ font-size: 36px; line-height: 42px; font-weight: 300; color: {INK}; font-variant-numeric: tabular-nums; margin-top: 4px; }}
.big .v.changed {{ animation: pop .6s ease-out; }}
.big .d {{ font-size: 12px; line-height: 16px; color: #525252; }}
.big.dark .v {{ color: #002d9c; }} .big.red .v {{ color: {CRIT}; }}
.feed {{ background: #fff; border: 1px solid #e0e0e0; }}
.feed .row {{ display: grid; grid-template-columns: 48px 1fr 300px; gap: 10px; align-items: center; padding: 7px 14px; border-bottom: 1px solid #e0e0e0; font-size: 14px; line-height: 18px; }}
.feed .row:last-child {{ border-bottom: 0; }}
.feed .row.new {{ animation: slidein .35s ease-out; background: #edf5ff; }}
.feed .t {{ font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 12px; color: #525252; }}
.feed .s {{ color: {INK}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.feed .s small {{ color: #525252; margin-left: 6px; }}
.feed .pills {{ display: flex; gap: 4px; justify-content: flex-end; align-items: center; }}
.feed .pills .pl {{ flex: 0 0 auto; }}
.pl {{ display: inline-block; font-size: 11px; line-height: 16px; padding: 1px 7px; border-radius: 20px; white-space: nowrap; }}
.pl.cat {{ background: #e0e0e0; color: #161616; }}
.pl.call {{ background: #002d9c; color: #fff; }} .pl.draft {{ background: #d0e2ff; color: #002d9c; }}
.pl.ok {{ background: #a7f0ba; color: #0e6027; }} .pl.warn {{ background: #fcf4d6; color: #684e00; }} .pl.bad {{ background: #ffd7d9; color: #a2191f; }}
.feed .empty {{ padding: 28px 14px; color: #8d8d8d; font-size: 14px; }}
.cats {{ background: #fff; border: 1px solid #e0e0e0; padding: 10px 14px 6px; }}
.cat {{ display: grid; grid-template-columns: 150px 1fr 28px; gap: 10px; align-items: center; font-size: 13px; margin: 0 0 6px; }}
.cat .n {{ color: #161616; }}
.cat .b {{ height: 12px; background: #f4f4f4; }}
.cat .b span {{ display: block; height: 12px; background: #4589ff; transform-origin: left; animation: grow .25s ease-out; }}
.cat .c {{ text-align: right; font-variant-numeric: tabular-nums; color: #525252; }}
.weeks {{ background: #fff; border: 1px solid #e0e0e0; padding: 12px 14px 6px; display: grid; grid-template-columns: repeat(10, 1fr); gap: 6px; align-items: end; height: 130px; }}
.wk {{ display: flex; flex-direction: column; justify-content: flex-end; height: 100%; font-size: 11px; color: #525252; text-align: center; }}
.wk .st {{ display: flex; flex-direction: column; justify-content: flex-end; flex: 1; }}
.wk .call {{ background: #002d9c; }} .wk .draft {{ background: #a6c8ff; }}
.wk .lab {{ margin-top: 4px; white-space: nowrap; }}
.legend {{ font-size: 12px; color: #525252; margin: 6px 0 0; }}
.legend i {{ display: inline-block; width: 10px; height: 10px; margin: 0 4px 0 10px; vertical-align: middle; }}
.done {{ font-size: 16px; line-height: 24px; color: {INK}; background: #fff; border: 1px solid #e0e0e0; border-left: 3px solid #24a148; padding: 14px 18px; margin: 0 0 14px; }}
</style>"""


def _e(s):
    return html.escape(str(s or ""))


def _frame(rows, upto, weeks, total_secs_left=None, prev=None):
    """HTML for the state after the first `upto` emails have arrived."""
    seen = rows[:upto]
    n = len(seen)
    calls = sum(1 for r in seen if r["route"] == "consultant_call")
    drafts = n - calls
    flagged = sum(1 for r in seen if r["route"] == "draft_reply" and r["qa_score"] == 0)
    prev = prev or {}

    def big(key, label, val, detail, cls=""):
        ch = " changed" if prev.get(key) != val else ""
        return f'<div class="big {cls}"><div class="l">{label}</div><div class="v{ch}">{val}</div><div class="d">{detail}</div></div>'

    if n:
        last = seen[-1]
        wk_i = weeks.index(last["week"]) + 1
        clock = f'<div class="clock"><span>Week <b>{wk_i}</b> of {len(weeks)}</span><span><b>{last["received_at"]:%a %d %b}</b>, {last["received_at"]:%H:%M}</span></div>'
    else:
        clock = '<div class="clock"><span>Week <b>1</b> of 10</span><span>waiting</span></div>'
    out = clock + f'<div class="bar"><span style="width:{100*n/len(rows):.1f}%"></span></div>'
    out += '<div class="bigs">' + big("n", "Emails received", n, "one at a time") + \
        big("c", "Consultant calls", calls, "a person phones, no draft", "dark") + \
        big("d", "Drafts written", drafts, "for the care team to edit") + \
        big("f", "Flagged by the safety check", flagged, "a person reads these closely", "red" if flagged else "") + "</div>"

    # feed, newest first
    feed = ""
    for i, r in enumerate(reversed(seen[-FEED_ROWS:])):
        if r["route"] == "consultant_call":
            pills = '<span class="pl call">Call</span>'
        else:
            q = r["qa_score"]
            safe = '<span class="pl ok">safe</span>' if q == 100 else ('<span class="pl bad">flagged</span>' if q == 0 else '<span class="pl warn">minor</span>')
            pills = '<span class="pl draft">Draft</span>' + safe
        pills = f'<span class="pl cat">{_e(r["Category"])}</span>' + pills
        new = " new" if i == 0 else ""
        feed += (f'<div class="row{new}"><span class="t">{r["received_at"]:%H:%M}</span>'
                 f'<span class="s">{_e(r["from_name"])}<small>{_e(r["subject"])}</small></span><span class="pills">{pills}</span></div>')
    if not feed:
        feed = '<div class="empty">Press Replay the ten weeks.</div>'

    # categories
    counts = {lab: 0 for lab in LABELS.values()}
    for r in seen:
        counts[r["Category"]] = counts.get(r["Category"], 0) + 1
    mx = max(max(counts.values()), 1)
    cats = "".join(f'<div class="cat"><span class="n">{_e(k)}</span><div class="b"><span style="width:{100*v/mx:.0f}%"></span></div><span class="c">{v}</span></div>'
                   for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))

    # weeks
    per = {w: [0, 0] for w in weeks}
    for r in seen:
        per[r["week"]][0 if r["route"] == "consultant_call" else 1] += 1
    wmax = max(max(a + b for a, b in per.values()), 1)
    wk = ""
    for w in weeks:
        c, d = per[w]
        wk += (f'<div class="wk"><div class="st"><div class="call" style="height:{100*c/wmax:.0f}%"></div>'
               f'<div class="draft" style="height:{100*d/wmax:.0f}%"></div></div><div class="lab">{w:%d %b}</div></div>')

    return out, feed, cats, wk, {"n": n, "c": calls, "d": drafts, "f": flagged}


def _render(box, parts):
    top, feed, cats, wk = parts
    with box.container():
        h(top)
        c1, c2 = st.columns([3, 2], gap="large")
        with c1:
            section("Arriving", f"newest first, last {FEED_ROWS}")
            h(f'<div class="feed">{feed}</div>')
        with c2:
            section("What they are about")
            h(f'<div class="cats">{cats}</div>')
            section("Each week", "calls on top of drafts")
            h(f'<div class="weeks">{wk}</div><div class="legend"><i style="background:#002d9c"></i>consultant call <i style="background:#a6c8ff"></i>draft</div>')


def replay():
    if not has_run():
        page_header("Inbox replay", "", {}); no_run_notice(); return
    df, run = load_results(), load_json("run")
    page_header("Inbox replay",
                "Ten weeks of customer email, replayed in half a minute. Same emails, same decisions as the run. "
                "Nothing is classified on this page; Live triage does that for one fresh email.", run)
    h(CSS)
    rows = df.sort_values("received_at")[["id", "received_at", "from_name", "subject", "Category", "route", "qa_score", "week"]].to_dict("records")
    weeks = sorted(df.week.unique())

    c1, c2, c3 = st.columns([1.2, 1, 3])
    go = c1.button("Replay the ten weeks", type="primary", width="stretch")
    speed = c2.selectbox("Speed", list(SPEEDS), index=0, label_visibility="collapsed")
    c3.caption("Each email appears as it arrived, with what the system decided about it. "
               "The numbers at the top count up as it goes. Open the Overview afterwards for the full picture.")

    box = st.empty()
    if go:
        st.session_state["replay_final"] = None
        total = SPEEDS[speed]
        per = total / len(rows)
        prev = None
        t0 = time.perf_counter()
        for i in range(1, len(rows) + 1):
            top, feed, cats, wk, cur = _frame(rows, i, weeks, prev=prev)
            _render(box, (top, feed, cats, wk))
            prev = cur
            wait = t0 + i * per - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
        st.session_state["replay_final"] = (top, feed, cats, wk)
        st.session_state["replay_done"] = True
    elif st.session_state.get("replay_final"):
        _render(box, st.session_state["replay_final"])
    else:
        top, feed, cats, wk, _ = _frame(rows, 0, weeks)
        _render(box, (top, feed, cats, wk))

    if st.session_state.get("replay_done"):
        n = len(rows); calls = int((df.route == "consultant_call").sum()); drafts = n - calls
        dr = df[df.route == "draft_reply"]; flagged = int((dr.qa_score == 0).sum())
        h(f'<div class="done">That was <b>{n} emails</b> over ten weeks. <b>{calls}</b> went to a Bone Health Consultant for a phone call. '
          f'<b>{drafts}</b> got a first draft, and the safety check flagged <b>{flagged}</b> of those before anyone read them. '
          f'The team lead sees this without opening a single email. Nothing was sent.</div>')
        b1, b2, _ = st.columns([1, 1, 3])
        if b1.button("Open the Overview", width="stretch"):
            st.switch_page(st.session_state["pages"]["Overview"])
        if b2.button("Try one email live", width="stretch"):
            st.switch_page(st.session_state["pages"]["Live triage"])
    footer(run)
