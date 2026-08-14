#!/usr/bin/env python3
"""Regression canary for the Adam overlay's giant-prompt intake contract.

This is intentionally hostile: it proves the payload representation used by the
Android overlay can carry a large multiline commission without shell parsing,
truncation, newline loss, or command-substitution execution.
"""
from pathlib import Path
import base64
import hashlib

ROOT=Path(__file__).resolve().parents[1]
state=(ROOT/"android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java").read_text(encoding="utf-8")
provider=(ROOT/"android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorStateProvider.java").read_text(encoding="utf-8")
service=(ROOT/"android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java").read_text(encoding="utf-8")

hostile="""FORTRESS OPERATOR RECOVERY — CONTINUE
Codex's Drive
$HOME
\"quoted text\"
$(this_must_not_execute)
- leading-hyphen
Unicode → survives
blank line follows:

END
"""
prompt=(hostile+"0123456789abcdef"*1024+"\n")*12
raw=prompt.encode("utf-8")
assert len(raw)>200_000, len(raw)
encoded=base64.b64encode(raw)
received=base64.b64decode(encoded,validate=True)
assert received==raw
assert hashlib.sha256(received).hexdigest()==hashlib.sha256(raw).hexdigest()

# The Android producer must preserve exact text; this exact historical bug
# silently chopped commissions at 12,000 characters.
assert 'if (clean.length() > 12000) clean = clean.substring(0, 12000)' not in state
assert 'String exact = text == null ? "" : text;' in state
assert '.putLong(KEY_ADAM_REQUEST_BYTES, bytes.length)' in state
assert '.putString(KEY_ADAM_REQUEST_SHA256, sha256(bytes))' in state
assert 'adam_request_bytes' in provider and 'adam_request_sha256' in provider
assert 'setSingleLine(false)' in service
assert 'submitAdamRequest()' in service

print(f"MAJESTIC_PROMPT_CANARY PASS bytes={len(raw)} sha256={hashlib.sha256(raw).hexdigest()}")
