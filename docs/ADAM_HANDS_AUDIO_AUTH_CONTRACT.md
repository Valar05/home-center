# Adam Hands / Audio / Login Authority Contract

## Product center

Adam's overlay is Drew's primary command surface.

Adam may reason, retrieve context, choose, compose, and request finite work. Hands executes exact bounded jobs and never becomes an agent.

## Hands

A Hands job is a finite ordered script with an explicit target, allowed operation vocabulary, runtime bound, TTL, signature, mechanical expectations, and receipt.

No screenshot-driven guess/check loop. Screenshots may be captured as artifacts, but interpretation happens before a new separately authorized job is authored.

Transport preference for remote targets is SSH, WLAN, then Computer Hands. Transport fallback may not change the job.

The phone-local fast path must pass through the existing Adam overlay control gate. The visible local control toggle remains authoritative.

## Contextual Adam

Natural-language requests such as `find me something to watch` are Adam intents, not Hands operations.

Adam may gather current conversation context, durable Drive-synced context, installed capability/app inventory, and current external availability where needed. Adam then chooses a concrete result and emits a finite Hands job such as an explicit Android VIEW URI.

Direct `hands ...` input bypasses inference and compiles immediately to the finite executor contract.

## Audio is first-class Adam sensing

Adam maintains a bounded moving microphone ring buffer when listening is enabled.

- raw ambient audio is rotating scratch, not an archive;
- old ring chunks are deleted automatically;
- deterministic features are extracted first: RMS, peak, zero crossings, coarse spectral bands, transient shape, and pulse;
- interesting events may promote one bounded clip plus features;
- each promoted event receives an `adam-sound-graph-v1` modular reconstruction graph;
- graphs are reusable synthesis recipes, not semantic truth claims;
- speech recognition is not required for the audio-analysis organ;
- modeled interpretation may enrich an already-isolated event later, but does not control capture or retention.

Goal: learn useful sound atoms and reproduce/combine them through modular graph nodes rather than accumulating recordings.

## Login and autofill authority

Credentials are a user-granted capability, not forbidden terrain.

Adam may complete a login without Drew physically typing credentials only when Drew explicitly authorizes that login/site/job.

The intended browser lane is a visible dedicated Adam browser profile that may contain Drew-authorized browser/password-manager/autofill state. This avoids copying credentials into Home Center and respects current Chromium restrictions on remote debugging the default browser data directory.

A login lease must be narrow:

- explicit origin/site;
- explicit user authorization;
- short expiry;
- single login job or bounded attempt count;
- visible browser only;
- no credential extraction.

Adam/Browser Nerve may focus fields, invoke normal browser autofill/password-manager behavior, submit the form, and mechanically verify login-state change. It must not read, return, copy, persist, or log password values, session cookies, password-manager databases, recovery codes, or equivalent secrets.

Browser observations and receipts must redact password-field values and report only booleans such as `credentialFieldNonEmpty`, `submitted`, and post-login URL/state changes.

If a site requires a genuinely non-automatable human challenge, report that exact boundary. Do not weaken the credential contract or invent secret-export plumbing.

## Capability states

Keep requested, implemented, tested, deployed, callable, delivered, and accepted distinct. Repository source is never device acceptance evidence.
