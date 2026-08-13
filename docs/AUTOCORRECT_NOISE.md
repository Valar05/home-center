# User-scoped autocorrect-noise learning

Status: implemented on a feature branch; not deployed or callable until the branch is merged and the Home Center MCP runtime is deployed.

## Outcome

Home Center learns recurring correction patterns for the authenticated user without turning one user's dialect into global truth.

Evidence states:

- Candidate: one observation. Preserve the original.
- Good: two consistent observations with at least 67 percent dominance. Suggest only.
- Gold: explicit confirmation, or at least three consistent observations across two contexts with at least 85 percent dominance. May apply only when the caller explicitly requests gold application.
- Rejected: rejection evidence exceeds confirmations. Preserve the original.

## Stable operation surface

The existing drive_operation dispatcher advertises:

- autocorrect_noise.observe
- autocorrect_noise.resolve
- autocorrect_noise.feedback
- autocorrect_noise.profile

No connector reinstall is required after backend deployment because capabilities advertises operations from the runtime registry.

## Scope and privacy

- Scope is derived from the authenticated Home Center uid or email. No operation accepts a user ID.
- Firestore stores the noisy term, intended term, counters, timestamps, and hashed context fingerprints.
- Raw messages and context excerpts are not stored.
- Patterns live beneath autocorrectNoiseUsers/{scopeHash}/patterns/{patternHash}.
- Idempotency receipts live in autocorrectNoiseAudit/{scopeAndRequestHash}.
- Candidate and context growth is bounded.
- Feedback verdict forget removes one pattern while retaining only a hashed audit identity.

## Agency and source fidelity

Resolve always returns originalText.

Good is advisory and never auto-applies.

Gold applies only when the caller sets applyGold=true, the winner is unique, the user has not protected it, and the term is not system-shaped or adjacent to identifier punctuation. The user may explicitly review and release that last brake with allow_auto.

Dotted tokens, URLs, paths, handles, identifiers, conflicts, and protected vocabulary fail closed. Ordinary typo cleanup therefore cannot silently mutate commands, filenames, coined terms, or literal capability names.

## Typical flow

1. Observe a correction with noisy, intended, contextId, explicit, and requestId.
2. Resolve new text with text and optional applyGold.
3. Inspect the learned profile.
4. Use feedback with confirm, reject, protect, unprotect, allow_auto, or forget.

## Capability boundary

Repository implementation and source tests do not prove deployment, callable state, delivery, or acceptance. After merge, deploy the exact accepted SHA and verify registry advertisement, cross-user isolation, candidate-to-good-to-gold progression, good-tier non-application, protected-token preservation, idempotent retries, feedback, and Firestore readback.
