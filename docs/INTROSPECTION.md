# She-Raw Introspection

She-Raw introspection does not claim hidden chain-of-thought access.

It may inspect only:

- original request fields
- retrieved evidence IDs
- stored response
- user correction
- later validation evidence when present

The introspection output names the original goal as understood, actual goal, mismatch, failed assumption, ignored evidence, what should have happened, proposed behavioral update, proposed scope, confidence, and whether confirmation is required.

## Causal Reconstruction

Introspection must reconstruct the visible failure chain when the stored evidence supports it:

```text
request -> route -> retrieval ranking -> stored response -> user correction -> behavioral update
```

If a retrieved case dominates the answer and pulls She-Raw away from the requested task layer, introspection must name this as retrieval dominance. It should identify contaminating case IDs, response terms that came from retrieval, the requested task terms that were under-served, and the durable rule needed to prevent the same pattern.

Example: if the user asks for connector capability/schema status and a humane-guardrail case hijacks the response, introspection should say the response followed the retrieved case instead of the connector-capability task. It should not merely say the desired behavior was not mapped into a durable rule.
