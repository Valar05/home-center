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
DEFAULT_ACTIVE_RETRIEVAL = (
    ROOT / "fixtures" / "ritsu-continuity" / "active-retrieval.v0.jsonl"
)

PROVENANCE_RANK = {
    "primary_transcript": 0,
    "accepted_summary": 1,
    "adjacent_evidence": 2,
    "unknown": 3,
}
REVIEW_PASSES = ("target", "antagonist", "provenance", "regression", "compression")


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
    active_retrieval: dict[str, Any] | None = None
    candidate_episode_ids: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["corrections"] = list(self.corrections)
        data["candidate_episode_ids"] = list(self.candidate_episode_ids)
        return data


class RitsuContextRouter:
    def __init__(
        self,
        policy_path: Path = DEFAULT_POLICY,
        ledger_path: Path = DEFAULT_LEDGER,
        active_retrieval_path: Path | None = None,
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

        # Synthetic ledgers used by deterministic tests should not accidentally inherit
        # production retrieval obligations. Production/default ledger does.
        if active_retrieval_path is None and Path(ledger_path).resolve() == DEFAULT_LEDGER.resolve():
            active_retrieval_path = DEFAULT_ACTIVE_RETRIEVAL
        self.active_retrieval_records = (
            _load_jsonl(active_retrieval_path)
            if active_retrieval_path is not None and active_retrieval_path.exists()
            else []
        )
        self.active_retrieval_by_episode: dict[str, dict[str, Any]] = {}
        for record in self.active_retrieval_records:
            if record.get("record_type") != "active_retrieval":
                continue
            episode_id = record.get("episode_id")
            if episode_id not in self.episodes:
                raise ValueError(
                    f"active retrieval {record.get('id')!r} references unknown episode {episode_id!r}"
                )
            if episode_id in self.active_retrieval_by_episode:
                raise ValueError(f"multiple active retrieval records for {episode_id!r}")
            if record.get("required_provenance") != "primary_transcript":
                raise ValueError(
                    f"active retrieval {record.get('id')!r} must require primary_transcript"
                )
            review = record.get("review")
            if not isinstance(review, Mapping) or any(
                not isinstance(review.get(name), str) or not review[name].strip()
                for name in REVIEW_PASSES
            ):
                raise ValueError(
                    f"active retrieval {record.get('id')!r} lacks complete five-pass review"
                )
            status = record.get("status")
            if status not in {"open", "closed"}:
                raise ValueError(
                    f"active retrieval {record.get('id')!r} has invalid status {status!r}"
                )
            if status == "closed" and not self._has_readable_primary(self.episodes[episode_id]):
                raise ValueError(
                    f"active retrieval {record.get('id')!r} cannot close without readable primary transcript"
                )
            self.active_retrieval_by_episode[episode_id] = record

        self.alias_to_episode: dict[str, str] = {}
        for episode_id, episode in self.episodes.items():
            for alias in episode.get("aliases", []):
                key = normalize_cue(alias)
                incumbent = self.alias_to_episode.get(key)
                if incumbent and incumbent != episode_id:
                    raise ValueError(f"ambiguous deterministic alias {alias!r}")
                self.alias_to_episode[key] = episode_id

        # Only explicitly promoted multi-token aliases may bind inside ordinary
        # sentences. Weak shorthand remains exact-only unless exact wording is being
        # requested, which keeps natural continuity from swallowing generic speech.
        self.embedded_aliases: set[str] = set()
        for episode_id, episode in self.episodes.items():
            for alias in episode.get("embedded_aliases", []):
                key = normalize_cue(alias)
                if self.alias_to_episode.get(key) != episode_id:
                    raise ValueError(
                        f"embedded alias {alias!r} must also be an alias of {episode_id!r}"
                    )
                if len(key.split()) < 2:
                    raise ValueError(
                        f"embedded alias {alias!r} must contain at least two tokens"
                    )
                self.embedded_aliases.add(key)

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

    @staticmethod
    def _has_readable_primary(episode: Mapping[str, Any]) -> bool:
        for source in episode.get("primary_sources") or []:
            text = source.get("text") if isinstance(source, Mapping) else None
            if isinstance(text, str) and text.strip():
                return True
        return False

    def _active_retrieval_payload(self, episode_id: str) -> dict[str, Any] | None:
        record = self.active_retrieval_by_episode.get(episode_id)
        if record is None:
            return None
        # Keep user-facing routing output compact and mechanical. Search observations
        # and review prose stay in the durable ledger instead of becoming narration.
        return {
            key: record[key]
            for key in (
                "id",
                "status",
                "required_provenance",
                "deterministic_queries",
                "search_order",
                "closure_requires",
            )
            if key in record
        }

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
        active_retrieval = None if has_primary else self._active_retrieval_payload(episode_id)
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
                active_retrieval=active_retrieval,
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
            active_retrieval=active_retrieval,
            reason=reason,
        )

    def _match_episode(
        self,
        cue: str,
        *,
        allow_embedded_alias: bool,
        allow_weak_embedded_alias: bool = False,
    ) -> tuple[str | None, str | None, tuple[str, ...]]:
        episode_id = self.alias_to_episode.get(cue)
        if episode_id:
            return episode_id, cue, ()
        if not allow_embedded_alias:
            return None, None, ()

        padded = f" {cue} "
        matches: list[tuple[str, str]] = []
        for alias, candidate_id in self.alias_to_episode.items():
            promoted = alias in self.embedded_aliases
            if not (promoted or allow_weak_embedded_alias):
                continue
            if len(alias.split()) >= 2 and f" {alias} " in padded:
                matches.append((candidate_id, alias))

        unique_ids = tuple(sorted({item[0] for item in matches}))
        if len(unique_ids) > 1:
            return None, None, unique_ids
        if matches:
            return matches[0][0], matches[0][1], ()
        return None, None, ()

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

        # Pass 2-4: promoted local alias -> relational episode -> correction overlay.
        episode_id, matched_alias, ambiguous_ids = self._match_episode(
            cue,
            allow_embedded_alias=True,
            allow_weak_embedded_alias=exact,
        )
        if ambiguous_ids:
            return RouteResult(
                status="AMBIGUOUS_LOCAL_MATCH",
                route="episodic",
                episode_id=None,
                matched_cue=None,
                provenance_tier="unknown",
                content=None,
                corrections=(),
                world_knowledge_allowed=False,
                seek_primary=False,
                candidate_episode_ids=ambiguous_ids,
                reason="multiple deterministic relational aliases matched; fail closed instead of guessing",
            )
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
    parser.add_argument("--active-retrieval", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    router = RitsuContextRouter(args.policy, args.ledger, args.active_retrieval)
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
