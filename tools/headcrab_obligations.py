#!/usr/bin/env python3
"""Deterministic timed obligation state for Headcrab."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

DEFAULT_LEAD_MINUTES = 5


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Headcrab obligation timestamps must be timezone-aware")
    return value


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    label: str
    due_at: str
    completed_at: str | None = None

    @classmethod
    def create(
        cls,
        label: str,
        due_at: datetime,
        *,
        obligation_id: str | None = None,
    ) -> "Obligation":
        due_at = _require_aware(due_at)
        clean = " ".join(label.split())
        if not clean:
            raise ValueError("obligation label must not be empty")
        if obligation_id is None:
            digest = sha256(f"{clean}\n{due_at.isoformat()}".encode("utf-8")).hexdigest()[:16]
            obligation_id = f"hc-{digest}"
        return cls(
            obligation_id=obligation_id,
            label=clean,
            due_at=due_at.isoformat(),
        )

    def due_datetime(self) -> datetime:
        return _require_aware(datetime.fromisoformat(self.due_at))

    def is_complete(self) -> bool:
        return self.completed_at is not None


@dataclass
class ObligationLedger:
    obligations: dict[str, Obligation]

    @classmethod
    def empty(cls) -> "ObligationLedger":
        return cls(obligations={})

    def capture(
        self,
        label: str,
        due_at: datetime,
        *,
        obligation_id: str | None = None,
    ) -> Obligation:
        item = Obligation.create(label, due_at, obligation_id=obligation_id)
        existing = self.obligations.get(item.obligation_id)
        if existing is not None:
            return existing
        self.obligations[item.obligation_id] = item
        return item

    def mark_done(self, obligation_id: str, *, completed_at: datetime) -> None:
        completed_at = _require_aware(completed_at)
        item = self.obligations[obligation_id]
        self.obligations[obligation_id] = Obligation(
            obligation_id=item.obligation_id,
            label=item.label,
            due_at=item.due_at,
            completed_at=completed_at.isoformat(),
        )

    def actionable(
        self,
        now: datetime,
        *,
        lead_minutes: int = DEFAULT_LEAD_MINUTES,
    ) -> tuple[Obligation, ...]:
        now = _require_aware(now)
        horizon = now + timedelta(minutes=lead_minutes)
        items = [
            item
            for item in self.obligations.values()
            if not item.is_complete() and item.due_datetime() <= horizon
        ]
        return tuple(
            sorted(items, key=lambda item: (item.due_datetime(), item.obligation_id))
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "obligations": [
                {
                    "obligation_id": item.obligation_id,
                    "label": item.label,
                    "due_at": item.due_at,
                    "completed_at": item.completed_at,
                }
                for item in sorted(
                    self.obligations.values(),
                    key=lambda item: (item.due_datetime(), item.obligation_id),
                )
            ]
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ObligationLedger":
        raw = payload.get("obligations", [])
        if not isinstance(raw, list):
            raise ValueError("obligations must be a list")

        items: dict[str, Obligation] = {}
        for entry in raw:
            if not isinstance(entry, dict):
                raise ValueError("obligation entries must be objects")
            item = Obligation(
                obligation_id=str(entry["obligation_id"]),
                label=str(entry["label"]),
                due_at=str(entry["due_at"]),
                completed_at=(
                    None
                    if entry.get("completed_at") is None
                    else str(entry["completed_at"])
                ),
            )
            item.due_datetime()
            items[item.obligation_id] = item
        return cls(obligations=items)


def render_reminders(
    items: Iterable[Obligation],
    *,
    now: datetime,
) -> tuple[str, ...]:
    now = _require_aware(now)
    rendered: list[str] = []
    for item in items:
        due = item.due_datetime()
        if due <= now:
            rendered.append(f"Headcrab: ⏰ {item.label} — now")
        else:
            minutes = max(1, int((due - now).total_seconds() // 60))
            rendered.append(f"Headcrab: ⏰ {item.label} — in {minutes}m")
    return tuple(rendered)


def load_ledger(path: str | Path) -> ObligationLedger:
    target = Path(path)
    if not target.exists():
        return ObligationLedger.empty()
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Headcrab obligation state must be a JSON object")
    return ObligationLedger.from_dict(payload)


def save_ledger(path: str | Path, ledger: ObligationLedger) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(ledger.to_dict(), indent=2, sort_keys=True) + "\n"
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=target.parent,
        prefix=target.name + ".",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(payload)
        temp_path = Path(handle.name)
    temp_path.replace(target)
