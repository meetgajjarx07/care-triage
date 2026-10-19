"""
Shared bits for the dashboard: design tokens, CSS, Altair theme, data loaders,
the review log, status checks, small HTML components.

Visual language is IBM's Carbon Design System (Gray 10 theme, IBM Plex,
square corners, 14px body, 12px labels, one interactive blue, status colours
only for status, pill tags only for state). Only the knowledge-base search
box and the Configuration page's health check talk to Ollama.
"""
import json, re, hashlib
from datetime import datetime
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from config import CFG, config_hash

ROOT = Path(__file__).resolve().parent.parent
OUT, MODELS, KB, DOCS = ROOT / "out", ROOT / "models", ROOT / "kb", ROOT / "docs"
REVIEWS = OUT / "reviews.jsonl"
APP_VERSION = CFG.get("version", "0.5.0")
APP_NAME = "Care Triage"

# ---- Carbon Gray 10 tokens
BG, LAYER, LAYER2 = "#f4f4f4", "#ffffff", "#f4f4f4"
LINE, LINE2, LINE_STRONG = "#e0e0e0", "#e0e0e0", "#8d8d8d"
INK, INK2, GREY, GREY2, GREY3 = "#161616", "#262626", "#525252", "#8d8d8d", "#a8a8a8"
BLUE, BLUE_HOVER, BLUE90, BLUE70, BLUE50, BLUE30, BLUE20, BLUE10 = "#0f62fe", "#0353e9", "#002d9c", "#0043ce", "#4589ff", "#a6c8ff", "#d0e2ff", "#edf5ff"
OK, OKBG, WARN, WARNBG, CRIT, CRITBG, INFO, INFOBG = "#24a148", "#defbe6", "#8e6a00", "#fcf4d6", "#da1e28", "#fff1f1", "#0043ce", "#edf5ff"
YELLOW, MAGENTA, PURPLE, TEAL = "#f1c21b", "#9f1853", "#6929c4", "#005d5d"
MONO = "'IBM Plex Mono', Menlo, ui-monospace, monospace"
SANS = "'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif"

# names the views use for chart colours (kept from v0.3 so the pages read the same)
G90, G80, G70, G60, G40, G20, G10 = BLUE90, BLUE70, BLUE, BLUE50, BLUE30, BLUE20, BLUE10
CORAL, CORAL10, YELLOW10, PAGE, PAPER = MAGENTA, "#ffd6e8", WARNBG, BG, LAYER2

LABELS = {
    "guarantee_claim": "Guarantee claim", "results_question": "Scan & results",
    "safety_concern": "Safety concern", "dosage_question": "Dosing question",
    "shipping_issue": "Shipping", "subscription_billing": "Subscription & billing",
    "positive_feedback": "Positive feedback",
}
ROUTE_LABEL = {"consultant_call": "Consultant call", "draft_reply": "Draft reply"}
STAGES = ["embed", "classify", "retrieve", "route", "draft", "check"]
SUPPORTED = CFG["draft_qa"]["support_thresholds"]["supported"]
WEAK = CFG["draft_qa"]["support_thresholds"]["weak"]
BAND_HIGH, BAND_MED = CFG["confidence_bands"]["high"], CFG["confidence_bands"]["medium"]

CSS = f"""
<style>
/* ---------- base type (Carbon body-compact-01, label-01, helper-text-01) ---------- */
html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, li, div, span, label, button, input, textarea {{ font-family: {SANS}; }}
[data-testid="stAppViewContainer"] {{ color: {INK}; font-size: 14px; background: {BG}; }}
[data-testid="stAppViewContainer"] .stMarkdown p {{ font-size: 14px; line-height: 20px; }}
.stMainBlockContainer, .block-container {{ padding: 1.25rem 2rem 4rem 2rem; max-width: 1600px; }}
header[data-testid="stHeader"] {{ display: none; }}
[data-testid="stAppViewContainer"] > .main, [data-testid="stMain"] {{ padding-top: 48px; }}
[data-testid="stDecoration"], [data-testid="stAppDeployButton"], [data-testid="stToolbarActions"], #MainMenu, footer {{ display: none; visibility: hidden; }}
.tnum {{ font-variant-numeric: tabular-nums; }}
.mono {{ font-family: {MONO}; font-size: 12px; color: {INK}; }}
code {{ font-family: {MONO} !important; font-size: 12px !important; background: none !important; color: {INK} !important; padding: 0 !important; }}

/* ---------- UI shell header (Carbon: 48px, gray-100) ---------- */
.shell {{ position: fixed; top: 0; left: 0; right: 0; height: 48px; background: {INK}; color: #f4f4f4; z-index: 1000000;
          display: flex; align-items: center; border-bottom: 1px solid #393939; font-size: 14px; }}
.shell .name {{ padding: 0 2rem 0 1rem; height: 48px; display: flex; align-items: center; color: #f4f4f4; text-decoration: none; letter-spacing: 0.1px; }}
.shell .name b {{ font-weight: 600; margin-right: 6px; }}
.shell .right {{ margin-left: auto; display: flex; align-items: stretch; height: 48px; }}
.shell .item {{ display: flex; align-items: center; padding: 0 14px; color: #c6c6c6; font-size: 12px; border-left: 1px solid #393939; text-decoration: none; white-space: nowrap; }}
.shell .item code {{ color: #c6c6c6 !important; font-size: 11.5px !important; }}
.shell .item:hover {{ background: #353535; color: #fff; }}
.shell .env {{ color: #78a9ff; }}
.shell .avatar {{ width: 28px; height: 28px; border-radius: 50%; background: {BLUE}; color: #fff; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; margin-right: 8px; }}
.shell .user {{ color: #f4f4f4; }}

/* ---------- side nav (Carbon side nav, g10) ---------- */
[data-testid="stSidebar"] {{ background: {LAYER}; border-right: 1px solid {LINE}; min-width: 256px !important; max-width: 256px !important; margin-top: 48px; height: calc(100vh - 48px); }}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{ padding: 0.5rem 0 0 0; }}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"], [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"] {{ display: none; }}
[data-testid="stSidebar"] .block-container, [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding: 0 0 1rem 0 !important; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0; }}
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.navsec) {{ height: auto !important; min-height: 2.4rem; }}
.navsec {{ font-size: 12px; line-height: 16px; letter-spacing: 0.32px; color: {GREY}; padding: 1rem 1rem 0.25rem; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {{ padding: 0 1rem 0 0.85rem; height: 32px; border-radius: 0; border-left: 3px solid transparent; font-size: 14px; line-height: 32px; display: flex; align-items: center; width: 100%; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{ background: #e5e5e5; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a span, [data-testid="stSidebar"] [data-testid="stPageLink"] a p {{ color: {GREY}; font-size: 14px; line-height: 18px; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a [data-testid="stIconMaterial"] {{ font-size: 16px; color: {GREY}; }}
[data-testid="stSidebar"] hr {{ border-color: {LINE}; margin: 0.75rem 1rem; }}
.sidefoot {{ padding: 0.5rem 1rem 0; font-size: 12px; line-height: 16px; color: {GREY}; }}
.sidefoot b {{ color: {INK}; font-weight: 500; }}
.sidefoot code {{ font-family: {MONO}; font-size: 11px !important; color: {GREY} !important; }}

/* ---------- page header ---------- */
.ph {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; padding: 0 0 1rem; margin-bottom: 1rem; border-bottom: 1px solid {LINE}; }}
.ph h1 {{ font-weight: 400; font-size: 28px; line-height: 36px; letter-spacing: 0; margin: 0; color: {INK}; }}
.ph .sub {{ color: {GREY}; font-size: 14px; line-height: 20px; margin-top: 4px; max-width: 90ch; }}
.ph .meta {{ font-size: 12px; line-height: 16px; color: {GREY}; text-align: right; white-space: nowrap; }}
.ph .meta code {{ font-size: 12px !important; color: {INK} !important; }}
.crumbs {{ font-size: 12px; color: {GREY}; margin-bottom: 4px; }}
.crumbs a {{ color: {BLUE}; text-decoration: none; }}

/* ---------- sections ---------- */
.sec {{ display: flex; align-items: baseline; justify-content: space-between; margin: 1.5rem 0 0.5rem; }}
.sec h2 {{ font-size: 16px; font-weight: 600; line-height: 22px; margin: 0; color: {INK}; }}
.sec .hint {{ font-size: 12px; line-height: 16px; color: {GREY}; }}
.plain {{ font-size: 16px; line-height: 24px; color: {INK}; background: {LAYER}; border: 1px solid {LINE}; border-left: 3px solid {BLUE}; padding: 14px 18px; margin: 0 0 14px; max-width: 110ch; }}
.plain b {{ font-weight: 600; }}
.note {{ font-size: 12px; line-height: 16px; color: {GREY}; max-width: 100ch; letter-spacing: 0.16px; }}
.note b {{ color: {INK}; font-weight: 500; }}
.note code {{ font-size: 11.5px !important; color: {INK} !important; }}

/* ---------- KPI tiles (1px gaps on gray-20, white cells) ---------- */
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: {LINE}; border: 1px solid {LINE}; }}
.stat {{ padding: 12px 16px 12px; background: {LAYER}; min-width: 0; }}
.stat .l {{ font-size: 12px; line-height: 16px; letter-spacing: 0.32px; color: {GREY}; }}
.stat .v {{ font-variant-numeric: tabular-nums; font-size: 28px; font-weight: 300; color: {INK}; margin-top: 6px; line-height: 36px; }}
.stat .v small {{ font-size: 14px; color: {GREY}; font-weight: 400; margin-left: 2px; }}
.stat .d {{ font-size: 12px; line-height: 16px; color: {GREY}; margin-top: 4px; }}
.stat .d.warn {{ color: {CRIT}; }} .stat .d.ok {{ color: #0e6027; }}

/* ---------- funnel ---------- */
.funnel {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 1px; background: {LINE}; border: 1px solid {LINE}; }}
.fstep {{ background: {LAYER}; padding: 12px 16px; position: relative; }}
.fstep .k {{ font-size: 12px; line-height: 16px; letter-spacing: 0.32px; color: {GREY}; }}
.fstep .n {{ font-size: 20px; font-weight: 400; font-variant-numeric: tabular-nums; line-height: 28px; margin: 4px 0 6px; }}
.fstep .n small {{ font-size: 12px; color: {GREY}; font-weight: 400; }}
.fstep .bars {{ display: flex; height: 4px; overflow: hidden; background: {LINE}; margin-bottom: 8px; }}
.fstep .bars span {{ display: block; height: 100%; }}
.fstep .row {{ display: flex; justify-content: space-between; font-size: 12px; color: {GREY}; line-height: 18px; font-variant-numeric: tabular-nums; }}
.fstep .row b {{ color: {INK}; font-weight: 500; }}

/* ---------- tiles, tags, kv ---------- */
.panel {{ background: {LAYER}; padding: 16px; border: 1px solid {LINE}; }}
.panel.soft {{ background: {LAYER2}; }}
.panel.warn {{ background: {WARNBG}; border-left: 3px solid {YELLOW}; }}
.panel.crit {{ background: {CRITBG}; border-left: 3px solid {CRIT}; }}
.panel .t {{ font-size: 14px; line-height: 18px; font-weight: 600; color: {INK}; margin-bottom: 6px; }}
.notif {{ display: flex; gap: 12px; padding: 12px 16px; border: 1px solid {LINE}; border-left: 3px solid {INFO}; background: {INFOBG}; margin: 4px 0 10px; font-size: 14px; line-height: 20px; }}
.notif.success {{ border-left-color: {OK}; background: {OKBG}; }}
.notif.warning {{ border-left-color: {YELLOW}; background: {WARNBG}; }}
.notif.error {{ border-left-color: {CRIT}; background: {CRITBG}; }}
.notif .ti {{ font-weight: 600; margin-right: 6px; }}
.notif .ic {{ width: 18px; height: 18px; border-radius: 50%; flex: 0 0 18px; margin-top: 1px; display: inline-flex; align-items: center; justify-content: center; color: #fff; font-size: 11px; font-weight: 600; background: {INFO}; }}
.notif.success .ic {{ background: {OK}; }} .notif.warning .ic {{ background: {WARN}; }} .notif.error .ic {{ background: {CRIT}; }}
.empty {{ background: {LAYER}; border: 1px solid {LINE}; padding: 28px 24px; text-align: left; }}
.empty .t {{ font-size: 16px; font-weight: 600; line-height: 22px; }}
.empty .b {{ font-size: 14px; color: {GREY}; line-height: 20px; margin-top: 4px; max-width: 70ch; }}
.tag {{ display: inline-flex; align-items: center; font-size: 12px; font-weight: 400; line-height: 16px; letter-spacing: 0.32px; height: 20px; padding: 0 8px; border-radius: 20px; margin: 0 4px 2px 0; white-space: nowrap; vertical-align: middle; background: {LINE}; color: {INK}; }}
.tag.g {{ background: {BLUE20}; color: {BLUE70}; }} .tag.gd {{ background: #393939; color: #fff; }}
.tag.ok {{ background: #a7f0ba; color: #0e6027; }} .tag.warn {{ background: #fcf4d6; color: #684e00; border: 1px solid #f1c21b; }} .tag.crit {{ background: #ffd7d9; color: #a2191f; }}
.tag.info {{ background: {BLUE20}; color: {BLUE70}; }} .tag.n {{ background: {LINE}; color: {INK}; }}
.tag.teal {{ background: #9ef0f0; color: #004144; }} .tag.purple {{ background: #e8daff; color: #491d8b; }} .tag.magenta {{ background: #ffd6e8; color: #9f1853; }}
.tag.m {{ font-family: {MONO}; background: {LINE}; color: {INK}; font-size: 11.5px; letter-spacing: 0; }}
.tag.chip {{ background: transparent; border: 1px solid {LINE_STRONG}; color: {INK}; border-radius: 20px; }}
.dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
.kv {{ width: 100%; border-collapse: collapse; font-size: 14px; border: 0; }}
.kv td {{ padding: 8px 0; border: 0; border-bottom: 1px solid {LINE}; vertical-align: top; background: transparent; line-height: 18px; }}
.kv td:first-child {{ color: {GREY}; width: 34%; padding-right: 16px; font-size: 12px; letter-spacing: 0.32px; }}
.kv tr:last-child td {{ border-bottom: 0; }}
.kv code {{ font-size: 12px !important; }}
.stab {{ width: 100%; border-collapse: collapse; font-size: 14px; background: {LAYER}; }}
.stab th {{ text-align: left; font-size: 12px; letter-spacing: 0.32px; font-weight: 600; color: {INK}; background: {LINE}; padding: 8px 12px; border: 0; }}
.stab td {{ padding: 8px 12px; border: 0; border-bottom: 1px solid {LINE}; vertical-align: top; line-height: 18px; }}
.stab tr:last-child td {{ border-bottom: 0; }}
.stab td.sub {{ color: {GREY}; font-size: 12px; }}

/* ---------- email + draft ---------- */
.mail {{ background: {LAYER}; border: 1px solid {LINE}; }}
.mail .hd {{ padding: 10px 16px; border-bottom: 1px solid {LINE}; display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }}
.mail .hd .s {{ font-weight: 600; font-size: 14px; }}
.mail .hd .m {{ font-size: 12px; color: {GREY}; white-space: nowrap; }}
.mail .hd .m code {{ color: {GREY} !important; }}
.mail .bd {{ padding: 12px 16px 14px; font-size: 14px; line-height: 20px; white-space: pre-wrap; }}
.mail .bd .sup {{ border-bottom: 2px solid {OK}; }}
.mail .bd .weak {{ background: {WARNBG}; }}
.mail .bd .unsup {{ background: {CRITBG}; border-bottom: 2px solid {CRIT}; }}
.prov {{ display: flex; flex-wrap: wrap; align-items: center; gap: 4px; font-size: 12px; color: {GREY}; padding: 8px 16px; background: {LAYER2}; border-bottom: 1px solid {LINE}; }}
.draft {{ border-left: 3px solid {BLUE}; }}
.draft.bad {{ border-left-color: {YELLOW}; }}
.draft.crit {{ border-left-color: {CRIT}; }}

/* ---------- QA scorecard ---------- */
.qa {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
.qa td {{ padding: 6px 6px 6px 0; border-bottom: 1px solid {LINE}; vertical-align: top; line-height: 18px; }}
.qa tr:last-child td {{ border-bottom: 0; }}
.qa .st {{ width: 64px; }}
.qa .ev {{ color: {GREY}; font-size: 12px; line-height: 16px; }}

/* ---------- audit ---------- */
.audit {{ font-size: 12px; color: {GREY}; line-height: 18px; }}
.audit b {{ color: {INK}; font-weight: 500; }}
.audit .when {{ font-family: {MONO}; font-size: 11px; margin-right: 6px; }}

/* ---------- trace ---------- */
.stage {{ display: grid; grid-template-columns: 2rem 1fr; gap: 0.5rem; padding: 12px 0; border-top: 1px solid {LINE}; }}
.stage .n {{ font-family: {MONO}; font-size: 12px; color: {GREY}; padding-top: 2px; }}
.stage .h {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }}
.stage .h .name {{ font-weight: 600; font-size: 14px; }}
.stage .h .comp {{ font-size: 12px; color: {GREY}; }}
.stage .h .comp code {{ color: {GREY} !important; }}
.stage .h .ms {{ font-family: {MONO}; font-size: 12px; color: {GREY}; white-space: nowrap; }}
.stage .body {{ margin-top: 6px; font-size: 14px; }}
.scores {{ display: flex; gap: 1px; flex-wrap: wrap; background: {LINE}; border: 1px solid {LINE}; }}
.score {{ background: {LAYER}; padding: 8px 14px; min-width: 130px; flex: 1; }}
.score .l {{ font-size: 12px; letter-spacing: 0.32px; color: {GREY}; }}
.score .v {{ font-size: 16px; font-weight: 400; font-variant-numeric: tabular-nums; margin-top: 2px; }}

/* ---------- pipeline map ---------- */
.flow {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 1px; background: {LINE}; border: 1px solid {LINE}; }}
.node {{ background: {LAYER}; padding: 12px 14px; min-height: 9.5rem; position: relative; }}
.node .k {{ font-family: {MONO}; font-size: 11px; color: {GREY}; }}
.node .nm {{ font-weight: 600; font-size: 14px; margin: 2px 0 4px; }}
.node .cp {{ font-size: 12px; color: {GREY}; line-height: 16px; min-height: 3.4rem; }}
.node .cp code {{ font-size: 11px !important; color: {GREY} !important; }}
.node .st {{ font-size: 13px; color: {INK}; margin-top: 8px; line-height: 18px; font-variant-numeric: tabular-nums; }}
.node .st span {{ color: {GREY}; }}
.node.llm {{ background: {BLUE10}; }}

/* ---------- status list (Configuration) ---------- */
.status {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 1px; background: {LINE}; border: 1px solid {LINE}; }}
.status .it {{ background: {LAYER}; padding: 12px 16px; }}
.status .it .l {{ font-size: 14px; font-weight: 600; line-height: 18px; display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
.status .it .d {{ font-size: 12px; color: {GREY}; line-height: 16px; margin-top: 4px; }}
.status .it .d code {{ font-size: 11px !important; color: {GREY} !important; }}

/* ---------- footer ---------- */
.foot {{ display: flex; justify-content: space-between; margin-top: 2.5rem; padding-top: 0.6rem; border-top: 1px solid {LINE}; font-size: 12px; color: {GREY2}; }}

/* ---------- Streamlit widgets in Carbon clothes ---------- */
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; }}
div[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="textarea"], [data-testid="stTextInput"] > div > div, [data-testid="stTextArea"] > div > div {{
  border: 0 !important; border-bottom: 1px solid {LINE_STRONG} !important; border-radius: 0 !important; background: {LAYER}; font-size: 14px; }}
div[data-baseweb="select"] > div {{ min-height: 40px; }}
[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within, [data-baseweb="textarea"]:focus-within {{ outline: 2px solid {BLUE}; outline-offset: -2px; border-bottom-color: transparent !important; }}
[data-testid="stExpander"] details {{ border: 1px solid {LINE}; border-radius: 0; background: {LAYER}; }}
[data-testid="stExpander"] summary p {{ font-size: 14px; font-weight: 500; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 0; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ padding: 0 16px; height: 40px; }}
.stTabs [data-baseweb="tab"] p {{ font-size: 14px; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {BLUE}; height: 2px; }}
[data-testid="stCode"] pre, [data-testid="stCode"] code {{ font-family: {MONO} !important; font-size: 12px !important; background: {LAYER} !important; }}
[data-testid="stCode"] {{ border: 1px solid {LINE}; }}
[data-testid="stCaptionContainer"] p {{ font-size: 12px; color: {GREY}; letter-spacing: 0.32px; }}
[data-testid="stSegmentedControl"] button {{ border-radius: 0 !important; border: 1px solid {LINE_STRONG} !important; margin-left: -1px; height: 32px; padding: 0 14px; background: {LAYER}; }}
[data-testid="stSegmentedControl"] button p {{ font-size: 14px; }}
[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"] {{ background: {INK} !important; border-color: {INK} !important; }}
[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"] p {{ color: #fff !important; }}
[data-testid="stRadio"] label p {{ font-size: 14px; }}
.stButton button, [data-testid="stDownloadButton"] button {{ font-size: 14px; border-radius: 0; padding: 0 16px; min-height: 40px; letter-spacing: 0.16px; }}
.stButton button[kind="primary"] {{ background: {BLUE}; border-color: {BLUE}; }}
.stButton button[kind="primary"]:hover {{ background: {BLUE_HOVER}; border-color: {BLUE_HOVER}; }}
.stButton button[kind="secondary"], [data-testid="stDownloadButton"] button {{ border: 1px solid {BLUE}; color: {BLUE}; background: transparent; }}
.stButton button[kind="secondary"]:hover, [data-testid="stDownloadButton"] button:hover {{ background: {BLUE}; color: #fff; }}
[data-testid="stToggle"] p {{ font-size: 14px; }}
[data-testid="stMetric"] label p {{ font-size: 12px; }}
.stProgress > div > div {{ border-radius: 0; }}
</style>
"""


def inject_css():
    st.markdown(re.sub(r"\n\s*\n", "\n", CSS), unsafe_allow_html=True)


def brand_theme():
    return {"config": {
        "font": "IBM Plex Sans, sans-serif",
        "view": {"stroke": None},
        "axis": {"labelColor": GREY, "titleColor": GREY, "labelFontSize": 12, "titleFontSize": 12, "titleFontWeight": 400,
                 "gridColor": LINE, "domainColor": LINE_STRONG, "tickColor": LINE_STRONG, "labelPadding": 6, "titlePadding": 8},
        "axisX": {"grid": False},
        "legend": {"labelColor": INK, "titleColor": GREY, "labelFontSize": 12, "titleFontSize": 12, "symbolType": "square", "symbolSize": 80, "orient": "bottom", "titleFontWeight": 400},
        "range": {"category": [BLUE, PURPLE, TEAL, MAGENTA, "#1192e8", "#fa4d56", "#198038", "#b28600"]},
        "bar": {"cornerRadiusEnd": 0},
        "text": {"color": INK, "fontSize": 12},
        "title": {"color": INK, "fontSize": 14, "fontWeight": 600, "anchor": "start"},
    }}


alt.themes.register("brand", brand_theme)
alt.themes.enable("brand")


# ---------------- data ----------------
@st.cache_data(show_spinner=False)
def load_results():
    p = OUT / "results.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    df["received_at"] = pd.to_datetime(df["received_at"])
    df["week"] = df["received_at"].dt.to_period("W-SUN").dt.start_time
    df["Category"] = df["pred_category"].map(LABELS)
    df["Route"] = df["route"].map(ROUTE_LABEL)
    for c in ["draft_reply", "check_flags", "qa_failed", "escalation_reason"]:
        if c in df: df[c] = df[c].fillna("")
        else: df[c] = ""
    if "confidence_band" not in df:
        df["confidence_band"] = pd.cut(df.pred_category_conf, [-1, BAND_MED, BAND_HIGH, 2], labels=["low", "medium", "high"]).astype(str)
    if "qa_score" not in df:
        df["qa_score"] = float("nan")
    df["flagged"] = (df["route"] == "draft_reply") & (df["check_flags"] != "")
    df["cancel_flag"] = df["body"].str.contains(r"cancel|stop sending|stop my", case=False, regex=True)
    return df


@st.cache_data(show_spinner=False)
def load_trace():
    p = OUT / "trace.jsonl"
    if not p.exists():
        return {}
    return {json.loads(l)["id"]: json.loads(l) for l in p.read_text().splitlines() if l.strip()}


@st.cache_data(show_spinner=False)
def load_json(name):
    p = {"run": OUT / "run.json", "metrics": MODELS / "metrics.json", "eval": MODELS / "eval.json",
         "retrieval": MODELS / "retrieval_eval.json"}[name]
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data(show_spinner=False)
def load_log():
    p = OUT / "pipeline.log"
    return p.read_text() if p.exists() else ""


@st.cache_data(show_spinner=False)
def load_text(path):
    p = Path(path)
    return p.read_text() if p.exists() else ""


def has_run():
    return (OUT / "results.csv").exists() and (OUT / "run.json").exists()


# ---------------- review log (append only) ----------------
REVIEW_COLS = ["at", "id", "action", "reviewer", "field", "old", "new", "reason", "text"]


@st.cache_data(show_spinner=False)
def load_reviews():
    if not REVIEWS.exists():
        return pd.DataFrame(columns=REVIEW_COLS)
    rows = [json.loads(l) for l in REVIEWS.read_text().splitlines() if l.strip()]
    return pd.DataFrame(rows, columns=REVIEW_COLS) if rows else pd.DataFrame(columns=REVIEW_COLS)


def add_review(**rec):
    rec = {"at": datetime.now().isoformat(timespec="seconds"), "reviewer": st.session_state.get("reviewer", "khushi"), **rec}
    OUT.mkdir(exist_ok=True)
    with open(REVIEWS, "a") as f:
        f.write(json.dumps(rec) + "\n")
    load_reviews.clear()


def flash(msg, icon=":material/check_circle:"):
    """Queue a toast that survives the st.rerun() after a review action."""
    st.session_state["flash"] = (msg, icon)


def show_flash():
    if "flash" in st.session_state:
        msg, icon = st.session_state.pop("flash")
        st.toast(msg, icon=icon)


def review_status(df):
    """Latest draft decision per email: pending / approved / edited / discarded; consultant calls = escalated."""
    r = load_reviews()
    status = pd.Series("pending", index=df.id)
    status[df.set_index("id").route == "consultant_call"] = "escalated"
    if len(r):
        d = r[r.action.isin(["approve", "edit", "discard"])].sort_values("at").groupby("id").last()
        m = {"approve": "approved", "edit": "edited", "discard": "discarded"}
        for i, a in d.action.items():
            if i in status.index:
                status[i] = m[a]
    return status


def corrections(df):
    r = load_reviews()
    return r[r.action == "correct"] if len(r) else r


# ---------------- health + monitoring ----------------
def ollama_status(timeout=1.0):
    """(reachable, {model_name: True}) using Ollama's /api/tags. Never raises."""
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=timeout) as r:
            tags = json.loads(r.read().decode())
        names = {m["name"].split(":")[0] for m in tags.get("models", [])}
        return True, names
    except Exception:
        return False, set()


def api_status(timeout=0.6):
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:8000/health", timeout=timeout) as r:
            return True, json.loads(r.read().decode())
    except Exception:
        return False, {}


def kb_index_fresh():
    """True if models/kb_index.json was built from the current kb/*.md chunk texts."""
    try:
        from retrieve import chunk_kb
        key = hashlib.md5(json.dumps([c["text"] for c in chunk_kb()]).encode()).hexdigest()
        cache = MODELS / "kb_index.json"
        return cache.exists() and json.loads(cache.read_text()).get("key") == key
    except Exception:
        return False


def system_checks(run):
    """List of {name, ok, level, detail} for the Configuration page and the header."""
    up, names = ollama_status()
    emb, drf = CFG["models"]["embed"], CFG["models"]["draft"]
    checks = [
        {"name": "Ollama", "ok": up, "level": "error", "detail": "reachable on localhost:11434" if up else "not reachable; drafting and the live retriever fall back or stop"},
        {"name": f"Embedding model {emb}", "ok": emb in names, "level": "error", "detail": "pulled" if emb in names else f"run <code>ollama pull {emb}</code>"},
        {"name": f"Drafting model {drf}", "ok": drf in names, "level": "error", "detail": "pulled" if drf in names else f"run <code>ollama pull {drf}</code>"},
    ]
    for f in ["category.joblib", "sentiment.joblib"]:
        p = MODELS / f
        checks.append({"name": f"Classifier {f.split('.')[0]}", "ok": p.exists(), "level": "error",
                       "detail": f"trained {datetime.fromtimestamp(p.stat().st_mtime):%d %b %H:%M}" if p.exists() else "missing; run <code>python app/classify.py --llm</code>"})
    fresh = kb_index_fresh()
    checks.append({"name": "Knowledge base index", "ok": fresh, "level": "warning", "detail": "dense index matches kb/*.md" if fresh else "kb/ changed since the index was built; rebuilds on next run"})
    if run:
        age = (datetime.now() - datetime.fromisoformat(run["finished_at"])).days
        mx = CFG["monitoring"]["run_age_days_max"]
        checks.append({"name": "Last run", "ok": age <= mx, "level": "warning", "detail": f"<code>{run['run_id']}</code> · {age} day{'s' if age != 1 else ''} old (limit {mx})"})
        same = run.get("config_hash") == config_hash()
        checks.append({"name": "Run matches config", "ok": same, "level": "warning",
                       "detail": f"config <code>{config_hash()}</code> is what produced this run" if same else "config/triage.yaml changed after this run; rerun the pipeline"})
    else:
        checks.append({"name": "Last run", "ok": False, "level": "error", "detail": "no run yet; run <code>python app/pipeline.py</code>"})
    rv = load_reviews()
    checks.append({"name": "Review log", "ok": True, "level": "info", "detail": f"{len(rv)} entries in <code>out/reviews.jsonl</code>"})
    api_up, api = api_status()
    checks.append({"name": "API service", "ok": api_up, "level": "info", "detail": f"localhost:8000 · v{api.get('version','')}" if api_up else "not running (optional) · <code>make api</code>"})
    return checks


def monitoring_rows(df, run):
    """Current value of each monitored metric against its threshold in config."""
    m = CFG["monitoring"]
    if df is None or not len(df):
        return []
    dr = df[df.route == "draft_reply"]
    crit = float((dr.qa_score == 0).mean()) if len(dr) else 0.0
    low = float((df.confidence_band == "low").mean())
    rv = load_reviews()
    reviewed = int(rv[rv.action.isin(["approve", "edit", "discard"])].id.nunique()) if len(rv) else 0
    corr = int(rv[rv.action == "correct"].id.nunique()) if len(rv) else 0
    corr_rate = corr / reviewed if reviewed else None
    age = (datetime.now() - datetime.fromisoformat(run["finished_at"])).days if run else None
    rows = [
        {"Metric": "Critical QA fail rate", "What it measures": "drafts with a critical QA fail, share of all drafts in the run", "Current": f"{crit:.0%}", "Limit": f"≤ {m['critical_qa_fail_rate_max']:.0%}", "ok": crit <= m["critical_qa_fail_rate_max"]},
        {"Metric": "Low confidence share", "What it measures": "emails whose top-1 probability is below the medium band", "Current": f"{low:.0%}", "Limit": f"≤ {m['low_band_share_max']:.0%}", "ok": low <= m["low_band_share_max"]},
        {"Metric": "Correction rate", "What it measures": "reviewed drafts where the reviewer changed category or sentiment", "Current": f"{corr_rate:.0%}" if corr_rate is not None else "no reviews yet", "Limit": f"≤ {m['correction_rate_max']:.0%}", "ok": (corr_rate or 0) <= m["correction_rate_max"]},
        {"Metric": "Run age", "What it measures": "days since the pipeline last ran", "Current": f"{age} d" if age is not None else "no run", "Limit": f"≤ {m['run_age_days_max']} d", "ok": age is not None and age <= m["run_age_days_max"]},
    ]
    return rows


# ---------------- components ----------------
def h(html):
    st.markdown(re.sub(r"\n\s*\n", "\n", html), unsafe_allow_html=True)


def initials(name):
    parts = [p for p in re.split(r"[\s._-]+", str(name).strip()) if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def shell_header(run, reviewer):
    env = CFG.get("environment", "local")
    rid = run.get("run_id", "no run") if run else "no run"
    h(f'<div class="shell"><a class="name" href="/"><b>{APP_NAME}</b> Customer care</a>'
      f'<div class="right">'
      f'<span class="item env">{env} · demo data</span>'
      f'<a class="item" href="/runs" title="Run log"><code>{rid}</code></a>'
      f'<a class="item" href="/facts" title="Model facts">Model facts</a>'
      f'<a class="item user" href="/settings" title="Configuration"><span class="avatar">{initials(reviewer)}</span>{reviewer}</a>'
      f'</div></div>')


def page_header(title, sub, run, crumbs=None):
    meta = ""
    if run:
        w = run.get("window", ["", ""])
        meta = (f'<div class="meta"><code>{run.get("run_id","")}</code><br>{run.get("emails","")} emails, '
                f'{w[0][:10]} to {w[1][:10]}<br>{run.get("embed_model","")} · {run.get("draft_model") or "no drafting"}</div>')
    bc = f'<div class="crumbs">{crumbs}</div>' if crumbs else ""
    h(f'<div class="ph"><div>{bc}<h1>{title}</h1><div class="sub">{sub}</div></div>{meta}</div>')


def footer(run):
    r = run or {}
    h(f'<div class="foot"><span>{APP_NAME} v{APP_VERSION} · config {config_hash()} · {r.get("run_id","no run")} · {CFG.get("environment","local")}</span>'
      f'<span>{r.get("emails","–")} fictional emails · last run {r.get("finished_at","–").replace("T"," ")}</span></div>')


def section(title, hint=""):
    h(f'<div class="sec"><h2>{title}</h2><span class="hint">{hint}</span></div>')


def notification(kind, title, body=""):
    ic = {"info": "i", "success": "✓", "warning": "!", "error": "✕"}.get(kind, "i")
    h(f'<div class="notif {kind}"><span class="ic">{ic}</span><div><span class="ti">{title}</span><span>{body}</span></div></div>')


def empty_state(title, body):
    h(f'<div class="empty"><div class="t">{title}</div><div class="b">{body}</div></div>')


def no_run_notice():
    notification("warning", "No pipeline run found.", "Run <code>python app/classify.py --llm</code>, then <code>python app/pipeline.py</code> and <code>python app/eval_retrieval.py</code>, or <code>make all</code>. See docs/runbook.md.")


def stats(items):
    cells = ""
    for it in items:
        l, v = it[0], it[1]
        unit = f"<small>{it[2]}</small>" if len(it) > 2 and it[2] else ""
        d = it[3] if len(it) > 3 else ""
        cls = it[4] if len(it) > 4 else ""
        cells += f'<div class="stat"><div class="l">{l}</div><div class="v">{v}{unit}</div><div class="d {cls}">{d}</div></div>'
    h(f'<div class="stats">{cells}</div>')


def tag(text, kind="n"):
    return f'<span class="tag {kind}">{text}</span>'


def kv(rows):
    body = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    h(f'<table class="kv">{body}</table>')


def table(cols, rows):
    """Small static HTML table in Carbon data-table clothes, for text-heavy rows."""
    head = "".join(f"<th>{c}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    h(f'<table class="stab"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')


def status_list(checks):
    cells = ""
    for c in checks:
        if c["ok"]:
            t = tag("OK", "ok")
        else:
            t = tag({"error": "Failed", "warning": "Warning", "info": "Off"}.get(c["level"], "Warning"), {"error": "crit", "warning": "warn", "info": "n"}.get(c["level"], "warn"))
        cells += f'<div class="it"><div class="l"><span>{c["name"]}</span>{t}</div><div class="d">{c["detail"]}</div></div>'
    h(f'<div class="status">{cells}</div>')


def route_tag(route):
    return tag("Consultant call", "gd") if route == "consultant_call" else tag("Draft reply", "g")


def band_tag(band):
    return tag({"high": "High confidence", "medium": "Medium confidence", "low": "Low confidence"}.get(band, band),
               {"high": "ok", "medium": "n", "low": "warn"}.get(band, "n"))


def status_tag(s):
    return tag(s.capitalize(), {"approved": "ok", "edited": "info", "discarded": "crit", "escalated": "gd", "pending": "n"}.get(s, "n"))


def qa_tag(score, critical=False):
    if score is None or (isinstance(score, float) and pd.isna(score)):
        return ""
    if critical or score == 0:
        return tag("QA fail", "crit")
    return tag(f"QA {int(score)}", "ok" if score == 100 else "warn")


def sentiment_dot(s):
    c = {"negative": CRIT, "positive": OK, "neutral": GREY2}.get(s, GREY2)
    return f'<span class="dot" style="background:{c}"></span>{s}'


def fmt_ms(ms):
    if ms is None:
        return "—"
    return f"{ms/1000:.1f} s" if ms >= 1000 else (f"{ms:.0f} ms" if ms >= 1 else f"{ms:.2f} ms")


def support_class(sim):
    return "sup" if sim >= SUPPORTED else ("weak" if sim >= WEAK else "unsup")


def faithfulness(support):
    if not support:
        return None
    return sum(1 for s in support if s["sim"] >= SUPPORTED) / len(support)


def highlight_draft(text, support):
    """Wrap each scored sentence of the draft in a span by its support band."""
    out = text
    for s in sorted(support, key=lambda x: -len(x["sentence"])):
        sent = s["sentence"]
        if sent in out:
            title = f'{s["sim"]:.2f} · {s["source"]}: {s["evidence"][:120]}'
            out = out.replace(sent, f'<span class="{support_class(s["sim"])}" title="{title}">{sent}</span>', 1)
    return out


def rel_time(ts, now=None):
    now = now or datetime(2026, 10, 18, 12, 0)
    d = now - ts
    if d.days < 1:
        return f"{int(d.seconds // 3600)}h ago"
    if d.days < 30:
        return f"{d.days}d ago"
    return ts.strftime("%d %b")
