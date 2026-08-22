#!/usr/bin/env python3
"""Capability gate for stronger directory-handle custody.

The portable pathname bracket used by TRY FOREVER correctly refuses to claim atomic binding. This
helper answers a narrower question: does the current Python/OS surface expose the POSIX-style
primitives needed to *attempt* one held-directory-descriptor implementation without silently
pretending every platform supports it?

`SUPPORTED_POSIX_PRIMITIVES` is not itself an atomicity proof. Filesystem semantics, descriptor-
relative artifact reads, replacement/identity-reuse behavior, execution tests, and owner integration
remain separate gates.
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
    has_o_directory: bool
    has_o_nofollow: bool
    boundary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def classify_directory_handle_binding_capability(
    *,
    os_name: str,
    scandir_accepts_fd: bool,
    open_accepts_dir_fd: bool,
    has_o_directory: bool,
    has_o_nofollow: bool,
) -> DirectoryHandleBindingCapability:
    required = (
        os_name == "posix",
        scandir_accepts_fd,
        open_accepts_dir_fd,
        has_o_directory,
        has_o_nofollow,
    )
    if all(required):
        return DirectoryHandleBindingCapability(
            status="SUPPORTED_POSIX_PRIMITIVES",
            os_name=os_name,
            scandir_accepts_fd=scandir_accepts_fd,
            open_accepts_dir_fd=open_accepts_dir_fd,
            has_o_directory=has_o_directory,
            has_o_nofollow=has_o_nofollow,
            boundary=(
                "The runtime exposes the primitives needed for a held-directory-descriptor source "
                "implementation. This does not prove filesystem atomicity, artifact custody, tests, "
                "owner integration, runtime behavior, deployment, or delivery."
            ),
        )

    return DirectoryHandleBindingCapability(
        status="PORTABLE_ATOMIC_BINDING_UNAVAILABLE",
        os_name=os_name,
        scandir_accepts_fd=scandir_accepts_fd,
        open_accepts_dir_fd=open_accepts_dir_fd,
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
        has_o_directory=hasattr(os, "O_DIRECTORY"),
        has_o_nofollow=hasattr(os, "O_NOFOLLOW"),
    )


if __name__ == "__main__":
    import json

    print(json.dumps(current_directory_handle_binding_capability().to_dict(), sort_keys=True))
