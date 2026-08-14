# Rene QA — Overlay recovery visibility

Directive: CONTINUE_REQUIRED

Claim earned by source evidence: the explicit overlay recovery path now requests the existing Android RESTORE action and refuses success unless the state provider reports a visible overlay with control disabled.

Not earned: physical visibility on the primary phone. Repository source is not phone acceptance.

Reachable-state checks required on the primary phone:

1. Existing package + hidden panel -> recovery restores panel visible and leaves control disabled.
2. Existing package + visible panel -> recovery remains visible and leaves control disabled.
3. Missing package -> local build/install/restore produces visible panel with control disabled.
4. Missing Shizuku/rish authority -> exact BLOCKED receipt; no fake success.
5. Hide remains a deliberate local action outside explicit recovery and is not reopened by Vlad's ordinary heartbeat.

Acceptance receipt must include the phone-produced recovery receipt plus human confirmation that the Home Center control is visibly reachable. Venice STOP_ALLOWED remains separate.
