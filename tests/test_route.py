from draft import route, route_rule


def test_guarantee_claim_goes_to_consultant():
    r = route_rule("guarantee_claim", "neutral", "My scan did not improve, I want my money back.")
    assert r["action"] == "consultant_call" and r["rule_id"] == "guarantee"
    assert r["short"] == "Guarantee claim: scan review"


def test_medical_context_needs_the_regex():
    assert route_rule("safety_concern", "neutral", "Is strontium safe?")["action"] == "draft_reply"
    r = route_rule("safety_concern", "neutral", "My cardiologist asked about warfarin.")
    assert r["rule_id"] == "medical" and r["short"] == "Medical context"


def test_medical_regex_is_case_insensitive():
    assert route_rule("safety_concern", "neutral", "my EGFR is low")["rule_id"] == "medical"


def test_disappointed_results_only_when_negative():
    assert route_rule("results_question", "neutral", "when should I expect results?")["action"] == "draft_reply"
    assert route_rule("results_question", "negative", "a year in and nothing changed")["rule_id"] == "disappointed"


def test_cancel_intent():
    assert route_rule("subscription_billing", "neutral", "please cancel my subscription")["short"] == "Cancel intent"
    assert route_rule("subscription_billing", "neutral", "charged twice this month")["action"] == "draft_reply"


def test_default_route_tuple_shape():
    rt, why = route("shipping_issue", "negative", "where is my parcel")
    assert rt == "draft_reply" and why.startswith("covered by the knowledge base")
    assert route_rule("shipping_issue", "negative", "x")["rule_id"] is None
