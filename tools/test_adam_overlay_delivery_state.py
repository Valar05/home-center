#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import vlad_swarm_daemon as daemon

with tempfile.TemporaryDirectory() as td:
    daemon.STATE_DIR = Path(td)

    # Corrupt post-execution delivery state must halt; it must never advance the
    # request id and therefore must never license a blind side-effecting rerun.
    corrupt = daemon._pending_response_path(41)
    corrupt.write_text("{not-json", encoding="utf-8")
    assert daemon._deliver_pending_responses() is False
    assert daemon._delivery_halt_path().is_file()
    assert daemon._last_adam_request_id() == 0
    assert not daemon._pending_response_paths()
    quarantined = list(Path(td).glob("quarantine-adam-pending-response-*.json"))
    assert quarantined, "corrupt pending response was not quarantined"

    # Clear only the synthetic test halt and prove transient delivery failure is
    # retried as delivery, not as task execution.
    daemon._delivery_halt_path().unlink()
    pending = {
        "schema": "adam-overlay-pending-response-v1",
        "requestId": 42,
        "mode": "chat",
        "display": "done once",
        "taskRc": 0,
        "taskResult": {"rc": 0},
        "attempts": 0,
        "nextAttemptEpoch": 0,
        "createdAtEpoch": daemon.now(),
    }
    path = daemon._save_pending_response(pending)
    daemon.operator_update = lambda text, source: {"rc": 1, "stdout": "", "stderr": "temporary"}
    assert daemon._deliver_pending_responses() is False
    assert path.is_file()
    assert daemon._last_adam_request_id() == 0
    retry = json.loads(path.read_text(encoding="utf-8"))
    assert retry["attempts"] == 1
    assert retry["nextAttemptEpoch"] > daemon.now()

    # Make the retry immediately eligible; successful delivery alone advances
    # the durable acknowledgement and removes pending state.
    retry["nextAttemptEpoch"] = 0
    path.write_text(json.dumps(retry), encoding="utf-8")
    daemon.operator_update = lambda text, source: {"rc": 0, "stdout": "ok", "stderr": ""}
    assert daemon._deliver_pending_responses() is True
    assert daemon._last_adam_request_id() == 42
    assert not path.exists()

print("Adam overlay durable delivery state contract: PASS")
