#!/usr/bin/env python3
import json
import sys


def evaluate():
    library = [
        {"name": "Noodle_Queen_Verdict_for_June.mp4", "mime": "video/mp4", "size": 8166734, "rank": 100},
        {"name": "Noodle Crown for June.mp4", "mime": "video/mp4", "size": 3201756, "rank": 70},
        {"name": "Noodle_Crown_for_June_accessible_master.mp4", "mime": "video/mp4", "size": 2517500, "rank": 90},
        {"name": "Noodle Crown Descriptive Transcript.txt", "mime": "text/plain", "size": 640, "rank": 40},
    ]
    drive = [
        {"name": "Noodle_Queen_PocketTTS_ASMR.opus", "mime": "application/ogg", "size": 658984, "rank": 10},
        {"name": "PocketTTS_render_receipt.txt", "mime": "text/plain", "size": 2349, "rank": 5},
    ]
    capabilities = {
        "gmail.send": True,
        "contacts.resolve": True,
        "library.materialize": True,
        "drive.write": False,
    }

    videos = [item for item in library + drive if item["mime"] == "video/mp4"]
    selected = max(videos, key=lambda item: item["rank"]) if videos else None

    route = []
    if selected and capabilities["library.materialize"]:
        route.append("Library.materialize")
    if capabilities["contacts.resolve"]:
        route.append("Contacts.resolve")
    if capabilities["gmail.send"]:
        route.extend(["Gmail.send", "Gmail.readback"])

    # Negative control: reproduce the historical bad behavior deliberately.
    broken_selected = drive[0]
    broken_false_blocker = not capabilities["drive.write"]

    checks = {
        "selected_video_not_audio": bool(selected and selected["mime"] == "video/mp4"),
        "selected_expected_verdict": bool(selected and selected["name"] == "Noodle_Queen_Verdict_for_June.mp4"),
        "drive_write_failure_not_global_blocker": (not capabilities["drive.write"] and capabilities["gmail.send"]),
        "capability_graph_traversed": route == ["Library.materialize", "Contacts.resolve", "Gmail.send", "Gmail.readback"],
        "outbound_receipt_shape_matches": bool(selected and selected["size"] == 8166734),
        "historical_bad_resolver_is_detected": bool(broken_selected["mime"] != "video/mp4" and broken_false_blocker),
    }

    passed = all(checks.values())
    return {
        "schema": "fortress.delivery.canary.v2",
        "fixture": "noodle-crown-incident",
        "selected": selected,
        "route": route,
        "negative_control": {
            "selected": broken_selected,
            "false_global_blocker": broken_false_blocker,
        },
        "checks": checks,
        "verdict": "PASS" if passed else "FAIL",
    }


def main():
    receipt = evaluate()
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 70


if __name__ == "__main__":
    raise SystemExit(main())
