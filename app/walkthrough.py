"""Walkthrough: the project told in five stops, inside the Carbon shell.

The stops follow the Round 2 question in order: the problem (1), how it
was solved (2, 3, 4), the outcome (5). Every stop has the same shape: a
stepper and the Next button at the top, one line of narrative, one piece of
evidence from the run. Stop two is the Live triage panel; stop three is the
real E061 draft with its failed check. Nothing on screen is a mock-up.
"""
import altair as alt
import pandas as pd
import streamlit as st

from ui import (G40, G60, G70, G90, CORAL, INK, GREY, LINE, BLUE, CRIT, h, page_header, footer, section, stats, table,
                load_results, load_trace, load_json, has_run, no_run_notice, notification)
import live
import views
import voc_view
import feed

# (name, chapter, time stamp in the four-minute video)
BEATS = [("The pile", "The problem", "0:49"),
         ("Four steps, live", "How I solved it", "1:03"),
         ("The one it got wrong", "How I solved it", "1:46"),
         ("Your reviews", "How I solved it", "2:19"),
         ("What changed", "The outcome", "2:50")]

CSS = f"""<style>
.stepper {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 2px 0 0; }}
.sp {{ border-top: 2px solid {LINE}; padding: 8px 6px 0 0; }}
.sp .c {{ font-size: 11px; line-height: 14px; letter-spacing: .32px; text-transform: uppercase; color: {GREY}; }}
.sp .l {{ font-size: 14px; line-height: 18px; color: {GREY}; margin-top: 2px; }}
.sp.done {{ border-top-color: {BLUE}; }} .sp.done .l {{ color: {INK}; }}
.sp.now {{ border-top-color: {BLUE}; }} .sp.now .l {{ color: {INK}; font-weight: 600; }}
.stop {{ display: flex; justify-content: space-between; align-items: baseline; margin: 26px 0 6px; }}
.stop h2 {{ font-size: 20px; line-height: 28px; font-weight: 400; margin: 0; color: {INK}; }}
.stop .t {{ font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 12px; color: {GREY}; }}
.lead {{ font-size: 28px; line-height: 38px; font-weight: 300; color: {INK}; max-width: 36ch; margin: 0 0 14px; }}
.lead b {{ font-weight: 400; color: {BLUE}; }}
.mail .bd.big {{ font-size: 16px; line-height: 24px; }}
.verdict {{ font-size: 20px; line-height: 28px; color: {CRIT}; margin: 12px 0 8px; }}
</style>"""


def _stepper(i):
    cells = "".join(f'<div class="sp {"done" if k < i else ("now" if k == i else "")}"><div class="c">{k+1} · {chap}</div><div class="l">{name}</div></div>'
                    for k, (name, chap, _) in enumerate(BEATS))
    h(f'<div class="stepper">{cells}</div>')


def _email_card(name, subject, body, meta="new email"):
    h(f'<div class="mail"><div class="hd"><span class="s">{subject}</span><span class="m">{meta}</span></div>'
      f'<div class="bd big"><b>{name}</b><br><br>{body}</div></div>')


def walkthrough():
    if not has_run():
        page_header("Walkthrough", "", {}); no_run_notice(); return
    df, run, tr = load_results(), load_json("run"), load_trace()
    h(CSS)
    i = st.session_state.setdefault("wt", 0)
    page_header("Walkthrough", "The project in five stops, in the order of the question. Everything on screen comes from the run.", run)

    left, right = st.columns([5, 1.1], gap="large")
    with left:
        _stepper(i)
    with right:
        a, b = st.columns([1, 1.6])
        if a.button("Back", disabled=i == 0, key="wt_back", width="stretch"):
            st.session_state["wt"] = i - 1; st.rerun()
        if b.button("Next", type="primary", disabled=i == len(BEATS) - 1, key="wt_next", width="stretch"):
            st.session_state["wt"] = i + 1; st.rerun()

    name, chap, t = BEATS[i]
    h(f'<div class="stop"><h2>{i+1}. {name}</h2><span class="t">{chap} · {t} in the video</span></div>')

    n = len(df); calls = int((df.route == "consultant_call").sum()); drafts = n - calls
    dr = df[df.route == "draft_reply"]; flagged = int((dr.qa_score == 0).sum())

    if i == 0:
        c1, c2 = st.columns([1, 1.2], gap="large")
        with c1:
            h('<div class="lead">Picture one email.</div>')
            jn, js, jb = live.EXAMPLES["Charged twice this month"]
            _email_card(jn, js, jb)
            h('<div class="plain" style="margin-top:14px">Someone opens it, works out what it is about, finds the right policy, and writes a reply from scratch. '
              'Then the next one. The team lead only knows what the week looked like if she reads the pile herself.</div>')
        with c2:
            h('<div class="lead">Now picture the pile.</div>')
            stats([("Emails in ten weeks", n, "", "every one opened by a person, every reply written from scratch")])
        h('<div class="lead" style="margin-top:18px">Could we sort the pile <b>before</b> a person opens it, and give them a head start on the reply?</div>')
        h('<div class="plain">Press the button and the first of them arrive. Each one is sorted, matched to the policy and routed by the real pipeline as it lands, on this laptop, in under a second. Nothing is replayed.</div>')
        feed.panel(key="wt_feed", limit=14, controls=False, full_default=False, reviews_default=False, pause_default=0.4, start_label="Let them arrive")

    elif i == 1:
        h('<div class="lead">One new email, handled in front of you.</div>')
        h('<div class="plain">Press <b>Handle this email</b> and watch the steps fill in. The language model does three jobs: it throws out weaker policy paragraphs that are about something else, it writes a two-line brief with the facts copied from the email, and it writes the first draft. Rules decide who handles it, and rules check the draft. Some emails skip the draft on purpose: '
          '<b>scan results, health questions, and anyone cancelling because it did not work</b> go straight to a Bone Health Consultant for a phone call.</div>')
        live.panel(key="wt", default_index=2, technical=False)

    elif i == 2:
        r = df[df.id == "E061"]
        if r.empty:
            notification("warning", "E061 is not in this run.", " The failure example lives in the Inbox under QA fails.")
        else:
            r = r.iloc[0]; trace = tr.get("E061", {})
            c1, c2 = st.columns([1, 1.4], gap="large")
            with c1:
                h('<div class="lead">The draft that made something up.</div>')
                _email_card(r.from_name, r.subject, r.body, f"<code>{r.id}</code> · {r.received_at:%d %b %H:%M}")
                h('<div class="verdict">Nothing in the pages says "taper off".</div>')
                h('<div class="plain">The model made it up, politely. A check reads every sentence of the draft and asks where it came from. '
                  'This sentence had no answer, so the draft is marked failed and a person writes the reply.</div>')
            with c2:
                views._draft_block(r, trace, run, "wt061")

    elif i == 3:
        vdf, vrun, vtr = voc_view.load_voc()
        if vdf.empty:
            notification("warning", "No review run found.", " Run <code>python app/voc.py</code>; the Voice of customer page explains.")
        else:
            wh = voc_view.warehouse(vdf, vrun)
            top, rt = voc_view.rising(wh)
            h(f'<div class="lead">Then I pointed the same sorter at <b>{len(vdf)} reviews</b>.</div>')
            c1, c2 = st.columns([1.3, 1], gap="large")
            with c1:
                h('<div class="plain">Reviews on the site and on Amazon say the same things as the emails, in public. Same four steps: sort by theme, read the mood, '
                  'one line on what the reviewer is saying, and a rule for what happens next. Every number comes from a SQL query over one table, the shape it would have in their warehouse.</div>')
                if top.recent_per_week > top.before_per_week:
                    notification("warning", f"{voc_view.THEME_LABEL.get(top.theme, top.theme)} is rising.",
                                 f" {top.recent_per_week:.1f} reviews a week in the last three weeks, against {top.before_per_week:.1f} a week before. The business should hear that the week it happens.")
                tw = wh.run("themes_by_week"); tw["week_start"] = pd.to_datetime(tw.week_start); tw["Theme"] = tw.theme.map(voc_view.THEME_LABEL)
                ch = alt.Chart(tw).mark_bar(size=22).encode(
                    x=alt.X("week_start:T", title=None, scale=alt.Scale(padding=22), axis=alt.Axis(format="%d %b", labelAngle=0)),
                    y=alt.Y("sum(n):Q", title=None, axis=alt.Axis(tickMinStep=1)),
                    color=alt.Color("Theme:N", scale=alt.Scale(domain=list(voc_view.THEME_LABEL.values()), range=[G90, G70, CORAL, G60, G40, "#a6c8ff", "#f1c21b"]), legend=alt.Legend(orient="top", columns=4, title=None)),
                    tooltip=[alt.Tooltip("week_start:T", format="%d %b"), "Theme", "sentiment", alt.Tooltip("sum(n):Q", title="reviews")]).properties(height=210)
                st.altair_chart(ch, width="stretch")
                st.caption("The rise is planted in this fictional set so there is something to find. The query that finds it is on the Voice of customer page.")
            with c2:
                ex = vdf[(vdf.sentiment == "negative") & (vdf.pred_theme == "price") & (vdf.action == "draft_reply") & (vdf.qa_score == 100)].sort_values("posted_at", ascending=False)
                if ex.empty:
                    ex = vdf[(vdf.sentiment == "negative") & (vdf.action == "draft_reply")].sort_values("posted_at", ascending=False)
                r = ex.iloc[0]
                voc_view._review_card(r, r.quote)
                if r.gist:
                    h(f'<div class="gist"><b>What the model read:</b> {r.gist}</div>')
                S = vtr.get(r.id, {}).get("stages", {}); qa = (S.get("check") or {}).get("qa")
                h('<div class="mail draft"><div class="hd"><span class="s">Public reply, draft</span><span class="m">' + (views.qa_tag(qa["score"], qa["critical_fail"]) if qa else "") + f'</span></div><div class="bd">{r.draft}</div></div>')
                h('<div class="note" style="margin-top:6px">Checked by the same seven rules as the email drafts. A scan result or a side effect in a review never gets a public reply; a consultant reaches out instead.</div>')

    elif i == 4:
        acc = live._band_words()
        h('<div class="lead">What changed, and the honest number.</div>')
        stats([("Emails", n, "", "sorted before anyone opened them"),
               ("Consultant calls", calls, "", "a person phones, no draft"),
               ("Drafts written", drafts, "", f"{dr.draft_seconds.median():.1f} s each, on a laptop"),
               ("Flagged by the check", flagged, "", "read closely by a person", "warn" if flagged else "ok")])
        st.write("")
        c1, c2 = st.columns([1, 1], gap="large")
        with c1:
            h('<div class="plain"><b>For the agents.</b> No more blank screen. Each email arrives sorted, with the policy attached and a draft to edit.</div>')
            h('<div class="plain"><b>For the team lead.</b> The whole week on one screen: what people write about, how they feel, who needs a call, what the reviews say.</div>')
        with c2:
            section("Right about three times in four on emails it has never seen", "out-of-fold, all 110")
            table(["When it says", "It is right"], [("Sure", live._in_n(acc["high"])), ("Fairly sure", live._in_n(acc["medium"])), ("Not sure", live._in_n(acc["low"]))])
            st.caption("Good enough to help, not good enough to trust blindly. So a person always decides. Exact figures on the Model facts page.")
            a, b = st.columns(2)
            if a.button("Open the Inbox", width="stretch"): st.switch_page(st.session_state["pages"]["Inbox"])
            if b.button("Try your own email", width="stretch"): st.switch_page(st.session_state["pages"]["Live triage"])
    footer(run)
