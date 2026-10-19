"""Offline test setup: no Ollama. Embeddings are replaced with deterministic
unit vectors of the right width so classifiers and the retriever still run."""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

DIM = 768


def fake_embed(texts):
    out = []
    for t in list(texts):
        seed = int(hashlib.md5(t.encode()).hexdigest()[:8], 16)
        v = np.random.default_rng(seed).standard_normal(DIM).astype(np.float32)
        out.append(v / np.linalg.norm(v))
    return np.array(out, dtype=np.float32)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import classify, retrieve
    monkeypatch.setattr(classify, "embed", fake_embed)
    monkeypatch.setattr(retrieve, "embed", fake_embed)
    import genai, json

    def fake_chat(task, system, user, num_predict=None):
        if task == "grade":
            return json.dumps({"useful": True, "why": "test"})
        if task == "brief":
            return json.dumps({"asks": "a refund of a duplicate charge", "check": "the two charges on the account", "facts": ["two charges", "order 99999"]})
        return json.dumps({"query": "duplicate charge refund subscription"})
    monkeypatch.setattr(genai, "_chat", fake_chat)
    try:
        import api
        monkeypatch.setattr(api, "embed", fake_embed, raising=False)
    except ImportError:
        pass
    yield
