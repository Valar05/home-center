#!/usr/bin/env python3
"""Regression source for canonical owner-surgery same-observation content witnesses.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from try_forever_owner_surgery_custody_probe import classify


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "1" * 40


def main() -> int:
    payload = (
        "# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n"
        f"# BASE OWNER BLOB: {BASE}\n"
        f"# OWNER: {OWNER}\n"
        "diff --git a/owner b/owner\n"
    ).encode("utf-8")

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / "try-forever-witness.patch"
        path.write_bytes(payload)

        result = classify(root, {OWNER: BASE})
        assert result["schema"] == "try-forever-owner-surgery-custody.v10"
        assert result["evidenceComplete"] is True
        assert len(result["surgeries"]) == 1
        assert len(result["artifactContentWitnesses"]) == 1

        surgery = result["surgeries"][0]
        witness = result["artifactContentWitnesses"][0]
        expected_sha = hashlib.sha256(payload).hexdigest()

        assert surgery["path"] == path.as_posix()
        assert surgery["artifact_byte_count"] == len(payload)
        assert surgery["artifact_sha256"] == expected_sha
        assert witness == {
            "path": path.as_posix(),
            "byteCount": len(payload),
            "sha256": expected_sha,
        }
        assert result["capability"]["sameObservationArtifactContentWitnesses"] is True
        assert result["capability"]["tested"] is False
        assert result["capability"]["phoneDelivered"] is False

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
