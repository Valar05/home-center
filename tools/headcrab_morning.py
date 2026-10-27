#!/usr/bin/env python3
"""Deterministic morning checklist state for Headcrab."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable

DEFAULT_ITEMS = ("pills", "food", "inhaler")
DEFAULT_MORNING_END_HOUR = 12


@dataclass
class MorningChecklist:
    local_date: str
    completed: set[str] = field(default_factory=set)

    @classmethod
    def fresh(cls, day: date) -> "MorningChecklist":
        return cls(local_date=day.isoformat())

    def reset_if_new_day(self, day: date) -> None:
        stamp = day.isoformat()
        if self.local_date != stamp:
            self.local_date = stamp
            self.completed.clear()

    def mark_done(self, item: str) -> None:
        normalized = item.strip().lower()
        if normalized not in DEFAULT_ITEMS:
            raise ValueError(f"unknown morning checklist item: {item}")
        self.completed.add(normalized)

    def pending(self, now: datetime) -> tuple[str, ...]:
        self.reset_if_new_day(now.date())
        if now.hour >= DEFAULT_MORNING_END_HOUR:
            return ()
        return tuple(item for item in DEFAULT_ITEMS if item not in self.completed)

    def to_dict(self) -> dict[str, object]:
        return {
            "local_date": self.local_date,
            "completed": sorted(self.completed),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object], *, today: date) -> "MorningChecklist":
        state = cls(
            local_date=str(payload.get("local_date") or today.isoformat()),
            completed={str(x).lower() for x in payload.get("completed", []) if isinstance(x, str)},
        )
        state.reset_if_new_day(today)
        state.completed.intersection_update(DEFAULT_ITEMS)
        return state


def render_reminder(pending: Iterable[str]) -> str | None:
    items = tuple(pending)
    if not items:
        return None
    labels = {"pills": "💊 pills", "food": "🍽️ food", "inhaler": "🫁 inhaler"}
    return "Morning Headcrab: " + " · ".join(labels[item] for item in items)
