"""
Care Triage API.

A small FastAPI service over the same code the batch pipeline runs, so the
dashboard is one client of the pipeline rather than the pipeline itself.
Everything is local: embeddings and drafting go through Ollama on this machine.
Nothing here sends email. POST /triage returns a routed, checked draft for a
person to read; POST /reviews records what that person decided.

    uvicorn api:app --app-dir app --port 8000      # docs at /docs
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).parent))

import httpx
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from triage import triage_email
from config import CFG, config_hash
from retrieve import Retriever

ROOT = Path(__file__).resolve().parent.parent
OUT, MODELS = ROOT / "out", ROOT / "models"
REVIEWS = OUT / "reviews.jsonl"
OLLAMA_URL = "http://localhost:11434"

app = FastAPI(title="Care Triage API", version=str(CFG["version"]), description=__doc__)

_state: dict = {}


def _retriever() -> Retriever:
    if "ret" not in _state:
        _state["ret"] = Retriever()
    return _state["ret"]


def _models():
    if "cat" not in _state:
        _state["cat"] = joblib.load(MODELS / "category.joblib")
        _state["sent"] = joblib.load(MODELS / "sentiment.joblib")
    return _state["cat"], _state["sent"]


def _results() -> pd.DataFrame:
    p = OUT / "results.csv"
    if not p.exists():
        raise HTTPException(503, "out/results.csv not found; run `make run` first")
    return pd.read_csv(p).fillna({"escalation_reason": "", "qa_failed": "", "draft_reply": "", "check_flags": ""})


def _ollama_status() -> tuple[bool, dict]:
    """(reachable, {embed: present, draft: present}); 1 s timeout, never raises."""
    want = {"embed": CFG["models"]["embed"], "draft": CFG["models"]["draft"]}
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=1.0)
        names = {m["name"].split(":")[0] for m in r.json().get("models", [])}
        return True, {k: v.split(":")[0] in names for k, v in want.items()}
    except Exception:
        return False, {k: False for k in want}


# ---------------------------------------------------------------- schemas
class Health(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    config_hash: str
    ollama: bool
    models: dict[str, bool]
    run_id: Optional[str] = None
    kb_chunks: int


class EmailRow(BaseModel):
    id: str
    received_at: str
    from_name: str
    subject: str
    pred_category: str
    pred_category_conf: float
    confidence_band: str
    pred_sentiment: str
    route: str
    escalation_reason: str = ""
    qa_score: Optional[float] = None


class EmailDetail(EmailRow):
    body: str
    route_reason: str
    draft_reply: str = ""
    qa_failed: str = ""
    trace: Optional[dict] = None


class TriageRequest(BaseModel):
    subject: str = Field(..., examples=["charged twice"])
    body: str = Field(..., examples=["My card shows two charges this month for one bottle."])
    from_name: str = Field("", examples=["Jean Whitford"])
    draft: bool = Field(False, description="also draft a reply with the local model when the route allows it")


class Chunk(BaseModel):
    doc: str
    title: Optional[str] = None
    heading: str
    text: str
    score: float
    bm25_rank: int
    dense_rank: Optional[int] = None


class TriageResponse(BaseModel):
    category: str
    category_probs: dict[str, float]
    confidence: float
    confidence_band: str
    sentiment: str
    sentiment_probs: dict[str, float]
    route: str
    route_reason: str
    escalation_reason: str
    rule_id: Optional[str]
    chunks: list[Chunk]
    draft: Optional[str] = None
    qa: Optional[dict] = None
    grounding_flags: list[str] = []
    brief: Optional[dict] = None
    crag: Optional[dict] = None
    ms: dict[str, float]


class ReviewIn(BaseModel):
    id: str
    action: Literal["approve", "edit", "discard", "correct"]
    reviewer: str = "khushi"
    field: Optional[Literal["category", "sentiment"]] = None
    old: Optional[str] = None
    new: Optional[str] = None
    reason: Optional[str] = None
    text: Optional[str] = None


class ReviewOut(ReviewIn):
    at: str


# ---------------------------------------------------------------- routes
@app.get("/health", response_model=Health, tags=["system"])
def health() -> Health:
    """Liveness plus the two things that break a demo: Ollama down, model not pulled."""
    ok, models = _ollama_status()
    run = json.loads((OUT / "run.json").read_text()) if (OUT / "run.json").exists() else {}
    return Health(status="ok" if ok and all(models.values()) else "degraded", version=str(CFG["version"]),
                  config_hash=config_hash(), ollama=ok, models=models, run_id=run.get("run_id"),
                  kb_chunks=len(_retriever().chunks))


@app.get("/config", tags=["system"])
def config() -> dict:
    """The configuration in force (config/triage.yaml merged over defaults). Read-only."""
    return CFG


@app.get("/emails", response_model=list[EmailRow], tags=["emails"])
def emails(route: Optional[str] = None, category: Optional[str] = None, band: Optional[str] = None,
           limit: int = Query(100, ge=1, le=1000)) -> list[EmailRow]:
    """Rows from the last batch run, newest first. Filter by route, predicted category or confidence band."""
    df = _results()
    if route: df = df[df.route == route]
    if category: df = df[df.pred_category == category]
    if band: df = df[df.confidence_band == band]
    df = df.sort_values("received_at", ascending=False).head(limit)
    cols = list(EmailRow.model_fields)
    return [EmailRow(**{c: (None if pd.isna(r[c]) else r[c]) for c in cols}) for _, r in df.iterrows()]


@app.get("/emails/{email_id}", response_model=EmailDetail, tags=["emails"])
def email(email_id: str) -> EmailDetail:
    """One email with its full trace record (every stage's output and timing)."""
    df = _results()
    hit = df[df.id == email_id]
    if hit.empty:
        raise HTTPException(404, f"no email {email_id}")
    r = hit.iloc[0]
    trace = None
    p = OUT / "trace.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip() and json.loads(line)["id"] == email_id:
                trace = json.loads(line); break
    cols = list(EmailDetail.model_fields)
    return EmailDetail(**{c: (None if pd.isna(r[c]) else r[c]) for c in cols if c != "trace"}, trace=trace)


@app.post("/triage", response_model=TriageResponse, tags=["triage"])
def triage(req: TriageRequest) -> TriageResponse:
    """Run one email through the same code as the dashboard and the pipeline: embed,
    classify, retrieve and grade, brief, route and, if asked and allowed, draft and check."""
    try:
        rec = triage_email(req.subject, req.body, req.from_name, draft=req.draft)
    except Exception as e:
        raise HTTPException(503, f"Ollama is not reachable or a model is not pulled: {e}")
    S = rec["stages"]; C = S["classify"]; R = S["retrieve"]; T = S["route"]
    ms = {"embed": S["embed"]["ms"], "classify": C["ms"], "retrieve": R["ms"]}
    if R.get("crag"): ms["grade"] = R["crag"]["ms"]
    if S.get("brief"): ms["brief"] = S["brief"]["ms"]
    if S["draft"]: ms["draft"] = S["draft"]["ms"]
    return TriageResponse(category=C["pred_category"], category_probs=C["category"], confidence=C["confidence"], confidence_band=C["band"],
                          sentiment=C["pred_sentiment"], sentiment_probs=C["sentiment"],
                          route=T["decision"], route_reason=T["reason"], escalation_reason=T.get("short", ""), rule_id=T["rule_id"],
                          chunks=[Chunk(**{k: h.get(k) for k in Chunk.model_fields}) for h in R["hits"]], ms=ms,
                          draft=S["draft"]["text"] if S["draft"] else None, qa=S["check"]["qa"] if S["check"] else None,
                          grounding_flags=S["check"]["flags"] if S["check"] else [], brief=S.get("brief"), crag=R.get("crag"))


@app.get("/reviews", response_model=list[ReviewOut], tags=["reviews"])
def reviews() -> list[ReviewOut]:
    """Every review decision logged so far, oldest first. Same file the dashboard appends to."""
    if not REVIEWS.exists():
        return []
    return [ReviewOut(**json.loads(l)) for l in REVIEWS.read_text().splitlines() if l.strip()]


@app.post("/reviews", response_model=ReviewOut, status_code=201, tags=["reviews"])
def add_review(rev: ReviewIn) -> ReviewOut:
    """Append one decision (approve, edit, discard, correct) to out/reviews.jsonl. Nothing is ever rewritten."""
    rec = {"at": datetime.now().isoformat(timespec="seconds"), "reviewer": rev.reviewer, "id": rev.id, "action": rev.action,
           **{k: v for k, v in rev.model_dump().items() if k in ("field", "old", "new", "reason", "text") and v is not None}}
    REVIEWS.parent.mkdir(exist_ok=True)
    with open(REVIEWS, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return ReviewOut(**rec)
