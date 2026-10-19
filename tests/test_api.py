import json

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "REVIEWS", tmp_path / "reviews.jsonl")
    monkeypatch.setattr(api, "_ollama_status", lambda: (False, {"embed": False, "draft": False}))
    return TestClient(api.app)


def test_health_degraded_without_ollama(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ollama"] is False and body["status"] == "degraded"
    assert body["kb_chunks"] > 20 and len(body["config_hash"]) == 12


def test_config_is_served(client):
    assert client.get("/config").json()["confidence_bands"]["high"] == 0.55


def test_emails_list_and_filters(client):
    rows = client.get("/emails", params={"limit": 5}).json()
    assert len(rows) == 5 and {"id", "route", "confidence_band"} <= set(rows[0])
    calls = client.get("/emails", params={"route": "consultant_call"}).json()
    assert calls and all(r["route"] == "consultant_call" for r in calls)


def test_email_detail_has_trace(client):
    r = client.get("/emails/E061")
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == "E061" and d["trace"]["stages"]["retrieve"]["hits"]


def test_unknown_email_404(client):
    assert client.get("/emails/NOPE").status_code == 404


def test_triage_without_draft(client):
    r = client.post("/triage", json={"subject": "charged twice", "body": "please cancel my subscription", "from_name": "Pat"})
    assert r.status_code == 200
    d = r.json()
    assert d["route"] in ("draft_reply", "consultant_call")
    assert len(d["chunks"]) == 4 and d["confidence_band"] in ("high", "medium", "low")
    assert set(d["ms"]) == {"embed", "classify", "retrieve", "grade", "brief"} and d["draft"] is None
    assert d["brief"]["facts"] == [] and d["crag"]["kept"] == 4


def test_reviews_roundtrip(client, tmp_path):
    assert client.get("/reviews").json() == []
    r = client.post("/reviews", json={"id": "E061", "action": "correct", "reviewer": "khushi", "field": "category",
                                      "old": "results_question", "new": "guarantee_claim", "reason": "scan mentioned"})
    assert r.status_code == 201 and r.json()["at"]
    rec = json.loads((tmp_path / "reviews.jsonl").read_text().splitlines()[0])
    assert list(rec)[:4] == ["at", "reviewer", "id", "action"]
    assert client.get("/reviews").json()[0]["new"] == "guarantee_claim"
