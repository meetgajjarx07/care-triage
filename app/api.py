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
import time
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).parent))

import httpx
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from classify import email_text, embed
from config import CFG, config_hash
from draft import confidence_band, draft_qa, draft_reply, lexical_check, route_rule
from retrieve import Retriever, TOP_K

ROOT = Path(__file__).resolve().parent.parent
OUT, MODELS = ROOT / "out", ROOT / "models"
REVIEWS = OUT / "reviews.jsonl"
OLLAMA_URL = "http://localhost:11434"

app = FastAPI(title="Care Triage API", version=str(CFG["version"]), description=__doc__)
# The story page (story/index.html) calls /triage from the browser. It may be opened from the folder
# or embedded in the dashboard, so any local origin is allowed. Nothing here is exposed beyond the laptop.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
STORY = ROOT / "story" / "index.html"


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/story")


@app.get("/story", include_in_schema=False)
def story_page():
    """The six-scene story, same origin as /triage so scene three runs live."""
    return FileResponse(STORY, media_type="text/html")

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
    """Run one email through embed, classify, retrieve, route and, if asked and allowed, draft and check."""
    ms: dict[str, float] = {}
    t0 = time.time()
    try:
        X = embed([email_text(req.subject, req.body)])
    except Exception as e:
        raise HTTPException(503, f"Ollama is not reachable or the embedding model is not pulled: {e}")
    ms["embed"] = round(1000 * (time.time() - t0), 1)
    cat_m, sent_m = _models()
    t0 = time.time()
    cp, sp = cat_m.predict_proba(X)[0], sent_m.predict_proba(X)[0]
    ms["classify"] = round(1000 * (time.time() - t0), 2)
    category, sentiment = str(cat_m.classes_[cp.argmax()]), str(sent_m.classes_[sp.argmax()])
    conf = float(cp.max())
    t0 = time.time()
    hits = _retriever().search(f"{req.subject}. {req.body}", k=TOP_K, category=category)
    ms["retrieve"] = round(1000 * (time.time() - t0), 1)
    rr = route_rule(category, sentiment, req.body)
    out = TriageResponse(category=category, category_probs={c: round(float(p), 3) for c, p in zip(cat_m.classes_, cp)},
                         confidence=round(conf, 3), confidence_band=confidence_band(conf), sentiment=sentiment,
                         sentiment_probs={c: round(float(p), 3) for c, p in zip(sent_m.classes_, sp)},
                         route=rr["action"], route_reason=rr["reason"], escalation_reason=rr["short"], rule_id=rr["rule_id"],
                         chunks=[Chunk(**{k: h[k] for k in Chunk.model_fields}) for h in hits], ms=ms)
    if req.draft and rr["action"] == "draft_reply":
        t0 = time.time()
        try:
            out.draft = draft_reply(req.body, req.from_name, category, hits)
        except Exception as e:
            raise HTTPException(503, f"drafting model unavailable: {e}")
        ms["draft"] = round(1000 * (time.time() - t0))
        out.grounding_flags = lexical_check(out.draft, hits, req.body)
        out.qa = draft_qa(out.draft, hits, req.body)
    return out


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
