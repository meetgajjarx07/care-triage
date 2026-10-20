"""The voice-of-customer table and the queries behind the dashboard numbers.

warehouse/bigquery_schema.sql is the table as it would exist in BigQuery.
Here the same rows are loaded into an in-memory SQLite database and
warehouse/queries.sql is run against it, so every figure on the page is a
query someone can read, and the same SQL (minus two date functions, marked
in the file) runs in the warehouse."""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
QUERIES_FILE = ROOT / "warehouse" / "queries.sql"
COLS = ["item_id", "source", "channel", "happened_at", "week_start", "product", "stars", "verified", "title", "body",
        "theme", "category", "theme_conf", "sentiment", "cancel_intent", "gist", "quote", "action", "action_reason",
        "draft", "qa_score", "qa_failed", "run_id"]


def load_queries(path=QUERIES_FILE):
    text = Path(path).read_text()
    out = {}
    for m in re.finditer(r"-- name: (\w+)\n(.*?)(?=\n-- name: |\Z)", text, re.S):
        body = "\n".join(l for l in m.group(2).splitlines() if not l.strip().startswith("--"))
        out[m.group(1)] = body.strip()
    return out


def week_start(ts):
    ts = pd.to_datetime(ts)
    return (ts - pd.to_timedelta(ts.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")


def rows_from_reviews(df, run_id="local"):
    t = pd.DataFrame({
        "item_id": df["id"], "source": df["source"], "channel": "review", "happened_at": pd.to_datetime(df["posted_at"]).dt.strftime("%Y-%m-%d %H:%M"),
        "week_start": week_start(df["posted_at"]), "product": df["product"], "stars": df["stars"].astype(int), "verified": df["verified"].astype(int),
        "title": df["title"], "body": df["body"], "theme": df["pred_theme"], "category": None, "theme_conf": df["pred_theme_conf"],
        "sentiment": df["sentiment"], "cancel_intent": df["cancel_intent"].astype(int), "gist": df["gist"], "quote": df["quote"],
        "action": df["action"], "action_reason": df["action_reason"], "draft": df["draft"], "qa_score": df["qa_score"], "qa_failed": df["qa_failed"], "run_id": run_id})
    return t[COLS]


def rows_from_emails(df, run_id="local"):
    t = pd.DataFrame({
        "item_id": df["id"], "source": "email", "channel": "email", "happened_at": pd.to_datetime(df["received_at"]).dt.strftime("%Y-%m-%d %H:%M"),
        "week_start": week_start(df["received_at"]), "product": None, "stars": None, "verified": None,
        "title": df["subject"], "body": df["body"], "theme": None, "category": df["pred_category"], "theme_conf": df["pred_category_conf"],
        "sentiment": df["pred_sentiment"], "cancel_intent": df["body"].str.contains(r"cancel|stop sending|not working", case=False, regex=True).astype(int),
        "gist": df.get("brief_asks", ""), "quote": None, "action": df["route"], "action_reason": df["route_reason"],
        "draft": df["draft_reply"], "qa_score": df["qa_score"], "qa_failed": df["qa_failed"], "run_id": run_id})
    return t[COLS]


class Warehouse:
    def __init__(self, frames):
        self.con = sqlite3.connect(":memory:")
        pd.concat(frames, ignore_index=True).to_sql("voice_of_customer", self.con, index=False)
        self.q = load_queries()

    def run(self, name, **params):
        sql = self.q[name]
        return pd.read_sql_query(sql, self.con, params=params or None)

    def sql(self, name):
        return self.q[name]
