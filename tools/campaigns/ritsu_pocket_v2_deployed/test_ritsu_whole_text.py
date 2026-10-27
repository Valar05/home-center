"""Contract checks: one agent-authored paragraph equals exactly one Pocket job/WAV."""
import hashlib
from unittest.mock import patch

import ritsu_say


class Log:
    def __init__(self):
        self.events = []
    def record(self, event, **kwargs):
        self.events.append((event, kwargs))


def check():
    original = "  Dr. Imani pauses...  Then Ritsu says, 'Yes, darling!'  "
    assert ritsu_say.validate_whole_text(original) == original
    assert ritsu_say.validate_whole_text("The rain continues. The workshop is quiet.") == (
        "The rain continues. The workshop is quiet.")
    for text in ("", " ", "x" * 451):
        try:
            ritsu_say.validate_whole_text(text)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid request accepted")

    calls = []
    jobid = "1" * 32
    relayid = "2" * 24

    def client(method, path, payload=None):
        calls.append((method, path, payload))
        if (method, path) == ("POST", "/v1/speak"):
            assert payload == {"text": original, "speaker": "normal"}
            return {"id": jobid, "state": "queued"}
        if (method, path) == ("GET", "/v1/jobs/" + jobid):
            return {"state": "completed", "generation_seconds": 2.0,
                    "audio_seconds": 8.2, "bytes": 393644}
        if (method, path) == ("POST", "/v1/deliver"):
            assert payload == {"job_id": jobid}
            return {"state": "enqueued", "relay_id": relayid}
        raise AssertionError("Unexpected Pocket call: " + repr((method, path)))

    log = Log()
    with patch("builtins.print"):
        receipts = ritsu_say.deliver_whole(
            original, "normal", "agent-whole-text-unit-test", client=client, trace=log)
    assert receipts == [relayid]
    assert len([x for x in calls if x[1] == "/v1/speak"]) == 1
    assert len([x for x in calls if x[1] == "/v1/deliver"]) == 1
    assert log.events[0][1]["text_sha256"] == hashlib.sha256(original.encode()).hexdigest()
    print("PASS verbatim paragraph, one synth job, one relay WAV, 450-char fail-closed")


if __name__ == "__main__":
    check()
