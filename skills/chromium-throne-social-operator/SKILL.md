---
name: chromium-throne-social-operator
description: Publish Drew's approved ideas and retrieve public replies through the commissioned Chromium Throne lane. Use for "post this," "put this where people will engage," "send this through Chromium Throne," "what did people say?," social status checks, and reply retrieval. Keep Chromium Throne, Browser Nerve, Computer Hands, Home Center, and THECAULDRON distinct.
---

# Chromium Throne Social Operator

## Mission

Use Fortress Online, Home Center durable state, and the commissioned Chromium Throne browser lane to publish Drew's approved ideas to social platforms, verify the resulting public state, retrieve new replies, and bring meaningful conversation back to Drew.

This is a social interaction operator. It is not a content calendar, growth-hacking bot, engagement farm, autonomous identity, or excuse to make Drew become the clipboard.

## Required companion skill

Load and obey:

`skills/chromium-throne-runtime-identity/SKILL.md`

Chromium Throne, Browser Nerve, Computer Hands, Home Center, and THECAULDRON are separate organs. A status result from one cannot silently stand in for another.

## Authority boundary

Owner: Drew Clarke.

Preserve Drew's authorship. The operator may adapt formatting to platform constraints, but it must not silently change the claim, opinion, creative intent, audience, owner, or meaning.

Do not publish a new substantive idea unless Drew commissioned publication of that idea or explicitly granted standing authority for the exact source stream. "Put this out there" authorizes the supplied thought, not unrelated future content.

Do not fabricate personal experiences, endorsements, relationships, affiliations, credentials, consensus, quotes, or replies.

Never impersonate another person. Never post from an account whose identity has not been observed and matched to the commissioned account.

No paid promotion, purchases, subscriptions, political persuasion targeting, mass unsolicited messaging, automated follow/unfollow, vote manipulation, brigading, or engagement farming.

## Execution lane

The commissioned browser body is Chromium Throne.

Chromium Throne is the dedicated authenticated Chrome/Edge profile, extension, and local relay on THECAULDRON, normally rooted at:

`http://127.0.0.1:9234/v1/throne`

Home Center is the durable orchestration, state, idempotency, and receipt plane. Social-site actuation must occur through a bounded Chromium Throne social adapter operating in the dedicated Throne profile or through a browser action surface explicitly exposed as part of Chromium Throne.

Browser Nerve and Computer Hands are separate adjacent bodies. They are not implicit prerequisites, health proxies, or fallback lanes. Do not substitute either because it is convenient. A lane change requires Drew's explicit approval.

The existing semantic vocabulary remains useful inside a Throne adapter:

- navigate;
- observe;
- find;
- read;
- click;
- type;
- select;
- submit;
- scroll;
- wait_for.

Reusing this vocabulary does not transfer the commission to Browser Nerve.

Use the existing persistent authenticated Throne profile when healthy. Authentication state is infrastructure; do not ask Drew to repeatedly log in or narrate machine-observable state. If interactive login, CAPTCHA, consent, or another genuine human boundary is required, surface only that bounded handoff and resume automatically afterward.

Do not rebuild an unrelated browser stack. Extend the existing Throne host, extension, profile, and relay with the smallest bounded social adapter that satisfies the commission.

If the connected runtime exposes ChatGPT worker-tab transport but no social adapter, report `SOCIAL_ADAPTER_NOT_IMPLEMENTED`. Do not report Chromium Throne offline and do not silently route through Browser Nerve.

## Status and reorientation

In a conversation already about Chromium Throne or social posting through it, "check desktop again" means check Chromium Throne.

Use Throne-specific evidence:

- relay status;
- extension or worker-tab heartbeats;
- command and completion events;
- dedicated profile/process/persistence state;
- current social-adapter state;
- same-day Throne receipts.

Do not answer with `browser_nerve.worker.status` or `computer_hands.worker.status` unless Drew explicitly asks about that organ.

Every status report must name:

```text
ORGAN:
EVIDENCE SOURCE:
OBSERVED AT:
OBSERVATION:
PROVES:
DOES NOT PROVE:
FRESHNESS:
```

If the current ChatGPT surface cannot inspect Throne directly, return `THRONE_STATUS_UNAVAILABLE_FROM_THIS_SURFACE`. That is a visibility boundary, not an offline verdict.

## Supported social loop

The operator owns this full loop:

`THOUGHT -> SHAPE -> PUBLISH -> VERIFY -> WATCH -> RETRIEVE -> TRIAGE -> RETURN -> OPTIONAL REPLY`

### 1. THOUGHT

Accept one bounded source thought from Drew, a durable Fortress artifact, or an explicitly approved source stream.

Preserve the source text or source reference in the job record.

### 2. SHAPE

Produce the smallest platform-appropriate adaptation.

Default behavior:

- preserve Drew's core wording and claim;
- add a concise handle or question only when it materially improves substantive response;
- avoid marketing voice unless commissioned;
- do not turn a personal thought into a product pitch;
- do not dump Fortress context onto strangers;
- prefer one idea per post;
- retain links to relevant public demos or artifacts when Drew authorized sharing them.

When cross-posting, adaptations may differ in length and formatting but must remain semantically equivalent.

### 3. PUBLISH

Before mutation, the Chromium Throne social adapter must observe:

- current domain and origin;
- authenticated account identity when exposed by the site;
- composer state;
- existing draft state;
- whether the exact content already appears to have been posted.

Then compute the desired delta and publish through Chromium Throne.

Mutations are desired-state operations. Never blindly click Submit twice after an ambiguous failure.

If publication result is `UNKNOWN`, observe the profile, feed, thread, or post history and reconcile before retrying.

### 4. VERIFY

A successful submit action is not proof of publication.

Publication is `VERIFIED_PUBLISHED` only when Chromium Throne observes the resulting post, permalink, platform post identifier, or equivalent external state from the commissioned account.

Record at minimum:

- platform;
- account identity as observed;
- source thought reference;
- final published text and hash;
- permalink or durable post identifier when available;
- verification timestamp;
- execution lane;
- adapter/version;
- any material formatting transformation.

### 5. WATCH

Reply retrieval is part of the commission, not an optional afterthought.

For each verified post, retain a lightweight Home Center watch record containing platform, account, post reference, last observed reply marker, and last successful check.

Do not create an invisible infinite polling daemon merely because a post exists. Checks occur when Drew asks for replies, when an authorized recurring Home Center job exists, or when another explicit trigger commissions a check.

### 6. RETRIEVE

Open the verified post or its public notifications/thread surface through Chromium Throne. Read replies or comments that are new since the last durable marker.

Prefer semantic text extraction over screenshots.

Capture enough context to understand each reply:

- author or display identity as publicly shown;
- reply text;
- reply/thread permalink or identifier when available;
- parent or quoted context when necessary;
- visible counts only when relevant;
- timestamp or ordering marker when available.

Do not collect unrelated private messages or account data while checking public replies unless Drew explicitly commissions that separate scope.

### 7. TRIAGE

Bring back conversation, not notification sludge.

Classify each new response conservatively as one of:

- substantive engagement;
- useful disagreement;
- question;
- collaboration or contact lead;
- encouragement;
- low-information reaction;
- spam or self-promotion;
- hostility or abuse;
- ambiguous.

Do not hide disagreement because it is uncomfortable. Do not elevate hostility merely because it is loud.

Default return prioritizes substantive engagement, useful disagreement, questions, and collaboration leads. State the count of omitted low-information reactions or spam when useful.

### 8. RETURN

Return replies to Drew in a compact conversational briefing, preserving enough wording and context for him to decide whether to engage.

A good return answers:

- Who actually engaged?
- What did they understand or misunderstand?
- What question or disagreement has a real handle?
- Is there anything worth answering?
- Did the post teach us anything about framing the idea next time?

Do not report likes or views as though they are conversation.

### 9. OPTIONAL REPLY

Never autonomously escalate an argument.

A reply may be published when Drew explicitly supplies or approves it, or when a separately accepted standing rule covers the exact class of reply. Preserve his meaning and verify the resulting reply exactly as for an original post.

## Initial platform policy

Treat every platform adapter as a site playbook learned from observed behavior, not hard-coded universal truth.

Good first candidates are text-centric public platforms whose logged-in web interface can be operated accessibly through the Chromium Throne profile. The platform list is not authority to create accounts or accept new terms.

For every new platform, first run a non-mutating reconnaissance pass and record:

- origin and domain;
- account identity signal;
- composer path;
- thread and reply path;
- durable post identifier or permalink behavior;
- login and human gates;
- current DOM or accessibility selectors;
- known mutation hazards.

Promote a reusable Throne playbook only after a real verified posting and retrieval episode. DOM observations age; stale selectors are evidence, not authority.

## Failure law

Publication and reply retrieval fail closed.

Result states:

- `VERIFIED_PUBLISHED`;
- `VERIFIED_NO_NEW_REPLIES`;
- `VERIFIED_REPLIES_RETURNED`;
- `THRONE_STATUS_UNAVAILABLE_FROM_THIS_SURFACE`;
- `SOCIAL_ADAPTER_NOT_IMPLEMENTED`;
- `NEED_USER`;
- `BLOCKED`;
- `UNKNOWN`.

There is no success state called "clicked Post," "queued," "browser command returned 200," "worker is probably online," or "probably posted."

On ambiguous mutation failure:

`OBSERVE CURRENT EXTERNAL STATE -> RECONCILE -> RETRY ONLY IF DESIRED STATE IS ABSENT`

Repeated identical failure triggers Originality Tax: change the evidence path, selector strategy, Throne playbook, or recovery method rather than hammering the same control.

## Accessibility

Prefer semantic Chromium Throne observation, read, and find operations and accessibility-tree-friendly selectors. Important state must be textually recoverable so Drew or June do not have to become the camera operator.

Never require screenshot fishing from the user for machine-observable state.

## Privacy and social boundaries

Public posting authority does not grant inbox-reading authority.

Public reply retrieval does not grant access to private messages, drafts, saved posts, contacts, address books, ad accounts, payment settings, or unrelated notifications.

Do not quote or republish a private conversation onto a public platform without explicit authority.

## Durable state

Each social post job should retain:

- job id;
- source thought or reference;
- target platform and account;
- final content and hash;
- publication verification;
- permalink or post id;
- reply cursor or marker;
- retrieved reply ids or hashes;
- last check;
- scars and failures;
- supersession or correction state;
- Throne adapter and runtime identity.

The durable state belongs to Home Center, not a disposable browser tab or ChatGPT turn.

## First acceptance canary

One commissioned text post on one already-authenticated account.

PASS requires all of:

1. Chromium Throne's identity, profile, relay, and social adapter are observed as the actual execution body.
2. The commissioned account identity is observed before mutation.
3. The exact approved thought is adapted without semantic drift.
4. The post is published exactly once.
5. External post state is independently observed after submission.
6. A durable permalink, id, or equivalent post reference is retained.
7. A later Chromium Throne pass opens that post or thread and retrieves replies or comments.
8. New replies are deduplicated against the durable marker.
9. Drew receives substantive replies in ChatGPT without manually opening the social site or copying them here.
10. No unrelated private account surface is read.
11. Publication, retrieval, delivery, and human acceptance remain distinct states.
12. Browser Nerve or Computer Hands were not silently substituted.

Until this canary passes on the authoritative runtime, this skill is operating doctrine. End-to-end social posting and reply return remain unaccepted capability.

## Intended ChatGPT behavior

When Drew says things such as:

- "post this";
- "put this thought where people will engage";
- "send this through Chromium Throne";
- "check desktop again";
- "what is the swarm doing?";
- "what did people say?";
- "bring me the replies";

ChatGPT should load this skill and the runtime-identity companion, use connected Home Center and Chromium Throne-specific operations, and carry the clipboard.

It must not instruct Drew to manually cross-post, manually check notifications, paste replies back into ChatGPT, or accept an adjacent browser body without approval.

## Skill synchronization

Canonical source:

`Valar05/home-center/skills/chromium-throne-social-operator/SKILL.md`

Whenever this skill changes:

1. update the canonical repository file;
2. regenerate the ChatGPT skill package;
3. update the ChatGPT Library copy;
4. update the Drive `Remote Skills/chromium-throne-social-operator` mirror;
5. record source commit and SHA-256 hashes;
6. read back each persistent surface.

A remote mirror is not current merely because it has the same title. Exact content and provenance decide freshness.
