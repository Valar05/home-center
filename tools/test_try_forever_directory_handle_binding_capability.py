#!/usr/bin/env python3
"""Regression source for platform-specific directory-handle custody capability.

SOURCE ONLY / UNEXECUTED. Besides ordinary capability classification, this fixture pins the public
machine-input boundary: caller-owned string subclasses and truthy Python objects must be rejected
before equality/truthiness callbacks can participate in platform evidence.
"""

from try_forever_directory_handle_binding_capability import (
    classify_directory_handle_binding_capability,
)


class HostileString(str):
    callback_count = 0

    def __eq__(self, other):
        type(self).callback_count += 1
        raise AssertionError("caller-owned string equality executed inside capability admission")


class HostileTruthy:
    callback_count = 0

    def __bool__(self):
        type(self).callback_count += 1
        raise AssertionError("caller-owned truthiness executed inside capability admission")


def _ordinary_inputs(**overrides):
    values = {
        "os_name": "posix",
        "scandir_accepts_fd": True,
        "open_accepts_dir_fd": True,
        "stat_accepts_dir_fd": True,
        "stat_accepts_follow_symlinks": True,
        "has_o_directory": True,
        "has_o_nofollow": True,
    }
    values.update(overrides)
    return values


def _expect_rejected_without_callback(**overrides):
    try:
        classify_directory_handle_binding_capability(**_ordinary_inputs(**overrides))
    except ValueError:
        return
    raise AssertionError(f"callback-capable capability input was admitted: {overrides!r}")


def test_posix_with_all_required_primitives_is_source_ready_only():
    verdict = classify_directory_handle_binding_capability(**_ordinary_inputs())
    assert verdict.status == "SUPPORTED_POSIX_PRIMITIVES"
    assert "does not prove filesystem atomicity" in verdict.boundary


def test_non_posix_never_inherits_posix_atomicity_claim():
    verdict = classify_directory_handle_binding_capability(
        **_ordinary_inputs(os_name="nt")
    )
    assert verdict.status == "PORTABLE_ATOMIC_BINDING_UNAVAILABLE"


def test_each_missing_primitive_fails_closed():
    fields = (
        "scandir_accepts_fd",
        "open_accepts_dir_fd",
        "stat_accepts_dir_fd",
        "stat_accepts_follow_symlinks",
        "has_o_directory",
        "has_o_nofollow",
    )
    for field in fields:
        verdict = classify_directory_handle_binding_capability(
            **_ordinary_inputs(**{field: False})
        )
        assert verdict.status == "PORTABLE_ATOMIC_BINDING_UNAVAILABLE"
        assert "Do not upgrade pathname pre/post revalidation" in verdict.boundary


def test_os_name_subclass_is_rejected_before_equality_callback():
    HostileString.callback_count = 0
    _expect_rejected_without_callback(os_name=HostileString("posix"))
    assert HostileString.callback_count == 0


def test_truthy_objects_are_rejected_before_bool_callback():
    boolean_fields = (
        "scandir_accepts_fd",
        "open_accepts_dir_fd",
        "stat_accepts_dir_fd",
        "stat_accepts_follow_symlinks",
        "has_o_directory",
        "has_o_nofollow",
    )
    for field in boolean_fields:
        HostileTruthy.callback_count = 0
        _expect_rejected_without_callback(**{field: HostileTruthy()})
        assert HostileTruthy.callback_count == 0
