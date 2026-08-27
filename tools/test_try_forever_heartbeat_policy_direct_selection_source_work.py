#!/usr/bin/env python3
"""Convergence source regression for direct HeartbeatSkillPolicy selection-list custody.

SOURCE ONLY / UNEXECUTED. Direct selectMaterialLights(...) now owns canonical MAX_LIGHTS parity at
its own public boundary: one size observation, explicit failure above MAX_LIGHTS, at most MAX_LIGHTS
indexed reads into a detached immutable snapshot, then material/dedupe traversal only over that
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
    assert "# STATUS: APPLIED_SOURCE" in patch
    assert "# OWNER BASE BLOB: a0cfad7ce47455d06d83607f4e5ebdf71b9aada5" in patch
    assert "# APPLIED COMMIT: 3e5aa33a11fef2fa8ba3cf224b6844aa4cbecde2" in patch
    assert "# OWNER RESULT BLOB: fad085133d55d6c154ee591ffc66d28ce4507223" in patch

    selection = owner.index("public static List<Candidate> selectMaterialLights")
    display = owner.index("public static List<Candidate> selectDisplayReadyLights", selection)
    current = owner[selection:display]
    assert "snapshotDirectSelectionCandidates(candidates)" in current
    assert "int size = candidates.size();" in current
    assert "candidates.isEmpty()" not in current
    assert "size > HeartbeatEnvelopeParser.MAX_LIGHTS" in current
    assert "throw new IllegalArgumentException(" in current
    assert "for (int index = 0; index < size; index++) detached.add(candidates.get(index));" in current
    assert "Collections.unmodifiableList(detached)" in current
    assert "for (Candidate candidate : boundedCandidates)" in current
    assert "for (Candidate candidate : candidates)" not in current
    assert current.count("candidates.size()") == 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
