"""
Internal dashboard for the triage pipeline. Reads out/ and models/, never
touches the emails themselves except through the knowledge-base search box.

    streamlit run app/dashboard.py

Ten pages behind a Carbon-style UI shell: Overview, Live triage, Inbox,
Activity (operate); Pipeline, Model quality, Model facts, Knowledge base (understand);
Configuration, Run log (administer). No logo or trademark is used anywhere.
"""
import streamlit as st

from ui import inject_css, load_json, h, shell_header, show_flash, APP_NAME
import views
import live

st.set_page_config(page_title=APP_NAME, page_icon=":material/mark_email_read:", layout="wide", initial_sidebar_state="expanded")
inject_css()
st.session_state.setdefault("reviewer", "khushi")

PAGES = {
    "Overview": st.Page(views.overview, title="Overview", icon=":material/space_dashboard:", default=True),
    "Live triage": st.Page(live.live, title="Live triage", icon=":material/bolt:", url_path="live"),
    "Inbox": st.Page(views.inbox, title="Inbox", icon=":material/inbox:", url_path="inbox"),
    "Activity": st.Page(views.activity, title="Activity", icon=":material/history:", url_path="activity"),
    "Pipeline": st.Page(views.pipeline, title="Pipeline", icon=":material/account_tree:", url_path="pipeline"),
    "Model quality": st.Page(views.quality, title="Model quality", icon=":material/analytics:", url_path="quality"),
    "Model facts": st.Page(views.facts, title="Model facts", icon=":material/fact_check:", url_path="facts"),
    "Knowledge base": st.Page(views.knowledge, title="Knowledge base", icon=":material/menu_book:", url_path="kb"),
    "Configuration": st.Page(views.settings, title="Configuration", icon=":material/tune:", url_path="settings"),
    "Run log": st.Page(views.runlog, title="Run log", icon=":material/terminal:", url_path="runs"),
}
NAV = [("Operate", ["Overview", "Live triage", "Inbox", "Activity"]),
       ("Understand", ["Pipeline", "Model quality", "Model facts", "Knowledge base"]),
       ("Administer", ["Configuration", "Run log"])]
st.session_state["pages"] = PAGES
current = st.navigation(list(PAGES.values()), position="hidden")
run = load_json("run")

shell_header(run, st.session_state["reviewer"])
with st.sidebar:
    for sec, names in NAV:
        h(f'<div class="navsec">{sec}</div>')
        for name in names:
            st.page_link(PAGES[name], label=name, icon=PAGES[name].icon)
    # active item: Carbon side nav, 3px blue left border, gray-20 background
    h(f'<style>[data-testid="stSidebar"] [data-testid="stPageLink"] a[href$="/{current.url_path}"] '
      f'{{ background: #e0e0e0; border-left-color: #0f62fe; }} [data-testid="stSidebar"] [data-testid="stPageLink"] a[href$="/{current.url_path}"] * {{ color: #161616; font-weight: 600; }}</style>')
    st.markdown("---")
    if run:
        h(f'<div class="sidefoot"><b>Last run</b><br><code>{run["run_id"]}</code><br>{run["emails"]} emails · {run["wall_seconds"]:.0f} s<br>'
          f'{run["embed_model"]} · {run["draft_model"] or "no drafting"}</div>')
    h('<div class="sidefoot" style="margin-top:.8rem">Built for the AlgaeCal Associate Data Scientist round 2. All emails are fictional.</div>')

show_flash()
current.run()
