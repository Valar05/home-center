#!/usr/bin/env python3
"""Deterministic Fortress Online continuation/output gate.

A checkpoint or blocker is not a parent-campaign stop.  This module is deliberately
small so phone/desktop workers can use it without model inference.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class TerminalReason(str, Enum):
    ACCEPTED_COMPLETE = "ACCEPTED_COMPLETE"
    PROVEN_OPERATOR_ONLY_BOUNDARY = "PROVEN_OPERATOR_ONLY_BOUNDARY"
    SAFETY_OR_AUTHORITY_BOUNDARY = "SAFETY_OR_AUTHORITY_BOUNDARY"


@dataclass(frozen=True)
class Transition:
    transition_id: str
    authorized: bool = True
    callable_now: bool = True
    waiting_external: bool = False
    materially_advances: bool = True
    priority: int = 0


@dataclass
class CampaignState:
    campaign_terminal: bool = False
    terminal_reason: str | None = None
    next_transition_id: str | None = None
    waiting_external_ids: list[str] = field(default_factory=list)
    last_receipt_ids: list[str] = field(default_factory=list)
    forced_yield: bool = False


def runnable(transitions: Iterable[Transition]) -> list[Transition]:
    """Return useful transitions executable now; waiting jobs never block siblings."""
    out = [
        t for t in transitions
        if t.authorized and t.callable_now and not t.waiting_external and t.materially_advances
    ]
    return sorted(out, key=lambda t: (-t.priority, t.transition_id))


def choose_next(state: CampaignState, transitions: Iterable[Transition]) -> Transition | None:
    choices = runnable(transitions)
    state.next_transition_id = choices[0].transition_id if choices else None
    return choices[0] if choices else None


def final_allowed(state: CampaignState, transitions: Iterable[Transition]) -> tuple[bool, str]:
    choices = runnable(transitions)
    if choices:
        state.next_transition_id = choices[0].transition_id
        return False, "RUNNABLE_TRANSITION_EXISTS"
    if not state.campaign_terminal:
        return False, "CAMPAIGN_INCOMPLETE_NO_TERMINAL_PROOF"
    try:
        TerminalReason(state.terminal_reason or "")
    except ValueError:
        return False, "INVALID_TERMINAL_REASON"
    return True, "TERMINAL_PROVEN"


def mark_forced_yield(state: CampaignState, transitions: Iterable[Transition]) -> CampaignState:
    """Persist inheritance intent when the host turn ends before the campaign does."""
    nxt = choose_next(state, transitions)
    state.forced_yield = nxt is not None
    return state


def self_test() -> None:
    # Regression: status/final is forbidden while useful work exists.
    s = CampaignState()
    work = [Transition("do-work", priority=10)]
    assert final_allowed(s, work) == (False, "RUNNABLE_TRANSITION_EXISTS")
    assert s.next_transition_id == "do-work"

    # Waiting async work does not prevent independent work from running.
    s = CampaignState()
    work = [Transition("phone-ticket", waiting_external=True, priority=99), Transition("mine-drive", priority=2)]
    assert choose_next(s, work).transition_id == "mine-drive"
    assert final_allowed(s, work)[0] is False

    # A genuine physical/operator boundary may terminate when nothing runnable remains.
    s = CampaignState(campaign_terminal=True, terminal_reason=TerminalReason.PROVEN_OPERATOR_ONLY_BOUNDARY.value)
    assert final_allowed(s, []) == (True, "TERMINAL_PROVEN")

    # Child stop cannot magically terminate parent state.
    s = CampaignState(campaign_terminal=False, terminal_reason=None)
    assert final_allowed(s, [Transition("stopped-child", callable_now=False)])[0] is False


if __name__ == "__main__":
    self_test()
    print("FORTRESS_CONTINUATION_GATE_SELF_TEST=PASS")
