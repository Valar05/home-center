#!/usr/bin/env python3
"""Regression source for exact owner-surgery state admission.

Source fixture only. Execution must be evidenced separately.
"""

import pytest

from try_forever_owner_surgery_state_policy import (
    MAX_STATE_CODEPOINTS,
    OwnerSurgeryStateError,
    admit_owner_surgery_state,
)


class CallbackState(str):
    strip_calls = 0

    def strip(self, *args, **kwargs):
        type(self).strip_calls += 1
        raise AssertionError("state policy executed caller-owned strip() before exact admission")


def test_exact_current_promotion_states_are_promotion_ready():
    assert admit_owner_surgery_state("PROPOSED_NOT_APPLIED").promotion_candidate is True
    assert admit_owner_surgery_state("CORRECTED_PROPOSED_NOT_APPLIED").promotion_candidate is True


def test_substring_proposed_does_not_create_authority():
    for state in (
        "NOT_PROPOSED",
        "PROPOSEDISH",
        "PROPOSED_NOT_APPLIED_EXTRA",
        "HISTORICAL_PROPOSED_ARTIFACT",
    ):
        admitted = admit_owner_surgery_state(state)
        assert admitted.promotion_candidate is False
        assert admitted.classification == "NON_PROMOTION_OR_UNKNOWN"


def test_terminal_or_historical_states_remain_nonpromotion():
    for state in (
        "APPLIED_SOURCE",
        "REJECTED_UNSAFE__DO_NOT_APPLY",
        "SUPERSEDED_DO_NOT_APPLY_ALONE",
    ):
        assert admit_owner_surgery_state(state).promotion_candidate is False


def test_normalization_dependent_or_noncanonical_text_fails_closed():
    for state in (
        " PROPOSED_NOT_APPLIED",
        "PROPOSED_NOT_APPLIED ",
        "proposed_not_applied",
        "PROPOSED-NOT-APPLIED",
        "PROPOSED\nNOT_APPLIED",
        "PROPOSED\u202e_NOT_APPLIED",
        "",
    ):
        with pytest.raises(OwnerSurgeryStateError):
            admit_owner_surgery_state(state)


def test_non_string_state_fails_closed():
    for state in (None, True, 1, [], {}):
        with pytest.raises(OwnerSurgeryStateError):
            admit_owner_surgery_state(state)


def test_string_subclass_is_rejected_before_caller_owned_strip_executes():
    CallbackState.strip_calls = 0
    with pytest.raises(OwnerSurgeryStateError, match="exact built-in string"):
        admit_owner_surgery_state(CallbackState("PROPOSED_NOT_APPLIED"))
    assert CallbackState.strip_calls == 0


def test_state_source_ceiling_is_enforced_before_regex_or_membership_work():
    admitted = "A" * MAX_STATE_CODEPOINTS
    result = admit_owner_surgery_state(admitted)
    assert result.state == admitted
    assert result.promotion_candidate is False

    with pytest.raises(OwnerSurgeryStateError, match="source ceiling"):
        admit_owner_surgery_state("A" * (MAX_STATE_CODEPOINTS + 1))
