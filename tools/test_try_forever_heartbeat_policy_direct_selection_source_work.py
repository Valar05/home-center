#!/usr/bin/env python3
"""RED source regression for direct HeartbeatSkillPolicy selection-list custody.

SOURCE ONLY / UNEXECUTED. The canonical envelope parser rejects more than MAX_LIGHTS before
candidate traversal, while direct selectMaterialLights(...) currently observes/traverses arbitrary
caller Lists. The staged existing-owner repair must perform one size observation, reject >MAX_LIGHTS
with an explicit typed failure, take at most MAX_LIGHTS indexed reads, detach, then traverse only the
snapshot. This fixture does not claim callback-free arbitrary-List admission or TESTED/runtime state.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatSkillPolicy.java"
)
PARSER = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatEnvelopeParser.java"
)
PATCH = ROOT / "patches/try-forever-heartbeat-policy-direct-selection-candidate-snapshot.patch"


def main() -> int:
    owner = OWNER.read_text(encoding="utf-8")
    parser = PARSER.read_text(encoding="utf-8")
    patch = PATCH.read_text(encoding="utf-8")

    assert "public static final int MAX_LIGHTS = 64;" in parser
    assert "# STATUS: PROPOSED_NOT_APPLIED" in patch
    assert "# OWNER BASE BLOB: a0cfad7ce47455d06d83607f4e5ebdf71b9aada5" in patch
    assert "snapshotDirectSelectionCandidates(candidates)" in patch
    assert "int size = candidates.size();" in patch
    assert "candidates.isEmpty()" not in patch
    assert "size > HeartbeatEnvelopeParser.MAX_LIGHTS" in patch
    assert "throw new IllegalArgumentException(" in patch
    assert "for (int index = 0; index < size; index++) detached.add(candidates.get(index));" in patch
    assert "Collections.unmodifiableList(detached)" in patch
    assert "for (Candidate candidate : boundedCandidates)" in patch

    # RED owner boundary: proposal must remain distinct from implemented capability.
    selection = owner.index("public static List<Candidate> selectMaterialLights")
    display = owner.index("public static List<Candidate> selectDisplayReadyLights", selection)
    current = owner[selection:display]
    assert "snapshotDirectSelectionCandidates(candidates)" not in current
    assert "for (Candidate candidate : candidates)" in current
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
