"""Replaying the last run through the YAML rules must reproduce the routing
columns of out/results.csv exactly. Guards the move from hard-coded rules."""
from pathlib import Path

import pandas as pd
import pytest

from draft import route, route_rule

RESULTS = Path(__file__).resolve().parent.parent / "out" / "results.csv"


@pytest.mark.skipif(not RESULTS.exists(), reason="no out/results.csv")
def test_routing_parity_with_last_run():
    df = pd.read_csv(RESULTS).fillna({"escalation_reason": ""})
    for r in df.itertuples():
        rt, why = route(r.pred_category, r.pred_sentiment, r.body)
        rr = route_rule(r.pred_category, r.pred_sentiment, r.body)
        assert rt == r.route, r.id
        assert why == r.route_reason, r.id
        assert (rr["short"] if rt == "consultant_call" else "") == r.escalation_reason, r.id
