#!/usr/bin/env python3
"""Fail-closed source and behavioral contract for the app-local tracker."""
from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay"
JAVA_TEST = ROOT / "android/operator-overlay/app/src/test/java/com/homecenter/operatoroverlay"
TOOLS = ROOT / "tools"
CORPUS = (
    ROOT
    / "android/operator-overlay/app/src/test/resources"
    / "nicotine_tracker_adversarial_vectors.tsv"
)


def read(path: Path) -> str:
    assert path.is_file(), f"required source missing: {path}"
    return path.read_text(encoding="utf-8")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode_escapes(value: str) -> str:
    value = re.sub(
        r"\\U([0-9a-fA-F]{8})",
        lambda match: chr(int(match.group(1), 16)),
        value,
    )
    return re.sub(
        r"\\u([0-9a-fA-F]{4})",
        lambda match: chr(int(match.group(1), 16)),
        value,
    )


def adversarial_vectors() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in read(CORPUS).splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        assert len(fields) == 3, f"invalid shared corpus row: {line!r}"
        rows.append((fields[0], decode_escapes(fields[1]), fields[2]))
    assert len(rows) == 33
    return rows


def assert_java_contract() -> None:
    parser = read(JAVA / "NicotineTrackerContract.java")
    ledger = read(JAVA / "NicotineTrackerLedger.java")
    store = read(JAVA / "NicotineTrackerStore.java")
    service = read(JAVA / "OperatorOverlayService.java")
    state = read(JAVA / "OperatorState.java")
    provider = read(JAVA / "OperatorStateProvider.java")
    receiver = read(JAVA / "OverlayUpdateReceiver.java")
    scroll = read(JAVA / "MaxHeightScrollView.java")
    parser_test = read(JAVA_TEST / "NicotineTrackerContractTest.java")
    ledger_test = read(JAVA_TEST / "NicotineTrackerLedgerTest.java")

    for token in (
        "HUNGER(\"hunger\")",
        "TANK(\"tank\")",
        "PUFFS(\"puffs\")",
        "EXPOSURE(\"exposure\")",
        "none\", \"mild\", \"moderate\", \"strong\", \"overwhelming",
        "unknown\", \"empty\", \"low\", \"about-half\", \"high",
        "mouth\", \"swallowed\", \"skin\", \"eye\", \"unknown",
        "0|[1-9][0-9]?|100",
        "UNSAVED_LOCAL_DRAFT",
    ):
        assert token in parser, f"parser contract missing {token!r}"
    assert parser.count("enum Kind") == 1
    enum_body = parser.split("enum Kind", 1)[1].split(";", 1)[0]
    assert enum_body.count("(\"") == 4, "event kind count changed"
    for token in (
        "Normalizer.Form.NFKD",
        "Character.FORMAT",
        "Character.NON_SPACING_MARK",
        "Character.COMBINING_SPACING_MARK",
        "Character.ENCLOSING_MARK",
        "isDefaultIgnorable(codePoint)",
        "compatibility.codePointAt(offset)",
    ):
        assert token in parser, f"Unicode classification contract missing {token!r}"
    guard = read(TOOLS / "nicotine_tracker_guard.py")
    assert 'unicodedata.normalize("NFKD"' in guard
    assert '{"Cf", "Mn", "Mc", "Me"}' in guard
    assert "_default_ignorable(ord(character))" in guard

    parse_at = service.index("NicotineTrackerContract.parse(raw)")
    dispatch_at = service.index("OperatorState.submitAdamRequest")
    assert parse_at < dispatch_at
    assert "State.VALID" in service[parse_at:dispatch_at]
    assert "State.UNSAVED_LOCAL_DRAFT" in service[parse_at:dispatch_at]
    assert "showTrackerReview" in service[parse_at:dispatch_at]
    assert "showInvalidTrackerDraft" in service[parse_at:dispatch_at]
    assert state.index("NicotineTrackerContract.parse(text)") < state.index(
        "Base64.encodeToString"
    )
    assert "adamRequestNeedsLocalReview" in state
    assert 'return adamRequestNeedsLocalReview(context) ? "" : encoded;' in state
    assert '"adam_request_local_review_required"' in provider
    assert "OperatorState.adamRequestNeedsLocalReview(getContext()) ? 1 : 0" in provider

    assert "getFilesDir()" in store
    assert "source=\"local\"" not in ledger  # JSON is assembled, never logged.
    for field in (
        "SecureRandom",
        "eventId",
        "idempotencyKey",
        "requestDigest",
        "eventDigest",
        "wallTimeEpochMs",
        "wallTimeZone",
        "monotonicNanos",
        "monotonicOrder",
        "previousEventDigest",
        "SOURCE_LOCAL",
        "StandardCopyOption.ATOMIC_MOVE",
        "output.getFD().sync()",
    ):
        assert field in ledger, f"ledger contract missing {field}"
    assert ledger.count("StandardCopyOption.REPLACE_EXISTING") == 1
    for integrity_token in (
        "parseEvent(body)",
        "expectedRequestDigest",
        "expectedEventDigest",
        "duplicate immutable local event id",
        "deletion or gap",
        "digest chain mismatch",
        "MAX_EVENT_ID_ATTEMPTS = 8",
        "uniqueEventId(existing, ids)",
        "atomic local event postcondition failed",
        "HEAD_SCHEMA = \"adam-nicotine-tracker-head-v1\"",
        "HEAD_FILE_NAME = \"head.json\"",
        "MAX_PENDING_FILES = 16",
        "unexpected entry in immutable local events directory",
        "verifyHead(root, result, allowSingleEventHeadRecovery)",
        "head.eventCount + 1L == events.length",
        "durable local ledger head does not match immutable events",
        "fsyncDirectory(events)",
        "fsyncDirectory(root)",
    ):
        assert integrity_token in ledger
    assert "nicotine-tracker-v1" in ledger
    assert "MAX_NOTE_CHARS = 240" in parser
    assert "InputFilter.LengthFilter(NicotineTrackerContract.MAX_NOTE_CHARS)" in service

    combined_remote = provider + receiver + read(TOOLS / "vlad_swarm_daemon.py")
    assert "saveFromLocalReview" not in combined_remote
    assert "NicotineTrackerLedger" not in combined_remote
    assert "nicotine-tracker-v1" not in combined_remote
    all_save_refs = []
    for path in list(JAVA.glob("*.java")):
        if "saveFromLocalReview" in read(path):
            all_save_refs.append(path.name)
    assert sorted(all_save_refs) == ["NicotineTrackerStore.java", "OperatorOverlayService.java"]

    for forbidden_field in (
        "tracker_value",
        "tracker_note",
        "tracker_event",
        "nicotine_tracker",
    ):
        assert forbidden_field not in provider.lower()
        assert forbidden_field not in receiver.lower()

    tracker_review = service[
        service.index("private void showTrackerReview") :
        service.index("private void recomputeExpandedWidth")
    ].lower()
    tracker_production = (parser + ledger + store + tracker_review).lower()
    forbidden_features = (
        "dose",
        "drop",
        "concentration",
        "mg/ml",
        "conversion",
        "equivalence",
        "prediction",
        "countdown",
        "target",
        "taper",
        "recommendation",
        "gamification",
        "streak",
        "reminder",
        "oral drip",
    )
    for word in forbidden_features:
        assert word not in tracker_production, f"forbidden tracker feature surfaced: {word}"
    assert "cleartracker" not in tracker_production
    assert "exporttracker" not in tracker_production
    assert "Log." not in service + ledger + store

    assert "Exposure entry only." in service
    assert "does not determine risk or safety" in service
    assert "Entry saved" in service
    assert "localDraftSummary" not in service[
        service.index("private Notification buildNotification") :
        service.index("private void createOverlay")
    ]
    assert "MaxHeightScrollView" in service + scroll
    assert "Math.min(incomingSize, maxHeightPx)" in scroll
    assert "MeasureSpec.getMode(heightMeasureSpec)" in scroll
    assert "detailsScroll.fullScroll(View.FOCUS_DOWN)" in service
    assert "MIN_TOUCH_TARGET_DP" in service
    assert "trackerNote.setMinimumHeight" in service
    for label in (
        "Local tracker review. Nothing is saved until Save entry is pressed.",
        "Save this reviewed entry to app-private local storage",
        "Cancel this unsaved local tracker draft",
    ):
        assert label in service

    for test_token in (
        "rejectMatrixStaysUnsavedAndNeverBecomesOrdinaryText",
        "for (int value = 0; value <= 100; value++)",
        "monotonicOrderSurvivesWallClockMovingBackward",
        "failedAtomicCommitLeavesNoEventAndNoPendingDraft",
        "idempotencyCollisionWithChangedDraftFailsClosed",
        "sharedAdversarialCorpusNeverFallsThrough",
        "duplicateRandomEventIdRetriesThenUsesUniqueIdentity",
        "duplicateRandomEventIdRetryExhaustionAppendsNothing",
        "duplicateImmutableEventIdBlocksAppend",
        "corruptedRequestDigestBlocksReplayAndAppend",
        "corruptedEventDigestBlocksReplayAndAppend",
        "deletedEventCreatesGapAndBlocksAppend",
        "truncatedEventBlocksAppend",
        "partialDestinationFromBrokenCommitIsRemoved",
        "deletedLastTailIsDetectedByDurableHead",
        "renamedEventBackupIsUnexpectedAndBlocksAppend",
        "missingHeadWithEventsBlocksAppend",
        "corruptHeadBlocksAppend",
        "singleCrashEventCompletesHeadBeforeNextAppend",
    ):
        assert test_token in parser_test + ledger_test


def assert_adam_router_quarantine() -> None:
    adam = load_module("adam_tracker_contract", TOOLS / "adam.py")
    calls: list[tuple] = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("tracker-shaped text reached a router lane")

    adam.classify_mode = forbidden
    adam.run_terminal = forbidden
    adam.run_text = forbidden
    adam.run_radio = forbidden
    adam.run_worker = forbidden
    samples = [
        (text, private_token)
        for expected, text, private_token in adversarial_vectors()
        if expected == "QUARANTINE"
    ]
    for mode in (*adam.ONE_SHOT_MODES, "not-a-mode"):
        for sample, private_token in samples:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = adam.run_mode(mode, sample, str(ROOT), 1)
            receipt = json.loads(output.getvalue())
            assert rc == 1
            assert receipt["state"] == "UNSAVED_LOCAL_DRAFT"
            assert receipt["persisted"] is False
            assert receipt["workerInvoked"] is False
            assert receipt["providerMutation"] is False
            assert receipt["requiresOnPhoneReview"] is True
            rendered = output.getvalue().lower()
            assert sample.lower() not in rendered
            encoded = base64.b64encode(sample.encode("utf-8")).decode("ascii").lower()
            assert encoded not in rendered
            if not private_token.isdigit():
                assert private_token.lower() not in rendered
    assert calls == []

    for expected, text, _private_token in adversarial_vectors():
        if expected == "ORDINARY":
            assert adam.local_tracker_guard(text) is False, text

    routed: list[tuple[str, str]] = []
    adam.classify_mode = lambda text: ("chat", "test")
    adam.run_worker = lambda mode, text, cwd, timeout: routed.append((mode, text)) or 0
    assert adam.run_mode("auto", "How does this work?", str(ROOT), 1) == 0
    assert routed == [("chat", "How does this work?")]


def assert_daemon_quarantine() -> None:
    daemon = load_module("daemon_tracker_contract", TOOLS / "vlad_swarm_daemon.py")
    source = read(TOOLS / "vlad_swarm_daemon.py")
    guard_at = source.index("if _looks_local_tracker_text(text):")
    run_at = source.index('result=run(["python3",str(Path(repo_root)/"tools"/"adam.py")')
    assert guard_at < run_at
    flag_at = source.index("if local_review_required:")
    decode_at = source.index("base64.b64decode(payload")
    assert flag_at < decode_at < run_at
    assert "_operator_probe_summary(query)" in source
    assert "_operator_probe_summary(verify)" in source

    quarantined = [
        (text, private_token)
        for expected, text, private_token in adversarial_vectors()
        if expected == "QUARANTINE"
    ]
    for request_id, (raw, private_token) in enumerate(quarantined, start=41):
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        with tempfile.TemporaryDirectory(prefix="adam-tracker-daemon-") as tmp:
            daemon.STATE_DIR = Path(tmp)
            deliveries: list[bool] = []
            daemon._deliver_pending_responses = lambda: deliveries.append(True) or True
            daemon._last_adam_request_id = lambda: 0
            daemon.rish = lambda command: {
                "rc": 0,
                "stdout": (
                    "Row: 0 control_enabled=1, "
                    f"adam_request_id={request_id}, adam_request_mode=auto, "
                    f"adam_request_payload_b64={encoded}"
                ),
                "stderr": "",
            }

            run_calls: list[object] = []
            daemon.run = lambda *args, **kwargs: run_calls.append((args, kwargs))
            daemon.process_adam_overlay(str(ROOT))
            assert run_calls == []
            assert len(deliveries) == 2
            pending = json.loads(next(Path(tmp).glob("adam-pending-response-*.json")).read_text())
            receipts = (Path(tmp) / "receipts.jsonl").read_text(encoding="utf-8")
            rendered = json.dumps(pending, sort_keys=True) + receipts
            assert pending["taskResult"] == {
                "persisted": False,
                "providerMutation": False,
                "state": "UNSAVED_LOCAL_DRAFT",
                "workerInvoked": False,
            }
            assert raw not in rendered
            assert encoded not in rendered
            if not private_token.isdigit():
                assert private_token not in rendered

    for expected, text, _private_token in adversarial_vectors():
        assert daemon._looks_local_tracker_text(text) is (expected == "QUARANTINE"), text

    with tempfile.TemporaryDirectory(prefix="adam-tracker-redacted-provider-") as tmp:
        daemon.STATE_DIR = Path(tmp)
        deliveries: list[bool] = []
        daemon._deliver_pending_responses = lambda: deliveries.append(True) or True
        daemon._last_adam_request_id = lambda: 0
        daemon.rish = lambda command: {
            "rc": 0,
            "stdout": (
                "Row: 0 control_enabled=1, adam_request_id=9001, "
                "adam_request_mode=auto, adam_request_local_review_required=1, "
                "adam_request_payload_b64="
            ),
            "stderr": "",
        }
        run_calls: list[object] = []
        daemon.run = lambda *args, **kwargs: run_calls.append((args, kwargs))
        daemon.process_adam_overlay(str(ROOT))
        assert run_calls == []
        assert len(deliveries) == 2
        pending = json.loads(next(Path(tmp).glob("adam-pending-response-*.json")).read_text())
        assert pending["taskResult"]["state"] == "UNSAVED_LOCAL_DRAFT"


def assert_build_wiring() -> None:
    installer = read(TOOLS / "install_adam_cli.sh")
    workflow = read(ROOT / ".github/workflows/operator-overlay-android.yml")
    termux_builder = read(TOOLS / "build_operator_overlay_termux.sh")
    gradle = read(ROOT / "android/operator-overlay/app/build.gradle")
    assert "tools/test_adam_nicotine_tracker_contract.py" in installer
    assert "tools/nicotine_tracker_guard.py" in installer
    assert "python3 tools/test_adam_nicotine_tracker_contract.py" in installer
    assert "auto|terminal|text|chat|continue|vlad|radio" in installer
    assert "tools/test_adam_nicotine_tracker_contract.py" in workflow
    assert "feat/adam-nicotine-tank-tracker" in workflow
    for token in (
        'GRADLE_FILE="$APP/build.gradle"',
        "HC_OPERATOR_OVERLAY_SOURCE_SHA",
        "status --porcelain=v1 --untracked-files=all",
        "HC_GRADLE_DISTRIBUTION_SHA256",
        "d725d707bfabd4dfdc958c624003b3c80accc03f7037b5122c4b1d0ef15cecab",
        "HC_GRADLE_TREE_SHA256",
        "HC_GRADLE_VERIFICATION_METADATA_SHA256",
        "HC_GRADLE_LOCKFILE_SHA256",
        "--dependency-verification=strict",
        "HC_JAVA_BIN",
        "HC_JAVAC_BIN",
        "HC_JAVA_SHA256",
        "HC_JAVAC_SHA256",
        "HC_ANDROID_JAR_SHA256",
        "HC_ANDROID_BUILD_TOOLS_VERSION",
        "HC_ANDROID_BUILD_TOOLS_TREE_SHA256",
        "HC_AAPT2_PATH",
        "HC_AAPT2_SHA256",
        "HC_APKSIGNER_PATH",
        "HC_APKSIGNER_SHA256",
        "HC_OPERATOR_OVERLAY_KEYSTORE_SHA256",
        "HC_OPERATOR_OVERLAY_SIGNER_SHA256",
        "--offline --no-daemon",
        'EXPECTED_PACKAGE="com.homecenter.operatoroverlay"',
        "APK package id diverges from release contract",
        'python3 "$ROOT/tools/test_adam_nicotine_tracker_contract.py"',
        "testDebugUnitTest assembleDebug",
        "APK versionCode diverges from Gradle",
        "APK signer mismatch",
    ):
        assert token in termux_builder
    for forbidden in (
        "pkg install",
        "curl ",
        "wget ",
        "sdkmanager",
        "--write-locks",
        "--refresh-dependencies",
        "keytool -genkeypair",
        "--version-code 3",
        "--version-name 1.2.0",
    ):
        assert forbidden not in termux_builder
    assert re.search(r"^\s*versionCode\s+5\s*$", gradle, re.MULTILINE)
    assert re.search(r"^\s*versionName\s+['\"]1\.3\.1['\"]\s*$", gradle, re.MULTILINE)
    assert "dependencyLocking" in gradle
    assert "lockAllConfigurations()" in gradle
    assert "lockMode = LockMode.STRICT" in gradle


def main() -> int:
    assert_java_contract()
    assert_adam_router_quarantine()
    assert_daemon_quarantine()
    assert_build_wiring()
    print("PASS: app-local nicotine hunger/tank tracker contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
