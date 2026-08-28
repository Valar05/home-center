#!/usr/bin/env python3

from pathlib import Path

from try_forever_heartbeat_selection_owner_probe import classify


OWNER = Path(
    "android/operator-overlay/app/src/main/java/com/homecenter/"
    "operatoroverlay/OperatorOverlayService.java"
)


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    result = classify(source)
    seam = result["nativePersistentSelection"]

    # Intentionally RED until the existing OperatorOverlayService consumes the
    # source collection/item policy. Native setSelected(...) alone is incomplete.
    assert seam["status"] == "SOURCE_WIRED", seam

    capability = result["capability"]
    assert capability["sourceInspection"] is True
    assert capability["regressionExecuted"] is False
    assert capability["tested"] is False
    assert capability["runtimeTalkBack"] is False
    assert capability["phoneDelivered"] is False

    print("Heartbeat native selection owner boundary: SOURCE_WIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
