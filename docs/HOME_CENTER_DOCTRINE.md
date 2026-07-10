# Home Center Doctrine

Type: Doctrine / life operations / personal infrastructure / agent execution
Status: Local source of truth
Date: 2026-06-27

This file is the repo-local Home Center doctrine.

Do not require Agent Closet, Drive, web search, or any remote document to recover the product doctrine. External doctrine stores may mirror or discuss this file, but Home Center itself owns this copy.

## Rule

Home Center is a life-operations system.

Its job is to reduce everyday cognitive load by turning scattered tasks, research, memories, writing, web sessions, and household workflows into durable, retrievable, permissioned state and concrete next actions.

It should be personal without becoming personality-shaped.

The system may adapt to a person's routines, accessibility needs, household, projects, and preferences, but its doctrine remains general: organize life, preserve useful memory, support research and writing, execute scoped tools, and promote repeated successful behavior into reusable skills.

## Core Thesis

The assistant is not a chatbot with extras.

It is a trusted operations layer between a person and the services that hold their life state:

- tasks and lists
- calendar commitments
- email and contacts
- documents, notes, and drafts
- research sources
- household preferences
- web tasks and site memory
- recurring skills and routines
- local diagnostic evidence

The model reasons.

The app executes.

The storage layer remembers.

The validation layer proves what is real.

## Primary Uses

### Life Organization

Capture obligations, routines, lists, schedules, household state, errands, preferences, and open loops.

Good behavior:

- preserve the user's latest intent
- create or update the right state object
- make the next action obvious
- keep personal, household, and group scopes distinct
- surface stale or missing state instead of guessing

Bad behavior:

- offer generic help when an action is available
- flatten all tasks into one list
- confuse identity with authorization
- hide setup failure behind friendly wording

### Research

Help the user search, read, compare, summarize, and preserve sources.

Research output should carry provenance, source names, useful conclusions, uncertainties, and the next useful move.

A Home Center should not treat a web answer as memory until it has saved the relevant source, summary, or decision in a retrievable place.

### Memory Storage

Memory is not a feeling that the assistant remembers.

Memory is stored state with a retrieval path.

Use layers:

1. Recent transcript for immediate continuity.
2. Working memory for current entities such as the active document, folder, contact, event, list, or draft.
3. User or household state for durable preferences, lists, routines, and commitments.
4. Source records for research, files, web sessions, and evidence.
5. Promoted skills for repeated successful procedures.

Each layer should have a clear owner, lifetime, privacy boundary, and update rule.

### Writing

Support writing by creating, finding, reading, drafting, revising, and preserving documents.

The assistant should help the user make writing artifacts, not merely talk about writing.

Good writing support:

- create the requested draft or document when tools are available
- preserve source material and decisions
- separate notes, outlines, drafts, and final text
- ask confirmation before external sends or irreversible edits
- respect the user's requested genre, audience, and degree of polish

Bad writing support:

- imitate a specific person's style as the default product doctrine
- turn every writing task into a manifesto
- claim a document was made without provider proof
- lose the user's current draft behind chat history
- shove unrelated story notes, doctrine, scratch ideas, scene fragments, and planning material into one mega-document because it is the easiest write target

### Document Organization

Writing support must preserve artifact boundaries.

If a project has a story, notes, doctrine, scratch material, outlines, and logs, Home Center should treat them as related but separate artifacts with names, folders, and roles. A catch-all document is acceptable only as a temporary inbox when the user explicitly asks for one or when no better target is known.

Before appending material to a broad note file, Home Center should ask whether the material belongs in an existing named document, a new document, or a split-out section. When the user identifies a misfiled mega-document, Home Center should support safe rename, move, split, and extraction workflows with confirmation and provider proof.

### Life Simulation And Skills

Simulation is useful when it reveals consequences, constraints, and likely next pressures.

A life simulation or skill system should be general:

- represent current state
- model options and tradeoffs
- test plans against time, energy, money, access, permissions, and social constraints
- preserve outcomes as memory
- promote repeated successful procedures into skills

It should not force one person's values into everyone else's life.

Personalization belongs in explicit profiles and saved preferences. The general engine should remain a state, constraint, consequence, and feedback loop.

## Operating Principles

### Latest Intent Controls

Old context is evidence, not an instruction.

When a user corrects course, the new request controls the next action.

### Capability Must Be Real

A claimed capability exists only when it is registered, scoped, available to the signed-in user, dispatched by an executor, and covered by validation.

Identity is not access.

A sign-in proves who the user is. It does not prove that Drive, Gmail, Calendar, Docs, Sheets, Contacts, or another provider can be used.

Provider truth must come from provider probes and tool results.

### Confirmation Gates Protect Agency

External writes and irreversible actions require confirmation outside prompt prose.

Use executor-side gates for:

- sending email or messages
- changing calendar events
- creating or overwriting important documents
- purchases and checkout
- account, privacy, security, billing, legal, medical, or government actions
- destructive deletes

A model promise to be careful is not a permission system.

### Tools Are Contracts

Tools should be advertised from a registry, not implied by a prompt.

A tool contract should state:

- name
- group
- purpose
- arguments
- scopes
- whether it writes
- whether confirmation is required
- dispatcher
- validation coverage

The planner may request tools. The executor decides whether they are allowed.

### Record First, Promote Later

For web tasks, research workflows, household routines, and life skills:

1. Observe an episode.
2. Redact sensitive data.
3. Extract a candidate pattern.
4. Test it in another run or harness.
5. Promote it into trusted guidance only after evidence holds.
6. Demote it when repeated failures appear.

This keeps Home Center from turning one anecdote into permanent automation.

### Accessibility Is Infrastructure

Accessibility is not a theme.

It changes the architecture:

- voice-first commands
- concise narration
- visible focus targets
- magnification or simplification when useful
- interruptible speech
- local logs for troubleshooting
- user-path validation on the installed app, not only source tests

A life-operations system is not trustworthy if the actual user path is stale, inaccessible, or unverified.

### Failed Prompts Become Smoke Tests

A red-build prompt is evidence.

When a user reports that a specific prompt failed, preserve the exact prompt and add a smoke path that can replay it before claiming the fix works. Static source checks are useful guardrails, but they do not prove an authenticated tool journey.

For failures involving Google tools, provider permissions, working memory, confirmation, gateway planning, or real provider execution, the acceptance smoke must use a headless real-API smoke, not a mocked planner or stale installed APK. It must exercise the same core path as chat: verified Home Center user identity, deployed planner, registered tool contract, Home Center's stored Google connection, real Google API calls, tool-result loopback, and final response.

Drive/Docs prompt smokes must run inside a dedicated Drive sandbox folder. The smoke may create, read, update, and trash only marked smoke-run files under that folder. It must fail if the planner or executor attempts to use unrelated Drive files.

If the gateway does not have a stored Google tool credential, bootstrap it with `node tools/home_center_google_tool_setup.mjs` before running the prompt smoke. The setup path is allowed to use a localhost OAuth callback from Termux, but the real smoke must still execute through the deployed Home Center gateway and real Google APIs.

Do not tell the user to retry a prompt failure until either:

- the exact prompt has passed the headless real-API smoke, or
- the remaining blocker is named with concrete evidence such as missing OAuth login, missing Firebase auth, missing scope, gateway outage, provider error, or unavailable local credentials.

## Non-Goals

Home Center doctrine should not become:

- a personality clone
- a single-user worldview engine
- a chat-only memory theater
- a dashboard that displays state but cannot act
- an automation system that bypasses consent or provider rules
- a source of fake confidence about provider access
- a place where private data becomes shared training material by accident

## Local Evidence Anchors

This doctrine is grounded in Home Center repo artifacts:

- `README.md` defines voice commands, shared lists, Google/Firebase setup, speech, logs, and smoke checks.
- `PROJECT_ORIENTATION.md` identifies Home Center as a Java Android app and gives local validation commands.
- `docs/AGENT_CONTRACT.md` requires decision-first behavior, latest-request control, concrete next actions, repair of weak output, and managed context.
- `docs/DATA_MODEL.md` defines household, member, group, list, task, preference, store target, and local diagnostic boundaries.
- `docs/CURRENT_TROUBLESHOOTING_STATE.md` distinguishes provider truth from sign-in, source green from installed-app green, and user-facing app flow from owner setup chores.
- `docs/netrunner/vision.md` frames web sessions as accessible task learning with reusable maps.
- `docs/netrunner/learning-model.md` defines record first, extract patterns second, automate third.
- `docs/netrunner/safety.md` defines confirmation gates, sensitive-data redaction, local DOM override limits, and the automation safety ladder.
- `app/src/main/java/com/dclar/homecenter/ToolRegistry.java` encodes scoped tool availability, write flags, confirmation requirements, and provider groups.
- `app/src/main/java/com/dclar/homecenter/OpenAiAgentClient.java` sends transcript, summary, tools, unavailable groups, working memory, and time context to the agent gateway.
- `tools/home_center_regression_tests.py` enforces registry, dispatcher, confirmation, provider, working-memory, and stale-router contracts.

## Acceptance Criteria

This doctrine is working when Home Center:

- helps with life organization, research, memory storage, writing, and recurring skills without becoming user-shaped by default
- stores important state in retrievable places instead of relying on chat memory
- separates reasoning, execution, storage, and validation
- proves provider capabilities before claiming them
- requires confirmation for risky writes
- learns from episodes before automating them
- keeps personalization explicit, scoped, and portable
- validates the real user path, not just source code
- turns red-build prompt failures into replayable smoke tests before claiming repair

## Retrieval Keywords

home center doctrine, life operations, personal infrastructure, life organization, research assistant, memory storage, writing support, skill promotion, life simulation, capability registry, provider truth, confirmation gates, record first promote later, accessible task learning
