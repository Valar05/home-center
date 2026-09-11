# She-Raw Learning Pipeline

Loop:

```text
invocation
-> response
-> user reaction or correction
-> structured correction
-> introspection
-> scoped behavioral rule
-> later analogous invocation
-> validation
-> corpus candidate
-> optional GitHub pull request
```

A correction is not learned just because it was stored. It becomes behaviorally active only when a scoped rule is applied and later validation shows analogous behavior changed.

## Correction load-path ratchet

A repeated failure must consume prior correction state before it consumes more human explanation.

The durable review memory tracks two recurrence clocks:

- `occurrence`: recurrence of the same stable finding fingerprint;
- `classOccurrence`: recurrence of the broader failure class even when the wording or evidence surface changes.

On the first correction, preserve enough structured precedent that a later analogous failure can be repaired from the smallest new delta. On a repeated failure class, load prior precedent first and apply the emitted `recoveryRule` before asking Drew to restate anything.

The recovery surface is intentionally not fixed. A later correction may arrive as prose, one word, a screenshot, an example, a gesture-description, a behavioral contradiction, a canary, or another available signal. When several surfaces could close the same gap, prefer a different lower-burden route from the one that previously failed. The invariant is the repaired behavior, not repetition of the original explanation ritual.

Ambiguity survives this ratchet. A smaller correction signal is not permission to collapse unresolved meaning. Preserve alternatives unless consequence actually requires resolution.

Compact law:

`same failure class -> more stored precedent -> less repeated human explanation -> changed recovery surface when useful -> behavioral proof`

Promotion to canonical corpus is conservative. Signals include explicit treasure feedback, implementation evidence, repeated success, explicit user confirmation, verified prevention of a failure, or independent review.
