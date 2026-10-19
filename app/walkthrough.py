"""Walkthrough: the project told in six beats, inside the same Carbon shell.

One email, the pile, the question, four steps running live, the draft that
made something up, what changed, and the honest number. Every beat is built
from the run in out/ and models/, so nothing on screen is a mock-up. Beat
three is the Live triage panel; beat four is the real E061 draft with its
failed check. Next and Back move through the beats; the same six stops are
listed in the progress bar at the top, in Carbon's progress-indicator style.
"""
import altair as alt
import streamlit as st

from ui import (G40, G90, INK, GREY, LINE, BLUE, CRIT, h, page_header, footer, section, stats, table,
                load_results, load_trace, load_json, has_run, no_run_notice, notification)
import live
import views

BEATS = [("The pile", "one email, then all of them"),
         ("The question", "what the team lead asked"),
         ("Four steps, live", "one email handled in front of you"),
         ("The one it got wrong", "and the check that caught it"),
         ("What changed", "for the agents and the team lead"),
         ("The honest number", "how far to trust it")]

CSS = f"""<style>
.prog {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin: 4px 0 18px; }}
.pstep {{ border-top: 2px solid {LINE}; padding: 8px 8px 0 0; min-height: 52px; }}
.pstep .n {{ display: inline-flex; width: 16px; height: 16px; border-radius: 50%; border: 1px solid {GREY}; color: {GREY}; font-size: 10px; align-items: center; justify-content: center; margin-right: 6px; vertical-align: -2px; }}
.pstep .l {{ font-size: 14px; line-height: 18px; color: {GREY}; }}
.pstep .s {{ font-size: 12px; line-height: 16px; color: {GREY}; margin-left: 22px; }}
.pstep.done {{ border-top-color: {BLUE}; }} .pstep.done .n {{ background: {BLUE}; border-color: {BLUE}; color: #fff; }} .pstep.done .l {{ color: {INK}; }}
.pstep.now {{ border-top-color: {BLUE}; }} .pstep.now .n {{ border: 2px solid {BLUE}; color: {BLUE}; font-weight: 600; }} .pstep.now .l {{ color: {INK}; font-weight: 600; }}
.display {{ font-size: 32px; line-height: 42px; font-weight: 300; color: {INK}; max-width: 34ch; margin: 6px 0 18px; letter-spacing: 0; }}
.display b {{ font-weight: 400; color: {BLUE}; }}
.mail .bd.big {{ font-size: 16px; line-height: 24px; }}
.verdict {{ font-size: 20px; line-height: 28px; font-weight: 400; color: {CRIT}; margin: 10px 0 6px; }}
.beatnav {{ display: flex; justify-content: space-between; align-items: center; margin: 2px 0 8px; font-size: 12px; color: {GREY}; }}
</style>"""


def _progress(i):
    cells = ""
    for k, (name, sub) in enumerate(BEATS):
        cls = "done" if k < i else ("now" if k == i else "")
        cells += f'<div class="pstep {cls}"><span class="n">{k+1}</span><span class="l">{name}</span><div class="s">{sub}</div></div>'
    h(f'<div class="prog">{cells}</div>')


def _email_card(name, subject, body, meta="new email"):
    h(f'<div class="mail"><div class="hd"><span class="s">{subject}</span><span class="m">{meta}</span></div>'
      f'<div class="bd big"><b>{name}</b><br><br>{body}</div></div>')


def _nav(i, where):
    a, b, c = st.columns([1, 1, 6])
    if a.button("Back", disabled=i == 0, key=f"wt_back_{where}", width="stretch"):
        st.session_state["wt"] = i - 1; st.rerun()
    if b.button("Next", type="primary", disabled=i == len(BEATS) - 1, key=f"wt_next_{where}", width="stretch"):
        st.session_state["wt"] = i + 1; st.rerun()


def walkthrough():
    if not has_run():
        page_header("Walkthrough", "", {}); no_run_notice(); return
    df, run, tr = load_results(), load_json("run"), load_trace()
    h(CSS)
    i = st.session_state.setdefault("wt", 0)
    page_header("Walkthrough", "The project in six stops, for someone who does not code. Everything on screen comes from the run; nothing is a mock-up.", run)
    _progress(i)
    _nav(i, "top")
    name, sub = BEATS[i]
    section(f"{i+1}. {name}", sub)

    n = len(df); calls = int((df.route == "consultant_call").sum()); drafts = n - calls
    dr = df[df.route == "draft_reply"]; flagged = int((dr.qa_score == 0).sum())

    if i == 0:
        h('<div class="display">Picture one email.</div>')
        c1, c2 = st.columns([1, 1.25], gap="large")
        with c1:
            jn, js, jb = live.EXAMPLES["Charged twice this month"]
            _email_card(jn, js, jb)
            h('<div class="plain" style="margin-top:14px">Someone opens it, works out what it is about, finds the right policy, and writes a reply from scratch. '
              'Then the next one. The team lead only knows what the week looked like if she reads the pile herself.</div>')
        with c2:
            stats([("Emails", n, "", f"{df.received_at.min():%d %b} to {df.received_at.max():%d %b}, ten weeks"),
                   ("Opened by a person", n, "", "every one"), ("Replies written from scratch", drafts + calls, "", "every one")])
            st.write("")
            newest = df.sort_values("received_at", ascending=False).head(8)
            table(["Received", "From", "Subject"], [(f"{r.received_at:%d %b %H:%M}", r.from_name, r.subject) for r in newest.itertuples()])
            st.caption(f"The newest 8 of {n}. The rest are in the Inbox.")

    elif i == 1:
        h('<div class="display">Could we sort the pile <b>before</b> a person opens it, and give them a head start on the reply?</div>')
        h('<div class="plain">Three things would have to be true. The system has to say what each email is about and how the customer feels. '
          'It has to find the policy that applies, not guess. And it must never send anything on its own; a person always decides.</div>')

    elif i == 2:
        h('<div class="plain">Press <b>Handle this email</b>. The steps fill in as the system finishes them, on this laptop. '
          'Some emails skip the draft on purpose: <b>scan results, health questions, and anyone cancelling because it did not work</b> go straight to a Bone Health Consultant for a phone call. That is a rule, not a guess.</div>')
        live.panel(key="wt", default_index=2, technical=False)

    elif i == 3:
        r = df[df.id == "E061"]
        if r.empty:
            notification("warning", "E061 is not in this run.", " The failure example lives in the Inbox under QA fails.")
        else:
            r = r.iloc[0]; t = tr.get("E061", {})
            c1, c2 = st.columns([1, 1.4], gap="large")
            with c1:
                _email_card(r.from_name, r.subject, r.body, f"<code>{r.id}</code> · {r.received_at:%d %b %H:%M}")
                h('<div class="verdict">Nothing in the pages says "taper off".</div>')
                h('<div class="plain">The model made it up, politely. A check reads every sentence of the draft and asks where it came from. '
                  'This sentence had no answer, so the draft is marked failed and a person writes the reply. '
                  'That check is the reason the system is allowed to draft at all.</div>')
            with c2:
                views._draft_block(r, t, run, "wt061")

    elif i == 4:
        h(f'<div class="plain">In the ten weeks shown, <b>{n} emails</b> came in. <b>{calls}</b> went straight to a Bone Health Consultant for a phone call. '
          f'<b>{drafts}</b> were routine and arrived with the policy beside them and a first draft to edit; the safety check flagged <b>{flagged}</b> of those before anyone read them. '
          f'Nothing was sent by the system.</div>')
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
                x=alt.X("week:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
                y=alt.Y("n:Q", title=None, axis=alt.Axis(tickMinStep=1)),
                color=alt.Color("Route:N", scale=alt.Scale(domain=["Draft reply", "Consultant call"], range=[G40, G90]), title=None),
                order=alt.Order("Route:N", sort="descending"), tooltip=[alt.Tooltip("week:T", format="%d %b"), "Route", "n"]).properties(height=210)
            st.altair_chart(ch, width="stretch")
        with c2:
            h('<div class="plain"><b>For the agents.</b> No more blank screen. Each email arrives sorted, with the policy attached and a draft to edit.</div>')
            h('<div class="plain"><b>For the team lead.</b> The whole week on one screen: what people write about, how they feel, who needs a call. A minute instead of an afternoon.</div>')

    elif i == 5:
        acc = live._band_words()
        h('<div class="display">Right about <b>three times in four</b> on emails it has never seen.</div>')
        c1, c2 = st.columns([1, 1], gap="large")
        with c1:
            table(["When it says", "It is right"], [("Sure", live._in_n(acc["high"])), ("Fairly sure", live._in_n(acc["medium"])), ("Not sure", live._in_n(acc["low"]))])
            st.caption("From out-of-fold predictions on all 110 labelled emails. The exact figures are on the Model facts page.")
        with c2:
            h('<div class="plain">Good enough to help. Not good enough to trust blindly. So a person always decides, and the first month of doing this for real '
              'would be spent with the people who answer the phone, labelling real emails, because their judgement is what the system should learn.</div>')
            a, b = st.columns(2)
            if a.button("Open the Overview", width="stretch"): st.switch_page(st.session_state["pages"]["Overview"])
            if b.button("Open the Inbox", width="stretch"): st.switch_page(st.session_state["pages"]["Inbox"])

    st.write("")
    _nav(i, "bottom")
    footer(run)
