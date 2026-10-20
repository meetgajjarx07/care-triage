"""Voice of customer: the email sorter pointed at reviews, with every number on the
page coming from a SQL query over one voice_of_customer table (warehouse/)."""
import json

import altair as alt
import pandas as pd
import streamlit as st

from ui import (G90, G70, G60, G40, CORAL, YELLOW, INK, GREY, LINE2, h, page_header, footer, section, stats, table,
                notification, load_results, OUT)
import views
import voc_sql

THEME_LABEL = {"results": "Results on a scan", "side_effects": "Stomach and side effects", "price": "Price and value", "pills": "Pill size and taking it",
               "shipping": "Shipping and delivery", "support": "Support and consultants", "subscription": "Subscription and billing"}
ACTION_LABEL = {"draft_reply": "Public reply drafted", "consultant_outreach": "Consultant reaches out", "no_action": "Counted, no reply"}
CSS = f"""<style>
.stars {{ color: {INK}; letter-spacing: 1px; font-size: 13px; }} .stars small {{ color: {GREY}; letter-spacing: 0; margin-left: 6px; }}
.src {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 14px; }}
.src .s {{ border: 1px solid {LINE2}; padding: 8px 12px; font-size: 12px; line-height: 16px; min-width: 150px; }}
.src .s b {{ display: block; font-size: 14px; font-weight: 600; }} .src .s.off {{ color: {GREY}; border-style: dashed; }}
mark.q {{ background: #d0e2ff; color: {INK}; padding: 0 2px; }}
.gist {{ font-size: 16px; line-height: 24px; margin: 8px 0 4px; }}
.sqlbox pre {{ font-size: 12px; line-height: 17px; }}
</style>"""


@st.cache_data(show_spinner=False)
def load_voc():
    p = OUT / "voc_results.csv"
    if not p.exists():
        return pd.DataFrame(), {}, {}
    df = pd.read_csv(p)
    for c in ["gist", "quote", "draft", "qa_failed", "action_short"]:
        df[c] = df[c].fillna("")
    df["posted_at"] = pd.to_datetime(df["posted_at"])
    run = json.loads((OUT / "voc_run.json").read_text()) if (OUT / "voc_run.json").exists() else {}
    tr = {}
    if (OUT / "voc_trace.jsonl").exists():
        tr = {json.loads(l)["id"]: json.loads(l) for l in (OUT / "voc_trace.jsonl").read_text().splitlines() if l.strip()}
    return df, run, tr


def warehouse(df, run):
    frames = [voc_sql.rows_from_reviews(df, run.get("run_id", "local"))]
    em = load_results()
    if not em.empty:
        frames.append(voc_sql.rows_from_emails(em, run.get("run_id", "local")))
    return voc_sql.Warehouse(frames)


def _stars(n):
    return f'<span class="stars">{"★" * int(n)}{"☆" * (5 - int(n))}</span>'


def _review_card(r, quote=""):
    body = r.body
    if quote and quote.lower() in body.lower():
        i = body.lower().index(quote.lower()); body = body[:i] + f'<mark class="q">{body[i:i+len(quote)]}</mark>' + body[i+len(quote):]
    h(f'<div class="mail"><div class="hd"><span class="s">{r.title}</span><span class="m">{_stars(r.stars)} <small>{r.source} · {r["product"]} · {r.posted_at:%d %b}</small></span></div>'
      f'<div class="bd"><b>{r.reviewer}</b>{" · verified buyer" if r.verified else ""}<br><br>{body}</div></div>')


def rising(wh):
    rt = wh.run("rising_themes")
    top = rt.iloc[0]
    return top, rt


def voc():
    df, run, tr = load_voc()
    h(CSS)
    if df.empty:
        page_header("Voice of customer", "", {}); notification("warning", "No review run found.", " Run <code>python app/voc.py</code> (about ten minutes with the local model) or <code>python app/voc.py --no-llm</code> (seconds)."); return
    page_header("Voice of customer", "The same sorter, pointed at reviews. Every number here is a SQL query over one voice_of_customer table.", {**run, "unit": "reviews"})
    wh = warehouse(df, run)
    n = len(df); neg = int((df.sentiment == "negative").sum()); drafted = int((df.action == "draft_reply").sum()); outreach = int((df.action == "consultant_outreach").sum())
    crit = int(((df.action == "draft_reply") & (df.qa_score == 0)).sum())
    h('<div class="plain">Emails are one channel. Reviews on the site and on Amazon say the same things to everyone, in public. '
      'This page reads them with the same four steps: sort by theme, read the mood, write one line about what the reviewer is saying, and decide by rule whether a public reply is drafted, '
      'a consultant reaches out privately, or it is simply counted. A scan result or a side effect is never discussed in public.</div>')
    src = wh.run("by_source")
    cells = "".join(f'<div class="s"><b>{int(r.n)}</b>{r.source} · {r.avg_stars:.1f} stars · {int(r.negative)} negative</div>' for r in src.itertuples())
    em = load_results()
    cells += f'<div class="s"><b>{len(em)}</b>Support email · in the Inbox</div>' if not em.empty else ""
    cells += '<div class="s off"><b>Not connected</b>Talkdesk calls and chat · same table, same sorter</div>'
    h(f'<div class="src">{cells}</div>')

    top, rt = rising(wh)
    stats([("Reviews in ten weeks", n, "", f"{run.get('sources', {}).get('Yotpo', 0)} on the site, {run.get('sources', {}).get('Amazon', 0)} on Amazon"),
           ("Average stars", f"{df.stars.mean():.1f}", "", f"{neg} of {n} at one or two stars"),
           ("Public replies drafted", drafted, "", f"{crit} failed a critical check" if crit else "all passed the critical checks", "warn" if crit else "ok"),
           ("Consultant reaches out", outreach, "", "health or scan in a negative review, never answered in public"),
           ("Theme sorter right", f"{100 * run.get('theme_oof_accuracy', 0):.0f}%", "", "out of fold, on reviews it never saw")])
    st.write("")
    if top.recent_per_week > top.before_per_week:
        notification("warning", f"{THEME_LABEL.get(top.theme, top.theme)} is rising.",
                     f" {top.recent_per_week:.1f} reviews a week in the last three weeks, against {top.before_per_week:.1f} a week before that. "
                     f"{int(top.recent_n)} in the window. This is the kind of thing the business should hear the week it happens.")
    st.caption("The rise in price complaints is planted in this fictional set on purpose, so the page has something to surface. The query that found it is under the charts.")

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        section("Themes by week", "stacked by mood, from themes_by_week")
        tw = wh.run("themes_by_week"); tw["week_start"] = pd.to_datetime(tw.week_start); tw["Theme"] = tw.theme.map(THEME_LABEL)
        ch = alt.Chart(tw).mark_bar(size=22).encode(
            x=alt.X("week_start:T", title=None, scale=alt.Scale(padding=22), axis=alt.Axis(format="%d %b", labelAngle=0)),
            y=alt.Y("sum(n):Q", title=None, axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Theme:N", scale=alt.Scale(domain=list(THEME_LABEL.values()), range=[G90, G70, CORAL, G60, G40, "#a6c8ff", YELLOW]), legend=alt.Legend(orient="top", columns=4, title=None)),
            tooltip=[alt.Tooltip("week_start:T", format="%d %b"), "Theme", "sentiment", alt.Tooltip("sum(n):Q", title="reviews")]).properties(height=230)
        st.altair_chart(ch, width="stretch")
    with c2:
        section("What the themes are", "share and how negative each runs")
        tm = wh.run("theme_mix"); tm["Theme"] = tm.theme.map(THEME_LABEL); tm["neg_share"] = tm.negative / tm.n
        base = alt.Chart(tm).encode(y=alt.Y("Theme:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False)))
        bars = base.mark_bar(size=18, color=LINE2).encode(x=alt.X("n:Q", title=None, scale=alt.Scale(domain=[0, float(tm.n.max()) * 1.25]), axis=alt.Axis(tickMinStep=5)), tooltip=["Theme", "n", "negative", "avg_stars"])
        negb = base.mark_bar(size=18, color=CORAL).encode(x="negative:Q", tooltip=["Theme", "negative"])
        txt = base.mark_text(align="left", dx=4, color=INK, fontSize=11).encode(x="n:Q", text=alt.Text("avg_stars:Q", format=".1f"))
        st.altair_chart((bars + negb + txt).properties(height=230), width="stretch")
        h('<div class="note">Grey is all reviews on the theme, red the one- and two-star ones, the number is the average stars.</div>')

    c1, c2, c3 = st.columns([1.3, 1.2, 1.5], gap="large")
    with c1:
        section("By product", "stars_by_product")
        sp = wh.run("stars_by_product")
        table(["Product", "Reviews", "Avg", "1 or 2 ★"], [(r.product, int(r.n), f"{r.avg_stars:.1f}", int(r.one_or_two_star)) for r in sp.itertuples()])
    with c2:
        section("What happened to the bad ones", "reply_backlog")
        rb = wh.run("reply_backlog")
        table(["Action", "Reviews", "Critical fail"], [(ACTION_LABEL.get(r.action, r.action), int(r.n), int(r.critical_fail)) for r in rb.itertuples()])
    with c3:
        section("Talking about leaving, both channels", "cancel_mentions_all_channels")
        cm = wh.run("cancel_mentions_all_channels"); cm["week_start"] = pd.to_datetime(cm.week_start)
        ch = alt.Chart(cm).mark_line(point=alt.OverlayMarkDef(size=30)).encode(
            x=alt.X("week_start:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)), y=alt.Y("cancel_n:Q", title=None, axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("channel:N", scale=alt.Scale(domain=["email", "review"], range=[G70, CORAL]), legend=alt.Legend(orient="top", title=None)),
            tooltip=[alt.Tooltip("week_start:T", format="%d %b"), "channel", "cancel_n", "n"]).properties(height=170)
        st.altair_chart(ch, width="stretch")

    section("Needs a person", "one- and two-star reviews, newest first; select one")
    q = df[df.sentiment == "negative"].sort_values("posted_at", ascending=False)
    view = pd.DataFrame({"ID": q.id, "Posted": q.posted_at.dt.strftime("%d %b"), "Source": q.source, "Stars": q.stars, "Product": q["product"],
                         "Theme": q.pred_theme.map(THEME_LABEL), "What they are saying": q.gist, "Action": q.action.map(ACTION_LABEL)})
    ev = st.dataframe(view, hide_index=True, height=320, width="stretch", on_select="rerun", selection_mode="single-row", key="voc_q",
                      column_config={"ID": st.column_config.TextColumn(width=60), "Posted": st.column_config.TextColumn(width=70), "Source": st.column_config.TextColumn(width=110),
                                     "Stars": st.column_config.NumberColumn(width=60), "Product": st.column_config.TextColumn(width=130), "Theme": st.column_config.TextColumn(width=170),
                                     "What they are saying": st.column_config.TextColumn(width=360), "Action": st.column_config.TextColumn(width=190)})
    sel = view.iloc[ev.selection.rows[0]]["ID"] if ev.selection.rows else q.iloc[0].id
    detail(df[df.id == sel].iloc[0], tr.get(sel, {}), run)

    with st.expander("The SQL behind this page"):
        st.markdown("The table is `warehouse/bigquery_schema.sql`; the queries are `warehouse/queries.sql`, run here on SQLite over the same rows. The one that found the rising theme:")
        st.code(wh.sql("rising_themes"), language="sql")
        st.dataframe(rt.assign(before_per_week=rt.before_per_week.round(2), recent_per_week=rt.recent_per_week.round(2)), hide_index=True, width="stretch")
    with st.expander("How this would run at AlgaeCal"):
        st.markdown("""A design, not something built here. Reviews from the **Yotpo** API and **Amazon Seller Central** exports, call and chat transcripts from **Talkdesk**, and the support mailbox land in **Cloud Storage**, and a scheduled job loads them into one `care.voice_of_customer` table in **BigQuery** (the DDL is in `warehouse/`). This sorter runs as a scheduled Python job over the new rows, writes the theme, the mood, the gist and the action back to the same table, and **Looker** reads it. Drafted public replies go to a person in the Yotpo moderation queue; consultant outreach becomes a **Salesforce** task. Nothing is posted by the system. The health rule stays: a scan result or a side effect is never answered in public.""")
    footer(run)


def detail(r, t, run):
    S = t.get("stages", {}); rd = S.get("read", {}) or {}
    c1, c2 = st.columns([1, 1.3], gap="large")
    with c1:
        _review_card(r, r.quote)
        if r.gist:
            h(f'<div class="gist"><b>What the model read:</b> {r.gist}</div>')
            h('<div class="note">The highlighted phrase is the one the model copied out as evidence; it is shown only because it really appears in the review. '
              + (f'Asks for: {rd.get("asks_for")}. ' if rd.get("asks_for") else "") + f'{rd.get("ms", 0)} ms.</div>')
        probs = (S.get("theme", {}) or {}).get("probs", {})
        if probs:
            top3 = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
            h('<div class="note" style="margin-top:8px">Theme, out of fold: ' + ", ".join(f"{THEME_LABEL.get(k, k)} {v:.2f}" for k, v in top3) + f'. Mood from the stars: {r.sentiment}.</div>')
    with c2:
        rule = S.get("rule", {}) or {}
        kind = "info" if r.action == "consultant_outreach" else ("warning" if r.action == "draft_reply" and r.qa_score == 0 else "success" if r.action == "draft_reply" else "info")
        notification(kind, ACTION_LABEL.get(r.action, r.action) + ".", f" {rule.get('reason', r.action_reason)} (rule <code>{rule.get('rule_id', '')}</code>)")
        if r.action == "draft_reply" and r.draft:
            C = S.get("check") or {}; qa = C.get("qa")
            hits = (S.get("retrieve") or {}).get("hits", [])
            cls = "crit" if (qa and qa["critical_fail"]) else ("bad" if (qa and qa["score"] < 100) else "")
            h(f'<div class="mail draft {cls}"><div class="hd"><span class="s">Public reply, draft</span><span class="m">' + (views.qa_tag(qa["score"], qa["critical_fail"]) if qa else "") + '</span></div>'
              + views._provenance(hits, run.get("draft_model", "llama3.2"), r.draft_seconds or 0, len(r.draft.split())) + f'<div class="bd">{r.draft}</div></div>')
            if qa:
                st.write(""); views._qa_table(qa)
        elif r.action == "consultant_outreach":
            h('<div class="note">No public text is generated for this review. The reviewer mentions a scan result or a side effect, and the rule says a Bone Health Consultant contacts them privately. The gist above is for the consultant.</div>')
