"""triage_email runs offline (fake embeddings from conftest) and returns a trace-shaped record."""
import numpy as np

from triage import triage_email


def test_triage_record_shape_without_draft():
    seen = []
    rec = triage_email("two charges", "My card shows two charges this month for one bottle.", "Jean",
                       draft=False, progress=lambda s, r: seen.append(s))
    S = rec["stages"]
    assert rec["id"].startswith("LIVE-") and rec["live"] is True
    assert seen == ["embed", "classify", "retrieve", "route"]
    assert S["embed"]["dim"] == 768
    assert S["classify"]["band"] in ("high", "medium", "low")
    assert set(S["classify"]["category"]) == {"guarantee_claim", "results_question", "safety_concern", "dosage_question",
                                              "shipping_issue", "subscription_billing", "positive_feedback"}
    assert len(S["retrieve"]["hits"]) == 4 and all("bm25_rank" in x for x in S["retrieve"]["hits"])
    assert S["route"]["decision"] in ("draft_reply", "consultant_call")
    assert S["draft"] is None and S["check"] is None


def test_guarantee_claim_routes_to_consultant_and_never_drafts(monkeypatch):
    import triage
    ret, cat, sent = triage.components()

    class Fixed:
        classes_ = cat.classes_

        def predict_proba(self, X):
            p = np.full((1, len(cat.classes_)), 0.01)
            p[0, list(cat.classes_).index("guarantee_claim")] = 0.9
            return p
    monkeypatch.setitem(triage._state, "cat", Fixed())
    rec = triage_email("scan went down", "my DEXA got worse, I want a refund", "Pat", draft=True)
    assert rec["stages"]["route"]["decision"] == "consultant_call"
    assert rec["stages"]["route"]["rule_id"] == "guarantee"
    assert rec["stages"]["draft"] is None
