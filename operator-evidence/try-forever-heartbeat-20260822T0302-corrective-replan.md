# TRY FOREVER corrective replan — 2026-08-22 03:02 CT

## Review scar
The first v5 custody implementation bounded the number of matching patch/delta candidates but still used `Path.glob(...)`. That bounds stored candidate paths, **not** directory traversal work: a directory with arbitrarily many non-matching entries can still be scanned before candidate max+1 is observed.

The first v5 source commit therefore remains useful but incomplete. Do not describe it as a complete finite discovery throat.

## Correction before completion
- Replace glob-driven discovery with one bounded, non-recursive directory scan.
- Count **all directory entries**, not only matching artifacts.
- Keep a separate matching-artifact candidate budget; either max+1 must fail the whole inventory closed with zero partial promotion authority.
- Preserve deterministic sorting only after bounded admission.
- Keep per-artifact finite regular-file custody unchanged and reused from the existing artifact observation organ.
- Add hostile source fixtures where unrelated directory junk exhausts traversal budget before any matching artifact can earn authority.

## Claims deliberately not made
This is not recursive filesystem atomicity, repository-root custody, runtime execution, TESTED evidence, or phone/P0 delivery. The P0/phone firewalls remain untouched.
