#!/usr/bin/env python3
from datetime import date, datetime

from headcrab_morning import MorningChecklist, render_reminder

state = MorningChecklist.fresh(date(2026, 10, 1))
now = datetime(2026, 10, 1, 5, 30)

assert state.pending(now) == ("pills", "food", "inhaler")
assert render_reminder(state.pending(now)) == "Morning Headcrab: 💊 pills · 🍽️ food · 🫁 inhaler"

state.mark_done("pills")
assert state.pending(now) == ("food", "inhaler")

state.mark_done("food")
state.mark_done("inhaler")
assert state.pending(now) == ()
assert render_reminder(state.pending(now)) is None

later = datetime(2026, 10, 1, 12, 0)
assert state.pending(later) == ()

tomorrow = datetime(2026, 10, 2, 5, 0)
assert state.pending(tomorrow) == ("pills", "food", "inhaler")
