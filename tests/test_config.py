import pytest

from config import CFG, DEFAULTS, _merge, validate, load_config, config_hash


def test_loads_and_has_rules():
    assert CFG["version"]
    assert len(CFG["routing_rules"]) == 4
    assert [r["id"] for r in CFG["routing_rules"]] == ["guarantee", "medical", "disappointed", "cancel"]
    assert len(config_hash()) == 12


def test_missing_file_gives_defaults(tmp_path):
    cfg = load_config(tmp_path / "nope.yaml")
    assert cfg["confidence_bands"] == DEFAULTS["confidence_bands"]
    assert cfg["routing_rules"] == []


def test_validate_rejects_bad_bands():
    cfg = _merge(DEFAULTS, {"confidence_bands": {"high": 0.3, "medium": 0.5}})
    with pytest.raises(ValueError):
        validate(cfg)


def test_validate_rejects_duplicate_rule_ids():
    rule = {"id": "x", "when": {"category": "shipping_issue"}, "action": "consultant_call", "reason": "r"}
    cfg = _merge(DEFAULTS, {"routing_rules": [rule, dict(rule)]})
    with pytest.raises(ValueError):
        validate(cfg)


def test_validate_rejects_unknown_action():
    cfg = _merge(DEFAULTS, {"routing_rules": [{"id": "x", "when": {"category": "a"}, "action": "email_them", "reason": "r"}]})
    with pytest.raises(ValueError):
        validate(cfg)
