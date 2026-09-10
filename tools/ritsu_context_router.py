#!/usr/bin/env python3
"""Deterministic first-pass router for Ritsu OS v0 continuity.

This candidate is intentionally narrow. It proves that a known relational cue can
outrank generic world knowledge without pretending to have the missing primary
transcript. It does not replace existing organs or model inference.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config" / "ritsu-os.v0.json"
DEFAULT_LEDGER = ROOT / "fixtures" / "ritsu-continuity" / "episode-ledger.v0.jsonl"

PROVENANCE_RANK = {
    "primary_transcript": 0,
    "accepted_summary": 1,
    "adjacent_evidence": 2,
    "unknown": 3,
}


def normalize_cue(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w\s']+", " ", value)
    return " ".join(value.split())


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{line_no}: record must be an object")
        records.append(item)
    return records


@dataclass(frozen=True)
class RouteResult:
    status: str
    route: str
    episode_id: str | None
    matched_cue: str | None
    provenance_tier: str
    content: str | None
    corrections: tuple[str, ...]
    world_knowledge_allowed: bool
    seek_primary: bool
    bound_target: dict[str, Any] | None = None
    delegated_owner: str | None = None
    required_provenance: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["corrections"] = list(self.corrections)
        return data


class RitsuContextRouter:
    def __init__(
        self,
        policy_path: Path = DEFAULT_POLICY,
        ledger_path: Path = DEFAULT_LEDGER,
    ) -> None:
        self.policy = _load_json(policy_path)
        self.records = _load_jsonl(ledger_path)
        self.episodes = {
            r["id"]: r for r in self.records if r.get("record_type") == "episode"
        }
        self.corrections: dict[str, list[dict[str, Any]]] = {}
        for record in self.records:
            if record.get("record_type") == "correction":
                self.corrections.setdefault(record["episode_id"], []).append(record)
        self.alias_to_episode: dict[str, str] = {}
        for episode_id, episode in self.episodes.items():
            for alias in episode.get("aliases", []):
                key = normalize_cue(alias)
                incumbent = self.alias_to_episode.get(key)
                if incumbent and incumbent != episode_id:
                    raise ValueError(f"ambiguous deterministic alias {alias!r}")
                self.alias_to_episode[key] = episode_id
        self.reserved = {
            normalize_cue(item["cue"]): item["owner"]
            for item in self.policy.get("reserved_existing_continuity", [])
        }
        self.immediate_bind_aliases = {
            normalize_cue(item)
            for item in self.policy.get("immediate_bind_aliases", [])
        }
        expected_order = self.policy.get("provenance_order")
        if expected_order != list(PROVENANCE_RANK):
            raise ValueError("policy provenance order diverges from router contract")

    def _exact_wording_requested(self, utterance: str, explicit: bool) -> bool:
        if explicit:
            return True
        cue = normalize_cue(utterance)
        return any(
            normalize_cue(marker) in cue
            for marker in self.policy.get("exact_wording_markers", [])
        )

    def _best_content(self, episode: Mapping[str, Any]) -> tuple[str, str | None]:
        for source in episode.get("primary_sources") or []:
            text = source.get("text") if isinstance(source, Mapping) else None
            if isinstance(text, str) and text.strip():
                return "primary_transcript", text
        summary = episode.get("accepted_summary")
        if isinstance(summary, str) and summary.strip():
            return episode.get("summary_tier", "accepted_summary"), summary
        adjacent = episode.get("adjacent_evidence") or []
        for item in adjacent:
            text = item.get("text") if isinstance(item, Mapping) else None
            if isinstance(text, str) and text.strip():
                return "adjacent_evidence", text
        return "unknown", None

    def _episode_result(
        self,
        episode_id: str,
        matched_cue: str,
        exact_wording: bool,
        reason: str,
    ) -> RouteResult:
        episode = self.episodes[episode_id]
        correction_effects = tuple(
            c["effect"] for c in self.corrections.get(episode_id, [])
        )
        tier, content = self._best_content(episode)
        if tier not in PROVENANCE_RANK:
            raise ValueError(f"unknown provenance tier {tier!r}")
        has_primary = tier == "primary_transcript"
        if exact_wording and not has_primary:
            return RouteResult(
                status="CONTINUITY_GAP",
                route="episodic",
                episode_id=episode_id,
                matched_cue=matched_cue,
                provenance_tier=tier,
                content=content,
                corrections=correction_effects,
                world_knowledge_allowed=False,
                seek_primary=True,
                required_provenance="primary_transcript",
                reason="exact wording requested but no readable primary transcript is bound",
            )

        return RouteResult(
            status="MATCH",
            route="episodic",
            episode_id=episode_id,
            matched_cue=matched_cue,
            provenance_tier=tier,
            content=content,
            corrections=correction_effects,
            world_knowledge_allowed=False,
            seek_primary=not has_primary,
            reason=reason,
        )

    def _match_episode(self, cue: str, *, allow_embedded_alias: bool) -> tuple[str | None, str | None]:
        episode_id = self.alias_to_episode.get(cue)
        if episode_id:
            return episode_id, cue
        if not allow_embedded_alias:
            return None, None
        padded = f" {cue} "
        matches: list[tuple[str, str]] = []
        for alias, candidate_id in self.alias_to_episode.items():
            if len(alias.split()) >= 2 and f" {alias} " in padded:
                matches.append((candidate_id, alias))
        unique_ids = {item[0] for item in matches}
        if len(unique_ids) > 1:
            raise ValueError("ambiguous embedded deterministic episode aliases")
        if matches:
            return matches[0]
        return None, None

    @staticmethod
    def _requested_actor(cue: str) -> str | None:
        first = cue.split(" ", 1)[0] if cue else ""
        if first in {"ritsu", "ritzu"}:
            return "ritsu"
        return None

    @staticmethod
    def _canonical_actor(value: Any) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        actor = normalize_cue(value)
        if actor in {"ritsu", "ritzu"}:
            return "ritsu"
        return actor

    def _bind_current_target(
        self,
        cue: str,
        working_state: Mapping[str, Any] | None,
    ) -> RouteResult | None:
        raw_target = (working_state or {}).get("current_target")
        if not isinstance(raw_target, Mapping):
            return None
        target = dict(raw_target)
        owner = self._canonical_actor(target.get("owner"))
        target_id = target.get("target_id")
        if owner is None or not isinstance(target_id, str) or not target_id.strip():
            return None
        requested_actor = self._requested_actor(cue)
        if requested_actor is not None and owner != requested_actor:
            return RouteResult(
                status="NEEDS_WORKING_STATE",
                route="immediate_bind",
                episode_id=None,
                matched_cue=cue,
                provenance_tier="unknown",
                content=None,
                corrections=(),
                world_knowledge_allowed=False,
                seek_primary=False,
                reason="named AGAIN cue does not match the attributable current target owner; do not guess",
            )
        return RouteResult(
            status="BOUND_WORKING_TARGET",
            route="immediate_bind",
            episode_id=None,
            matched_cue=cue,
            provenance_tier="unknown",
            content=None,
            corrections=(),
            world_knowledge_allowed=False,
            seek_primary=False,
            bound_target=target,
            reason="bound attributable current target before episodic or generic retrieval",
        )

    def resolve(
        self,
        utterance: str,
        *,
        working_state: Mapping[str, Any] | None = None,
        exact_wording: bool = False,
    ) -> RouteResult:
        """Resolve local continuity before permitting generic world knowledge."""
        cue = normalize_cue(utterance)
        exact = self._exact_wording_requested(utterance, exact_wording)

        # Pass 1: immediate bind. AGAIN is grammatical state, not a search term.
        if cue in self.immediate_bind_aliases:
            target_result = self._bind_current_target(cue, working_state)
            if target_result is not None:
                return target_result
            episode_id = (working_state or {}).get("last_episode_id")
            if episode_id in self.episodes:
                return self._episode_result(
                    episode_id,
                    matched_cue=cue,
                    exact_wording=exact,
                    reason="immediate bind to working-state episode before retrieval",
                )
            return RouteResult(
                status="NEEDS_WORKING_STATE",
                route="immediate_bind",
                episode_id=None,
                matched_cue=cue,
                provenance_tier="unknown",
                content=None,
                corrections=(),
                world_knowledge_allowed=False,
                seek_primary=False,
                reason="AGAIN requires the attributable current target; do not guess",
            )

        # Pass 2-4: exact local alias -> relational episode -> correction overlay.
        episode_id, matched_alias = self._match_episode(cue, allow_embedded_alias=exact)
        if episode_id:
            return self._episode_result(
                episode_id,
                matched_cue=matched_alias or cue,
                exact_wording=exact,
                reason="deterministic relational alias outranked generic world knowledge",
            )

        # Existing continuity owners remain separate; this candidate cannot swallow them.
        owner = self.reserved.get(cue)
        if owner:
            return RouteResult(
                status="DEFER_EXISTING_CONTINUITY",
                route="reserved_existing_continuity",
                episode_id=None,
                matched_cue=cue,
                provenance_tier="unknown",
                content=None,
                corrections=(),
                world_knowledge_allowed=False,
                seek_primary=False,
                delegated_owner=owner,
                reason="preserve existing organ authority instead of generic fallback",
            )

        return RouteResult(
            status="NO_LOCAL_MATCH",
            route="generic_world_knowledge",
            episode_id=None,
            matched_cue=None,
            provenance_tier="unknown",
            content=None,
            corrections=(),
            world_knowledge_allowed=True,
            seek_primary=False,
            reason="no deterministic local cue matched",
        )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("utterance")
    parser.add_argument("--last-episode-id")
    parser.add_argument("--exact-wording", action="store_true")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args(list(argv) if argv is not None else None)
    router = RitsuContextRouter(args.policy, args.ledger)
    state = (
        {"last_episode_id": args.last_episode_id}
        if args.last_episode_id
        else None
    )
    print(
        json.dumps(
            router.resolve(
                args.utterance,
                working_state=state,
                exact_wording=args.exact_wording,
            ).to_dict(),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
