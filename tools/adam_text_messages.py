#!/usr/bin/env python3
"""Superseded prototype guard.

This file previously experimented with a phone-local message-provider reader.
That is not the commissioned Home Center Text Inbox architecture and must not
be used as evidence of implementation, deployment, or acceptance.

Canonical campaign contract:
    docs/HARROWAY_TEXT_INBOX_CAMPAIGN.md

The commissioned feature requires Home Center orchestration and an explicit
self-service device permission boundary. This guard intentionally performs no
message access.
"""

raise SystemExit(
    "BLOCKED: superseded prototype. Use the Home Center Harroway Text Inbox campaign; "
    "this file performs no message access."
)
