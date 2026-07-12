# Netrunner Architecture

Netrunner is a Home Center child capability with two halves:

1. Local browser shell: visible, interruptible, accessible, and safe.
2. Cloud brain: shared playbooks, discoveries, schemas, and trust promotion.

## Local components

### Browser shell

A Playwright desktop Chromium browser-worker is the primary browser surface for v1. Android WebView/Chrome remains useful for visible manual lanes, but Playwright is the first-class automation and learning runtime. Playwright does not run inside Android/Termux Node; on Android phones, Home Center runs it through Debian/proot with Debian-native `/usr/bin/node` and `/usr/bin/chromium`. Desktop/cloud workers are fallback capacity, not the proof target for on-device operation.

Responsibilities:

- Load pages.
- Provide visible browser area beside or above chat.
- Expose page state to the observer.
- Accept safe commands from the action executor.

### Accessibility overlay

Responsibilities:

- Focus spotlight.
- Magnifier region.
- High contrast transforms.
- Large target mode.
- Element Command Mode on long press.
- Read focused element.
- Freeze-and-confirm mode for risky actions.

### DOM observer

Responsibilities:

- Extract visible text.
- Extract landmarks, headings, buttons, inputs, links, labels, forms, and focused element.
- Associate clicked/touched coordinates with DOM candidates.
- Capture modal/overlay candidates.
- Redact sensitive values before writing episode logs.

### Episode recorder

Records human-driven sessions as training data.

An episode is not automatically trusted. It is raw evidence.

### Action executor

Executes constrained local actions:

- Scroll.
- Focus.
- Click only after policy allows.
- Type only into selected fields.
- Apply temporary CSS/DOM user overrides.
- Undo temporary overrides.

### Voice engine

ElevenLabs Brian hosted read aloud.

API keys must be entered by the user through Home Center settings and stored in Android Keystore or cloud Secret Manager. Keys must never enter repository files, logs, prompt memory, or shared discovery data.

## Cloud components

### Discovery store

Stores observed facts from episodes.

Discovery states:

1. observed
2. candidate
3. tested
4. trusted
5. deprecated

### Site playbooks

Site-specific knowledge:

- navigation paths
- recurring modal patterns
- checkout quirks
- hidden totals
- accessibility repairs
- common failure modes

### Task playbooks

Task-specific knowledge independent of site:

- compare products
- fill a form
- download invoice
- cancel subscription
- find return policy
- manage appointment

### Safety policies

Shared rules for risky tasks.

Never allow global behavior to self-modify directly from one session. Use promote-through-evidence, not mutation-by-vibes.

## Recommended first implementation path

1. Build and validate the `browser-worker/` Playwright desktop Chromium runtime on device through Debian/proot.
2. Expose browser session, action, episode, discovery, and promotion operations through Command Center.
3. Record a redacted browser episode for every invocation before any final answer.
4. Add Netrunner UI affordances for narration, focus, magnifier, resume, and stop.
5. Use Android Shizuku/Chrome only as a device fallback or manual subframe lane.
6. Promote discoveries to trusted playbooks only after repeat evidence or explicit approval.
