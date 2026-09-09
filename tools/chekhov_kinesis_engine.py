#!/usr/bin/env python3
"""Deterministic Chekhov Arsenal -> embodied-kinesis transform.

Ingress is deliberately high-recall: violent use, affordance, intention,
imagination, opinion, coercion, defense, or meaningful refusal is enough to
admit a Chekhov candidate. Mechanics are deliberately conservative: the engine
emits only structured or lexically witnessed kinetic primitives. Unknown stays
unknown.

Contract: same normalized input + ENGINE_VERSION => same graph bytes/hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Any, Iterable

SCHEMA = "home-center.chekhov-kinesis-graph.v1"
ENGINE_VERSION = "chekhov-kinesis/v1"

STATE_ORDER = (
    "USED", "THREATENED", "AFFORDS", "IMAGINED", "OPINIONATED",
    "COERCIVE", "DEFENSIVE", "REFUSED", "BORROWED", "MISATTRIBUTED",
    "DOCTRINE_EXAMPLE", "SUPERSEDED", "QUARANTINED",
)

STATE_PATTERNS = {
    "USED": (
        r"\bused (?:it |this |the )?(?:as )?(?:a )?weapon\b",
        r"\b(?:hit|struck|stabbed|cut|shot|killed|crushed|smashed|bludgeoned)\b",
    ),
    "THREATENED": (r"\bthreat(?:en|ened|ening|ens)?\b", r"\bbrandish(?:ed|es|ing)?\b"),
    "AFFORDS": (
        r"\bweapon\b", r"\bviolent affordance\b",
        r"\bcould (?:hurt|harm|kill|strike|stab|cut|crush|smash|burn|shoot)\b",
    ),
    "IMAGINED": (
        r"\b(?:thought|think|thinking|imagined|imagine|imagining|fantasy|fantasized)\b.{0,80}\b(?:violent|violently|weapon|hurt|harm|kill|murder|strike|stab|smash)\b",
        r"\b(?:violent|violently|weapon|hurt|harm|kill|murder|strike|stab|smash)\b.{0,80}\b(?:thought|think|thinking|imagined|imagine|imagining|fantasy|fantasized)\b",
    ),
    "OPINIONATED": (
        r"\bviolent(?:ly)?\b.{0,60}\bopinion(?:s|ated)?\b",
        r"\bopinion(?:s|ated)?\b.{0,60}\bviolent(?:ly)?\b",
        r"\bmurderous\b", r"\bhomicidal\b",
    ),
    "COERCIVE": (r"\bcoerc(?:e|ed|ion|ive)\b", r"\bcompel(?:led|s|ling)?\b", r"\bforced? stillness\b"),
    "DEFENSIVE": (r"\bdefen(?:d|ded|sive|se)\b", r"\bshield(?:ed|s|ing)?\b", r"\bblock(?:ed|s|ing)?\b"),
    "REFUSED": (r"\brefus(?:e|ed|es|ing|al)\b", r"\bdeliberately (?:unfired|unused|not used|not fired)\b", r"\bleft (?:it |the .* )?behind\b"),
}

PRIMITIVE_ORDER = (
    "GRIP", "HOLD", "PLANT", "ANCHOR", "BRACE", "LOAD", "STORE",
    "COMPRESS", "TENSION", "RELEASE", "STRIKE", "THRUST", "CUT",
    "CRUSH", "PRY", "WEDGE", "HOOK", "LEVER", "BIND", "SHEAR",
    "TORQUE", "PIVOT", "OSCILLATE", "CARRY", "TRANSFER", "REDIRECT",
    "ABSORB", "DISTRIBUTE", "CONTAIN", "BLOCK", "OPEN", "CLOSE",
    "JAM", "INTERRUPT", "SIGNAL", "FEED", "REFUSE", "ABANDON",
    "BECOME_ARCHITECTURE", "BORROW_BEHAVIOR",
)

PRIMITIVE_PATTERNS = {
    "GRIP": (r"\bgrip(?:ped|s|ping)?\b", r"\bgrasp(?:ed|s|ing)?\b"),
    "HOLD": (r"\bhold(?:s|ing)?\b", r"\bheld\b"),
    "PLANT": (r"\bplant(?:ed|s|ing)?\b",),
    "ANCHOR": (r"\banchor(?:ed|s|ing)?\b", r"\bhardpoint\b"),
    "BRACE": (r"\bbrace(?:d|s|ing)?\b",),
    "LOAD": (r"\bload(?:ed|s|ing)?\b",),
    "STORE": (r"\bstor(?:e|ed|es|ing) (?:energy|motion|force)\b",),
    "COMPRESS": (r"\bcompress(?:ed|es|ing|ion)?\b",),
    "TENSION": (r"\btension(?:ed|s|ing)?\b", r"\bsnaps? taut\b", r"\btaut\b"),
    "RELEASE": (r"\breleas(?:e|ed|es|ing)\b",),
    "STRIKE": (r"\bstrik(?:e|es|ing)\b", r"\bstruck\b", r"\bhit(?:s|ting)?\b", r"\bsmash(?:ed|es|ing)?\b", r"\bbludgeon(?:ed|s|ing)?\b"),
    "THRUST": (r"\bthrust(?:s|ing)?\b", r"\bstab(?:bed|s|bing)?\b"),
    "CUT": (r"\bcut(?:s|ting)?\b", r"\bslic(?:e|ed|es|ing)\b", r"\bslash(?:ed|es|ing)?\b"),
    "CRUSH": (r"\bcrush(?:ed|es|ing)?\b",),
    "PRY": (r"\bpr(?:y|ied|ies|ying)\b",),
    "WEDGE": (r"\bwedge(?:d|s|ing)?\b",),
    "HOOK": (r"\bhook(?:ed|s|ing)?\b",),
    "LEVER": (r"\blever(?:ed|s|ing)?\b", r"\bleverage\b"),
    "BIND": (r"\bbind(?:s|ing)?\b", r"\bbound\b", r"\bweb(?:bed|s|bing)?\b", r"\btie(?:d|s|ing)?\b"),
    "SHEAR": (r"\bshear(?:ed|s|ing)?\b",),
    "TORQUE": (r"\btorque(?:d|s|ing)?\b",),
    "PIVOT": (r"\bpivot(?:ed|s|ing)?\b",),
    "OSCILLATE": (r"\boscillat(?:e|ed|es|ing|ion)\b", r"\bswing(?:s|ing)?\b", r"\bswung\b"),
    "CARRY": (r"\bcarry(?:ing|ies)?\b", r"\bcarried\b"),
    "TRANSFER": (r"\btransfer(?:red|s|ring)?\b", r"\bload path\b"),
    "REDIRECT": (r"\bredirect(?:ed|s|ing)?\b", r"\bdeflect(?:ed|s|ing)?\b", r"\brerout(?:e|ed|es|ing)\b"),
    "ABSORB": (r"\babsorb(?:ed|s|ing)?\b",),
    "DISTRIBUTE": (r"\bdistribut(?:e|ed|es|ing|ion)\b",),
    "CONTAIN": (r"\bcontain(?:ed|s|ing)?\b", r"\bcage(?:d|s|ing)?\b", r"\btrap(?:ped|s|ping)?\b"),
    "BLOCK": (r"\bblock(?:ed|s|ing)?\b", r"\bshield(?:ed|s|ing)?\b"),
    "OPEN": (r"\bopen(?:ed|s|ing)?\b", r"\bbreach(?:ed|es|ing)?\b"),
    "CLOSE": (r"\bclos(?:e|ed|es|ing)\b", r"\bseal(?:ed|s|ing)?\b"),
    "JAM": (r"\bjam(?:med|s|ming)?\b", r"\bchok(?:e|ed|es|ing)\b"),
    "INTERRUPT": (r"\binterrupt(?:ed|s|ing)?\b", r"\bstop(?:ped|s|ping)?\b", r"\barrest(?:ed|s|ing)?\b"),
    "SIGNAL": (r"\bsignal(?:ed|led|s|ing)?\b", r"\bcall-and-response\b"),
    "FEED": (r"\bfeed(?:s|ing)?\b", r"\bfed\b", r"\bdiet\b", r"\bration\b"),
    "REFUSE": (r"\brefus(?:e|ed|es|ing|al)\b", r"\bunfired\b", r"\bnot fired\b", r"\bnot used\b"),
    "ABANDON": (r"\babandon(?:ed|s|ing)?\b", r"\bleft behind\b", r"\bdiscard(?:ed|s|ing)?\b"),
    "BECOME_ARCHITECTURE": (r"\bbecame (?:a |the )?(?:door|bridge|brace|support|architecture|structure)\b", r"\bbecomes? (?:a |the )?(?:door|bridge|brace|support|architecture|structure)\b", r"\bholding (?:a |the )?(?:route|door|frame) open\b", r"\bload-bearing\b"),
    "BORROW_BEHAVIOR": (r"\bborrow(?:ed|s|ing)? (?:a |the |one )?behavio[u]?r\b", r"\bone behavio[u]?r for one measure\b", r"\bworst habit\b"),
}

CHANNELS = {
    "body_interface": frozenset({"GRIP", "HOLD", "PLANT", "BRACE", "CARRY"}),
    "contact": frozenset({"STRIKE", "THRUST", "CUT", "CRUSH", "PRY", "WEDGE", "HOOK", "BIND", "BLOCK"}),
    "load": frozenset({"LOAD", "STORE", "COMPRESS", "TENSION", "TORQUE", "OSCILLATE"}),
    "constraint": frozenset({"ANCHOR", "BRACE", "WEDGE", "BIND", "CONTAIN", "BLOCK", "JAM"}),
    "transfer": frozenset({"LEVER", "TRANSFER", "REDIRECT", "ABSORB", "DISTRIBUTE", "SHEAR", "PIVOT"}),
    "terminal": frozenset({"RELEASE", "OPEN", "CLOSE", "INTERRUPT", "SIGNAL", "FEED", "REFUSE", "ABANDON", "BECOME_ARCHITECTURE", "BORROW_BEHAVIOR"}),
}

FOURTH_DOOR_PATTERNS = {
    "ROLE_CHANGE": (r"\bbecome(?:s)?\b", r"\bbecame\b", r"\bused as\b", r"\brole change\b"),
    "CUSTODY_CHANGE": (r"\bcustody\b", r"\bborrow(?:ed|s|ing)?\b", r"\bownership\b", r"\bprovenance\b", r"\bnot (?:mine|his|hers|theirs)\b"),
    "SYSTEM_CHANGE": (r"\bsystem\b", r"\bload path\b", r"\barchitecture\b", r"\broute\b", r"\binfrastructure\b"),
    "NON_USE_CHANGE": (r"\bunfired\b", r"\brefus(?:e|ed|es|ing|al)\b", r"\bnot (?:used|fired|taken)\b", r"\bleft behind\b"),
}


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _ordered(values: Iterable[str], order: tuple[str, ...]) -> list[str]:
    wanted = {str(value).upper().replace("-", "_").replace(" ", "_") for value in values}
    return [name for name in order if name in wanted]


def _matches(text: str, table: dict[str, tuple[str, ...]], order: Iterable[str]) -> list[str]:
    result = []
    for name in order:
        if any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in table.get(name, ())):
            result.append(name)
    return result


def _evidence_text(item: dict[str, Any]) -> str:
    parts = []
    for key in ("label", "name", "title", "text", "prose", "description", "evidence", "instrument", "prose_anchor", "fourth_door", "fourthDoor"):
        value = item.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(v) for v in value)
    return " ".join(" ".join(parts).lower().split())


def _source_refs(item: dict[str, Any]) -> list[str]:
    refs = []
    for key in ("sourceRefs", "sources", "source_refs"):
        refs.extend(_strings(item.get(key)))
    return sorted(set(refs))


def _stable_id(item: dict[str, Any], text: str, refs: list[str]) -> str:
    for key in ("id", "canonicalKey", "canonical_key", "itemId", "item_id"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    label = str(item.get("label") or item.get("name") or item.get("title") or "").strip()
    return "chekhov.auto." + _sha({"label": label, "text": text, "sourceRefs": refs})[:20]


def _compression(primitives: list[str]) -> dict[str, Any]:
    selected = set(primitives)
    channels = {}
    compact = []
    for channel, allowed in CHANNELS.items():
        hits = [name for name in PRIMITIVE_ORDER if name in selected and name in allowed]
        channels[channel] = hits if hits else "unknown"
        compact.append(channel + "=" + ("+".join(hits) if hits else "?"))
    return {"schema": "chekhov-kinetic-compression/v1", "channels": channels, "compact": " -> ".join(compact)}


def normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    item = dict(raw)
    text = _evidence_text(item)
    refs = _source_refs(item)

    states = []
    for key in ("evidenceState", "evidenceStates", "state", "states", "chekhovSignals"):
        states.extend(_strings(item.get(key)))
    states = _ordered(states + _matches(text, STATE_PATTERNS, STATE_ORDER), STATE_ORDER)
    included = item.get("chekhov") is True or item.get("included") is True or bool(states)

    primitives = []
    for key in ("kineticPrimitives", "kinetic_primitives", "verbs", "mechanics"):
        primitives.extend(_strings(item.get(key)))
    primitives = _ordered(primitives + _matches(text, PRIMITIVE_PATTERNS, PRIMITIVE_ORDER), PRIMITIVE_ORDER)

    fourth = _matches(text, FOURTH_DOOR_PATTERNS, FOURTH_DOOR_PATTERNS.keys())
    fourth += [value.upper().replace("-", "_").replace(" ", "_") for value in _strings(item.get("fourthDoorClass") or item.get("fourth_door_class"))]
    fourth = sorted(set(fourth))

    item_id = _stable_id(item, text, refs)
    label = str(item.get("label") or item.get("name") or item.get("title") or item_id).strip()
    normalized = {
        "id": item_id,
        "label": label,
        "included": included,
        "evidence": {
            "states": states,
            "sourceRefs": refs,
            "textSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "mechanics": {
            "status": "SUPPORTED" if primitives else "UNKNOWN",
            "primitives": primitives,
            "compression": _compression(primitives),
            "fourthDoorClasses": fourth,
        },
    }
    normalized["recordSha256"] = _sha(normalized)
    return normalized


def derive_graph(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        raw_items = payload
        source = {}
    elif isinstance(payload, dict):
        raw_items = payload.get("items", payload.get("records", []))
        source = {key: payload[key] for key in ("projectId", "frameId", "frameVersion", "sourceHash") if key in payload}
    else:
        raise TypeError("input must be a JSON array or object containing items/records")
    if not isinstance(raw_items, list) or any(not isinstance(item, dict) for item in raw_items):
        raise TypeError("items/records must be an array of objects")

    sortable = [( _stable_id(item, _evidence_text(item), _source_refs(item)), dict(item)) for item in raw_items]
    sortable.sort(key=lambda pair: pair[0])
    ids = [pair[0] for pair in sortable]
    duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
    if duplicates:
        raise ValueError("duplicate Chekhov item ids: " + ", ".join(duplicates))

    normalized_input = [pair[1] for pair in sortable]
    input_hash = _sha({"engineVersion": ENGINE_VERSION, "source": source, "items": normalized_input})
    items = [normalize_item(item) for item in normalized_input]
    included = [item["id"] for item in items if item["included"]]
    excluded = [item["id"] for item in items if not item["included"]]
    graph = {
        "schema": SCHEMA,
        "engineVersion": ENGINE_VERSION,
        "inputSha256": input_hash,
        "source": source,
        "itemCount": len(items),
        "includedCount": len(included),
        "excludedCount": len(excluded),
        "items": items,
        "includedIds": included,
        "excludedIds": excluded,
    }
    graph["graphSha256"] = _sha(graph)
    return graph


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="JSON file; stdin when omitted")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    if args.input:
        with open(args.input, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = json.load(sys.stdin)
    graph = derive_graph(payload)
    if args.pretty:
        json.dump(graph, sys.stdout, ensure_ascii=False, sort_keys=True, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(_canonical(graph) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
