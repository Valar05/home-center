#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from headcrab_obligations import (
    ObligationLedger,
    load_ledger,
    render_reminders,
    save_ledger,
)

central = timezone(timedelta(hours=-5))
ledger = ObligationLedger.empty()

call_corey = ledger.capture(
    "Call Corey",
    datetime(2026, 10, 1, 20, 0, tzinfo=central),
)

assert ledger.actionable(
    datetime(2026, 10, 1, 19, 54, tzinfo=central)
) == ()

actionable = ledger.actionable(
    datetime(2026, 10, 1, 19, 55, tzinfo=central)
)
assert actionable == (call_corey,)
assert render_reminders(
    actionable,
    now=datetime(2026, 10, 1, 19, 55, tzinfo=central),
) == ("Headcrab: ⏰ Call Corey — in 5m",)

assert render_reminders(
    ledger.actionable(datetime(2026, 10, 1, 20, 0, tzinfo=central)),
    now=datetime(2026, 10, 1, 20, 0, tzinfo=central),
) == ("Headcrab: ⏰ Call Corey — now",)

# Capture is idempotent for the same label + due time.
same = ledger.capture(
    "Call Corey",
    datetime(2026, 10, 1, 20, 0, tzinfo=central),
)
assert same.obligation_id == call_corey.obligation_id
assert len(ledger.obligations) == 1

# Completion closes the loop and suppresses later reminders.
ledger.mark_done(
    call_corey.obligation_id,
    completed_at=datetime(2026, 10, 1, 20, 2, tzinfo=central),
)
assert ledger.actionable(
    datetime(2026, 10, 1, 20, 3, tzinfo=central)
) == ()

# State round-trips durably.
restored = ObligationLedger.from_dict(ledger.to_dict())
assert restored.to_dict() == ledger.to_dict()

# Missing timezone is a hard failure rather than silently guessing.
try:
    ObligationLedger.empty().capture(
        "ambiguous task",
        datetime(2026, 10, 1, 8, 0),
    )
except ValueError as exc:
    assert "timezone-aware" in str(exc)
else:
    raise AssertionError("naive obligation time should fail closed")


# File persistence survives process/runtime boundaries.
with TemporaryDirectory() as tmp:
    path = Path(tmp) / "headcrab-obligations.json"
    fresh = ObligationLedger.empty()
    saved = fresh.capture(
        "Call Corey",
        datetime(2026, 10, 2, 20, 0, tzinfo=central),
    )
    save_ledger(path, fresh)
    loaded = load_ledger(path)
    assert loaded.to_dict() == fresh.to_dict()
    assert loaded.actionable(
        datetime(2026, 10, 2, 19, 55, tzinfo=central)
    ) == (saved,)
