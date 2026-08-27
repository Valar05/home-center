#!/usr/bin/env python3
"""RED source regression for direct scene candidate-count source-work custody.

SOURCE ONLY / UNEXECUTED. Canonical heartbeat parsing rejects more than MAX_LIGHTS records before
candidate traversal. Direct HeartbeatSceneGraph.build(...) currently reaches duplicate/material
list traversal without the equivalent cardinality gate. This fixture pins the existing-owner
repair and last-good/no-motion rejection boundary without claiming the repair is applied.
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


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    parser = PARSER.read_text(encoding="utf-8")

    assert "public static final int MAX_LIGHTS = 64;" in parser
    build = source.index(
        "public static Frame build(\n"
        "            String pulseId,\n"
        "            List<HeartbeatSkillPolicy.Candidate> candidates,"
    )
    count_gate = source.index(
        "candidates.size() > HeartbeatEnvelopeParser.MAX_LIGHTS",
        build,
    )
    duplicate_scan = source.index("hasDuplicateMaterialIdentity(candidates)", build)
    material_scan = source.index("HeartbeatSkillPolicy.selectMaterialLights(candidates)", build)
    assert count_gate < duplicate_scan < material_scan
    assert '"Direct heartbeat scene exceeds "' in source[count_gate:duplicate_scan]
    assert "preserveLastGood(" in source[count_gate:duplicate_scan]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
