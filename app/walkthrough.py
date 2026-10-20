"""Walkthrough: the project told in six stops, inside the Carbon shell.

The stops follow the Round 2 question in order: the problem (1, 2), how it
was solved (3, 4), the outcome (5, 6). Every stop has the same shape: a
stepper and the Next button at the top, one line of narrative, one piece of
evidence from the run. Stop three is the Live triage panel; stop four is the
real E061 draft with its failed check. Nothing on screen is a mock-up.
"""
import altair as alt
import streamlit as st

from ui import (G40, G90, INK, GREY, LINE, BLUE, CRIT, h, page_header, footer, section, stats, table,
                load_results, load_trace, load_json, has_run, no_run_notice, notification)
import live
import views

# (name, chapter, time stamp in the four-minute video)
BEATS = [("The pile", "The problem", "1:05"),
         ("The question", "The problem", "1:10"),
         ("Four steps, live", "How I solved it", "1:20"),
         ("The one it got wrong", "How I solved it", "2:15"),
         ("What changed", "The outcome", "2:50"),
         ("The honest number", "The outcome", "3:05")]

CSS = f"""<style>
.stepper {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; margin: 2px 0 0; }}
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
    page_header("Walkthrough", "The project in six stops, in the order of the question. Everything on screen comes from the run.", run)

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
            st.write("")
            newest = df.sort_values("received_at", ascending=False).head(7)
            table(["Received", "From", "Subject"], [(f"{r.received_at:%d %b %H:%M}", r.from_name, r.subject) for r in newest.itertuples()])
            st.caption(f"The newest 7 of {n}. All of them are in the Inbox.")

    elif i == 1:
        h('<div class="lead">Could we sort the pile <b>before</b> a person opens it, and give them a head start on the reply?</div>')
        h('<div class="plain">Three things would have to hold. It says what each email is about and how the customer feels. '
          'It finds the policy that applies instead of guessing. And it never sends anything on its own: a person always decides.</div>')

    elif i == 2:
        h('<div class="lead">One new email, handled in front of you.</div>')
        h('<div class="plain">Press <b>Handle this email</b> and watch the steps fill in. The language model does three jobs: it throws out weaker policy paragraphs that are about something else, it writes a two-line brief with the facts copied from the email, and it writes the first draft. Rules decide who handles it, and rules check the draft. Some emails skip the draft on purpose: '
          '<b>scan results, health questions, and anyone cancelling because it did not work</b> go straight to a Bone Health Consultant for a phone call.</div>')
        live.panel(key="wt", default_index=2, technical=False)

    elif i == 3:
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

    elif i == 4:
        h('<div class="lead">What changed for the people doing the work.</div>')
        stats([("Emails", n, "", "sorted before anyone opened them"),
               ("Consultant calls", calls, "", "a person phones, no draft"),
               ("Drafts written", drafts, "", f"{dr.draft_seconds.median():.1f} s each, on a laptop"),
               ("Flagged by the check", flagged, "", "read closely by a person", "warn" if flagged else "ok")])
        st.write("")
        c1, c2 = st.columns([1.4, 1], gap="large")
        with c1:
            section("Each week", "calls on top of drafts")
            wk = df.groupby(["week", "Route"]).size().reset_index(name="n")
            ch = alt.Chart(wk).mark_bar(size=26).encode(
                x=alt.X("week:T", title=None, scale=alt.Scale(padding=22), axis=alt.Axis(format="%d %b", labelAngle=0)),
                y=alt.Y("n:Q", title=None, axis=alt.Axis(tickMinStep=1)),
                color=alt.Color("Route:N", scale=alt.Scale(domain=["Draft reply", "Consultant call"], range=[G40, G90]), title=None, legend=alt.Legend(orient="top", direction="horizontal")),
                order=alt.Order("Route:N", sort="descending"), tooltip=[alt.Tooltip("week:T", format="%d %b"), "Route", "n"]).properties(height=220)
            st.altair_chart(ch, width="stretch")
        with c2:
            h('<div class="plain"><b>For the agents.</b> No more blank screen. Each email arrives sorted, with the policy attached and a draft to edit.</div>')
            h('<div class="plain"><b>For the team lead.</b> The whole week on one screen: what people write about, how they feel, who needs a call. A minute instead of an afternoon.</div>')

    elif i == 5:
        acc = live._band_words()
        h('<div class="lead">Right about <b>three times in four</b> on emails it has never seen.</div>')
        c1, c2 = st.columns([1, 1], gap="large")
        with c1:
            table(["When it says", "It is right"], [("Sure", live._in_n(acc["high"])), ("Fairly sure", live._in_n(acc["medium"])), ("Not sure", live._in_n(acc["low"]))])
            st.caption("From out-of-fold predictions on all 110 labelled emails. The exact figures are on the Model facts page.")
        with c2:
            h('<div class="plain">Good enough to help. Not good enough to trust blindly. So a person always decides, and the first month of doing this for real '
              'would be spent with the people who answer the phone, labelling real emails, because their judgement is what the system should learn.</div>')
            a, b = st.columns(2)
            if a.button("Open the Inbox", width="stretch"): st.switch_page(st.session_state["pages"]["Inbox"])
            if b.button("Try your own email", width="stretch"): st.switch_page(st.session_state["pages"]["Live triage"])
    footer(run)
