#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:?Usage: ./bootstrap_dionysis_cloud.sh YOUR_GCP_PROJECT_ID}"
REGION="${REGION:-us-central1}"
SERVICE="dionysus-tax"
API_KEY="$(openssl rand -hex 32)"

gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com

mkdir -p services/dionysus-tax
cd services/dionysus-tax

cat > requirements.txt <<'EOF'
fastapi
uvicorn[standard]
google-cloud-firestore
pydantic
EOF

cat > main.py <<'EOF'
import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException
from google.cloud import firestore
from pydantic import BaseModel

API_KEY = os.environ["DIONYSUS_API_KEY"]
db = firestore.Client()
app = FastAPI(title="Dionysus Tax API", version="0.1.0")


class Event(BaseModel):
    substance: str
    amount_text: str
    method: str | None = None
    notes: str | None = None
    state: str | None = None


def auth(authorization: str | None) -> None:
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/events")
def log_event(event: Event, authorization: str | None = Header(default=None)):
    auth(authorization)
    doc = {
        **event.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db.collection("dionysus_events").add(doc)
    return {"ok": True, "logged": doc}


@app.get("/today")
def today(authorization: str | None = Header(default=None)):
    auth(authorization)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    docs = (
        db.collection("dionysus_events")
        .where("created_at", ">=", since.isoformat())
        .stream()
    )
    events = [d.to_dict() for d in docs]
    return {"window_hours": 24, "events": events, "count": len(events)}


@app.get("/status")
def status(authorization: str | None = Header(default=None)):
    auth(authorization)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    events = [
        d.to_dict()
        for d in db.collection("dionysus_events")
        .where("created_at", ">=", since.isoformat())
        .stream()
    ]
    alcohol = [e for e in events if e.get("substance") == "alcohol"]
    cannabis = [e for e in events if e.get("substance") == "cannabis"]

    mode = "normal"
    caution = []
    if len(alcohol) >= 3 or len(cannabis) >= 2:
        mode = "brainstorm/document"
        caution.append(
            "Avoid deployment, purchases, major architecture commitments, and emotional messages."
        )

    return {
        "mode": mode,
        "last_24h": {
            "alcohol_events": len(alcohol),
            "cannabis_events": len(cannabis),
            "total_events": len(events),
        },
        "caution": caution,
    }
EOF

cat > openapi.yaml <<EOF
openapi: 3.1.0
info:
  title: Dionysus Tax API
  version: 0.1.0
servers:
  - url: https://REPLACE_WITH_CLOUD_RUN_URL
paths:
  /events:
    post:
      operationId: logDionysusEvent
      summary: Log alcohol or cannabis intake
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [substance, amount_text]
              properties:
                substance:
                  type: string
                  enum: [alcohol, cannabis, caffeine, nicotine, other]
                amount_text:
                  type: string
                method:
                  type: string
                notes:
                  type: string
                state:
                  type: string
      responses:
        "200":
          description: Logged
  /today:
    get:
      operationId: getDionysusToday
      security:
        - bearerAuth: []
      responses:
        "200":
          description: Recent events
  /status:
    get:
      operationId: getDionysusStatus
      security:
        - bearerAuth: []
      responses:
        "200":
          description: Current operator-state read
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
EOF

gcloud firestore databases create \
  --database="(default)" \
  --location="$REGION" \
  --type=firestore-native || true

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "DIONYSUS_API_KEY=$API_KEY"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"

sed -i.bak "s|https://REPLACE_WITH_CLOUD_RUN_URL|$URL|g" openapi.yaml
rm -f openapi.yaml.bak

echo ""
echo "Dionysus Tax deployed."
echo "URL: $URL"
echo "Bearer token:"
echo "$API_KEY"
echo ""
echo "Test:"
echo "curl -X POST \"$URL/events\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"substance\":\"alcohol\",\"amount_text\":\"2 Cabernet spritzes + 1 beer\",\"state\":\"pleasant\"}'"
