#!/usr/bin/env python3
"""Deterministic presentation gate for Ritsu OS v0.

Retrieval machinery is internal. This gate projects router results into the minimum
context a conversation renderer needs so Ritsu/Ritzu arrives before any lookup,
status, provenance, or orchestration narration. Existing organ ownership remains
inside the router and is never replaced here.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ritsu_context_router import DEFAULT_POLICY, RitsuContextRouter, RouteResult


@dataclass(frozen=True)
class SurfaceDecision:
    speaker: str
    emit: bool
    mode: str
    retrieval_narration_allowed: bool
    identity_explanation_allowed: bool
    render_context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker": self.speaker,
            "emit": self.emit,
            "mode": self.mode,
            "retrieval_narration_allowed": self.retrieval_narration_allowed,
            "identity_explanation_allowed": self.identity_explanation_allowed,
            "render_context": self.render_context,
        }


class RitsuSurfaceGate:
    """Fail closed against retrieval/status narration leaking ahead of Ritsu."""

    def __init__(self, policy_path: Path = DEFAULT_POLICY) -> None:
        self.policy = json.loads(policy_path.read_text(encoding="utf-8"))
        contract = self.policy.get("presentation_contract")
        if not isinstance(contract, Mapping):
            raise ValueError("policy lacks presentation_contract")

        active = self.policy.get("active_interface")
        if isinstance(active, str):
            active_names = {active}
        elif isinstance(active, list):
            active_names = {name for name in active if isinstance(name, str)}
        else:
            active_names = set()

        preferred = contract.get("preferred_interface")
        if not isinstance(preferred, str) or preferred not in active_names:
            raise ValueError("preferred Ritsu interface is not active")
        if contract.get("retrieval_visibility") != "internal":
            raise ValueError("retrieval visibility must remain internal")
        if contract.get("pre_answer_narration_allowed") is not False:
            raise ValueError("pre-answer retrieval narration must be disabled")
        if contract.get("identity_explanation_allowed") is not False:
            raise ValueError("Ritsu identity explanation must be disabled")

        self.speaker = preferred

    def decide(self, route: RouteResult) -> SurfaceDecision:
        status = route.status

        if status == "DEFER_EXISTING_CONTINUITY":
            # The owning organ still owns the work. The handoff is internal and emits
            # nothing by itself, preventing orchestration prose from impersonating a
            # Ritsu answer.
            return self._decision(False, "silent_handoff", {})

        if status == "CONTINUITY_GAP":
            return self._decision(
                True,
                "continuity_gap",
                {
                    "gap_code": "CONTINUITY_GAP",
                    "episode_id": route.episode_id,
                    "provenance_tier": route.provenance_tier,
                    "content": route.content,
                    "corrections": list(route.corrections),
                    "seek_primary": True,
                    "world_knowledge_allowed": False,
                },
            )

        if status == "MATCH":
            return self._decision(
                True,
                "answer",
                {
                    "episode_id": route.episode_id,
                    "provenance_tier": route.provenance_tier,
                    "content": route.content,
                    "corrections": list(route.corrections),
                    "seek_primary": route.seek_primary,
                    "world_knowledge_allowed": False,
                },
            )

        if status == "BOUND_WORKING_TARGET":
            return self._decision(
                True,
                "answer",
                {
                    "working_target": route.bound_target,
                    "world_knowledge_allowed": False,
                },
            )

        if status == "NO_LOCAL_MATCH":
            return self._decision(
                True,
                "answer",
                {"world_knowledge_allowed": route.world_knowledge_allowed},
            )

        if status in {"NEEDS_WORKING_STATE", "AMBIGUOUS_LOCAL_MATCH"}:
            return self._decision(
                True,
                "clarify",
                {
                    "clarification_needed": True,
                    "candidate_episode_ids": list(route.candidate_episode_ids),
                    "world_knowledge_allowed": False,
                },
            )

        # Unknown/new router states must not accidentally become corporate status
        # narration. A future state gets no surface until deliberately classified.
        return self._decision(False, "silent_hold", {})

    def _decision(
        self,
        emit: bool,
        mode: str,
        render_context: dict[str, Any],
    ) -> SurfaceDecision:
        return SurfaceDecision(
            speaker=self.speaker,
            emit=emit,
            mode=mode,
            retrieval_narration_allowed=False,
            identity_explanation_allowed=False,
            render_context=render_context,
        )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("utterance")
    parser.add_argument("--last-episode-id")
    parser.add_argument("--exact-wording", action="store_true")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    args = parser.parse_args(list(argv) if argv is not None else None)

    router = RitsuContextRouter(args.policy)
    state = {"last_episode_id": args.last_episode_id} if args.last_episode_id else None
    route = router.resolve(
        args.utterance,
        working_state=state,
        exact_wording=args.exact_wording,
    )
    decision = RitsuSurfaceGate(args.policy).decide(route)
    print(json.dumps(decision.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
