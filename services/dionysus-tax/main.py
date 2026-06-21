import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from google.cloud import firestore
from pydantic import BaseModel

API_KEY = os.environ.get("DIONYSUS_API_KEY", "")
if not API_KEY:
    raise RuntimeError("DIONYSUS_API_KEY is required")

app = FastAPI(title="Dionysus Tax API", version="0.1.0")
db = firestore.Client()


class EventIn(BaseModel):
    substance: str
    amount_text: str
    method: Optional[str] = None
    state: Optional[str] = None
    notes: Optional[str] = None
    intent: Optional[str] = None


class NoteIn(BaseModel):
    note: str
    mood: Optional[str] = None
    energy: Optional[int] = None
    anxiety: Optional[int] = None
    focus: Optional[int] = None


def require_auth(authorization: Optional[str]) -> None:
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def recent_events(hours: int = 24):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    docs = (
        db.collection("dionysus_events")
        .where("created_at", ">=", since.isoformat())
        .order_by("created_at")
        .stream()
    )
    return [dict(id=doc.id, **doc.to_dict()) for doc in docs]


@app.get("/health")
def health():
    return {"ok": True, "service": "dionysus-tax"}


@app.post("/events")
def log_event(event: EventIn, authorization: Optional[str] = Header(default=None)):
    require_auth(authorization)
    doc = event.model_dump()
    doc["created_at"] = now_iso()
    ref = db.collection("dionysus_events").document()
    ref.set(doc)
    return {"ok": True, "id": ref.id, "logged": doc}


@app.post("/notes")
def log_note(note: NoteIn, authorization: Optional[str] = Header(default=None)):
    require_auth(authorization)
    doc = note.model_dump()
    doc["created_at"] = now_iso()
    ref = db.collection("dionysus_notes").document()
    ref.set(doc)
    return {"ok": True, "id": ref.id, "logged": doc}


@app.get("/today")
def today(authorization: Optional[str] = Header(default=None)):
    require_auth(authorization)
    events = recent_events(24)
    counts = {}
    for event in events:
        key = event.get("substance", "other")
        counts[key] = counts.get(key, 0) + 1
    return {"window_hours": 24, "count": len(events), "counts": counts, "events": events}


@app.get("/status")
def status(authorization: Optional[str] = Header(default=None)):
    require_auth(authorization)
    events = recent_events(24)
    alcohol_count = len([e for e in events if e.get("substance") == "alcohol"])
    cannabis_count = len([e for e in events if e.get("substance") == "cannabis"])
    mode = "normal"
    cautions = []
    if alcohol_count >= 3 or cannabis_count >= 2:
        mode = "brainstorm-document"
        cautions.append("Use caution with irreversible decisions.")
    if alcohol_count and cannabis_count:
        cautions.append("Mixed intake window logged.")
    if not cautions:
        cautions.append("No elevated caution from logged intake in the last 24 hours.")
    return {
        "mode": mode,
        "last_24h": {
            "alcohol_events": alcohol_count,
            "cannabis_events": cannabis_count,
            "total_events": len(events),
        },
        "caution": cautions,
    }


@app.get("/reflect")
def reflect(authorization: Optional[str] = Header(default=None)):
    require_auth(authorization)
    return {"summary": "Use logged events as an operator-state mirror.", "status": status(authorization)}
