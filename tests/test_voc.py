"""Voice of customer: rules, the quote guard and the SQL layer, all offline."""
import pandas as pd

import voc
import voc_sql


def test_review_rules_follow_config():
    assert voc.review_rule("results", "negative")["action"] == "consultant_outreach"
    assert voc.review_rule("side_effects", "negative")["action"] == "consultant_outreach"
    assert voc.review_rule("price", "negative")["action"] == "draft_reply"
    assert voc.review_rule("price", "neutral")["action"] == "no_action"
    assert voc.review_rule("support", "positive")["action"] == "no_action"


def test_sentiment_from_stars():
    assert [voc.sentiment_from_stars(s) for s in (1, 2, 3, 4, 5)] == ["negative", "negative", "neutral", "positive", "positive"]


def test_read_review_keeps_only_quotes_that_appear():
    rd = voc.read_review("Charged twice", "My card shows two charges this month for one bottle.")
    assert rd["quote"] == "two charges" and rd["asks_for"] == "a refund" and rd["gist"]
    rd2 = voc.read_review("Late", "The box came a week late.")   # the fake quote 'two charges' is not in this text
    assert rd2["quote"] == "" and rd2["quote_rejected"] == "two charges"


def test_reviews_csv_is_well_formed():
    df = pd.read_csv(voc.ROOT / "data" / "reviews.csv")
    assert set(df.theme) <= set(voc.THEMES) and df.stars.between(1, 5).all()
    assert df.id.is_unique and len(df) >= 100


def _fake_results():
    return pd.DataFrame({
        "id": ["R1", "R2", "R3", "R4"], "source": ["Yotpo", "Amazon", "Yotpo", "Yotpo"],
        "posted_at": ["2026-08-04 09:00", "2026-08-11 09:00", "2026-10-05 09:00", "2026-10-06 09:00"],
        "stars": [5, 2, 1, 2], "product": ["AlgaeCal Plus"] * 4, "verified": [1, 1, 0, 1], "title": ["a", "b", "c", "d"], "body": ["x", "cancel", "price", "price up"],
        "pred_theme": ["results", "subscription", "price", "price"], "pred_theme_conf": [0.9, 0.5, 0.7, 0.6],
        "sentiment": ["positive", "negative", "negative", "negative"], "cancel_intent": [False, True, False, False],
        "gist": ["", "", "", ""], "quote": ["", "", "", ""], "action": ["no_action", "draft_reply", "draft_reply", "draft_reply"],
        "action_reason": [""] * 4, "draft": ["", "d", "d", "d"], "qa_score": [None, 100, 0, 100], "qa_failed": ["", "", "Grounded in policy", ""]})


def test_sql_layer_runs_every_query_and_finds_the_rising_theme():
    wh = voc_sql.Warehouse([voc_sql.rows_from_reviews(_fake_results(), "t")])
    for name in wh.q:
        wh.run(name)
    rt = wh.run("rising_themes")
    assert rt.iloc[0]["theme"] == "price" and rt.iloc[0]["recent_n"] == 2
    rb = wh.run("reply_backlog")
    assert int(rb[rb.action == "draft_reply"].critical_fail.iloc[0]) == 1


def test_bigquery_schema_names_every_column_the_loader_writes():
    ddl = (voc.ROOT / "warehouse" / "bigquery_schema.sql").read_text()
    for col in voc_sql.COLS:
        assert col in ddl, col
