# She-Raw Executive Control

She-Raw retrieval and learned rules support answers. They do not own answers.

Answer precedence is:

1. explicit request
2. response contract
3. command state
4. grounded runtime evidence
5. corpus evidence

Corpus cases are evidence records. A retrieved case can explain, cite, or warn, but it must not supply the main thesis when the request has a clearer contract such as operational health, connector visibility, brain invocation, or introspection.

Learned rules are scoped. Project-scoped rules apply only inside their project, pattern-scoped rules apply only when the pattern is detected, duplicate rule text collapses to one rule, and zero-validation rules are candidates only. `lastUsedAtMs` is not validation.

Brain-scoped retrieval is bounded to the selected brain's corpus unless an explicitly relevant supporting case is proven by the route. Bikini Bottom must not drag Humane Guardrails or wrong-layer cases into evidence just because they are strong corpus records.

Introspection requires a stored invocation target. It must recover the request, route, retrieval set, response, correction, and validation plan before making causal claims. It may identify contaminating evidence only when retrieved evidence controlled the response against the request contract.

SQLite is not part of this repair. Markdown remains canonical corpus/doctrine; Firebase/Firestore remains the current runtime substrate. A future database migration must preserve this precedence rule instead of turning retrieval into the executive layer.
