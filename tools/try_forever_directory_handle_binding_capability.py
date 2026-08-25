#!/usr/bin/env python3
"""Capability gate for stronger directory-handle custody.

The portable pathname bracket used by TRY FOREVER correctly refuses to claim atomic binding. This
helper answers a narrower question: does the current Python/OS surface expose the POSIX-style
primitives needed to *attempt* one held-directory-descriptor implementation without silently
pretending every platform supports it?

`SUPPORTED_POSIX_PRIMITIVES` is not itself an atomicity proof. Filesystem semantics, descriptor-
relative artifact reads, replacement/identity-reuse behavior, execution tests, and owner integration
remain separate gates.

Capability classification is a machine-evidence boundary, not an extensible Python callback
surface. Every public control input is admitted as its exact built-in scalar type before equality or
truthiness can participate in selection. A caller-owned ``str`` subclass or truthy object therefore
cannot execute code while manufacturing platform capability evidence.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DirectoryHandleBindingCapability:
    status: str
    os_name: str
    scandir_accepts_fd: bool
    open_accepts_dir_fd: bool
    stat_accepts_dir_fd: bool
    stat_accepts_follow_symlinks: bool
    has_o_directory: bool
    has_o_nofollow: bool
    boundary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _require_exact_capability_inputs(
    *,
    os_name: str,
    scandir_accepts_fd: bool,
    open_accepts_dir_fd: bool,
    stat_accepts_dir_fd: bool,
    stat_accepts_follow_symlinks: bool,
    has_o_directory: bool,
    has_o_nofollow: bool,
) -> None:
    if type(os_name) is not str:
        raise ValueError("os_name must be one exact built-in string")

    boolean_inputs = {
        "scandir_accepts_fd": scandir_accepts_fd,
        "open_accepts_dir_fd": open_accepts_dir_fd,
        "stat_accepts_dir_fd": stat_accepts_dir_fd,
        "stat_accepts_follow_symlinks": stat_accepts_follow_symlinks,
        "has_o_directory": has_o_directory,
        "has_o_nofollow": has_o_nofollow,
    }
    for field, value in boolean_inputs.items():
        if type(value) is not bool:
            raise ValueError(f"{field} must be one exact built-in boolean")


def classify_directory_handle_binding_capability(
    *,
    os_name: str,
    scandir_accepts_fd: bool,
    open_accepts_dir_fd: bool,
    stat_accepts_dir_fd: bool,
    stat_accepts_follow_symlinks: bool,
    has_o_directory: bool,
    has_o_nofollow: bool,
) -> DirectoryHandleBindingCapability:
    _require_exact_capability_inputs(
        os_name=os_name,
        scandir_accepts_fd=scandir_accepts_fd,
        open_accepts_dir_fd=open_accepts_dir_fd,
        stat_accepts_dir_fd=stat_accepts_dir_fd,
        stat_accepts_follow_symlinks=stat_accepts_follow_symlinks,
        has_o_directory=has_o_directory,
        has_o_nofollow=has_o_nofollow,
    )

    required = (
        os_name == "posix",
        scandir_accepts_fd,
        open_accepts_dir_fd,
        stat_accepts_dir_fd,
        stat_accepts_follow_symlinks,
        has_o_directory,
        has_o_nofollow,
    )
    if all(required):
        return DirectoryHandleBindingCapability(
            status="SUPPORTED_POSIX_PRIMITIVES",
            os_name=os_name,
            scandir_accepts_fd=scandir_accepts_fd,
            open_accepts_dir_fd=open_accepts_dir_fd,
            stat_accepts_dir_fd=stat_accepts_dir_fd,
            stat_accepts_follow_symlinks=stat_accepts_follow_symlinks,
            has_o_directory=has_o_directory,
            has_o_nofollow=has_o_nofollow,
            boundary=(
                "The runtime exposes the primitives needed for a held-directory-descriptor source "
                "implementation, including no-follow descriptor-relative name revalidation. This "
                "does not prove filesystem atomicity, artifact custody, tests, owner integration, "
                "runtime behavior, deployment, or delivery."
            ),
        )

    return DirectoryHandleBindingCapability(
        status="PORTABLE_ATOMIC_BINDING_UNAVAILABLE",
        os_name=os_name,
        scandir_accepts_fd=scandir_accepts_fd,
        open_accepts_dir_fd=open_accepts_dir_fd,
        stat_accepts_dir_fd=stat_accepts_dir_fd,
        stat_accepts_follow_symlinks=stat_accepts_follow_symlinks,
        has_o_directory=has_o_directory,
        has_o_nofollow=has_o_nofollow,
        boundary=(
            "Do not upgrade pathname pre/post revalidation into an atomic-binding claim on this "
            "platform surface. Preserve the existing persistent-drift boundary and require a "
            "platform-specific design before promotion."
        ),
    )


def current_directory_handle_binding_capability() -> DirectoryHandleBindingCapability:
    return classify_directory_handle_binding_capability(
        os_name=os.name,
        scandir_accepts_fd=os.scandir in getattr(os, "supports_fd", set()),
        open_accepts_dir_fd=os.open in getattr(os, "supports_dir_fd", set()),
        stat_accepts_dir_fd=os.stat in getattr(os, "supports_dir_fd", set()),
        stat_accepts_follow_symlinks=os.stat in getattr(os, "supports_follow_symlinks", set()),
        has_o_directory=hasattr(os, "O_DIRECTORY"),
        has_o_nofollow=hasattr(os, "O_NOFOLLOW"),
    )


if __name__ == "__main__":
    import json

    print(json.dumps(current_directory_handle_binding_capability().to_dict(), sort_keys=True))
