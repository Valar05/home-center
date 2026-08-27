#!/usr/bin/env python3
"""Source regression for direct scene candidate-count source-work custody.

SOURCE ONLY / UNEXECUTED. Canonical heartbeat parsing rejects more than MAX_LIGHTS records before
candidate traversal. Direct HeartbeatSceneGraph.build(...) now performs one size observation,
at most MAX_LIGHTS indexed reads, then traverses only a detached snapshot. This fixture pins that
existing-owner ordering. It deliberately does not claim callback-free arbitrary-List admission,
regression execution, TESTED state, runtime UI, TalkBack, deployment, phone delivery, or P0 work.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatSceneGraph.java"
)
PARSER = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatEnvelopeParser.java"
)
JAVA_REGRESSION = ROOT / (
    "android/operator-overlay/app/src/test/java/com/homecenter/operatoroverlay/"
    "HeartbeatDirectSceneCandidateSnapshotTest.java"
)


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    parser = PARSER.read_text(encoding="utf-8")
    java_regression = JAVA_REGRESSION.read_text(encoding="utf-8")

    assert "public static final int MAX_LIGHTS = 64;" in parser
    build = source.index(
        "public static Frame build(\n"
        "            String pulseId,\n"
        "            List<HeartbeatSkillPolicy.Candidate> candidates,"
    )
    snapshot_call = source.index("snapshotDirectCandidates(candidates)", build)
    duplicate_scan = source.index("hasDuplicateMaterialIdentity(boundedCandidates)", build)
    material_scan = source.index("HeartbeatSkillPolicy.selectMaterialLights(boundedCandidates)", build)
    display_scan = source.index("HeartbeatSkillPolicy.selectDisplayReadyLights(boundedCandidates)", build)
    assert snapshot_call < duplicate_scan < material_scan < display_scan
    assert '"Direct heartbeat scene exceeds "' in source[snapshot_call:duplicate_scan]
    assert "preserveLastGood(" in source[snapshot_call:duplicate_scan]

    helper = source.index(
        "private static List<HeartbeatSkillPolicy.Candidate> snapshotDirectCandidates("
    )
    helper_end = source.index("private static boolean hasDuplicateMaterialIdentity", helper)
    helper_source = source[helper:helper_end]
    assert "int size = candidates.size();" in helper_source
    assert "candidates.isEmpty()" not in helper_source
    assert "size > HeartbeatEnvelopeParser.MAX_LIGHTS" in helper_source
    assert "for (int index = 0; index < size; index++) detached.add(candidates.get(index));" in helper_source
    assert "Collections.unmodifiableList(detached)" in helper_source

    assert "maxPlusOneRejectsAfterOneSizeObservationWithoutElementReads" in java_regression
    assert "exactMaximumUsesOneSizeObservationAndAtMostSixtyFourIndexedReads" in java_regression
    assert "assertEquals(1, hostile.sizeCalls);" in java_regression
    assert "assertEquals(0, hostile.getCalls);" in java_regression
    assert "assertEquals(1, admitted.sizeCalls);" in java_regression
    assert "HeartbeatEnvelopeParser.MAX_LIGHTS, admitted.getCalls" in java_regression
    assert "assertFalse(rejected.transitionMotionAllowed);" in java_regression
    assert "assertFalse(rejected.nodes.get(0).transitionMotion);" in java_regression
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
