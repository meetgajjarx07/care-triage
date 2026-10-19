"""
Single source of configuration. Reads config/triage.yaml once, merges it over
the defaults below (so a missing key never crashes a page), validates the
few things that would silently break routing, and exposes CFG.

    from config import CFG, config_hash
"""
import copy
import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "triage.yaml"

DEFAULTS = {
    "version": "0.0.0", "owner": "", "environment": "local",
    "models": {"embed": "nomic-embed-text", "draft": "llama3.2",
               "draft_options": {"temperature": 0, "seed": 7, "num_predict": 260}},
    "classifier": {"C": 4, "class_weight": "balanced", "max_iter": 5000},
    "confidence_bands": {"high": 0.55, "medium": 0.35},
    "retrieval": {"k": 4, "rrf_k": 60, "category_boost": 1 / 60, "low_evidence_quantile": 0.10},
    "draft_qa": {"max_words": 140, "support_thresholds": {"supported": 0.72, "weak": 0.62}},
    "routing_rules": [],
    "default_route": {"action": "draft_reply", "reason": "covered by the knowledge base, draft for human review"},
    "monitoring": {"critical_qa_fail_rate_max": 0.20, "low_band_share_max": 0.25,
                   "correction_rate_max": 0.15, "run_age_days_max": 7},
}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def validate(cfg):
    """Raise ValueError on anything that would make routing or banding wrong."""
    b = cfg["confidence_bands"]
    if not (0 < b["medium"] < b["high"] <= 1):
        raise ValueError(f"confidence_bands must satisfy 0 < medium < high <= 1, got {b}")
    t = cfg["draft_qa"]["support_thresholds"]
    if not (0 < t["weak"] < t["supported"] <= 1):
        raise ValueError(f"support_thresholds must satisfy 0 < weak < supported <= 1, got {t}")
    if cfg["retrieval"]["k"] < 1:
        raise ValueError("retrieval.k must be >= 1")
    seen = set()
    for r in cfg["routing_rules"]:
        for key in ("id", "when", "action", "reason"):
            if key not in r:
                raise ValueError(f"routing rule missing '{key}': {r}")
        if r["id"] in seen:
            raise ValueError(f"duplicate routing rule id {r['id']}")
        seen.add(r["id"])
        if r["action"] not in ("consultant_call", "draft_reply"):
            raise ValueError(f"unknown action {r['action']} in rule {r['id']}")
        if "category" not in r["when"]:
            raise ValueError(f"rule {r['id']} needs when.category")
    return cfg


def load_config(path=CONFIG_PATH):
    raw = yaml.safe_load(Path(path).read_text()) if Path(path).exists() else {}
    return validate(_merge(DEFAULTS, raw))


def config_hash(path=CONFIG_PATH):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else "none"


CFG = load_config()
