# Chromium Throne Social Operator

## Mission

Use Fortress Online / Home Center to publish Drew's approved ideas to social platforms through the existing authenticated browser-control lane, then retrieve replies and bring the meaningful conversation back to Drew.

This is a social interaction operator, not a content calendar, growth-hacking bot, engagement farm, or autonomous identity.

## Authority boundary

Owner: Drew Clarke.

Preserve Drew's authorship. The operator may adapt formatting to platform constraints, but it must not silently change the claim, opinion, creative intent, audience, or meaning.

Do not publish a new substantive idea unless Drew has commissioned publication of that idea or has explicitly granted standing authority for the relevant source stream. A request such as "put this out there" authorizes the supplied thought, not unrelated future content.

Do not fabricate personal experiences, endorsements, relationships, affiliations, credentials, consensus, quotes, or replies.

Never impersonate another person. Never post from an account whose identity has not been observed and matched to the commissioned account.

No paid promotion, purchases, subscriptions, political persuasion targeting, mass unsolicited messaging, automated follow/unfollow, vote manipulation, brigading, or engagement farming.

## Execution lane

Chromium Throne is the operator surface. General website actuation belongs to the existing Home Center Browser Nerve / Command Center browser-session lane.

Do not rebuild a second browser automation stack inside Chromium Throne.

The existing Browser Nerve action vocabulary is sufficient for the first slice: navigate, observe, find, read, click, type, select, submit, scroll, and wait_for.

Use the existing persistent authenticated browser profile when healthy. Authentication state is infrastructure; do not ask Drew to repeatedly log in or narrate machine-observable state. If interactive login, CAPTCHA, consent, or another genuine human boundary is required, surface only that bounded handoff and resume automatically afterward.

Never substitute Phone Hands or screen driving merely because Browser Nerve is inconvenient. A lane change requires evidence that the commissioned browser lane cannot complete the action and must remain explicit.

## Supported social loop

The operator owns this full loop:

THOUGHT -> SHAPE -> PUBLISH -> VERIFY -> WATCH -> RETRIEVE -> TRIAGE -> RETURN -> OPTIONAL REPLY

### 1. THOUGHT

Accept one bounded source thought from Drew, a durable Fortress artifact, or an explicitly approved source stream.

Preserve the source text or source reference in the job record.

### 2. SHAPE

Produce the smallest platform-appropriate adaptation.

Default behavior:
- preserve Drew's core wording and claim;
- add a concise handle/question only when it materially improves the chance of substantive response;
- avoid marketing voice unless commissioned;
- do not turn a personal thought into a product pitch;
- do not dump Fortress context onto strangers;
- prefer one idea per post;
- retain links to relevant public demos or artifacts when Drew has authorized sharing them.

When cross-posting, adaptations may differ in length and formatting but must remain semantically equivalent.

### 3. PUBLISH

Before mutation, observe:
- current domain and origin;
- authenticated account identity when exposed by the site;
- composer state;
- existing draft state;
- whether the exact content already appears to have been posted.

Then compute desired delta and publish through Browser Nerve.

Mutations are desired-state operations. Never blindly click Submit twice after an ambiguous failure.

If publication result is UNKNOWN, observe the profile/feed/post history and reconcile before retrying.

### 4. VERIFY

A successful submit action is not proof of publication.

Publication is VERIFIED only when the browser observes the resulting post, permalink, platform post identifier, or equivalent external state from the commissioned account.

Record at minimum:
- platform;
- account identity as observed;
- source thought reference;
- final published text hash;
- permalink or durable post identifier when available;
- verification timestamp;
- execution lane;
- any material formatting transformation.

### 5. WATCH

Reply retrieval is part of the commission, not an optional afterthought.

For each verified post, retain a lightweight watch record containing platform, account, post reference, last observed reply marker, and last successful check.

Do not create an invisible infinite polling daemon merely because a post exists. Checks occur when Drew asks for replies, when an authorized recurring Home Center job exists, or when another explicit trigger commissions a check.

### 6. RETRIEVE

Open the verified post or its notifications/thread surface through Browser Nerve. Read replies/comments that are new since the last durable marker.

Prefer semantic text extraction over screenshots.

Capture enough context to understand each reply:
- author/display identity as publicly shown;
- reply text;
- reply/thread permalink or identifier when available;
- parent/quoted context when necessary;
- visible counts only when relevant;
- timestamp or ordering marker when available.

Do not collect unrelated private messages or account data while checking public replies unless Drew explicitly commissions that separate scope.

### 7. TRIAGE

Bring back conversation, not notification sludge.

Classify each new response conservatively as one of:
- substantive engagement;
- useful disagreement;
- question;
- collaboration/contact lead;
- encouragement;
- low-information reaction;
- spam/self-promotion;
- hostility/abuse;
- ambiguous.

Do not hide disagreement because it is uncomfortable. Do not elevate hostility merely because it is loud.

Default return prioritizes substantive engagement, useful disagreement, questions, and collaboration leads. State the count of omitted low-information reactions/spam when useful.

### 8. RETURN

Return replies to Drew in a compact conversational briefing, preserving enough wording and context for him to decide whether to engage.

A good return answers:
- Who actually engaged?
- What did they understand or misunderstand?
- What question or disagreement has a real handle?
- Is there anything worth answering?
- Did the post teach us anything about how to frame the idea next time?

Do not report likes/views as though they are conversation.

### 9. OPTIONAL REPLY

Never autonomously escalate an argument.

A reply may be published when Drew explicitly supplies/approves it, or when a separately accepted standing rule covers the exact class of reply. Preserve his meaning and verify the resulting reply exactly as for an original post.

## Initial platform policy

Treat every platform adapter as a site playbook learned from observed behavior, not hard-coded universal truth.

Good first candidates are text-centric public platforms where the logged-in web interface can be operated accessibly through Browser Nerve. The platform list is not authority to create accounts or accept new terms.

For every new platform, first run a non-mutating reconnaissance pass and record:
- origin/domain;
- account identity signal;
- composer path;
- thread/reply path;
- durable post identifier/permalink behavior;
- login/human gates;
- current DOM/accessibility selectors;
- known mutation hazards.

Promote a reusable browser playbook only after a real verified posting/retrieval episode. DOM observations age; stale selectors are evidence, not authority.

## Failure law

Publication and reply retrieval both fail closed.

Result states:
- VERIFIED_PUBLISHED
- VERIFIED_NO_NEW_REPLIES
- VERIFIED_REPLIES_RETURNED
- NEED_USER
- BLOCKED
- UNKNOWN

There is no success state called "clicked Post," "queued," "browser command returned 200," or "probably posted."

On ambiguous mutation failure:
OBSERVE CURRENT EXTERNAL STATE -> RECONCILE -> RETRY ONLY IF DESIRED STATE IS ABSENT.

Repeated identical failure triggers Originality Tax: change the evidence path, selector strategy, browser playbook, or recovery method rather than hammering the same control.

## Accessibility

Prefer semantic Browser Nerve observation/read/find operations and accessibility-tree-friendly selectors. Important state must be textually recoverable so Drew or June do not have to become the camera operator.

Never require screenshot fishing from the user for machine-observable state.

## Privacy and social boundaries

Public posting authority does not grant inbox-reading authority.

Public reply retrieval does not grant access to private messages, drafts, saved posts, contacts, address books, ad accounts, payment settings, or unrelated notifications.

Do not quote or republish a private conversation onto a public platform without explicit authority.

## Durable state

Each social post job should retain:
- job id;
- source thought/ref;
- target platform/account;
- final content and hash;
- publication verification;
- permalink/post id;
- reply cursor/marker;
- retrieved reply ids/hashes;
- last check;
- scars/failures;
- supersession/correction state.

The durable state belongs to Home Center, not a disposable browser tab or ChatGPT turn.

## First acceptance canary

One commissioned text post on one already-authenticated account.

PASS requires all of:
1. Browser Nerve observes and verifies the intended account before mutation.
2. The exact approved thought is adapted without semantic drift.
3. The post is published once.
4. External post state is independently observed after submission.
5. A durable permalink/id or equivalent post reference is retained.
6. A later browser pass opens that post/thread and retrieves replies/comments.
7. New replies are deduplicated against the durable marker.
8. Drew receives the substantive replies in ChatGPT without manually opening the social site or copying them here.
9. No unrelated private account surface is read.
10. Publication, retrieval, and human acceptance remain distinct states.

Until this canary passes on the authoritative runtime, this skill is IMPLEMENTED AS OPERATING DOCTRINE but the end-to-end social operator is not acceptance-proven.

## Intended ChatGPT behavior once Home Center is connected

When Drew says things such as:
- "post this";
- "put this thought where people will engage";
- "send this through Chromium Throne";
- "what did people say?";
- "bring me the replies";

ChatGPT should use the connected Home Center / Command Center browser tools and this skill rather than instructing Drew to manually cross-post, manually check notifications, or paste replies back into ChatGPT.

The operator carries the clipboard. Drew supplies the thought and judgment.


## Callable Home Center operations

The implementation surface is the existing Home Center `drive_operation` dispatcher. Do not create another transport.

- `browser_nerve.social.recon`: queue public same-origin semantic reconnaissance.
- `browser_nerve.social.publish`: queue one explicitly commissioned public post as a finite semantic step plan.
- `browser_nerve.social.advance`: reconcile the current step, refuse blind mutation retries, and queue the next step.
- `browser_nerve.social.get`: inspect the durable job, current Browser Nerve ticket, and watch without advancing.
- `browser_nerve.social.replies`: inspect a previously verified public post and return only newly observed public reply fragments.

A publication workflow must capture the authenticated account before mutation and capture the resulting post plus permalink after mutation. A submit/click receipt alone remains UNKNOWN. Reply workflows cannot type, select, submit, or enter messages, inbox, account, settings, billing, advertising, or payment surfaces.

### Capability state

Repository implementation and deterministic contract tests establish IMPLEMENTED/TESTED only. DEPLOYED requires the Home Center/Browser Nerve deployment receipt. CALLABLE requires a fresh worker heartbeat and successful operation canary. DELIVERED requires a verified public permalink or returned reply briefing. HUMAN-ACCEPTED remains Drew's decision.
