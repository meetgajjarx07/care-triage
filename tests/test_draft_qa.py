from draft import draft_qa, lexical_check, confidence_band, _sentences, MAX_WORDS

CHUNKS = [{"doc": "shipping.md", "heading": "Times", "title": "Shipping",
           "text": "Orders ship within 2 business days. Canada delivery takes 5 to 8 business days."}]
EMAIL = "Where is my order? It has been a week."
GOOD = "Hi Jean, orders ship within 2 business days and Canada delivery takes 5 to 8 business days. We will check the tracking and come back to you.\n\nAlgaeCal Customer Care"


def _check(qa, key):
    return next(c for c in qa["checks"] if c["key"] == key)


def test_clean_draft_scores_100():
    qa = draft_qa(GOOD, CHUNKS, EMAIL)
    assert qa["score"] == 100 and not qa["critical_fail"] and qa["failed"] == []


def test_invented_number_is_a_critical_grounding_fail():
    bad = GOOD.replace("5 to 8", "3 to 4")
    assert lexical_check(bad, CHUNKS, EMAIL)
    qa = draft_qa(bad, CHUNKS, EMAIL)
    assert qa["critical_fail"] and qa["score"] == 0 and not _check(qa, "grounded")["ok"]


def test_refund_promise_positive_and_negative():
    assert not _check(draft_qa(GOOD + " We will refund you in full.", CHUNKS, EMAIL), "no_refund_promise")["ok"]
    assert not _check(draft_qa("A refund of $49.95 is on its way. AlgaeCal Customer Care", CHUNKS, EMAIL), "no_refund_promise")["ok"]
    # mentioning the word without promising an outcome passes
    assert _check(draft_qa("Our team can explain how the refund policy works. AlgaeCal Customer Care", CHUNKS, EMAIL), "no_refund_promise")["ok"]
    # a dollar amount with no refund talk is fine
    assert _check(draft_qa("Shipping is $9.95 on small orders. AlgaeCal Customer Care", CHUNKS, EMAIL), "no_refund_promise")["ok"]


def test_medical_directive_positive_and_negative():
    assert not _check(draft_qa("You should stop taking the capsules for a week. AlgaeCal Customer Care", CHUNKS, EMAIL), "no_medical_advice")["ok"]
    assert not _check(draft_qa("Please double your dose tonight. AlgaeCal Customer Care", CHUNKS, EMAIL), "no_medical_advice")["ok"]
    assert _check(draft_qa("Please confirm the dose with your doctor or pharmacist. AlgaeCal Customer Care", CHUNKS, EMAIL), "no_medical_advice")["ok"]


def test_length_rule_uses_config():
    long = " ".join(["word"] * (MAX_WORDS + 1)) + " AlgaeCal Customer Care"
    qa = draft_qa(long, CHUNKS, EMAIL)
    assert not _check(qa, "length")["ok"] and not qa["critical_fail"] and 0 < qa["score"] < 100


def test_signoff_and_answers_first():
    qa = draft_qa("Thanks for reaching out! Orders ship within 2 business days.", CHUNKS, EMAIL)
    assert not _check(qa, "signoff")["ok"]
    assert not _check(qa, "answers_first")["ok"]
    assert not _check(qa, "tone")["ok"]


def test_confidence_bands():
    assert confidence_band(0.9) == "high" and confidence_band(0.55) == "high"
    assert confidence_band(0.5) == "medium" and confidence_band(0.35) == "medium"
    assert confidence_band(0.34) == "low"


def test_sentence_split_drops_fragments():
    s = _sentences("Hi there. This is a real sentence here. Ok.")
    assert s == ["This is a real sentence here."]
